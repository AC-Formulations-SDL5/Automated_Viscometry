"""
Backfill per-cell calibration JSON from a calibration CSV export.

Hitpoint preference (matches runtime resolve_calibration_rough_z):
1. Classic: LAST False in descent order followed by 3 True Z-levels
2. Vote-hit recovery: last clean Z before the first True (early-stop runs)
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from viscometry.calibration.store import save_calibration, update_calibration_for_cells
from viscometry.measurement.hitpoint import (
    extract_hitpoint_from_sequence,
    extract_vote_last_clean_from_sequence,
)


def _parse_rows(csv_path: Path) -> List[dict]:
    """
    Parse CSV rows while ignoring metadata lines before the true header row.
    """
    text = ""
    for enc in ("utf-8", "latin-1"):
        try:
            text = csv_path.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if not text:
        raise ValueError(f"Could not decode CSV file: {csv_path}")

    lines = text.splitlines()
    header_idx = None
    for idx, line in enumerate(lines):
        if line.lower().startswith("row,cell,"):
            header_idx = idx
            break
    if header_idx is None:
        raise ValueError("CSV header not found (expected line starting with 'row,cell,').")

    reader = csv.DictReader(lines[header_idx:])
    rows = list(reader)
    if not rows:
        raise ValueError("No data rows found in CSV.")
    return rows


def _build_hit_sequences(rows: Iterable[dict]) -> Dict[int, List[Tuple[float, bool]]]:
    """
    Group rows by cell and z-height, reducing to a per-z any-hit boolean.
    """
    per_cell_per_z: Dict[int, Dict[float, bool]] = defaultdict(dict)
    for row in rows:
        try:
            cell_id = int(str(row.get("cell", "")).strip())
            z = float(str(row.get("Z_Height_mm", "")).strip())
            hit = str(row.get("Hit_Detected", "")).strip().lower() == "true"
        except Exception:
            continue
        prior = per_cell_per_z[cell_id].get(z, False)
        per_cell_per_z[cell_id][z] = prior or hit

    sequences: Dict[int, List[Tuple[float, bool]]] = {}
    for cell_id, z_map in per_cell_per_z.items():
        sequences[cell_id] = sorted(z_map.items(), key=lambda item: item[0], reverse=True)
    return sequences


def _resolve_rough_from_sequence(hit_sequence: List[Tuple[float, bool]]) -> Optional[float]:
    """Classic 3-True pattern, else vote-hit last-clean reconstruction."""
    classic = extract_hitpoint_from_sequence(hit_sequence)
    if classic is not None:
        return float(classic)
    vote_clean = extract_vote_last_clean_from_sequence(hit_sequence)
    if vote_clean is not None:
        return float(vote_clean)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill per-cell calibration JSON from calibration CSV.")
    parser.add_argument("--csv", required=True, help="Path to calibration CSV file.")
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge only computed cells into existing calibration file instead of replacing all cells.",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv).expanduser().resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    rows = _parse_rows(csv_path)
    sequences = _build_hit_sequences(rows)

    calibration_cells: Dict[int, float] = {}
    cells_with_any_hit = 0
    classic_count = 0
    vote_recovery_count = 0
    for cell_id, seq in sorted(sequences.items()):
        if any(is_hit for _, is_hit in seq):
            cells_with_any_hit += 1
        classic = extract_hitpoint_from_sequence(seq)
        rough = _resolve_rough_from_sequence(seq)
        if rough is not None:
            calibration_cells[cell_id] = rough
            if classic is not None:
                classic_count += 1
            else:
                vote_recovery_count += 1

    calibrated_at_local = datetime.now().astimezone().isoformat(timespec="seconds")
    if calibration_cells:
        if args.merge:
            update_calibration_for_cells(calibration_cells, calibrated_at=calibrated_at_local)
        else:
            save_calibration(calibration_cells, calibrated_at=calibrated_at_local)

    mode = "MERGE" if args.merge else "REPLACE"
    print(f"CSV: {csv_path}")
    print(f"Mode: {mode}")
    print(f"Cells present in CSV: {len(sequences)}")
    print(f"Cells with any Hit_Detected=True: {cells_with_any_hit}")
    print(f"Cells via classic (False then 3 True): {classic_count}")
    print(f"Cells via vote-hit last-clean recovery: {vote_recovery_count}")
    print(f"Saved cells: {sorted(calibration_cells.keys())}")
    for cell_id in sorted(calibration_cells):
        print(f"  cell {cell_id}: {calibration_cells[cell_id]:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

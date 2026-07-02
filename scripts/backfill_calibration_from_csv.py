#!/usr/bin/env python3
"""Backfill per-cell calibration JSON from a calibration CSV export.

Reliable hitpoint rule used here matches the runtime extractor:
- A rough hitpoint is the LAST z-level (descent order, higher to lower)
  where Hit_Detected == False and the next 3 z-levels are all True.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from viscometry.calibration.store import save_calibration, update_calibration_for_cells
from viscometry.io.csv_text import find_row_cell_header_index, read_text_lines_with_fallback
from viscometry.measurement.hitpoint import extract_hitpoint_from_sequence


def _parse_rows(csv_path: Path) -> List[dict]:
    """Parse CSV rows while ignoring metadata lines before the true header row."""
    lines, _enc = read_text_lines_with_fallback(csv_path)
    text = "\n".join(lines)
    if not text:
        raise ValueError(f"Could not decode CSV file: {csv_path}")

    try:
        header_idx = find_row_cell_header_index(lines)
    except ValueError as exc:
        raise ValueError("CSV header not found (expected line starting with 'row,cell,').") from exc

    reader = csv.DictReader(lines[header_idx:])
    rows = list(reader)
    if not rows:
        raise ValueError("No data rows found in CSV.")
    return rows


def _build_hit_sequences(rows: Iterable[dict]) -> Dict[int, List[Tuple[float, bool]]]:
    """Group rows by cell and z-height, reducing to a per-z any-hit boolean."""
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
    for cell_id, seq in sorted(sequences.items()):
        if any(is_hit for _, is_hit in seq):
            cells_with_any_hit += 1
        rough = extract_hitpoint_from_sequence(seq)
        if rough is not None:
            calibration_cells[cell_id] = rough

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
    print(f"Cells passing reliable criterion (False then 3 True): {len(calibration_cells)}")
    print(f"Saved cells: {sorted(calibration_cells.keys())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

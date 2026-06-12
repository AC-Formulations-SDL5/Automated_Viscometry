"""
Offline calibration for Discovery Mode bulk-offset RPM model.

CLI-only: fits K_BULK from historical viscosity/RPM/torque tables and writes
calibration_data/discovery_bulk_calibration.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

_MODULE_DIR = Path(__file__).resolve().parent
_DEFAULT_OUTPUT = _MODULE_DIR / "calibration_data" / "discovery_bulk_calibration.json"
_PROJECT_ROOT = _MODULE_DIR.parents[1]


def load_manual_viscosity_rpm_table(csv_path: Path) -> List[Dict[str, float]]:
    """Parse manual viscosity readings CSV into numeric rows."""
    rows: List[Dict[str, float]] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                rpm = float(row["speed_RPM"])
                eta = float(row["Viscosity_cP"])
                torque = float(row["Torque_%"])
            except (KeyError, TypeError, ValueError):
                continue
            if rpm <= 0 or eta <= 0:
                continue
            rows.append(
                {
                    "viscosity_cp": eta,
                    "rpm": rpm,
                    "torque_pct": torque,
                }
            )
    return rows


def fit_k_bulk_from_manual(
    manual_rows: Sequence[Dict[str, float]],
    *,
    torque_min: float = 45.0,
    torque_max: float = 55.0,
    bulk_torque_scale: float = 0.6,
) -> Dict[str, Any]:
    """
    Fit Torque% ≈ K * Viscosity_cP * RPM from near-50% surface readings.

    bulk_torque_scale scales surface K toward bulk-offset target (~30% vs ~50%).
    """
    ks: List[float] = []
    for row in manual_rows:
        t = row["torque_pct"]
        if not (torque_min <= t <= torque_max):
            continue
        eta = row["viscosity_cp"]
        rpm = row["rpm"]
        ks.append(t / (eta * rpm))

    if not ks:
        return {"k_bulk": 1.0e-5, "k_bulk_std": 0.0, "n_points": 0, "fit_method": "fallback"}

    k_surface = statistics.median(ks)
    k_bulk = k_surface * bulk_torque_scale
    k_std = statistics.pstdev(ks) * bulk_torque_scale if len(ks) > 1 else 0.0
    return {
        "k_bulk": float(k_bulk),
        "k_bulk_std": float(k_std),
        "n_points": len(ks),
        "fit_method": "manual_csv_median_surface_scaled",
    }


def unique_valid_rpms(manual_rows: Sequence[Dict[str, float]]) -> List[float]:
    """Collect sorted unique RPMs from manual table."""
    rpms = sorted({round(row["rpm"], 4) for row in manual_rows})
    return rpms


def write_discovery_calibration_json(
    fit_result: Dict[str, Any],
    valid_rpms: Sequence[float],
    output_path: Path,
    *,
    viscosity_table_path: str = "results/Viscosity Readings - Manual.csv",
) -> None:
    """Write discovery_bulk_calibration.json."""
    payload = {
        "version": 1,
        "calibrated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "k_bulk": fit_result.get("k_bulk", 1.0e-5),
        "k_bulk_std": fit_result.get("k_bulk_std", 0.0),
        "target_torque_bulk": 30.0,
        "torque_window_bulk": [25.0, 35.0],
        "hit_point_offset_mm": 0.35,
        "cold_start_rpm": 5.0,
        "valid_rpms": [float(r) for r in valid_rpms],
        "viscosity_table_path": viscosity_table_path,
        "notes": f"Fit: {fit_result.get('fit_method', 'unknown')}, n={fit_result.get('n_points', 0)}",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Fit Discovery Mode K_BULK calibration JSON")
    parser.add_argument(
        "--manual-csv",
        type=Path,
        default=_PROJECT_ROOT / "results" / "Viscosity Readings - Manual.csv",
    )
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    if not args.manual_csv.exists():
        print(f"Manual CSV not found: {args.manual_csv}")
        return 1

    rows = load_manual_viscosity_rpm_table(args.manual_csv)
    fit = fit_k_bulk_from_manual(rows)
    rpms = unique_valid_rpms(rows)
    rel_path = str(args.manual_csv.relative_to(_PROJECT_ROOT)) if args.manual_csv.is_relative_to(_PROJECT_ROOT) else str(args.manual_csv)
    write_discovery_calibration_json(fit, rpms, args.output, viscosity_table_path=rel_path)
    print(f"Wrote {args.output}")
    print(f"  k_bulk={fit['k_bulk']:.6e} (n={fit['n_points']})")
    print(f"  valid_rpms: {len(rpms)} speeds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

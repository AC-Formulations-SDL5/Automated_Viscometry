#!/usr/bin/env python3
"""Offline calibration for Discovery Mode bulk-offset RPM model.

CLI-only: fits K_BULK and continuous RPM↔viscosity power law from manual CSV,
writes data/calibration/discovery_bulk_calibration.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from viscometry.discovery.rpm_calibration import A_CAL, B_CAL, DEFAULT_RPM_MAX, DEFAULT_RPM_MIN
from viscometry.paths import CALIBRATION_DIR

_MODULE_DIR = Path(__file__).resolve().parent
_DEFAULT_OUTPUT = CALIBRATION_DIR / "discovery_bulk_calibration.json"
_PROJECT_ROOT = _MODULE_DIR.parents[1]

# Known bad manual row: eta looks like copy-paste of SS_dyne/cm2 column
_BAD_ROW_ETA = 982.3
_BAD_ROW_RPM = 0.5


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


def _is_excluded_manual_row(row: Dict[str, float]) -> bool:
    eta = row["viscosity_cp"]
    rpm = row["rpm"]
    if abs(eta - _BAD_ROW_ETA) < 1.0 and abs(rpm - _BAD_ROW_RPM) < 0.05:
        return True
    return False


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
        if _is_excluded_manual_row(row):
            continue
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


def fit_power_law_rpm_viscosity(
    manual_rows: Sequence[Dict[str, float]],
    *,
    torque_min: float = 45.0,
    torque_max: float = 55.0,
    reference_torque: float = 50.0,
) -> Dict[str, Any]:
    """
    Log-log fit: RPM@50% = a_cal * eta^b_cal from torque-corrected manual readings.
    """
    points: List[Tuple[float, float]] = []
    for row in manual_rows:
        if _is_excluded_manual_row(row):
            continue
        t = row["torque_pct"]
        if not (torque_min <= t <= torque_max):
            continue
        eta = row["viscosity_cp"]
        rpm = row["rpm"]
        if t <= 0:
            continue
        rpm_50 = rpm * (reference_torque / t)
        if eta <= 0 or rpm_50 <= 0:
            continue
        points.append((math.log(eta), math.log(rpm_50)))

    if len(points) < 2:
        return {
            "a_cal": float(A_CAL),
            "b_cal": float(B_CAL),
            "a_cal_r_squared": 0.0,
            "n_points": len(points),
            "fit_method": "fallback_defaults",
        }

    n = len(points)
    sx = sum(x for x, _ in points)
    sy = sum(y for _, y in points)
    sxx = sum(x * x for x, _ in points)
    sxy = sum(x * y for x, y in points)
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-18:
        return {
            "a_cal": float(A_CAL),
            "b_cal": float(B_CAL),
            "a_cal_r_squared": 0.0,
            "n_points": n,
            "fit_method": "fallback_degenerate",
        }

    b_cal = (n * sxy - sx * sy) / denom
    log_a = (sy - b_cal * sx) / n
    a_cal = math.exp(log_a)

    y_mean = sy / n
    ss_tot = sum((y - y_mean) ** 2 for _, y in points)
    ss_res = sum((y - (log_a + b_cal * x)) ** 2 for x, y in points)
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    return {
        "a_cal": float(a_cal),
        "b_cal": float(b_cal),
        "a_cal_r_squared": float(r_squared),
        "n_points": n,
        "fit_method": "log_log_torque_corrected_50pct",
    }


def unique_valid_rpms(manual_rows: Sequence[Dict[str, float]]) -> List[float]:
    """Collect sorted unique RPMs from manual table (UI reference chips only)."""
    rpms = sorted({round(row["rpm"], 4) for row in manual_rows})
    return rpms


def write_discovery_calibration_json(
    fit_result: Dict[str, Any],
    power_law: Dict[str, Any],
    valid_rpms: Sequence[float],
    output_path: Path,
    *,
    viscosity_table_path: str = "data/reference/Viscosity Readings - Manual.csv",
) -> None:
    """Write discovery_bulk_calibration.json."""
    payload = {
        "version": 2,
        "calibrated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "rpm_selection_mode": "continuous",
        "a_cal": power_law.get("a_cal", A_CAL),
        "b_cal": power_law.get("b_cal", B_CAL),
        "a_cal_r_squared": power_law.get("a_cal_r_squared", 0.0),
        "surface_torque_ref": 50.0,
        "rpm_min": DEFAULT_RPM_MIN,
        "rpm_max": DEFAULT_RPM_MAX,
        "k_bulk": fit_result.get("k_bulk", 1.0e-5),
        "k_bulk_std": fit_result.get("k_bulk_std", 0.0),
        "target_torque_bulk": 30.0,
        "torque_window_bulk": [25.0, 35.0],
        "hit_point_offset_mm": 0.35,
        "cold_start_rpm": 5.0,
        "max_iterations": 3,
        "valid_rpms": [float(r) for r in valid_rpms],
        "viscosity_table_path": viscosity_table_path,
        "discovery_stage2_enabled": True,
        "ladder_targets": [30.0, 40.0, 50.0, 60.0, 70.0],
        "ladder_tolerance_pct": 2.5,
        "newtonian_n_threshold": 0.975,
        "squeeze_boundary_base": 0.6,
        "hello_probe_rpm": 5.0,
        "ladder_max_iterations_per_target": 3,
        "landing_torque_window": [45.0, 55.0],
        "min_ladder_points_for_fit": 3,
        "min_power_law_r_squared": 0.85,
        "notes": (
            f"K_BULK: {fit_result.get('fit_method', 'unknown')}, n={fit_result.get('n_points', 0)}; "
            f"power_law: {power_law.get('fit_method', 'unknown')}, "
            f"n={power_law.get('n_points', 0)}, R²={power_law.get('a_cal_r_squared', 0):.4f}"
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Fit Discovery Mode calibration JSON")
    parser.add_argument(
        "--manual-csv",
        type=Path,
        default=_PROJECT_ROOT / "data" / "reference" / "Viscosity Readings - Manual.csv",
    )
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    if not args.manual_csv.exists():
        print(f"Manual CSV not found: {args.manual_csv}")
        return 1

    rows = load_manual_viscosity_rpm_table(args.manual_csv)
    fit = fit_k_bulk_from_manual(rows)
    power_law = fit_power_law_rpm_viscosity(rows)
    rpms = unique_valid_rpms(rows)
    rel_path = (
        str(args.manual_csv.relative_to(_PROJECT_ROOT))
        if args.manual_csv.is_relative_to(_PROJECT_ROOT)
        else str(args.manual_csv)
    )
    write_discovery_calibration_json(fit, power_law, rpms, args.output, viscosity_table_path=rel_path)
    print(f"Wrote {args.output}")
    print(f"  k_bulk={fit['k_bulk']:.6e} (n={fit['n_points']})")
    print(
        f"  a_cal={power_law['a_cal']:.4f}, b_cal={power_law['b_cal']:.6f}, "
        f"R²={power_law.get('a_cal_r_squared', 0):.4f} (n={power_law['n_points']})"
    )
    print(f"  valid_rpms (reference): {len(rpms)} speeds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
Live unified rheology prediction from rotational-drag vs Z-height data.

Model: D(h) = A/(h + h_c) + B with silicone calibration and multi-RPM power-law extension.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from rheology_live_adapter import (
    SUMMARY_KEY,
    filter_measurement_points,
    fit_sweep_drag,
    predict_cell_rheology,
    prepare_sweep_arrays,
)

VISCOSITY_PREDICTION_MODES = frozenset({"off", "on"})


def normalize_viscosity_prediction_mode(
    mode: Optional[str] = None,
    *,
    legacy_enabled: Optional[bool] = None,
) -> str:
    """Map settings to 'on' or 'off' (legacy Newtonian/Non-Newtonian -> on)."""
    if mode is not None:
        m = str(mode).strip()
        if m in ("on", "Newtonian", "Non-Newtonian"):
            return "on"
        if m == "off":
            return "off"
    if legacy_enabled is True:
        return "on"
    return "off"


def predict_viscosity(
    cell_id: int,
    rpm: float,
    measurement_data: Sequence[Dict[str, Any]],
    *,
    torque_floor_pct: float,
    hit_point_z: Optional[float] = None,
    viscosity_prediction_mode: str = "off",
) -> Dict[str, Any]:
    """
    Predict viscosity for one cell at one RPM (sweep fit for dashboard charts).

    viscosity_prediction_mode: 'off', 'on', or legacy 'Newtonian'/'Non-Newtonian'.
    """
    mode = normalize_viscosity_prediction_mode(viscosity_prediction_mode)
    base: Dict[str, Any] = {
        "cell_id": int(cell_id),
        "rpm": float(rpm),
        "viscosity_kcp": None,
        "A": None,
        "B": None,
        "hc": None,
        "R2": None,
        "n_points_used": 0,
        "fit_curve_z": [],
        "fit_curve_drag": [],
        "pretrim_z": [],
        "pretrim_drag": [],
        "success": False,
        "error": None,
        "viscosity_prediction_mode": mode,
    }

    if mode == "off":
        base["error"] = "Viscosity prediction is off"
        return base

    try:
        points = filter_measurement_points(measurement_data, cell_id, rpm)
        if not points:
            base["error"] = "No measurement points for this cell and RPM"
            return base

        h_norm, torque_pct, _pre_d, norm_offset, pretrim_z, pretrim_drag = prepare_sweep_arrays(
            points, torque_floor_pct, hit_point_z
        )
        base["pretrim_z"] = pretrim_z
        base["pretrim_drag"] = pretrim_drag
        base["n_points_used"] = int(len(h_norm))

        if len(h_norm) < 4:
            base["error"] = f"Insufficient points after pre-trim ({len(h_norm)} < 4)"
            return base

        fit_result = fit_sweep_drag(h_norm, torque_pct, float(rpm), norm_offset)
        base.update(fit_result)
        base["cell_id"] = int(cell_id)
        base["viscosity_prediction_mode"] = mode
    except Exception as exc:
        base["error"] = str(exc)

    return base


def predict_cell_viscosity(
    cell_id: int,
    rpms: Sequence[float],
    measurement_data: Sequence[Dict[str, Any]],
    *,
    torque_floor_pct: float,
    hit_point_z: Optional[float] = None,
    viscosity_prediction_mode: str = "off",
) -> Dict[str, Any]:
    """
    Full cell-level rheology: per-RPM sweeps plus __summary__ entry.

    Returns dict keyed by RPM floats and SUMMARY_KEY ('__summary__').
    """
    mode = normalize_viscosity_prediction_mode(viscosity_prediction_mode)
    out: Dict[str, Any] = {SUMMARY_KEY: {"success": False, "error": "Viscosity prediction is off"}}

    if mode == "off":
        return out

    try:
        per_rpm, summary = predict_cell_rheology(
            cell_id,
            rpms,
            measurement_data,
            torque_floor_pct=torque_floor_pct,
            hit_point_z=hit_point_z,
        )
        for rpm_f, result in per_rpm.items():
            result["viscosity_prediction_mode"] = mode
            out[float(rpm_f)] = result
        summary["viscosity_prediction_mode"] = mode
        out[SUMMARY_KEY] = summary
    except Exception as exc:
        out[SUMMARY_KEY] = {
            "cell_id": int(cell_id),
            "success": False,
            "error": str(exc),
            "viscosity_prediction_mode": mode,
        }

    return out

"""
Live measurement adapter for unified rheology prediction.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from rheology_constants import FIT_R2_MIN, H_C_UNIVERSAL_MM, shear_rate
from rheology_prediction import (
    amplitude_to_viscosity,
    drag_model_curve,
    fit_drag,
    passes_r2_gate,
    predict_rheology,
    serialize_rheology_result,
)

_RPM_TOL = 1e-6
SUMMARY_KEY = "__summary__"


def _rpm_match(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) < _RPM_TOL


def filter_measurement_points(
    measurement_data: Sequence[Dict[str, Any]],
    cell_id: int,
    rpm: float,
) -> List[Dict[str, Any]]:
    """Latest measurement per Z-height for one cell and RPM."""
    latest: Dict[str, Dict[str, Any]] = {}
    for row in measurement_data:
        try:
            cid = int(row.get("cell_id"))
        except (TypeError, ValueError):
            continue
        if cid != int(cell_id):
            continue
        row_rpm = row.get("rpm")
        if row_rpm is None or not _rpm_match(float(row_rpm), float(rpm)):
            continue
        height = row.get("height")
        if height is None:
            continue
        try:
            h_key = f"{float(height):.3f}"
        except (TypeError, ValueError):
            continue
        ts = float(row.get("timestamp") or 0)
        prev = latest.get(h_key)
        if prev is None or ts >= float(prev.get("timestamp") or 0):
            latest[h_key] = row
    return list(latest.values())


def _apply_pretrims(
    points: List[Dict[str, Any]],
    torque_floor_pct: float,
    hit_point_z: Optional[float],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return pretrim heights, drags, torques, and norm_offset source heights."""
    rows: List[Tuple[float, float, float]] = []
    for p in points:
        drag = p.get("rotational_drag")
        height = p.get("height")
        if height is None or drag is None:
            continue
        try:
            h = float(height)
            d = float(drag)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(h) or not math.isfinite(d):
            continue
        tp = p.get("torque_percent")
        try:
            torque = float(tp) if tp is not None else float("nan")
        except (TypeError, ValueError):
            torque = float("nan")
        rows.append((h, d, torque))

    rows.sort(key=lambda t: t[0])
    if not rows:
        return (
            np.array([], dtype=float),
            np.array([], dtype=float),
            np.array([], dtype=float),
            np.array([], dtype=float),
        )

    kept: List[Tuple[float, float, float]] = []
    for h, d, torque in rows:
        if math.isfinite(torque) and torque < float(torque_floor_pct):
            continue
        # Descent decreases Z: keep hitpoint and shallower gap (h >= hitpoint_z); drop deeper contact plateau only.
        if hit_point_z is not None and h < float(hit_point_z):
            continue
        kept.append((h, d, torque))

    if not kept:
        return (
            np.array([], dtype=float),
            np.array([], dtype=float),
            np.array([], dtype=float),
            np.array([], dtype=float),
        )

    pre_h = np.array([k[0] for k in kept], dtype=float)
    pre_d = np.array([k[1] for k in kept], dtype=float)
    pre_t = np.array([k[2] for k in kept], dtype=float)
    return pre_h, pre_d, pre_t, pre_h.copy()


def _lists_from_arrays(
    heights: np.ndarray,
    values: np.ndarray,
    norm_offset: float,
) -> Tuple[List[float], List[float]]:
    z_out = (heights + norm_offset).tolist() if len(heights) else []
    v_out = values.tolist() if len(values) else []
    return z_out, v_out


def prepare_sweep_arrays(
    points: List[Dict[str, Any]],
    torque_floor_pct: float,
    hit_point_z: Optional[float],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float, List[float], List[float]]:
    """Pretrim, re-zero height; return h_norm, torque_pct, drag, norm_offset, pretrim lists."""
    pre_h, pre_d, pre_t, _ = _apply_pretrims(points, torque_floor_pct, hit_point_z)
    norm_offset = float(np.min(pre_h)) if len(pre_h) else 0.0
    pretrim_z, pretrim_drag = _lists_from_arrays(pre_h, pre_d, 0.0)
    h_norm = pre_h - norm_offset if len(pre_h) else np.array([], dtype=float)
    return h_norm, pre_t, pre_d, norm_offset, pretrim_z, pretrim_drag


def fit_sweep_drag(
    h_norm: np.ndarray,
    torque_pct: np.ndarray,
    rpm: float,
    norm_offset: float,
    *,
    min_r2: float = FIT_R2_MIN,
    hc: float = H_C_UNIVERSAL_MM,
) -> Dict[str, Any]:
    """Fit one RPM sweep; apply R² quality gate."""
    rpm_f = float(rpm)
    base: Dict[str, Any] = {
        "rpm": rpm_f,
        "A": None,
        "B": None,
        "hc": hc,
        "R2": None,
        "n_points_used": int(len(h_norm)),
        "fit_curve_z": [],
        "fit_curve_drag": [],
        "success": False,
        "error": None,
        "viscosity_kcp": None,
    }
    if len(h_norm) < 4 or np.ptp(h_norm) <= 0:
        base["error"] = f"Insufficient points after pre-trim ({len(h_norm)} < 4)"
        return base

    d = np.asarray(torque_pct, float) / rpm_f
    fit = fit_drag(h_norm, d, hc=hc)
    r2 = fit.get("R2")
    base["A"] = fit.get("A")
    base["B"] = fit.get("B")
    base["R2"] = r2

    if not passes_r2_gate(r2, min_r2):
        base["error"] = f"Fit R² below threshold ({min_r2:.2f})"
        return base

    a_val = fit.get("A")
    if a_val is None or not np.isfinite(a_val) or a_val <= 0:
        base["error"] = "Invalid amplitude A from drag fit"
        return base

    mu_cp = float(amplitude_to_viscosity([a_val])[0])
    base["viscosity_kcp"] = mu_cp / 1000.0
    base["success"] = True

    x_line = np.linspace(float(np.min(h_norm)), float(np.max(h_norm)), 80)
    y_line = drag_model_curve(x_line, float(a_val), float(fit["B"]), hc)
    base["fit_curve_z"], base["fit_curve_drag"] = _lists_from_arrays(x_line, y_line, norm_offset)
    return base


def predict_cell_rheology(
    cell_id: int,
    rpms: Sequence[float],
    measurement_data: Sequence[Dict[str, Any]],
    *,
    torque_floor_pct: float,
    hit_point_z: Optional[float] = None,
    min_r2: float = FIT_R2_MIN,
) -> Tuple[Dict[float, Dict[str, Any]], Dict[str, Any]]:
    """Fit each RPM sweep and run cell-level predict_rheology."""
    per_rpm: Dict[float, Dict[str, Any]] = {}
    valid_h: List[np.ndarray] = []
    valid_t: List[np.ndarray] = []
    valid_r: List[float] = []

    for rpm in rpms:
        rpm_f = float(rpm)
        sweep_base: Dict[str, Any] = {
            "cell_id": int(cell_id),
            "rpm": rpm_f,
            "A": None,
            "B": None,
            "hc": H_C_UNIVERSAL_MM,
            "R2": None,
            "n_points_used": 0,
            "fit_curve_z": [],
            "fit_curve_drag": [],
            "pretrim_z": [],
            "pretrim_drag": [],
            "success": False,
            "error": None,
            "viscosity_kcp": None,
        }
        try:
            points = filter_measurement_points(measurement_data, cell_id, rpm_f)
            if not points:
                sweep_base["error"] = "No measurement points for this cell and RPM"
                per_rpm[rpm_f] = sweep_base
                continue

            h_norm, torque_pct, _pre_d, norm_offset, pretrim_z, pretrim_drag = prepare_sweep_arrays(
                points, torque_floor_pct, hit_point_z
            )
            sweep_base["pretrim_z"] = pretrim_z
            sweep_base["pretrim_drag"] = pretrim_drag
            sweep_base["n_points_used"] = int(len(h_norm))

            fit_result = fit_sweep_drag(
                h_norm, torque_pct, rpm_f, norm_offset, min_r2=min_r2
            )
            sweep_base.update(fit_result)
            per_rpm[rpm_f] = sweep_base

            if sweep_base.get("success"):
                valid_h.append(h_norm)
                valid_t.append(np.asarray(torque_pct, float))
                valid_r.append(rpm_f)
        except Exception as exc:
            sweep_base["error"] = str(exc)
            per_rpm[rpm_f] = sweep_base

    summary: Dict[str, Any] = {
        "cell_id": int(cell_id),
        "success": False,
        "error": None,
        "mode": None,
        "regime": "undetermined",
        "n": None,
        "K_Pas_n": None,
        "viscosity_kcp": None,
        "mu_app_cP": None,
        "R2_powerlaw": None,
        "A_per_rpm": [],
    }

    try:
        if len(valid_r) == 0:
            summary["error"] = "No valid RPM sweeps passed quality gate"
            return per_rpm, summary

        if len(valid_r) == 1:
            rheo = predict_rheology(valid_h[0], valid_t[0], valid_r[0])
        else:
            rheo = predict_rheology(valid_h, valid_t, valid_r)

        gamma_ref = float(shear_rate(np.median(valid_r)))
        serialized = serialize_rheology_result(rheo, gamma_dot_ref=gamma_ref)
        summary.update(serialized)
        summary["success"] = True
        summary["A_per_rpm"] = serialized.get("A_per_rpm", [])
    except Exception as exc:
        summary["error"] = str(exc)

    return per_rpm, summary

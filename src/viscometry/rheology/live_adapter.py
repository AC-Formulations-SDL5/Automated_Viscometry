"""
Live measurement adapter for unified rheology prediction.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from viscometry.rheology.constants import FIT_R2_MIN, H_C_UNIVERSAL_MM, PCT_TO_PA
from viscometry.rheology.characterization import compute_cell_characterization
from viscometry.rheology.prediction import (
    amplitude_to_viscosity,
    drag_model_curve,
    fit_drag,
    passes_r2_gate,
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


def _hitpoint_stress_from_sweep(
    h_norm: np.ndarray,
    torque_pct: np.ndarray,
    rpm: float,
    *,
    A: Optional[float] = None,
    B: Optional[float] = None,
    hc: float = H_C_UNIVERSAL_MM,
) -> Dict[str, Optional[float]]:
    """Torque, drag, and shear stress at the hitpoint (h_norm = 0)."""
    rpm_f = float(rpm)
    torque_raw: Optional[float] = None
    if len(torque_pct) > 0:
        t0 = float(torque_pct[0])
        if np.isfinite(t0):
            torque_raw = t0

    torque_hit = torque_raw
    drag_hit: Optional[float] = None
    tau_hit: Optional[float] = None

    if A is not None and B is not None and np.isfinite(A) and np.isfinite(B):
        drag_fit = float(A) / float(hc) + float(B)
        if np.isfinite(drag_fit) and drag_fit > 0 and rpm_f > 0:
            drag_hit = drag_fit
            torque_fit = drag_fit * rpm_f
            if np.isfinite(torque_fit) and torque_fit > 0:
                torque_hit = torque_fit
                tau_hit = PCT_TO_PA * torque_fit

    if tau_hit is None and torque_hit is not None and np.isfinite(torque_hit) and torque_hit > 0:
        tau_hit = PCT_TO_PA * torque_hit
        if rpm_f > 0:
            drag_hit = torque_hit / rpm_f

    return {
        "torque_pct_hit": torque_hit,
        "drag_hit": drag_hit,
        "tau_Pa_hit": tau_hit,
    }


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
        "torque_pct_hit": None,
        "drag_hit": None,
        "tau_Pa_hit": None,
    }
    hit_pre = _hitpoint_stress_from_sweep(h_norm, torque_pct, rpm_f, hc=hc)
    base.update(hit_pre)
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
    base.update(
        _hitpoint_stress_from_sweep(
            h_norm,
            torque_pct,
            rpm_f,
            A=float(a_val),
            B=float(fit["B"]),
            hc=hc,
        )
    )

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
    """Fit each RPM sweep and run three-pathway cell characterization."""
    per_rpm: Dict[float, Dict[str, Any]] = {}

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
        except Exception as exc:
            sweep_base["error"] = str(exc)
            per_rpm[rpm_f] = sweep_base

    successful = {
        rpm: fit for rpm, fit in per_rpm.items() if fit.get("success")
    }
    summary = compute_cell_characterization(
        successful,
        cell_id=int(cell_id),
    )
    for rpm, fit in successful.items():
        per_rpm[rpm] = fit
    return per_rpm, summary


def recompute_characterization_from_measurements(
    cells: Sequence[int],
    measurements: Sequence[Dict[str, Any]],
    *,
    torque_floor_pct: float = 0.0,
    hit_point_z_by_cell: Optional[Dict[int, float]] = None,
    min_r2: float = FIT_R2_MIN,
) -> Dict[str, Any]:
    """Recompute per-cell characterization from saved measurement rows."""
    hit_map = hit_point_z_by_cell or {}
    out: Dict[str, Any] = {}
    for cell_id in cells:
        cid = int(cell_id)
        rpms = sorted(
            {
                float(m["rpm"])
                for m in measurements
                if int(m.get("cell_id", -1)) == cid and m.get("rpm") is not None
            }
        )
        if not rpms:
            continue
        per_rpm, summary = predict_cell_rheology(
            cid,
            rpms,
            measurements,
            torque_floor_pct=torque_floor_pct,
            hit_point_z=hit_map.get(cid),
            min_r2=min_r2,
        )
        cell_map: Dict[str, Any] = {SUMMARY_KEY: summary}
        for rpm, fit in per_rpm.items():
            cell_map[str(float(rpm))] = fit
        out[str(cid)] = cell_map
    return out

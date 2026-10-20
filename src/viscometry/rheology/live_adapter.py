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
    fit_drag_newtonian_app_v4,
    passes_r2_gate,
    trim_stat_middle_arrays,
)

_RPM_TOL = 1e-6
SUMMARY_KEY = "__summary__"


def _rpm_match(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) < _RPM_TOL


def _height_key(height: float) -> str:
    return f"{float(height):.3f}"


def _normalize_excluded_heights(excluded_heights: Optional[Sequence[float]]) -> set:
    """Round heights to the same .3f keys used by measurement dedupe."""
    out: set = set()
    if not excluded_heights:
        return out
    for h in excluded_heights:
        try:
            out.add(_height_key(float(h)))
        except (TypeError, ValueError):
            continue
    return out


def _normalize_excluded_rpms(excluded_rpms: Optional[Sequence[float]]) -> List[float]:
    out: List[float] = []
    if not excluded_rpms:
        return out
    for r in excluded_rpms:
        try:
            out.append(float(r))
        except (TypeError, ValueError):
            continue
    return out


def filter_measurement_points(
    measurement_data: Sequence[Dict[str, Any]],
    cell_id: int,
    rpm: float,
    *,
    excluded_heights: Optional[Sequence[float]] = None,
) -> List[Dict[str, Any]]:
    """Latest measurement per Z-height for one cell and RPM."""
    drop_heights = _normalize_excluded_heights(excluded_heights)
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
            h_key = _height_key(float(height))
        except (TypeError, ValueError):
            continue
        if h_key in drop_heights:
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


def _apply_pretrims_newtonian_app_v4(
    points: List[Dict[str, Any]],
    torque_floor_pct: float,
    hit_point_z: Optional[float],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """APP_V4-style pretrim for Newtonian sweeps."""
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
    kept: List[Tuple[float, float, float]] = []
    for h, d, torque in rows:
        if math.isfinite(torque) and torque < float(torque_floor_pct):
            continue
        if hit_point_z is not None and h <= float(hit_point_z):
            continue
        kept.append((h, d, torque))

    if not kept:
        return (
            np.array([], dtype=float),
            np.array([], dtype=float),
            np.array([], dtype=float),
        )
    pre_h = np.array([k[0] for k in kept], dtype=float)
    pre_d = np.array([k[1] for k in kept], dtype=float)
    pre_t = np.array([k[2] for k in kept], dtype=float)
    return pre_h, pre_d, pre_t


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
        "drag_model": "app_v6_hyperbola",
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
    base["drag_model"] = fit.get("drag_model") or "app_v6_hyperbola"
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


def refit_sweep_drag_newtonian_app_v4(
    h_norm: np.ndarray,
    drag: np.ndarray,
    rpm: float,
    norm_offset: float,
    *,
    min_r2: float = FIT_R2_MIN,
) -> Dict[str, Any]:
    """Refit one RPM sweep with the APP_V4 Newtonian drag model."""
    rpm_f = float(rpm)
    base: Dict[str, Any] = {
        "rpm": rpm_f,
        "A": None,
        "B": None,
        "hc": None,
        "drag_model": "app_v4_newtonian",
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
    if len(h_norm) < 4 or np.ptp(h_norm) <= 0:
        base["error"] = f"Insufficient points after pre-trim ({len(h_norm)} < 4)"
        return base

    d = np.asarray(drag, float)
    h_trim, d_trim = trim_stat_middle_arrays(h_norm, d)
    if len(h_trim) < 4 or np.ptp(h_trim) <= 0:
        base["error"] = "Insufficient distinct points after statistical trim"
        return base
    base["n_points_used"] = int(len(h_trim))
    fit = fit_drag_newtonian_app_v4(h_trim, d_trim)
    r2 = fit.get("R2")
    base["A"] = fit.get("A")
    base["B"] = fit.get("B")
    base["R2"] = r2

    if not passes_r2_gate(r2, min_r2):
        base["error"] = f"Fit R² below threshold ({min_r2:.2f})"
        return base

    a_val = fit.get("A")
    b_val = fit.get("B")
    if a_val is None or b_val is None or not np.isfinite(a_val) or a_val <= 0:
        base["error"] = "Invalid APP_V4 Newtonian coefficients from drag fit"
        return base

    mu_cp = float(amplitude_to_viscosity([a_val], drag_model="app_v4_newtonian")[0])
    drag_hit = float(drag_model_curve([0.0], float(a_val), float(b_val), 0.0, drag_model="app_v4_newtonian")[0])
    torque_hit = drag_hit * rpm_f if np.isfinite(drag_hit) and drag_hit > 0 else None
    tau_hit = PCT_TO_PA * torque_hit if torque_hit is not None else None

    base["viscosity_kcp"] = mu_cp / 1000.0
    base["success"] = True
    base["drag_hit"] = drag_hit
    base["torque_pct_hit"] = torque_hit
    base["tau_Pa_hit"] = tau_hit

    x_line = np.linspace(float(np.min(h_trim)), float(np.max(h_trim)), 80)
    y_line = drag_model_curve(
        x_line,
        float(a_val),
        float(b_val),
        0.0,
        drag_model="app_v4_newtonian",
    )
    base["fit_curve_z"], base["fit_curve_drag"] = _lists_from_arrays(x_line, y_line, norm_offset)
    return base


def fit_newtonian_app_v4_from_points(
    points: List[Dict[str, Any]],
    rpm: float,
    *,
    torque_floor_pct: float,
    hit_point_z: Optional[float],
    min_r2: float = FIT_R2_MIN,
) -> Dict[str, Any]:
    """Full APP_V4 Newtonian sweep path from raw measurement points."""
    pre_h, pre_d, pre_t = _apply_pretrims_newtonian_app_v4(points, torque_floor_pct, hit_point_z)
    norm_offset = float(np.min(pre_h)) if len(pre_h) else 0.0
    h_norm = pre_h - norm_offset if len(pre_h) else np.array([], dtype=float)
    return refit_sweep_drag_newtonian_app_v4(
        h_norm,
        pre_d,
        float(rpm),
        norm_offset,
        min_r2=min_r2,
    )


def predict_cell_rheology(
    cell_id: int,
    rpms: Sequence[float],
    measurement_data: Sequence[Dict[str, Any]],
    *,
    torque_floor_pct: float,
    hit_point_z: Optional[float] = None,
    min_r2: float = FIT_R2_MIN,
    excluded_rpms: Optional[Sequence[float]] = None,
    excluded_heights: Optional[Sequence[float]] = None,
) -> Tuple[Dict[float, Dict[str, Any]], Dict[str, Any]]:
    """Fit each RPM sweep and run three-pathway cell characterization."""
    per_rpm: Dict[float, Dict[str, Any]] = {}
    excluded_rpm_list = _normalize_excluded_rpms(excluded_rpms)

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
            points = filter_measurement_points(
                measurement_data,
                cell_id,
                rpm_f,
                excluded_heights=excluded_heights,
            )
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
            sweep_base["_points"] = points
            sweep_base["_h_norm"] = h_norm
            sweep_base["_torque_pct"] = torque_pct
            sweep_base["_norm_offset"] = norm_offset

            fit_result = fit_sweep_drag(
                h_norm, torque_pct, rpm_f, norm_offset, min_r2=min_r2
            )
            sweep_base.update(fit_result)
            per_rpm[rpm_f] = sweep_base
        except Exception as exc:
            sweep_base["error"] = str(exc)
            per_rpm[rpm_f] = sweep_base

    successful = {
        rpm: fit
        for rpm, fit in per_rpm.items()
        if fit.get("success")
        and not any(_rpm_match(rpm, ex) for ex in excluded_rpm_list)
    }
    summary = compute_cell_characterization(
        successful,
        cell_id=int(cell_id),
    )
    if summary.get("pathway") == "newtonian":
        refit_successful: Dict[float, Dict[str, Any]] = {}
        for rpm, fit in successful.items():
            points = fit.get("_points")
            if not points:
                refit_successful[rpm] = fit
                continue
            legacy_fit = fit_newtonian_app_v4_from_points(
                list(points),
                float(rpm),
                torque_floor_pct=torque_floor_pct,
                hit_point_z=hit_point_z,
                min_r2=min_r2,
            )
            merged = dict(fit)
            merged.update(legacy_fit)
            refit_successful[rpm] = merged
        successful = {rpm: fit for rpm, fit in refit_successful.items() if fit.get("success")}
        summary = compute_cell_characterization(
            successful,
            cell_id=int(cell_id),
        )
    for rpm, fit in successful.items():
        per_rpm[rpm] = fit
    return per_rpm, summary


def _parse_exclusion_map(raw: Any) -> Dict[int, List[float]]:
    """Normalize {cell_id: [floats]} maps from JSON payloads."""
    out: Dict[int, List[float]] = {}
    if not isinstance(raw, dict):
        return out
    for key, values in raw.items():
        try:
            cid = int(key)
        except (TypeError, ValueError):
            continue
        if not isinstance(values, (list, tuple)):
            continue
        parsed: List[float] = []
        for v in values:
            try:
                parsed.append(float(v))
            except (TypeError, ValueError):
                continue
        out[cid] = parsed
    return out


def _json_safe_value(value: Any) -> Any:
    """Convert numpy / non-finite values into JSON-serializable Python types."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (np.floating, np.integer)):
        f = float(value)
        return f if math.isfinite(f) else None
    if isinstance(value, np.ndarray):
        return [_json_safe_value(v) for v in value.tolist()]
    if isinstance(value, dict):
        return {
            str(k): _json_safe_value(v)
            for k, v in value.items()
            if not (isinstance(k, str) and k.startswith("_"))
        }
    if isinstance(value, (list, tuple)):
        return [_json_safe_value(v) for v in value]
    if isinstance(value, (np.bool_,)):
        return bool(value)
    try:
        if math.isfinite(float(value)):
            return float(value)
    except (TypeError, ValueError):
        pass
    return None


def _sanitize_fit_for_json(fit: Dict[str, Any]) -> Dict[str, Any]:
    """Drop private scratch keys and make a fit/summary dict JSON-safe."""
    return {
        str(k): _json_safe_value(v)
        for k, v in fit.items()
        if not (isinstance(k, str) and k.startswith("_"))
    }


def recompute_characterization_from_measurements(
    cells: Sequence[int],
    measurements: Sequence[Dict[str, Any]],
    *,
    torque_floor_pct: float = 0.0,
    hit_point_z_by_cell: Optional[Dict[int, float]] = None,
    excluded_rpms_by_cell: Optional[Dict[Any, Sequence[float]]] = None,
    excluded_heights_by_cell: Optional[Dict[Any, Sequence[float]]] = None,
    min_r2: float = FIT_R2_MIN,
) -> Dict[str, Any]:
    """Recompute per-cell characterization from saved measurement rows."""
    hit_map = hit_point_z_by_cell or {}
    excl_rpms = _parse_exclusion_map(excluded_rpms_by_cell)
    excl_heights = _parse_exclusion_map(excluded_heights_by_cell)
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
            excluded_rpms=excl_rpms.get(cid),
            excluded_heights=excl_heights.get(cid),
        )
        cell_map: Dict[str, Any] = {SUMMARY_KEY: _sanitize_fit_for_json(summary)}
        for rpm, fit in per_rpm.items():
            cell_map[str(float(rpm))] = _sanitize_fit_for_json(fit)
        out[str(cid)] = cell_map
    return out

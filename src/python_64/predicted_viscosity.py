"""
Live hyperbolic viscosity prediction from rotational-drag vs Z-height data.

Model: D(h) = a / (h - b), with viscosity_kcp = abs(a) * M_HYP.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import curve_fit

M_HYP = 2.330

_RPM_TOL = 1e-6


def _hyperbola_2param(x: np.ndarray, a: float, b: float) -> np.ndarray:
    return a / (x - b)


def _rpm_match(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) < _RPM_TOL


def _rolling_centered(
    arr: np.ndarray, win: int, min_periods: int = 2
) -> Tuple[np.ndarray, np.ndarray]:
    """Centered rolling mean and std mimicking pandas rolling(center=True, min_periods=2)."""
    n = len(arr)
    mean_out = np.full(n, np.nan, dtype=float)
    std_out = np.full(n, np.nan, dtype=float)
    half = win // 2

    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        window = arr[lo:hi]
        if len(window) >= min_periods:
            mean_out[i] = float(np.nanmean(window))
            std_out[i] = float(np.nanstd(window, ddof=1)) if len(window) > 1 else 0.0

    # bfill then ffill on mean (pandas behavior for rolling mean edges)
    last_valid = None
    for i in range(n - 1, -1, -1):
        if np.isfinite(mean_out[i]):
            last_valid = mean_out[i]
        elif last_valid is not None:
            mean_out[i] = last_valid
    first_valid = None
    for i in range(n):
        if np.isfinite(mean_out[i]):
            first_valid = mean_out[i]
        elif first_valid is not None:
            mean_out[i] = first_valid

    std_out = np.nan_to_num(std_out, nan=0.0)
    return mean_out, std_out


def trim_stat_middle_arrays(
    x: np.ndarray,
    y: np.ndarray,
    q: float = 0.65,
    win: int = 5,
    min_keep_frac: float = 0.5,
    max_keep_frac: float = 0.8,
) -> Tuple[np.ndarray, np.ndarray]:
    """Trim to the smooth middle segment (single series, numpy port of trim_stat_middle)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    eps = 1e-9

    if n == 0:
        return x.copy(), y.copy()

    if n < 6:
        x_out = x - np.min(x)
        return x_out, y.copy()

    y_sm, sd = _rolling_centered(y, win, min_periods=2)
    dy = np.gradient(y_sm, x)
    d2 = np.gradient(dy, x)

    cv = np.abs(sd / (np.abs(y_sm) + eps))
    d1_dev = np.abs(dy - np.nanmedian(dy))
    d2_abs = np.abs(d2)
    t_cv, t_d1, t_d2 = [float(np.nanquantile(v, q)) for v in (cv, d1_dev, d2_abs)]
    neg = np.clip(-dy, 0, None)
    t_neg = max(float(np.nanquantile(neg, q)), eps)

    raw = (
        cv / (t_cv + eps)
        + d1_dev / (t_d1 + eps)
        + d2_abs / (t_d2 + eps)
        + 2.0 * np.clip(dy, 0, None) / t_neg
        - 0.8 * neg / t_neg
    )

    min_k = max(5, int(np.ceil(min_keep_frac * n)))
    max_frac = 0.92 if n <= 14 else max_keep_frac
    max_k = min(n, max(min_k, int(np.floor(max_frac * n))))
    mid = 0.5 * (n - 1)

    best = (np.inf, 0, n)
    for length in range(min_k, max_k + 1):
        for i in range(0, n - length + 1):
            j = i + length
            dy_w = dy[i:j]
            pos_w = np.clip(dy_w, 0, None)
            neg_strength = float(np.nanmean(np.clip(-dy_w, 0, None)) / (t_neg + eps))
            score = float(np.nanmean(raw[i:j]))
            score += 1.8 * float(np.nanmean(pos_w / (t_neg + eps)))
            score += 0.9 * max(0.0, float(np.mean(dy_w > 0)) - 0.15)
            score += 0.35 * max(0.0, 0.55 - neg_strength)
            score += 0.10 * abs((i + j - 1) * 0.5 - mid) / max(n, 1)
            if score < best[0]:
                best = (score, i, j)

    _, i, j = best
    x_sel = x[i:j].copy()
    y_sel = y[i:j].copy()
    x_sel -= np.min(x_sel)
    return x_sel, y_sel


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
    """Return raw heights/drags and pretrim heights/drags (after floor + hit filters)."""
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

    raw_h = np.array([r[0] for r in rows], dtype=float)
    raw_d = np.array([r[1] for r in rows], dtype=float)

    kept: List[Tuple[float, float]] = []
    for h, d, torque in rows:
        if math.isfinite(torque) and torque < float(torque_floor_pct):
            continue
        if hit_point_z is not None and h <= float(hit_point_z):
            continue
        kept.append((h, d))

    if not kept:
        return raw_h, raw_d, np.array([], dtype=float), np.array([], dtype=float)

    pre_h = np.array([k[0] for k in kept], dtype=float)
    pre_d = np.array([k[1] for k in kept], dtype=float)
    return raw_h, raw_d, pre_h, pre_d


def _fit_hyperbola(x: np.ndarray, y: np.ndarray) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    if len(x) < 4 or np.ptp(x) <= 0:
        return None, None, "Need at least 4 distinct Z points after trimming"

    b0 = float(np.min(x) - 0.5 * max(np.ptp(x), 1e-6))
    a0 = float((y[0] - y[-1]) * max(np.ptp(x), 1e-6))
    lower_b = float(np.min(x) - 5.0 * max(np.ptp(x), 1e-6))
    upper_b = float(np.min(x) - 1e-6)

    try:
        popt, _ = curve_fit(
            _hyperbola_2param,
            x,
            y,
            p0=[a0, b0],
            bounds=([-np.inf, lower_b], [np.inf, upper_b]),
            maxfev=20000,
        )
        return float(popt[0]), float(popt[1]), None
    except Exception as exc:
        return None, None, str(exc)


def _lists_from_arrays(
    heights: np.ndarray,
    drags: np.ndarray,
    norm_offset: float,
) -> Tuple[List[float], List[float]]:
    z_out = (heights + norm_offset).tolist() if len(heights) else []
    d_out = drags.tolist() if len(drags) else []
    return z_out, d_out


def predict_viscosity(
    cell_id: int,
    rpm: float,
    measurement_data: Sequence[Dict[str, Any]],
    *,
    torque_floor_pct: float,
    hit_point_z: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Predict viscosity (kCp) for one cell at one RPM from live measurement_data.

    Result includes pretrim_z/pretrim_drag (after dedupe + torque/hit filters, before stat trim)
    for dashboard scatter plots.
    """
    base: Dict[str, Any] = {
        "cell_id": int(cell_id),
        "rpm": float(rpm),
        "viscosity_kcp": None,
        "a": None,
        "b": None,
        "n_points_used": 0,
        "trimmed_z": [],
        "trimmed_drag": [],
        "fit_curve_z": [],
        "fit_curve_drag": [],
        "pretrim_z": [],
        "pretrim_drag": [],
        "success": False,
        "error": None,
    }

    points = filter_measurement_points(measurement_data, cell_id, rpm)
    if not points:
        base["error"] = "No measurement points for this cell and RPM"
        return base

    _raw_h, _raw_d, pre_h, pre_d = _apply_pretrims(points, torque_floor_pct, hit_point_z)
    norm_offset = float(np.min(pre_h)) if len(pre_h) else 0.0
    base["pretrim_z"], base["pretrim_drag"] = _lists_from_arrays(pre_h, pre_d, 0.0)

    if len(pre_h) < 4:
        base["error"] = f"Insufficient points after pre-trim ({len(pre_h)} < 4)"
        return base

    x_norm = pre_h - norm_offset
    y = pre_d.copy()

    x_trim, y_trim = trim_stat_middle_arrays(x_norm, y)
    base["n_points_used"] = int(len(x_trim))
    base["trimmed_z"], base["trimmed_drag"] = _lists_from_arrays(x_trim, y_trim, norm_offset)

    if len(x_trim) < 4 or np.ptp(x_trim) <= 0:
        base["error"] = "Insufficient distinct points after statistical trim"
        return base

    a, b, fit_err = _fit_hyperbola(x_trim, y_trim)
    if fit_err is not None or a is None or b is None:
        base["error"] = fit_err or "Hyperbola fit failed"
        return base

    base["a"] = a
    base["b"] = b
    base["viscosity_kcp"] = float(abs(a) * M_HYP)
    base["success"] = True

    x_line = np.linspace(float(np.min(x_trim)), float(np.max(x_trim)), 80)
    y_line = _hyperbola_2param(x_line, a, b)
    base["fit_curve_z"], base["fit_curve_drag"] = _lists_from_arrays(x_line, y_line, norm_offset)

    return base

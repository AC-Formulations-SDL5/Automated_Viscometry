"""
Unified rheology prediction: drag-profile amplitude to Newtonian or power-law flow curves.

Model: D(h) = A/(h + h_c) + B  with universal h_c and silicone calibration A = k·μ^p.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
from scipy.optimize import curve_fit
from scipy import stats

from viscometry.rheology.constants import (
    CP_TO_PAS,
    FIT_R2_MIN,
    H_C_UNIVERSAL_MM,
    SILICONE_K,
    SILICONE_P,
    THICKENING_THRESHOLD,
    THINNING_THRESHOLD,
    shear_rate,
)

ArrayLike = Union[np.ndarray, Sequence[float]]
APP_V4_M_HYP = 2.330
_DENOM_FLOOR = 1e-12


def _hyperbola_powerlaw(x: np.ndarray, a: float, b: float, n: float) -> np.ndarray:
    denom = np.abs(np.asarray(x, float) - b)
    denom = np.maximum(denom, _DENOM_FLOOR)
    return a / np.power(denom, n)


def _rolling_centered(
    arr: np.ndarray,
    win: int,
    min_periods: int = 2,
) -> Tuple[np.ndarray, np.ndarray]:
    """Centered rolling mean/std compatible with the APP_V4 middle trim."""
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
    x: ArrayLike,
    y: ArrayLike,
    *,
    q: float = 0.65,
    win: int = 5,
    min_keep_frac: float = 0.5,
    max_keep_frac: float = 0.8,
) -> Tuple[np.ndarray, np.ndarray]:
    """APP_V4 statistical middle trim for Newtonian drag fitting."""
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    n = len(x_arr)
    eps = 1e-9

    if n == 0:
        return x_arr.copy(), y_arr.copy()
    if n < 6:
        x_out = x_arr - np.min(x_arr)
        return x_out, y_arr.copy()

    y_sm, sd = _rolling_centered(y_arr, win, min_periods=2)
    dy = np.gradient(y_sm, x_arr)
    d2 = np.gradient(dy, x_arr)

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
    x_sel = x_arr[i:j].copy()
    y_sel = y_arr[i:j].copy()
    x_sel -= np.min(x_sel)
    return x_sel, y_sel


def fit_drag(
    h: ArrayLike,
    D: ArrayLike,
    hc: Optional[float] = None,
) -> Dict[str, Any]:
    """Fit D(h) = A/(h + h_c) + B. If hc is None, h_c is also a free parameter."""
    h_arr = np.asarray(h, float)
    d_arr = np.asarray(D, float)
    mask = np.isfinite(h_arr) & np.isfinite(d_arr)
    h_arr, d_arr = h_arr[mask], d_arr[mask]
    if len(h_arr) < 4:
        return {"A": np.nan, "B": np.nan, "hc": np.nan, "R2": np.nan, "n": len(h_arr), "drag_model": "app_v6_hyperbola"}

    if hc is None:
        def model(x, A, B, hc_fit):
            return A / (x + hc_fit) + B

        a0 = (d_arr.max() - d_arr.min()) * (h_arr.min() + 0.25)
        try:
            popt, _ = curve_fit(
                model,
                h_arr,
                d_arr,
                p0=[max(a0, 1e-3), float(np.median(d_arr[-5:])), 0.25],
                bounds=([0, -np.inf, 1e-3], [np.inf, np.inf, 5.0]),
                maxfev=20000,
            )
            a_val, b_val, hc_fit = popt
            pred = model(h_arr, *popt)
        except Exception:
            return {"A": np.nan, "B": np.nan, "hc": np.nan, "R2": np.nan, "n": len(h_arr), "drag_model": "app_v6_hyperbola"}
    else:
        def model_fixed(x, A, B):
            return A / (x + hc) + B

        a0 = (d_arr.max() - d_arr.min()) * (h_arr.min() + hc)
        try:
            popt, _ = curve_fit(
                model_fixed,
                h_arr,
                d_arr,
                p0=[max(a0, 1e-3), float(np.median(d_arr[-5:]))],
                maxfev=20000,
            )
            a_val, b_val = popt
            hc_fit = hc
            pred = model_fixed(h_arr, *popt)
        except Exception:
            return {"A": np.nan, "B": np.nan, "hc": hc, "R2": np.nan, "n": len(h_arr), "drag_model": "app_v6_hyperbola"}

    ss_r = float(np.sum((d_arr - pred) ** 2))
    ss_t = float(np.sum((d_arr - d_arr.mean()) ** 2))
    r2 = 1.0 - ss_r / ss_t if ss_t > 0 else np.nan
    return {
        "A": float(a_val),
        "B": float(b_val),
        "hc": float(hc_fit),
        "R2": float(r2),
        "n": len(h_arr),
        "drag_model": "app_v6_hyperbola",
    }


def fit_drag_newtonian_app_v4(
    h: ArrayLike,
    D: ArrayLike,
) -> Dict[str, Any]:
    """Fit APP_V4 Newtonian drag model D(h) = a / |h - b|."""
    h_arr = np.asarray(h, float)
    d_arr = np.asarray(D, float)
    mask = np.isfinite(h_arr) & np.isfinite(d_arr)
    h_arr, d_arr = h_arr[mask], d_arr[mask]
    if len(h_arr) < 4 or np.ptp(h_arr) <= 0:
        return {"A": np.nan, "B": np.nan, "hc": np.nan, "R2": np.nan, "n": len(h_arr), "drag_model": "app_v4_newtonian"}

    ptp = max(float(np.ptp(h_arr)), 1e-6)
    b0 = float(np.min(h_arr) - 0.5 * ptp)
    a0 = float(max((d_arr[0] - d_arr[-1]) * ptp, 1e-6))
    upper_b = float(np.min(h_arr))

    try:
        def model(x, a, b):
            return _hyperbola_powerlaw(x, a, b, 1.0)

        popt, _ = curve_fit(
            model,
            h_arr,
            d_arr,
            p0=[a0, b0],
            bounds=([0.0, -np.inf], [np.inf, upper_b]),
            maxfev=20000,
        )
        a_val, b_val = popt
        pred = model(h_arr, *popt)
    except Exception:
        return {"A": np.nan, "B": np.nan, "hc": np.nan, "R2": np.nan, "n": len(h_arr), "drag_model": "app_v4_newtonian"}

    ss_r = float(np.sum((d_arr - pred) ** 2))
    ss_t = float(np.sum((d_arr - d_arr.mean()) ** 2))
    r2 = 1.0 - ss_r / ss_t if ss_t > 0 else np.nan
    return {
        "A": float(a_val),
        "B": float(b_val),
        "hc": np.nan,
        "R2": float(r2),
        "n": len(h_arr),
        "drag_model": "app_v4_newtonian",
    }


def drag_model_curve(
    h: ArrayLike,
    A: float,
    B: float,
    hc: float,
    *,
    drag_model: str = "app_v6_hyperbola",
) -> np.ndarray:
    """Evaluate the configured drag model curve."""
    if drag_model == "app_v4_newtonian":
        return _hyperbola_powerlaw(np.asarray(h, float), A, B, 1.0)
    return A / (np.asarray(h, float) + hc) + B


def amplitude_to_viscosity(
    A: ArrayLike,
    k: Optional[float] = None,
    p: Optional[float] = None,
    *,
    drag_model: str = "app_v6_hyperbola",
) -> np.ndarray:
    """Invert silicone calibration for the configured drag model."""
    a_arr = np.asarray(A, float)
    out = np.full_like(a_arr, np.nan, dtype=float)
    pos = a_arr > 0
    if drag_model == "app_v4_newtonian":
        out[pos] = np.abs(a_arr[pos]) * APP_V4_M_HYP * 1000.0
        return out

    k_val = SILICONE_K if k is None else k
    p_val = SILICONE_P if p is None else p
    out[pos] = (a_arr[pos] / k_val) ** (1.0 / p_val)
    return out


def fit_powerlaw(gamma_dot: ArrayLike, A_vals: ArrayLike) -> Dict[str, Any]:
    """Log-log fit: ln A = ln A0 + (n-1) ln gamma_dot."""
    g = np.asarray(gamma_dot, float)
    a = np.asarray(A_vals, float)
    mask = np.isfinite(g) & np.isfinite(a) & (g > 0) & (a > 0)
    g, a = g[mask], a[mask]
    if len(g) < 2:
        return {"n": np.nan, "A0": np.nan, "R2": np.nan, "n_pts": int(len(g))}
    if len(g) == 2:
        slope = (np.log(a[1]) - np.log(a[0])) / (np.log(g[1]) - np.log(g[0]))
        return {
            "n": float(slope + 1.0),
            "A0": float(a[0] * g[0] ** (-slope)),
            "R2": np.nan,
            "n_pts": 2,
        }
    res = stats.linregress(np.log(g), np.log(a))
    return {
        "n": float(res.slope + 1.0),
        "A0": float(np.exp(res.intercept)),
        "R2": float(res.rvalue**2),
        "n_pts": int(len(g)),
    }


def passes_r2_gate(r2: float, min_r2: float = FIT_R2_MIN) -> bool:
    """Return True if fit R² meets the quality threshold."""
    return bool(np.isfinite(r2) and r2 >= min_r2)


def predict_rheology(
    h_mm: ArrayLike,
    torque_pct: ArrayLike,
    rpm: Union[float, Sequence[float]],
    *,
    hc: Optional[float] = None,
    k: Optional[float] = None,
    p: Optional[float] = None,
    thinning_thr: float = THINNING_THRESHOLD,
    thickening_thr: float = THICKENING_THRESHOLD,
) -> Dict[str, Any]:
    """
    Unified Newtonian / power-law rheology estimator (amplitude-only).

    For three-pathway cell characterization (Newtonian / mild / strong stress routing),
    use ``predict_cell_rheology`` or ``compute_cell_characterization`` instead.

    Single-RPM: h_mm, torque_pct are 1-D arrays; rpm is scalar.
    Multi-RPM: h_mm, torque_pct are sequences of 1-D arrays; rpm is a sequence.

    Returns dict with mode, regime, n, K_Pas_n, mu_app (scalar or callable),
    tau (callable), A_per_rpm, R2_powerlaw.
    """
    hc_val = H_C_UNIVERSAL_MM if hc is None else hc
    k_val = SILICONE_K if k is None else k
    p_val = SILICONE_P if p is None else p

    try:
        is_seq = (
            hasattr(h_mm, "__len__")
            and not isinstance(h_mm, (str, bytes, np.ndarray))
            and hasattr(h_mm[0], "__len__")
            and not isinstance(h_mm[0], (str, bytes))
        )
    except (IndexError, TypeError):
        is_seq = False

    def _amplitude(h, torque, rpm_):
        d = np.asarray(torque, float) / float(rpm_)
        fit = fit_drag(np.asarray(h, float), d, hc=hc_val)
        return fit["A"]

    def _amplitude_newtonian_legacy(h, torque, rpm_):
        d = np.asarray(torque, float) / float(rpm_)
        h_arr = np.asarray(h, float)
        h_trim, d_trim = trim_stat_middle_arrays(h_arr, d)
        fit = fit_drag_newtonian_app_v4(h_trim, d_trim)
        return fit["A"]

    if not is_seq:
        a_val = _amplitude_newtonian_legacy(h_mm, torque_pct, rpm)
        mu = float(amplitude_to_viscosity(np.array([a_val]), k=k_val, p=p_val, drag_model="app_v4_newtonian")[0])
        k_pas = mu * CP_TO_PAS
        return {
            "mode": "newtonian",
            "regime": "Newtonian",
            "n": 1.0,
            "K_Pas_n": k_pas,
            "mu_app": mu,
            "tau": lambda g: k_pas * np.asarray(g, float),
            "A_per_rpm": [(float(rpm), float(a_val))],
            "R2_powerlaw": np.nan,
        }

    a_pts: List[Tuple[float, float]] = []
    for hh, tt, rr in zip(h_mm, torque_pct, rpm):
        a_pts.append((float(rr), float(_amplitude(hh, tt, rr))))
    a_pts = [(r_, a_) for r_, a_ in a_pts if np.isfinite(a_) and a_ > 0]
    if len(a_pts) < 2:
        return {
            "mode": "powerlaw",
            "regime": "undetermined",
            "n": np.nan,
            "K_Pas_n": np.nan,
            "mu_app": lambda g: np.nan,
            "tau": lambda g: np.nan,
            "A_per_rpm": a_pts,
            "R2_powerlaw": np.nan,
        }

    rpms_arr, as_arr = map(np.array, zip(*a_pts))
    g_arr = shear_rate(rpms_arr)
    pl = fit_powerlaw(g_arr, as_arr)
    mu0 = float(amplitude_to_viscosity(np.array([as_arr[np.argmin(g_arr)]]), k=k_val, p=p_val)[0])
    g0 = float(g_arr.min())
    k_cp = mu0 * g0 ** (1.0 - pl["n"])
    k_pas = k_cp * CP_TO_PAS
    n_flow = pl["n"]
    if n_flow > thickening_thr:
        regime = "shear-thickening"
    elif n_flow < thinning_thr:
        regime = "shear-thinning"
    else:
        regime = "Newtonian"
    eta_cp = lambda g: k_cp * np.asarray(g, float) ** (n_flow - 1.0)
    tau_pa = lambda g: k_pas * np.asarray(g, float) ** n_flow
    return {
        "mode": "powerlaw",
        "regime": regime,
        "n": n_flow,
        "K_Pas_n": k_pas,
        "mu_app": eta_cp,
        "tau": tau_pa,
        "A_per_rpm": a_pts,
        "R2_powerlaw": pl["R2"],
    }


def mu_app_at_gamma(rheology: Dict[str, Any], gamma_dot: float) -> float:
    """Scalar apparent viscosity (cP) at a given shear rate."""
    mu = rheology.get("mu_app")
    if mu is None:
        return float("nan")
    if np.isscalar(mu):
        return float(mu)
    try:
        return float(mu(gamma_dot))
    except Exception:
        return float("nan")


def serialize_rheology_result(rheology: Dict[str, Any], *, gamma_dot_ref: float) -> Dict[str, Any]:
    """JSON-safe dict from predict_rheology output (strips callables)."""
    mu = rheology.get("mu_app")
    if callable(mu):
        mu_scalar = float(mu(gamma_dot_ref))
    elif np.isscalar(mu):
        mu_scalar = float(mu)
    else:
        mu_scalar = float("nan")

    a_per_rpm = [
        [float(r), float(a)] for r, a in rheology.get("A_per_rpm", [])
    ]
    return {
        "mode": rheology.get("mode"),
        "regime": rheology.get("regime"),
        "n": None if not np.isfinite(rheology.get("n", np.nan)) else float(rheology["n"]),
        "K_Pas_n": None
        if not np.isfinite(rheology.get("K_Pas_n", np.nan))
        else float(rheology["K_Pas_n"]),
        "mu_app_cP": mu_scalar,
        "viscosity_kcp": mu_scalar / 1000.0 if np.isfinite(mu_scalar) else None,
        "R2_powerlaw": None
        if not np.isfinite(rheology.get("R2_powerlaw", np.nan))
        else float(rheology["R2_powerlaw"]),
        "A_per_rpm": a_per_rpm,
    }

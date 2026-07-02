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
        return {"A": np.nan, "B": np.nan, "hc": np.nan, "R2": np.nan, "n": len(h_arr)}

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
            return {"A": np.nan, "B": np.nan, "hc": np.nan, "R2": np.nan, "n": len(h_arr)}
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
            return {"A": np.nan, "B": np.nan, "hc": hc, "R2": np.nan, "n": len(h_arr)}

    ss_r = float(np.sum((d_arr - pred) ** 2))
    ss_t = float(np.sum((d_arr - d_arr.mean()) ** 2))
    r2 = 1.0 - ss_r / ss_t if ss_t > 0 else np.nan
    return {
        "A": float(a_val),
        "B": float(b_val),
        "hc": float(hc_fit),
        "R2": float(r2),
        "n": len(h_arr),
    }


def drag_model_curve(h: ArrayLike, A: float, B: float, hc: float) -> np.ndarray:
    """Evaluate D(h) = A/(h + hc) + B."""
    return A / (np.asarray(h, float) + hc) + B


def amplitude_to_viscosity(
    A: ArrayLike,
    k: Optional[float] = None,
    p: Optional[float] = None,
) -> np.ndarray:
    """Invert silicone calibration: mu_app(cP) = (A/k)^(1/p)."""
    k_val = SILICONE_K if k is None else k
    p_val = SILICONE_P if p is None else p
    a_arr = np.asarray(A, float)
    out = np.full_like(a_arr, np.nan, dtype=float)
    pos = a_arr > 0
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
    Unified Newtonian / power-law rheology estimator.

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

    if not is_seq:
        a_val = _amplitude(h_mm, torque_pct, rpm)
        mu = float(amplitude_to_viscosity(np.array([a_val]), k=k_val, p=p_val)[0])
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

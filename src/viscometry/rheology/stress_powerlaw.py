"""
Stress-based power-law fitting and outlier staging for rheology characterization.

Ported from APP_V3 Rheology_Newtonian_Non_Newtonian_Material.ipynb (cell 9).
Amplitude-based fits live in prediction.fit_powerlaw; this module fits tau vs gamma_dot.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd


def fit_stress_powerlaw(
    gamma_dot: np.ndarray | Sequence[float],
    tau: np.ndarray | Sequence[float],
) -> Dict[str, Any]:
    """
    Fit tau = K * gamma_dot^n in log space.

    Returns dict with K_stress (Pa·s^n), n_stress, R2_stress.
    """
    x = np.asarray(gamma_dot, dtype=float)
    y = np.asarray(tau, dtype=float)
    keep = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y > 0)
    x, y = x[keep], y[keep]
    if len(x) < 2:
        return {"K_stress": np.nan, "n_stress": np.nan, "R2_stress": np.nan, "n_pts": int(len(x))}

    lx = np.log(x)
    ly = np.log(y)
    n_slope, log_k = np.polyfit(lx, ly, 1)
    yhat = n_slope * lx + log_k
    ss_res = float(np.sum((ly - yhat) ** 2))
    ss_tot = float(np.sum((ly - np.mean(ly)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return {
        "K_stress": float(np.exp(log_k)),
        "n_stress": float(n_slope),
        "R2_stress": float(r2),
        "n_pts": int(len(x)),
    }


def clean_for_powerlaw(
    d: pd.DataFrame,
    *,
    r2_drag_min: float = 0.2,
    mad_k: float = 4.5,
    min_keep: int = 3,
    max_iter: int = 4,
) -> np.ndarray:
    """Return a robust boolean mask for points suitable for stress power-law fitting."""
    keep = (
        np.isfinite(d["gamma_dot_1_s"])
        & np.isfinite(d["tau_Pa"])
        & (d["gamma_dot_1_s"] > 0)
        & (d["tau_Pa"] > 0)
    )

    if "R2_drag" in d.columns:
        keep = keep & (d["R2_drag"].fillna(1.0) >= r2_drag_min)

    keep = keep.astype(bool).to_numpy()

    for _ in range(max_iter):
        if keep.sum() <= min_keep:
            break

        x = d.loc[keep, "gamma_dot_1_s"].to_numpy(dtype=float)
        y = d.loc[keep, "tau_Pa"].to_numpy(dtype=float)
        pl = fit_stress_powerlaw(x, y)
        k_val, n_val = pl["K_stress"], pl["n_stress"]
        if not (np.isfinite(k_val) and np.isfinite(n_val)):
            break

        log_res = np.log(y) - (np.log(k_val) + n_val * np.log(x))
        med = np.median(log_res)
        mad = np.median(np.abs(log_res - med))
        if not np.isfinite(mad) or mad <= 1e-12:
            break

        good_local = np.abs(log_res - med) <= (mad_k * mad)
        if good_local.all():
            break

        keep_idx = np.flatnonzero(keep)
        keep[keep_idx[~good_local]] = False

    return keep


def stage_powerlaw_points(
    rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Apply strict -> relaxed -> raw fallback outlier staging on per-RPM rows.

    Each row must include gamma_dot_1_s, tau_Pa; optional R2_drag.
    """
    if not rows:
        return []

    d = pd.DataFrame(list(rows))

    keep = clean_for_powerlaw(d)
    d_in = d[keep]

    if len(d_in) < 2:
        keep_relaxed = clean_for_powerlaw(
            d, r2_drag_min=0.0, mad_k=8.0, min_keep=2, max_iter=2
        )
        d_in = d[keep_relaxed]

    if len(d_in) < 2:
        raw_mask = (
            np.isfinite(d["gamma_dot_1_s"])
            & np.isfinite(d["tau_Pa"])
            & (d["gamma_dot_1_s"] > 0)
            & (d["tau_Pa"] > 0)
        )
        d_in = d[raw_mask]

    return d_in.to_dict(orient="records")

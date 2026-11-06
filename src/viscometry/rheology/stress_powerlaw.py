"""
Stress-based power-law fitting and outlier staging for rheology characterization.

Ported from APP_V3 Rheology_Newtonian_Non_Newtonian_Material.ipynb (cell 9).
Amplitude-based fits live in prediction.fit_powerlaw; this module fits tau vs gamma_dot.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


def _empty_fit(n_pts: int) -> Dict[str, Any]:
    return {
        "K_stress": np.nan,
        "n_stress": np.nan,
        "R2_stress": np.nan,
        "n_pts": int(n_pts),
        "se_n_stress": np.nan,
        "se_log_K_stress": np.nan,
        "cov_logK_n": np.nan,
    }


def fit_stress_powerlaw(
    gamma_dot: np.ndarray | Sequence[float],
    tau: np.ndarray | Sequence[float],
) -> Dict[str, Any]:
    """
    Fit tau = K * gamma_dot^n in log space.

    Uses OLS on log(tau) vs log(gamma). Slope SE matches a centered design;
    intercept SE is for the uncentered log(K). Standard errors require
    n_pts >= 3 (df = n_pts - 2); otherwise SE fields are NaN.
    """
    x = np.asarray(gamma_dot, dtype=float)
    y = np.asarray(tau, dtype=float)
    keep = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y > 0)
    x, y = x[keep], y[keep]
    n_pts = int(len(x))
    if n_pts < 2:
        return _empty_fit(n_pts)

    lx = np.log(x)
    ly = np.log(y)
    n_slope, log_k = np.polyfit(lx, ly, 1)
    yhat = n_slope * lx + log_k
    ss_res = float(np.sum((ly - yhat) ** 2))
    ss_tot = float(np.sum((ly - np.mean(ly)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0

    se_n = np.nan
    se_log_k = np.nan
    cov_logk_n = np.nan
    df = n_pts - 2
    if df >= 1:
        xbar = float(np.mean(lx))
        sxx = float(np.sum((lx - xbar) ** 2))
        if sxx > 0 and np.isfinite(ss_res):
            mse = ss_res / float(df)
            se_n = float(np.sqrt(mse / sxx))
            se_log_k = float(np.sqrt(mse * (1.0 / n_pts + (xbar ** 2) / sxx)))
            cov_logk_n = float(-mse * xbar / sxx)

    return {
        "K_stress": float(np.exp(log_k)),
        "n_stress": float(n_slope),
        "R2_stress": float(r2),
        "n_pts": n_pts,
        "se_n_stress": float(se_n) if np.isfinite(se_n) else np.nan,
        "se_log_K_stress": float(se_log_k) if np.isfinite(se_log_k) else np.nan,
        "cov_logK_n": float(cov_logk_n) if np.isfinite(cov_logk_n) else np.nan,
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

    # Explicit writable copy: pandas .to_numpy() may return a read-only view.
    keep = np.array(keep.astype(bool), dtype=bool, copy=True)

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
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Apply strict -> relaxed -> raw fallback outlier staging on per-RPM rows.

    Each row must include gamma_dot_1_s, tau_Pa; optional R2_drag.
    Returns (kept_rows, stage_name) where stage_name is strict|relaxed|raw|empty.
    """
    if not rows:
        return [], "empty"

    d = pd.DataFrame(list(rows))

    keep = clean_for_powerlaw(d)
    d_in = d[keep]
    stage = "strict"

    if len(d_in) < 2:
        keep_relaxed = clean_for_powerlaw(
            d, r2_drag_min=0.0, mad_k=8.0, min_keep=2, max_iter=2
        )
        d_in = d[keep_relaxed]
        stage = "relaxed"

    if len(d_in) < 2:
        raw_mask = (
            np.isfinite(d["gamma_dot_1_s"])
            & np.isfinite(d["tau_Pa"])
            & (d["gamma_dot_1_s"] > 0)
            & (d["tau_Pa"] > 0)
        )
        d_in = d[raw_mask]
        stage = "raw"

    if len(d_in) < 2:
        return [], "empty"

    return d_in.to_dict(orient="records"), stage

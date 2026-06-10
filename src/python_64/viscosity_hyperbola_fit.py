"""
DEPRECATED: Legacy hyperbola fit for offline/batch analysis only.

The live measurement path uses rheology_prediction.fit_drag (D = A/(h+h_c)+B).
This module remains for results/auto_runs helpers until those are migrated.

Power-law modified hyperbola for rotational drag vs gap height.

Model: D(h) = a / |h - b|^n
  a: consistency coefficient
  b: zero-gap Z offset (asymptote below measured heights)
  n: flow behavior index (1 = Newtonian, < 1 = shear-thinning)
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
from scipy.optimize import curve_fit

_DENOM_FLOOR = 1e-12


def _hyperbola_powerlaw(x: np.ndarray, a: float, b: float, n: float) -> np.ndarray:
    denom = np.abs(x - b)
    denom = np.maximum(denom, _DENOM_FLOOR)
    return a / np.power(denom, n)


def _hyperbola_powerlaw_fixed_n(n_fixed: float):
    def model(x: np.ndarray, a: float, b: float) -> np.ndarray:
        return _hyperbola_powerlaw(x, a, b, n_fixed)

    return model


def _initial_guesses(x: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
    ptp = max(float(np.ptp(x)), 1e-6)
    b0 = float(np.min(x) - 0.5 * ptp)
    a0 = float((y[0] - y[-1]) * ptp)
    return a0, b0


def fit_hyperbola_powerlaw(
    x: np.ndarray,
    y: np.ndarray,
    *,
    fix_n: Optional[float] = None,
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[str]]:
    """
    Fit (a, b, n) to y = a / |x - b|^n.

    If fix_n is set (e.g. 1.0 for Newtonian), only a and b are optimized.
    Returns (a, b, n, error_message). On failure, coefficients are None.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    if len(x) < 4 or np.ptp(x) <= 0:
        return None, None, None, "Need at least 4 distinct Z points after trimming"

    a0, b0 = _initial_guesses(x, y)
    upper_b = float(np.min(x))

    try:
        if fix_n is not None:
            n_val = float(fix_n)
            model = _hyperbola_powerlaw_fixed_n(n_val)
            popt, _ = curve_fit(
                model,
                x,
                y,
                p0=[a0, b0],
                bounds=([0.0, -np.inf], [np.inf, upper_b]),
                maxfev=20000,
            )
            return float(popt[0]), float(popt[1]), n_val, None

        popt, _ = curve_fit(
            _hyperbola_powerlaw,
            x,
            y,
            p0=[a0, b0, 1.0],
            bounds=(
                [0.0, -np.inf, 0.1],
                [np.inf, upper_b, 2.0],
            ),
            maxfev=20000,
        )
        return float(popt[0]), float(popt[1]), float(popt[2]), None
    except Exception as exc:
        return None, None, None, str(exc)

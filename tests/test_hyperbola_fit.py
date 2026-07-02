"""Tests for hyperbola power-law fit."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from viscometry.analysis.hyperbola_fit import _hyperbola_powerlaw, fit_hyperbola_powerlaw


def test_hyperbola_fit_recovers_synthetic_parameters():
    x = np.linspace(0.05, 2.0, 20)
    a_true, b_true, n_true = 5.0, -0.1, 1.2
    y = _hyperbola_powerlaw(x, a_true, b_true, n_true)
    a, b, n, err = fit_hyperbola_powerlaw(x, y)
    assert err is None
    assert a is not None and b is not None and n is not None
    assert abs(a - a_true) / a_true < 0.15
    assert abs(n - n_true) < 0.3

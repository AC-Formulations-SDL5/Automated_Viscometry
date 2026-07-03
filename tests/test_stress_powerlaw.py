"""Tests for stress power-law fitting and clean_for_powerlaw staging."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from viscometry.rheology.stress_powerlaw import (
    clean_for_powerlaw,
    fit_stress_powerlaw,
    stage_powerlaw_points,
)


class TestStressPowerlaw(unittest.TestCase):
    def test_fit_stress_powerlaw_recovers_known_exponents(self):
        g = np.array([1.0, 10.0, 100.0])
        k_true = 2.5
        n_true = 0.7
        tau = k_true * g**n_true
        pl = fit_stress_powerlaw(g, tau)
        self.assertAlmostEqual(pl["n_stress"], n_true, places=3)
        self.assertAlmostEqual(pl["K_stress"], k_true, places=2)
        self.assertGreater(pl["R2_stress"], 0.99)

    def test_clean_for_powerlaw_drops_outlier(self):
        rows = []
        for i, g in enumerate([5.0, 10.0, 20.0, 40.0, 80.0]):
            rows.append(
                {
                    "gamma_dot_1_s": g,
                    "tau_Pa": 1.2 * g**0.8,
                    "R2_drag": 0.9,
                }
            )
        rows.append({"gamma_dot_1_s": 15.0, "tau_Pa": 500.0, "R2_drag": 0.9})
        d = pd.DataFrame(rows)
        mask = clean_for_powerlaw(d)
        self.assertEqual(int(mask.sum()), 5)

    def test_stage_powerlaw_relaxed_fallback(self):
        rows = [
            {"gamma_dot_1_s": 10.0, "tau_Pa": 5.0, "R2_drag": 0.05},
            {"gamma_dot_1_s": 20.0, "tau_Pa": 8.0, "R2_drag": 0.05},
            {"gamma_dot_1_s": 30.0, "tau_Pa": 11.0, "R2_drag": 0.9},
        ]
        staged = stage_powerlaw_points(rows)
        self.assertGreaterEqual(len(staged), 2)


if __name__ == "__main__":
    unittest.main()

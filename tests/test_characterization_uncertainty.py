"""Tests for stress-fit uncertainty fields and pathway_ambiguous."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from viscometry.rheology.characterization import (
    _stress_uncertainty_fields,
    compute_cell_characterization,
)
from viscometry.rheology.constants import N_STRESS_SE_FLOOR, NEWTONIAN_N_LOW
from viscometry.rheology.stress_powerlaw import fit_stress_powerlaw


def _good_fit(rpm: float, a: float, tau: float) -> dict:
    return {
        "success": True,
        "A": a,
        "tau_Pa_hit": tau,
        "R2": 0.99,
        "drag_model": "app_v6_hyperbola",
    }


class TestCharacterizationUncertainty(unittest.TestCase):
    def test_floor_applied_to_tiny_fit_se(self):
        g = np.array([1.0, 10.0, 100.0, 200.0])
        tau = 2.0 * g**0.9
        pl = fit_stress_powerlaw(g, tau)
        fields = _stress_uncertainty_fields(pl)
        self.assertIsNotNone(fields["se_n_stress"])
        self.assertGreaterEqual(fields["se_eff_n_stress"], N_STRESS_SE_FLOOR)

    def test_ambiguous_near_newtonian_threshold(self):
        # Force a wide se_eff by injecting a large fit SE
        pl = {
            "K_stress": 1.0,
            "n_stress": 0.905,
            "R2_stress": 0.99,
            "n_pts": 5,
            "se_n_stress": 0.05,
            "se_log_K_stress": 0.1,
            "cov_logK_n": 0.0,
        }
        fields = _stress_uncertainty_fields(pl)
        self.assertTrue(fields["pathway_ambiguous"])
        self.assertLess(fields["n_stress_ci_low"], NEWTONIAN_N_LOW)
        self.assertGreater(fields["n_stress_ci_high"], NEWTONIAN_N_LOW)

    def test_compute_cell_characterization_includes_se_and_keeps_pathway(self):
        # Mild thinning: n around 0.7 with several RPMs
        fits = {}
        for i, rpm in enumerate([10.0, 20.0, 40.0, 80.0]):
            g_scale = rpm
            fits[rpm] = _good_fit(rpm, a=0.1 / (i + 1), tau=5.0 * (g_scale**0.7))
        result = compute_cell_characterization(fits, cell_id=1)
        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("pathway"), "mild_shear_thinning")
        self.assertIn("se_eff_n_stress", result)
        self.assertIn("pathway_ambiguous", result)
        self.assertIn("stress_fit_stage", result)


if __name__ == "__main__":
    unittest.main()

"""Tests for unified rheology prediction (notebook parity)."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parent


from viscometry.rheology.constants import FIT_R2_MIN, H_C_UNIVERSAL_MM
from viscometry.rheology.prediction import (
    amplitude_to_viscosity,
    drag_model_curve,
    fit_drag,
    passes_r2_gate,
    predict_rheology,
)


class TestRheologyPrediction(unittest.TestCase):
    def test_fit_drag_silicone_sweep(self):
        path = _ROOT / "results" / "Auto-runs" / "height_normalized.csv"
        if not path.is_file():
            self.skipTest("height_normalized.csv not available")
        wide = pd.read_csv(path)
        col = next(c for c in wide.columns if "kcp" in c.lower())
        sub = wide[["Height", col]].dropna().sort_values("Height")
        h = sub["Height"].values - sub["Height"].min()
        m = re.match(
            r"^(?P<nom>[\d.]+)kcp_(?P<mu>[\d.]+)_torque_%_rpm_(?P<rpm>[\d.]+)$",
            col,
        )
        self.assertIsNotNone(m)
        rpm = float(m.group("rpm"))
        d = sub[col].values / rpm
        fit = fit_drag(h, d, hc=H_C_UNIVERSAL_MM)
        self.assertGreater(fit["R2"], 0.95)
        self.assertGreater(fit["A"], 0)
        mu = float(amplitude_to_viscosity([fit["A"]])[0])
        self.assertAlmostEqual(mu, 1118.0, delta=50.0)

    def test_predict_rheology_carbopol_multi_rpm(self):
        path = _ROOT / "results" / "auto_runs" / "Polymers" / "all_carbopol.csv"
        if not path.is_file():
            self.skipTest("all_carbopol.csv not available")
        raw = pd.read_csv(path)
        for c in ("RPM", "Z_Height_mm", "Torque_%"):
            raw[c] = pd.to_numeric(raw[c], errors="coerce")
        cell = int(raw["cell"].dropna().iloc[0])
        sub = raw[raw["cell"] == cell]
        rpms = sorted(sub["RPM"].dropna().unique())[:4]
        hs, ts = [], []
        for r in rpms:
            gg = sub[np.isclose(sub["RPM"], r)].sort_values("Z_Height_mm")
            h = gg["Z_Height_mm"].values - gg["Z_Height_mm"].min()
            hs.append(h)
            ts.append(gg["Torque_%"].values)
        res = predict_rheology(hs, ts, rpms)
        self.assertEqual(res["mode"], "powerlaw")
        self.assertEqual(res["regime"], "shear-thinning")
        self.assertAlmostEqual(res["n"], -0.18, delta=0.05)
        self.assertGreater(res["R2_powerlaw"], 0.85)

    def test_r2_gate(self):
        self.assertTrue(passes_r2_gate(0.85))
        self.assertFalse(passes_r2_gate(0.5))
        self.assertFalse(passes_r2_gate(float("nan")))

    def test_flat_data_low_r2(self):
        h = np.linspace(0, 5, 20)
        d = np.full(20, 3.0) + np.random.default_rng(0).normal(0, 0.5, 20)
        fit = fit_drag(h, d, hc=H_C_UNIVERSAL_MM)
        self.assertFalse(passes_r2_gate(fit["R2"], FIT_R2_MIN))

    def test_drag_model_curve(self):
        h = np.array([0.0, 1.0, 2.0])
        y = drag_model_curve(h, A=1.0, B=0.1, hc=0.2774)
        self.assertEqual(len(y), 3)


if __name__ == "__main__":
    unittest.main()

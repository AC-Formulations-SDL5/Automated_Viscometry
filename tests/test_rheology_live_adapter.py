"""Tests for live rheology adapter (pretrim, R² gate, cell-level prediction)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

import numpy as np

_ROOT = Path(__file__).resolve().parent


from viscometry.rheology.constants import FIT_R2_MIN, H_C_UNIVERSAL_MM
from viscometry.rheology.live_adapter import (
    fit_sweep_drag,
    predict_cell_rheology,
    prepare_sweep_arrays,
)
from viscometry.rheology.prediction import drag_model_curve


def _sweep_rows(
    cell_id: int = 1,
    rpm: float = 10.0,
    *,
    A: float = 0.6,
    B: float = 0.05,
    n_points: int = 12,
    height_start: float = 1.0,
    height_step: float = 0.35,
    torque_scale: float = 1.0,
) -> list:
    hc = H_C_UNIVERSAL_MM
    rows = []
    for i in range(n_points):
        h = height_start + i * height_step
        d = float(drag_model_curve(h, A, B, hc))
        torque = d * rpm * torque_scale
        rows.append(
            {
                "cell_id": cell_id,
                "rpm": rpm,
                "height": h,
                "rotational_drag": d,
                "torque_percent": torque,
                "timestamp": float(i),
            }
        )
    return rows


class TestRheologyLiveAdapter(unittest.TestCase):
    def test_torque_floor_removes_pre_contact_points(self):
        low_torque = [
            {
                "height": 0.2,
                "rotational_drag": 0.01,
                "torque_percent": 5.0,
            },
            {
                "height": 0.4,
                "rotational_drag": 0.02,
                "torque_percent": 8.0,
            },
        ]
        good = _sweep_rows(n_points=10, torque_scale=50.0)
        points = low_torque + [{k: v for k, v in r.items() if k != "cell_id"} for r in good]
        h_norm, torque_pct, _d, _no, _pz, _pd = prepare_sweep_arrays(
            points, torque_floor_pct=25.0, hit_point_z=None
        )
        self.assertEqual(len(h_norm), 10)
        self.assertTrue(np.all(torque_pct >= 25.0))

    def test_hit_point_filter_negative_z_keeps_shallower(self):
        """Machine descent: shallower Z is larger; keep hitpoint and gap above (h >= hitpoint_z)."""
        points = []
        for i in range(10):
            z = -65.20 - i * 0.02
            points.append(
                {
                    "height": z,
                    "rotational_drag": 1.0 + i * 0.05,
                    "torque_percent": 50.0,
                }
            )
        hitpoint_z = -65.28
        h_all, _t, _d, _no, pre_z_all, _pd = prepare_sweep_arrays(
            points, torque_floor_pct=0.0, hit_point_z=None
        )
        h_hit, _t2, _d2, _no2, pre_z_hit, _pd2 = prepare_sweep_arrays(
            points, torque_floor_pct=0.0, hit_point_z=hitpoint_z
        )
        self.assertEqual(len(h_all), 10)
        self.assertEqual(len(h_hit), 5)
        self.assertTrue(all(z >= hitpoint_z - 1e-9 for z in pre_z_hit))
        self.assertAlmostEqual(max(pre_z_hit), -65.20, places=2)
        self.assertAlmostEqual(min(pre_z_hit), hitpoint_z, places=2)

    def test_r2_gate_rejects_noisy_flat_sweep(self):
        h = np.linspace(0.5, 4.0, 10)
        torque = np.full(10, 80.0) + np.random.default_rng(1).normal(0, 15.0, 10)
        result = fit_sweep_drag(h, torque, 10.0, 0.0, min_r2=FIT_R2_MIN)
        self.assertFalse(result["success"])
        self.assertIn("R²", result["error"] or "")

    def test_predict_cell_rheology_single_rpm_newtonian(self):
        data = _sweep_rows(rpm=12.0, A=0.55)
        per_rpm, summary = predict_cell_rheology(
            1, [12.0], data, torque_floor_pct=0.0, hit_point_z=None
        )
        self.assertTrue(per_rpm[12.0]["success"])
        self.assertTrue(summary["success"])
        self.assertEqual(summary["mode"], "newtonian")
        self.assertEqual(summary["regime"], "Newtonian")

    def test_predict_cell_rheology_multi_rpm_powerlaw(self):
        data = []
        for rpm, A in ((5.0, 1.0), (15.0, 0.72), (30.0, 0.52)):
            data.extend(_sweep_rows(rpm=rpm, A=A))
        per_rpm, summary = predict_cell_rheology(
            1, [5.0, 15.0, 30.0], data, torque_floor_pct=0.0, hit_point_z=None
        )
        for rpm in (5.0, 15.0, 30.0):
            self.assertTrue(per_rpm[rpm]["success"], per_rpm[rpm].get("error"))
        self.assertTrue(summary["success"])
        self.assertEqual(summary["mode"], "powerlaw")
        self.assertIn(summary["regime"], ("shear-thinning", "Newtonian", "shear-thickening"))


if __name__ == "__main__":
    unittest.main()

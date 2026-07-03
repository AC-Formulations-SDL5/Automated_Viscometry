"""Unit tests for LiveCellSession incremental characterization."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from viscometry.rheology.constants import H_C_UNIVERSAL_MM
from viscometry.rheology.live_engine import CharacterizationManager, LiveCellSession
from viscometry.rheology.prediction import drag_model_curve


def _feed_sweep(session: LiveCellSession, rpm: float, *, A: float = 0.6, n_z: int = 8) -> None:
    hc = H_C_UNIVERSAL_MM
    for i in range(n_z):
        h = 1.0 + i * 0.35
        d = float(drag_model_curve(h, A, 0.05, hc))
        session.add_point(h, rpm, d * rpm)
        session.on_z_slice_complete(h)


class TestLiveEngineSession(unittest.TestCase):
    def test_provisional_rezero_shifts_with_new_minimum(self):
        session = LiveCellSession(1, [10.0], torque_floor_pct=0.0)
        ev1 = session.add_point(2.0, 10.0, 50.0)
        self.assertAlmostEqual(ev1[0]["h_norm"], 0.0, places=3)
        ev2 = session.add_point(1.5, 10.0, 48.0)
        # New minimum height re-zeros the incoming point.
        self.assertAlmostEqual(ev2[0]["h_norm"], 0.0, places=3)
        ev3 = session.add_point(2.5, 10.0, 52.0)
        self.assertAlmostEqual(ev3[0]["h_norm"], 1.0, places=3)

    def test_min_four_points_before_rpm_fit(self):
        session = LiveCellSession(1, [10.0], torque_floor_pct=0.0)
        for i in range(3):
            session.add_point(1.0 + i * 0.3, 10.0, 40.0 + i)
            events = session.on_z_slice_complete(1.0 + i * 0.3)
        fit_events = [e for e in events if e.get("type") == "rpm_fit"]
        self.assertEqual(len(fit_events), 0)
        session.add_point(2.0, 10.0, 45.0)
        events = session.on_z_slice_complete(2.0)
        fit_events = [e for e in events if e.get("type") == "rpm_fit"]
        self.assertEqual(len(fit_events), 1)
        self.assertTrue(fit_events[0]["provisional"])

    def test_hit_point_refit_drops_deeper_points(self):
        session = LiveCellSession(1, [10.0], torque_floor_pct=0.0)
        for z in (-65.20, -65.24, -65.28, -65.32, -65.36, -65.40):
            session.add_point(z, 10.0, 50.0)
            session.on_z_slice_complete(z)
        before = session._rpm_fits[10.0]["n_points_used"]
        session.set_hit_point_z(-65.28)
        after = session._rpm_fits[10.0]["n_points_used"]
        self.assertLess(after, before)

    def test_finalize_marks_non_provisional(self):
        session = LiveCellSession(1, [10.0], torque_floor_pct=0.0)
        _feed_sweep(session, 10.0)
        events = session.finalize_cell()
        fit_events = [e for e in events if e.get("type") == "rpm_fit"]
        self.assertTrue(fit_events)
        self.assertFalse(fit_events[0]["provisional"])
        summary = [e for e in events if e.get("type") == "summary"][0]
        self.assertFalse(summary["provisional"])
        self.assertTrue(summary["success"])

    def test_manager_start_and_reset(self):
        mgr = CharacterizationManager()
        mgr.start_cell(2, [5.0, 15.0])
        self.assertIsNotNone(mgr.get_session(2))
        mgr.reset_all()
        self.assertIsNone(mgr.get_session(2))


if __name__ == "__main__":
    unittest.main()

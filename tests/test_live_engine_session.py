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

    def test_z_slice_emits_no_rpm_fit(self):
        session = LiveCellSession(1, [10.0], torque_floor_pct=0.0)
        for i in range(4):
            session.add_point(1.0 + i * 0.3, 10.0, 40.0 + i)
            events = session.on_z_slice_complete(1.0 + i * 0.3)
            fit_events = [e for e in events if e.get("type") == "rpm_fit"]
            self.assertEqual(len(fit_events), 0)
            self.assertEqual(events[0]["type"], "z_slice")

    def test_fit_only_after_finalize_with_min_four_points(self):
        session = LiveCellSession(1, [10.0], torque_floor_pct=0.0)
        for i in range(3):
            session.add_point(1.0 + i * 0.3, 10.0, 40.0 + i)
            session.on_z_slice_complete(1.0 + i * 0.3)
        events = session.finalize_cell()
        fit_events = [e for e in events if e.get("type") == "rpm_fit"]
        self.assertEqual(len(fit_events), 0)

        session2 = LiveCellSession(1, [10.0], torque_floor_pct=0.0)
        for i in range(4):
            session2.add_point(1.0 + i * 0.3, 10.0, 40.0 + i)
            session2.on_z_slice_complete(1.0 + i * 0.3)
        events2 = session2.finalize_cell()
        fit_events2 = [e for e in events2 if e.get("type") == "rpm_fit"]
        self.assertEqual(len(fit_events2), 1)
        self.assertFalse(fit_events2[0]["provisional"])

    def test_hit_point_applied_at_finalize_drops_deeper_points(self):
        zs = (-65.20, -65.24, -65.28, -65.32, -65.36, -65.40)
        session_no_hit = LiveCellSession(1, [10.0], torque_floor_pct=0.0)
        for z in zs:
            session_no_hit.add_point(z, 10.0, 50.0)
            session_no_hit.on_z_slice_complete(z)
        session_no_hit.finalize_cell()
        without_hit = session_no_hit._rpm_fits[10.0]["n_points_used"]

        session_hit = LiveCellSession(1, [10.0], torque_floor_pct=0.0)
        for z in zs:
            session_hit.add_point(z, 10.0, 50.0)
            session_hit.on_z_slice_complete(z)
        events = session_hit.set_hit_point_z(-65.28)
        self.assertEqual(events, [])
        self.assertEqual(session_hit.hit_point_z, -65.28)
        self.assertEqual(session_hit._rpm_fits, {})
        session_hit.finalize_cell()
        with_hit = session_hit._rpm_fits[10.0]["n_points_used"]
        self.assertLess(with_hit, without_hit)

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

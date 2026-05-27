#!/usr/bin/env python3
"""Unit checks for fail-safe logic, R² confidence, and virtual CNC teardown order."""

import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_ROOT, "src", "python_64"))

from feedback_helper_function import _linear_regression_extended, RotationalDragFeedbackController
from cnc_controller import CNC_Machine, CNCMotionError


class TestFailSafeComparator(unittest.TestCase):
    def test_sub_threshold_streak(self):
        threshold = 0.8 * 0.75
        self.assertAlmostEqual(threshold, 0.6)
        confidences = [0.55, 0.58, 0.59, 0.57, 0.56]
        streak = 0
        for c in confidences:
            if c < threshold:
                streak += 1
            else:
                streak = 0
        self.assertEqual(streak, 5)

    def test_at_threshold_does_not_streak(self):
        threshold = 0.6
        self.assertFalse(0.60 < threshold)
        self.assertTrue(0.59 < threshold)


class TestR2ConfidenceValidity(unittest.TestCase):
    def test_flat_drag_does_not_count_as_r2_hit(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [1.0, 1.0, 1.0, 1.0, 1.0]
        _, _, r2, ss_tot = _linear_regression_extended(x, y)
        self.assertEqual(ss_tot, 0.0)
        self.assertEqual(r2, 0.0)
        hit_r2_drag = ss_tot > 0 and r2 < 0.975
        self.assertFalse(hit_r2_drag)

    def test_controller_confidence_not_inflated_by_flat_data(self):
        ctrl = RotationalDragFeedbackController(
            feedback_enabled=True,
            min_data_points=3,
            r2_drag_min=0.975,
            r2_cv_min=0.975,
            r2_slope_min=0.975,
            hit_point_confidence_threshold=0.8,
        )
        for i in range(8):
            z = -65.0 - i * 0.02
            ctrl.add_measurements_at_z(z, {0.8: [{"torque_percent": 10.0, "rotational_drag": 1.0}]})
        trend = ctrl.analyze_trend_for_rpm(0.8)
        self.assertTrue(trend["valid"])
        self.assertLess(trend["hit_confidence"], 0.6)


class TestVirtualCNCRetract(unittest.TestCase):
    def setUp(self):
        os.chdir(_ROOT)

    def test_retract_before_concurrent_message(self):
        cnc = CNC_Machine(virtual=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            cnc.retract_z_at_cell(10, 62, z_safe=0, speed=500)
        out = buf.getvalue()
        self.assertIn("VIRTUAL GCODE", out)
        self.assertIn("Z0", out)

    def test_out_of_bounds_raises(self):
        cnc = CNC_Machine(virtual=True)
        with self.assertRaises(CNCMotionError):
            cnc.move_to_point(x=9999, y=0, z=0)


class TestFinishCellOrder(unittest.TestCase):
    def setUp(self):
        os.chdir(_ROOT)

    def test_retract_logged_before_concurrent(self):
        import all_cells_with_rotational_drag_feedback as exp

        cnc = CNC_Machine(virtual=True)
        client = MagicMock()
        pump = MagicMock()
        log = []

        def fake_fill(_pump):
            log.append("fill")

        def fake_motor(_pump):
            log.append("motor")

        orig_fill = exp._pump_fill_station1
        orig_motor = exp._motor1_start
        exp._pump_fill_station1 = fake_fill
        exp._motor1_start = fake_motor
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                exp._finish_cell_measurement(
                    cnc, client, pump, global_cell=11,
                    exit_reason="fail_safe", start_wash_prefill=True,
                )
            out = buf.getvalue()
            retract_pos = out.find("returned to safe Z position")
            concurrent_pos = out.find("[CONCURRENT]")
            self.assertGreater(retract_pos, -1)
            self.assertGreater(concurrent_pos, -1)
            self.assertLess(retract_pos, concurrent_pos)
            self.assertEqual(log, ["fill", "motor"])
        finally:
            exp._pump_fill_station1 = orig_fill
            exp._motor1_start = orig_motor

    def test_no_prefill_when_retract_would_fail(self):
        import all_cells_with_rotational_drag_feedback as exp

        cnc = CNC_Machine(virtual=True)
        client = MagicMock()
        pump = MagicMock()
        log = []

        def failing_retract(*_a, **_k):
            raise CNCMotionError("simulated failure")

        cnc.retract_z_at_cell = failing_retract
        orig_fill = exp._pump_fill_station1
        exp._pump_fill_station1 = lambda _p: log.append("fill")
        try:
            ft, ok, reason = exp._finish_cell_measurement(
                cnc, client, pump, 11, "fail_safe", start_wash_prefill=True,
            )
            self.assertFalse(ok)
            self.assertIsNone(ft)
            self.assertEqual(log, [])
            pump.send_tag.assert_called()
        finally:
            exp._pump_fill_station1 = orig_fill


if __name__ == "__main__":
    unittest.main()

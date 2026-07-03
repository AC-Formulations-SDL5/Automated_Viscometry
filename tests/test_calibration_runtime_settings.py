#!/usr/bin/env python3
"""Tests for calibration/recalibration runtime flag sync and liquid-contact skip."""

import copy
import os
import sys
import unittest
from unittest.mock import patch

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from viscometry.run import controller as ctrl
from viscometry.run import settings as run_settings


def _default_runtime_payload() -> dict:
    return {
        "experiment_name": "",
        "testing_mode": "custom",
        "selected_rows": [2],
        "selected_cells": [1],
        "test_rpms": [0.8],
        "cell_rpm_map": {},
        "cell_content_map": {},
        "z_step_size": -0.02,
        "measurement_duration": 40.0,
        "sample_interval": 5.0,
        "dwell_seconds": 2.0,
        "inter_rpm_pause": 2.0,
        "feedback_control_enabled": True,
        "smart_early_exit_enabled": True,
        "fail_safe_enabled": True,
        "smart_cv_threshold": 0.005,
        "smart_window_size": 3,
        "min_data_points_for_trend": 8,
        "r2_drag_min": 0.975,
        "r2_cv_min": 0.975,
        "r2_slope_min": 0.975,
        "hit_point_confidence_threshold": 0.8,
        "weight_2nd_deriv_drag": 0.2,
        "weight_2nd_deriv_cv": 0.2,
        "weight_2nd_deriv_slope": 0.2,
        "weight_r2_drag": 0.2,
        "weight_r2_cv": 0.2,
        "weight_r2_slope": 0.2,
        "baseline_n_calibration": 10,
        "baseline_z_threshold": 5.0,
        "torque_break_threshold": 100.0,
        "calibration_mode": False,
        "recalibrate_individual_cells": False,
        "recalibration_cells": {},
        "recalibration_ignore_max_z_travel": False,
        "low_torque_liquid_contact_skip_enabled": True,
        "low_torque_liquid_contact_threshold_pct": 25.0,
        "viscosity_prediction_mode": "off",
        "characterization_mode": "off",
        "characterization_enabled": False,
        "save_all_sample_data": False,
        "z_start_offset_mm": 0.4,
        "discovery_mode_enabled": False,
        "discovery_eta_guess_map": {},
        "discovery_probe_duration_s": 60.0,
        "discovery_duck_torque_pct": 80.0,
        "discovery_handoff_pause_s": 10.0,
    }


def _snapshot_runtime_settings():
    return {
        name: copy.deepcopy(getattr(run_settings, name))
        for name in ctrl._RUNTIME_SETTING_NAMES
    }


def _restore_runtime_settings(snapshot: dict) -> None:
    for name, value in snapshot.items():
        setattr(run_settings, name, copy.deepcopy(value))
    ctrl._sync_controller_runtime_settings()


class TestCalibrationRuntimeSettings(unittest.TestCase):
    def setUp(self):
        self._saved = _snapshot_runtime_settings()

    def tearDown(self):
        _restore_runtime_settings(self._saved)

    def _apply(self, payload: dict) -> None:
        with patch.object(
            ctrl.web_interface,
            "get_runtime_settings",
            return_value=copy.deepcopy(payload),
        ):
            ctrl.apply_runtime_settings_from_web()

    def test_sync_after_full_calibration_start(self):
        payload = _default_runtime_payload()
        payload.update(
            {
                "calibration_mode": True,
                "testing_mode": "full",
                "low_torque_liquid_contact_skip_enabled": True,
            }
        )
        self._apply(payload)

        self.assertTrue(ctrl.CALIBRATION_MODE)
        self.assertTrue(run_settings.CALIBRATION_MODE)
        self.assertFalse(ctrl.LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED)
        self.assertFalse(run_settings.use_liquid_z_skip())
        mode, cells = ctrl.get_selected_cells()
        self.assertEqual(mode, "calibration")
        self.assertEqual(cells, list(range(1, 19)))

    def test_sync_after_recalibration_start(self):
        payload = _default_runtime_payload()
        payload.update(
            {
                "recalibrate_individual_cells": True,
                "calibration_mode": False,
                "recalibration_cells": {5: -65.2},
                "testing_mode": "custom",
                "selected_cells": [5],
            }
        )
        self._apply(payload)

        self.assertTrue(ctrl.RECALIBRATE_INDIVIDUAL_CELLS)
        self.assertEqual(ctrl.RECALIBRATION_CELLS, {5: -65.2})
        self.assertFalse(run_settings.use_liquid_z_skip())
        mode, cells = ctrl.get_selected_cells()
        self.assertEqual(mode, "recalibration")
        self.assertEqual(cells, [5])

    def test_regular_run_liquid_skip_still_on(self):
        payload = _default_runtime_payload()
        payload["low_torque_liquid_contact_skip_enabled"] = True
        self._apply(payload)

        self.assertTrue(ctrl.LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED)
        self.assertTrue(run_settings.use_liquid_z_skip())
        mode, cells = ctrl.get_selected_cells()
        self.assertEqual(mode, "custom")
        self.assertEqual(cells, [1])

    def test_calibration_override_wins_over_payload(self):
        payload = _default_runtime_payload()
        payload.update(
            {
                "calibration_mode": True,
                "testing_mode": "full",
                "low_torque_liquid_contact_skip_enabled": True,
            }
        )
        self._apply(payload)

        self.assertFalse(ctrl.LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED)
        self.assertFalse(run_settings.LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED)
        self.assertFalse(run_settings.use_liquid_z_skip())

    def test_characterization_mode_syncs_from_web(self):
        payload = _default_runtime_payload()
        payload.update(
            {
                "characterization_mode": "on",
                "characterization_enabled": True,
                "viscosity_prediction_mode": "off",
            }
        )
        self._apply(payload)

        self.assertEqual(ctrl.CHARACTERIZATION_MODE, "on")
        self.assertEqual(run_settings.CHARACTERIZATION_MODE, "on")
        self.assertEqual(ctrl.VISCOSITY_PREDICTION_MODE, "on")

    def test_legacy_viscosity_prediction_without_characterization(self):
        payload = _default_runtime_payload()
        payload.update(
            {
                "viscosity_prediction_mode": "on",
                "predicted_viscosity_enabled": True,
                "characterization_mode": "off",
            }
        )
        self._apply(payload)

        self.assertEqual(ctrl.CHARACTERIZATION_MODE, "off")
        self.assertEqual(ctrl.VISCOSITY_PREDICTION_MODE, "on")


if __name__ == "__main__":
    unittest.main()

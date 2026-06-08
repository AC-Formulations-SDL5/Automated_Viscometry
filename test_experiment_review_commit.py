#!/usr/bin/env python3
"""Unit tests for experiment review commit and all_data key handling."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_ROOT, "src", "python_64"))

from web_interface import ViscometryWebInterface, _coerce_all_data_keys


def _stringified_all_data_fixture():
    return {
        "1": {
            "65.5": {
                "0.8": [
                    {
                        "torque_percent": 10.0,
                        "elapsed_time": 5.0,
                    }
                ]
            }
        }
    }


def _native_all_data_fixture():
    return {
        1: {
            65.5: {
                0.8: [
                    {
                        "torque_percent": 12.0,
                        "elapsed_time": 6.0,
                    }
                ]
            }
        }
    }


class TestCoerceAllDataKeys(unittest.TestCase):
    def test_stringified_keys_coerced_to_numeric(self):
        coerced = _coerce_all_data_keys(_stringified_all_data_fixture())
        self.assertIn(1, coerced)
        self.assertIn(65.5, coerced[1])
        self.assertIn(0.8, coerced[1][65.5])
        measurements = coerced[1][65.5][0.8]
        self.assertEqual(len(measurements), 1)
        rpm = 0.8
        self.assertTrue(rpm > 0)

    def test_native_keys_unchanged(self):
        native = _native_all_data_fixture()
        coerced = _coerce_all_data_keys(native)
        self.assertEqual(list(coerced.keys()), [1])
        self.assertEqual(list(coerced[1].keys()), [65.5])
        self.assertEqual(list(coerced[1][65.5].keys()), [0.8])


class TestExperimentReviewCommit(unittest.TestCase):
    def setUp(self):
        self.iface = ViscometryWebInterface(port=5099)
        self.iface.socketio = MagicMock()
        self.iface.experiment_history = []
        self.iface._persist_experiment_history = MagicMock()

        self.session_id = "test-session-001"
        self.iface.experiment_review_session = {
            "session_id": self.session_id,
            "completion_order": [1],
            "cells": {
                "1": {
                    "cell_id": 1,
                    "measurements": [
                        {
                            "height": 65.5,
                            "rotational_drag": 12.5,
                            "torque_percent": 10.0,
                            "rpm": 0.8,
                            "timestamp": 1_700_000_000.0,
                        }
                    ],
                    "termination_reason": "normal",
                    "decision": "saved",
                }
            },
            "queued_saves": {"1": True},
        }
        self.iface._experiment_review_run_context = {
            "all_data": _native_all_data_fixture(),
            "timestamp": "20260608_120000",
            "mode": "custom",
            "experiment_name": "unit_test",
            "termination_by_cell": {"1": "normal"},
            "completed_cells": [1],
            "run_start_ts": 1_700_000_000.0,
            "runtime_settings": {},
            "predicted_viscosity_results": {},
        }

    def test_stash_preserves_numeric_keys(self):
        iface = ViscometryWebInterface(port=5098)
        iface.socketio = MagicMock()
        iface.runtime_settings = {}
        iface.experiment_start_ts = 1_700_000_000.0
        iface.predicted_viscosity_results = {}

        native = _native_all_data_fixture()
        iface.set_experiment_review_run_context(
            native,
            "20260608_120000",
            "custom",
            "unit_test",
            termination_by_cell={1: "normal"},
            completed_cells=[1],
        )
        stashed = iface._experiment_review_run_context["all_data"]
        self.assertIn(1, stashed)
        self.assertIn(65.5, stashed[1])
        self.assertIn(0.8, stashed[1][65.5])
        rpm = 0.8
        self.assertTrue(rpm > 0)

    @patch("all_cells_with_rotational_drag_feedback.save_dynamic_analysis_data")
    def test_commit_happy_path_clears_session(self, mock_save):
        mock_save.return_value = "dynamic_analysis_unit_test_custom_20260608_120000.csv"
        result = self.iface.commit_experiment_review(self.session_id)

        self.assertIsNone(self.iface.experiment_review_session)
        self.assertIsNone(self.iface._experiment_review_run_context)
        self.assertEqual(result["saved_cells"], [1])
        self.assertEqual(result["csv_filename"], mock_save.return_value)
        mock_save.assert_called_once()
        saved_all_data = mock_save.call_args[0][0]
        self.assertIn(1, saved_all_data)
        self.assertIn(0.8, saved_all_data[1][65.5])

    @patch("all_cells_with_rotational_drag_feedback.save_dynamic_analysis_data")
    def test_commit_failure_retains_session(self, mock_save):
        mock_save.side_effect = TypeError("'>' not supported between instances of 'str' and 'int'")
        with self.assertRaises(ValueError) as ctx:
            self.iface.commit_experiment_review(self.session_id)

        self.assertIn("Failed to write experiment CSV", str(ctx.exception))
        self.assertIsNotNone(self.iface.experiment_review_session)
        self.assertIsNotNone(self.iface._experiment_review_run_context)
        self.assertEqual(
            self.iface.experiment_review_session.get("session_id"),
            self.session_id,
        )


if __name__ == "__main__":
    unittest.main()

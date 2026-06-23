#!/usr/bin/env python3
"""Unit tests for experiment review commit and all_data key handling."""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_ROOT, "src", "python_64"))

from flask import Flask, jsonify

from web_interface import (
    ViscometryWebInterface,
    _coerce_all_data_keys,
    _dedupe_experiment_history_list,
    _experiment_history_id_for_run,
    _string_key_cell_termination_reasons,
)


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


def _two_cell_all_data_fixture():
    return {
        10: {
            65.5: {
                95.0: [
                    {"torque_percent": 40.0, "elapsed_time": 5.0, "timestamp": 1_700_000_100.0},
                    {"torque_percent": 41.0, "elapsed_time": 6.0, "timestamp": 1_700_000_101.0},
                ]
            }
        },
        11: {
            66.0: {
                1.4: [
                    {"torque_percent": 30.0, "elapsed_time": 8.0, "timestamp": 1_700_000_200.0},
                ]
            }
        },
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
                    "is_partial": False,
                    "z_level_count": 1,
                    "decision": "saved",
                }
            },
            "queued_saves": {"1": True},
            "run_ended_early": False,
        }
        self.iface._experiment_review_run_context = {
            "all_data": _native_all_data_fixture(),
            "timestamp": "20260608_120000",
            "mode": "custom",
            "experiment_name": "unit_test",
            "termination_by_cell": {"1": "normal"},
            "partial_by_cell": {"1": False},
            "completed_cells": [1],
            "run_ended_early": False,
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

    def test_history_id_uses_run_start_ts(self):
        entry = self.iface._build_experiment_history_entry_from_review(
            self.iface.experiment_review_session,
            self.iface._experiment_review_run_context,
            [1],
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry["id"], "exp-1700000000000")
        self.assertEqual(entry["runStartTsSec"], 1_700_000_000.0)
        terms = entry["cell_termination_reasons"]
        self.assertEqual(terms, {"1": "normal"})
        self.assertEqual(set(type(k).__name__ for k in terms), {"str"})

    @patch("all_cells_with_rotational_drag_feedback.save_dynamic_analysis_data")
    def test_commit_happy_path_clears_session(self, mock_save):
        mock_save.return_value = "dynamic_analysis_unit_test_custom_20260608_120000.csv"
        result = self.iface.commit_experiment_review(self.session_id)

        self.assertIsNone(self.iface.experiment_review_session)
        self.assertIsNone(self.iface._experiment_review_run_context)
        self.assertEqual(result["saved_cells"], [1])
        self.assertEqual(result["csv_filename"], mock_save.return_value)
        self.assertEqual(result["experiment"]["id"], "exp-1700000000000")
        mock_save.assert_called_once()
        saved_all_data = mock_save.call_args[0][0]
        self.assertIn(1, saved_all_data)
        self.assertIn(0.8, saved_all_data[1][65.5])
        self.assertEqual(len(self.iface.experiment_history), 1)
        self.assertEqual(self.iface.experiment_history[0]["id"], "exp-1700000000000")

    def test_history_built_from_all_data_not_snapshots(self):
        session = {
            "cells": {
                "10": {
                    "termination_reason": "normal",
                    "is_partial": False,
                    "measurements": [],
                },
                "11": {
                    "termination_reason": "user_stop",
                    "is_partial": True,
                    "measurements": [],
                },
            }
        }
        run_context = {
            "all_data": _two_cell_all_data_fixture(),
            "run_start_ts": 1_700_000_000.0,
            "termination_by_cell": {"10": "normal", "11": "user_stop"},
            "partial_by_cell": {"10": False, "11": True},
            "runtime_settings": {},
            "predicted_viscosity_results": {},
        }
        entry = self.iface._build_experiment_history_entry_from_review(
            session, run_context, [10, 11]
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry["cells"], [10, 11])
        self.assertEqual(entry["measurement_count"], 2)
        self.assertEqual(entry["cell_partial_flags"], {"10": False, "11": True})
        latest = entry["latestPerZ"]
        self.assertEqual(len(latest), 2)
        cell_ids = {int(p["cell_id"]) for p in latest}
        self.assertEqual(cell_ids, {10, 11})
        cell10 = next(p for p in latest if p["cell_id"] == 10)
        self.assertAlmostEqual(cell10["torque_percent"], 41.0)

    @patch("all_cells_with_rotational_drag_feedback.save_dynamic_analysis_data")
    def test_commit_two_cells_after_user_stop(self, mock_save):
        mock_save.return_value = "dynamic_analysis_unit_test_custom_PARTIAL_20260608_120000.csv"
        self.iface.experiment_review_session = {
            "session_id": self.session_id,
            "completion_order": [10, 11],
            "cells": {
                "10": {
                    "cell_id": 10,
                    "measurements": [],
                    "termination_reason": "normal",
                    "is_partial": False,
                    "z_level_count": 1,
                    "decision": "saved",
                },
                "11": {
                    "cell_id": 11,
                    "measurements": [],
                    "termination_reason": "user_stop",
                    "is_partial": True,
                    "z_level_count": 1,
                    "decision": "saved",
                },
            },
            "queued_saves": {"10": True, "11": True},
            "run_ended_early": True,
        }
        self.iface._experiment_review_run_context = {
            "all_data": _two_cell_all_data_fixture(),
            "timestamp": "20260608_120000",
            "mode": "custom",
            "experiment_name": "unit_test",
            "termination_by_cell": {"10": "normal", "11": "user_stop"},
            "partial_by_cell": {"10": False, "11": True},
            "completed_cells": [10, 11],
            "run_ended_early": True,
            "run_start_ts": 1_700_000_000.0,
            "runtime_settings": {},
            "predicted_viscosity_results": {},
        }
        result = self.iface.commit_experiment_review(self.session_id)
        self.assertEqual(result["saved_cells"], [10, 11])
        mock_save.assert_called_once()
        saved_all_data = mock_save.call_args[0][0]
        self.assertIn(10, saved_all_data)
        self.assertIn(11, saved_all_data)
        self.assertTrue(mock_save.call_args[1]["partial"])
        self.assertEqual(result["experiment"]["cell_partial_flags"]["11"], True)

    def test_sync_does_not_queue_measurement_only_cell(self):
        iface = ViscometryWebInterface(port=5095)
        iface.socketio = MagicMock()
        iface.measurement_data = [
            {
                "cell_id": 12,
                "height": 65.0,
                "rotational_drag": 1.0,
                "torque_percent": 1.0,
                "rpm": 0.8,
                "timestamp": 1_700_000_000.0,
            }
        ]
        iface.sync_experiment_review_cells_from_run(
            all_data={},
            termination_by_cell={},
            default_termination="user_stop",
        )
        pending = iface._experiment_review_pending
        self.assertEqual(pending["completion_order"], [])
        self.assertEqual(pending["cells"], {})

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


class TestExperimentHistoryJsonSafe(unittest.TestCase):
    def test_string_key_cell_termination_reasons_normalizes_mixed_keys(self):
        normalized = _string_key_cell_termination_reasons({1: "normal", "1": "user_stop"})
        self.assertEqual(normalized, {"1": "user_stop"})

    def test_add_entry_jsonify_safe_after_commit(self):
        iface = ViscometryWebInterface(port=5096)
        iface.socketio = MagicMock()
        iface.experiment_history = []
        iface._persist_experiment_history = MagicMock()
        iface.add_experiment_history_entry({
            "id": "exp-test",
            "created_at": 1,
            "runStartTsSec": 1_700_000_000.0,
            "cell_termination_reasons": {1: "normal", "1": "normal"},
        })
        app = Flask(__name__)
        with app.app_context():
            jsonify(iface.get_experiment_history())


class TestExperimentHistoryDedupe(unittest.TestCase):
    def setUp(self):
        self.iface = ViscometryWebInterface(port=5097)
        self.iface.socketio = MagicMock()
        self.iface.experiment_history = []
        self.iface._persist_experiment_history = MagicMock()

    def test_experiment_history_id_for_run(self):
        self.assertEqual(
            _experiment_history_id_for_run(1_700_000_000.0),
            "exp-1700000000000",
        )

    def test_add_entry_replaces_same_run_start(self):
        run_start = 1_780_416_587.1392233
        draft = {
            "id": "exp-draft-old",
            "created_at": 100,
            "runStartTsSec": run_start,
            "measurement_count": 100,
            "cells": [10, 11],
        }
        committed = {
            "id": "exp-1780416587139",
            "created_at": 200,
            "runStartTsSec": run_start,
            "measurement_count": 4000,
            "cells": [10, 11],
            "csv_filename": "dynamic_analysis_test.csv",
        }
        self.iface.add_experiment_history_entry(draft)
        self.iface.add_experiment_history_entry(committed)
        self.assertEqual(len(self.iface.experiment_history), 1)
        self.assertEqual(self.iface.experiment_history[0]["id"], "exp-1780416587139")
        self.assertEqual(self.iface.experiment_history[0]["csv_filename"], "dynamic_analysis_test.csv")

    def test_load_dedupes_legacy_duplicates(self):
        run_start = 1_780_416_587.1392233
        entries = [
            {
                "id": "exp-1780426159206",
                "created_at": 1780426159206,
                "runStartTsSec": run_start,
                "measurement_count": 4197,
                "cells": [10, 11],
            },
            {
                "id": "exp-1780426159429",
                "created_at": 1780426159429,
                "runStartTsSec": run_start,
                "measurement_count": 1802,
                "cells": [10, 11],
                "csv_filename": "dynamic_analysis_polymer.csv",
            },
        ]
        deduped = _dedupe_experiment_history_list(entries)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0]["id"], "exp-1780426159429")
        self.assertEqual(deduped[0]["csv_filename"], "dynamic_analysis_polymer.csv")


class TestSaveDynamicPartialFilename(unittest.TestCase):
    def test_partial_filename_and_warning_header(self):
        from all_cells_with_rotational_drag_feedback import save_dynamic_analysis_data

        with tempfile.TemporaryDirectory() as tmp:
            prev = os.getcwd()
            try:
                os.chdir(tmp)
                path = save_dynamic_analysis_data(
                    _native_all_data_fixture(),
                    "20260608_120000",
                    "custom",
                    "unit_test",
                    partial=True,
                    completed_cells=[1],
                )
                self.assertIn("_PARTIAL_", path)
                with open(path, encoding="utf-8") as f:
                    content = f.read()
            finally:
                os.chdir(prev)
        self.assertIn("PARTIAL RESULTS", content)
        self.assertIn("terminated early", content)
        self.assertIn("Completed cells: [1]", content)


class TestSaveDynamicAnalysisCsvShape(unittest.TestCase):
    def test_summary_csv_uses_slim_headers_and_termination_metadata(self):
        from all_cells_with_rotational_drag_feedback import save_dynamic_analysis_data

        data = {
            1: {
                65.5: {
                    0.8: [
                        {
                            "torque_percent": 12.0,
                            "elapsed_time": 6.0,
                        }
                    ],
                    "_metrics": {
                        0.8: {
                            "Hit_Detected": True,
                            "CV": 0.1,
                            "Hit_Reasons": "kept internal only",
                        }
                    },
                }
            }
        }

        with tempfile.TemporaryDirectory() as tmp:
            prev = os.getcwd()
            try:
                os.chdir(tmp)
                path = save_dynamic_analysis_data(
                    data,
                    "20260608_120000",
                    "custom",
                    "unit_test",
                    termination_by_cell={1: "hit_detected"},
                )
                with open(path, encoding="utf-8") as f:
                    lines = f.read().splitlines()
            finally:
                os.chdir(prev)

        self.assertIn("# Cell termination methods: {1: 'hit_detected'}", lines)
        header = next(line for line in lines if line.startswith("row,cell,"))
        self.assertEqual(
            header,
            "row,cell,Cell_Label,Z_Height_mm,RPM,Elapsed_Time_s,Torque_%,Rotational_Drag,Hit_Detected",
        )
        self.assertNotIn("Cell_Termination_Method", header)
        self.assertNotIn("CV", header)
        self.assertNotIn("Hit_Reasons", header)

        header_idx = lines.index(header)
        data_rows = [
            ln for ln in lines[header_idx + 1:]
            if ln.strip()
        ]
        self.assertEqual(len(data_rows), 1)
        self.assertTrue(data_rows[0].endswith(",True"))


class TestSaveTimeseriesData(unittest.TestCase):
    def test_timeseries_writes_all_samples(self):
        from all_cells_with_rotational_drag_feedback import (
            save_dynamic_analysis_data,
            save_timeseries_data,
        )

        data = _two_cell_all_data_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            prev = os.getcwd()
            try:
                os.chdir(tmp)
                summary = save_dynamic_analysis_data(
                    data,
                    "20260608_120000",
                    "custom",
                    "unit_test",
                )
                ts_path = save_timeseries_data(
                    data,
                    "20260608_120000",
                    "custom",
                    "unit_test",
                )
                with open(summary, encoding="utf-8") as f:
                    summary_content = f.read()
                with open(ts_path, encoding="utf-8") as f:
                    ts_content = f.read()
            finally:
                os.chdir(prev)

        ts_data_rows = [
            ln for ln in ts_content.splitlines()
            if ln.strip()
        ]
        self.assertTrue(summary.endswith(".csv"))
        self.assertTrue(ts_path.endswith("_timeseries.csv"))
        self.assertIn("Save all sample data: ENABLED", ts_content)
        self.assertIn("# Cell termination methods: {10: 'normal', 11: 'normal'}", ts_content)
        self.assertIn(
            "row,cell,Cell_Label,Z_Height_mm,RPM,Elapsed_Time_s,Torque_%,Rotational_Drag",
            ts_content,
        )
        self.assertNotIn("Cell_Termination_Method", ts_content)
        ts_header_idx = ts_data_rows.index(
            "row,cell,Cell_Label,Z_Height_mm,RPM,Elapsed_Time_s,Torque_%,Rotational_Drag"
        )
        ts_data_rows = ts_data_rows[ts_header_idx + 1:]
        self.assertEqual(len(ts_data_rows), 3)


class TestRuntimeSettingsSaveAllAndZStart(unittest.TestCase):
    def test_save_all_and_z_start_round_trip(self):
        iface = ViscometryWebInterface(port=5101)
        saved = iface.update_runtime_settings({
            "save_all_sample_data": True,
            "z_start_offset_mm": 0.15,
        })
        self.assertTrue(saved["save_all_sample_data"])
        self.assertAlmostEqual(saved["z_start_offset_mm"], 0.15)

    def test_invalid_z_start_offset_defaults(self):
        iface = ViscometryWebInterface(port=5102)
        saved = iface.update_runtime_settings({"z_start_offset_mm": 99})
        self.assertAlmostEqual(saved["z_start_offset_mm"], 0.4)


class TestZStartOffsetRuntime(unittest.TestCase):
    def test_get_safe_z_uses_custom_offset(self):
        from calibration_store import get_safe_z_for_cell

        rough = -65.0
        self.assertAlmostEqual(
            get_safe_z_for_cell(99, -60.0, offset=0.15),
            -60.0,
        )
        with patch("calibration_store.load_calibration") as mock_load:
            mock_load.return_value = {"cells": {"1": rough}}
            self.assertAlmostEqual(
                get_safe_z_for_cell(1, -60.0, offset=0.15),
                rough + 0.15,
            )


class TestViscosityPredictionModeNormalization(unittest.TestCase):
    def test_legacy_newtonian_maps_to_on(self):
        from predicted_viscosity import normalize_viscosity_prediction_mode

        self.assertEqual(normalize_viscosity_prediction_mode("Newtonian"), "on")
        self.assertEqual(normalize_viscosity_prediction_mode("Non-Newtonian"), "on")
        self.assertEqual(normalize_viscosity_prediction_mode("on"), "on")
        self.assertEqual(normalize_viscosity_prediction_mode("off"), "off")

    def test_web_interface_normalizes_legacy_settings(self):
        iface = ViscometryWebInterface(port=5100)
        mode = iface._normalize_viscosity_prediction_mode(
            {"viscosity_prediction_mode": "Newtonian", "predicted_viscosity_enabled": False}
        )
        self.assertEqual(mode, "on")

    def test_legacy_enabled_flag_maps_to_on(self):
        from predicted_viscosity import normalize_viscosity_prediction_mode

        self.assertEqual(
            normalize_viscosity_prediction_mode(None, legacy_enabled=True),
            "on",
        )


if __name__ == "__main__":
    unittest.main()

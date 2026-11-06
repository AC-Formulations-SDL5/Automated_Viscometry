"""Tests for structured timing model and append-only training store."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from viscometry.timing.features import z_geometry_from_heights
from viscometry.timing.model import (
    default_posterior,
    estimate_discovery_probe_phase_s,
    predict_cell_seconds,
    predict_run_seconds,
    update_posterior_from_rows,
)
from viscometry.timing.training_store import TRAINING_COLUMNS, append_rows, ensure_headers, row_count


class TestTimingModel(unittest.TestCase):
    def test_predict_monotonic_in_n_rpms(self):
        post = default_posterior()
        low = predict_cell_seconds(n_rpms=3, mu_cp=1e3, posterior=post)
        high = predict_cell_seconds(n_rpms=8, mu_cp=1e3, posterior=post)
        self.assertGreater(high["expected_s"], low["expected_s"])

    def test_predict_longer_for_higher_viscosity(self):
        post = default_posterior()
        thin = predict_cell_seconds(n_rpms=5, mu_cp=1e2, posterior=post)
        thick = predict_cell_seconds(n_rpms=5, mu_cp=1e6, posterior=post)
        self.assertGreater(thick["expected_s"], thin["expected_s"])

    def test_run_prediction_includes_wash_for_multi_cell(self):
        post = default_posterior()
        one = predict_run_seconds(n_cells=1, n_rpms=4, mu_cp=1e3, posterior=post)
        two = predict_run_seconds(n_cells=2, n_rpms=4, mu_cp=1e3, posterior=post)
        self.assertGreater(two["expected_s"] - one["expected_s"], post["wash_s"]["mean"] * 0.5)

    def test_append_only_store_never_shrinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "timing.csv"
            ensure_headers(path)
            self.assertEqual(row_count(path), 0)
            n1 = append_rows(
                [{"sample_label": "A", "experiment_id": "e1", "cell_id": 1, "row_level": "cell"}],
                path=path,
            )
            self.assertEqual(n1, 1)
            self.assertEqual(row_count(path), 1)
            n2 = append_rows(
                [{"sample_label": "B", "experiment_id": "e2", "cell_id": 2, "row_level": "cell"}],
                path=path,
            )
            self.assertEqual(n2, 1)
            self.assertEqual(row_count(path), 2)
            # ensure_headers must not wipe
            ensure_headers(path)
            self.assertEqual(row_count(path), 2)

    def test_posterior_update_from_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "posterior.json"
            post = default_posterior()
            before = post["n_z"]["mean"]
            updated = update_posterior_from_rows(
                [{"row_level": "cell", "n_z": 30, "actual_duration_s": 1000, "predicted_duration_s": 900}],
                posterior=post,
                path=path,
            )
            self.assertNotEqual(updated["n_z"]["mean"], before)
            self.assertTrue(path.is_file())

    def test_partial_n_z_does_not_update_posterior(self):
        post = default_posterior()
        before = post["n_z"]["mean"]
        updated = update_posterior_from_rows(
            [{"row_level": "cell", "n_z": 1, "actual_duration_s": 10, "predicted_duration_s": 10}],
            posterior=post,
            path=Path(tempfile.mkdtemp()) / "p.json",
        )
        self.assertEqual(updated["n_z"]["mean"], before)

    def test_discovery_probe_phase_capped_near_four_minutes(self):
        s = estimate_discovery_probe_phase_s(max_screening_rpms=6, probe_duration_s=60.0)
        self.assertGreater(s, 60.0)
        self.assertLessEqual(s, 240.0)

    def test_hit_relative_is_hit_minus_start(self):
        geom = z_geometry_from_heights([-65.0, -65.4, -65.8, -66.2])
        self.assertAlmostEqual(geom["start_z"], -65.0)
        self.assertAlmostEqual(geom["hit_z"], -66.2)
        self.assertAlmostEqual(geom["hit_relative_mm"], -1.2)
        self.assertEqual(geom["n_z"], 4.0)

    def test_training_columns_include_relative_hit(self):
        self.assertIn("start_z", TRAINING_COLUMNS)
        self.assertIn("hit_relative_mm", TRAINING_COLUMNS)


if __name__ == "__main__":
    unittest.main()

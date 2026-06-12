"""Unit tests for Discovery Mode pure logic."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import List, Optional, Tuple

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "src" / "python_64"))

from discovery_mode import (
    DiscoveryConfig,
    clamp_rpm_index_steps,
    cold_start_rpm,
    discover_rpm,
    estimate_initial_rpm,
    is_discovery_success,
    load_discovery_config,
    snap_rpm,
    suggest_next_rpm,
)
from discovery_types import ViscosityTableRow


VALID = (0.5, 1.0, 2.0, 5.0, 10.0)


class TestSnapRpm(unittest.TestCase):
    def test_snap_nearest(self):
        self.assertEqual(snap_rpm(4.7, VALID), 5.0)
        self.assertEqual(snap_rpm(0.6, VALID), 0.5)

    def test_snap_tie_prefers_lower(self):
        # 1.5 equidistant from 1.0 and 2.0
        self.assertEqual(snap_rpm(1.5, VALID), 1.0)


class TestSuggestNextRpm(unittest.TestCase):
    def test_high_torque_reduces_more(self):
        fine = tuple(i * 0.5 for i in range(1, 41))  # 0.5 .. 20.0
        from_85 = suggest_next_rpm(10.0, 85.0, target_torque=30.0, valid_rpms=fine, max_index_steps=20)
        from_45 = suggest_next_rpm(10.0, 45.0, target_torque=30.0, valid_rpms=fine, max_index_steps=20)
        self.assertLess(from_85, from_45)

    def test_step_cap(self):
        r = clamp_rpm_index_steps(0.5, 10.0, VALID, max_steps=2)
        self.assertEqual(r, 2.0)


class FakeProbe:
    def __init__(self, torques: List[float]):
        self.torques = list(torques)
        self.calls: List[Tuple[int, float, float]] = []

    def __call__(self, cell_id: int, z_mm: float, rpm: float) -> Optional[float]:
        self.calls.append((cell_id, z_mm, rpm))
        if not self.torques:
            return None
        return self.torques.pop(0)


class TestDiscoverRpm(unittest.TestCase):
    def _cfg(self) -> DiscoveryConfig:
        return DiscoveryConfig(
            k_bulk=1e-3,
            target_torque=30.0,
            torque_window=(25.0, 35.0),
            hit_point_offset_mm=0.35,
            valid_rpms=VALID,
            max_iterations=4,
            max_rpm_index_steps=4,
        )

    def test_converged_in_window(self):
        probe = FakeProbe([30.0])
        result = discover_rpm(
            1,
            probe,
            config=self._cfg(),
            viscosity_table=[],
        )
        # cell 1 is calibrated in repo JSON — if not, skip
        if result["status"] == "uncalibrated_cell":
            self.skipTest("cell 1 not calibrated in test environment")
        self.assertEqual(result["status"], "converged")
        self.assertTrue(is_discovery_success(result))
        self.assertEqual(result["rpm"], probe.calls[0][2])

    def test_iterative_convergence(self):
        probe = FakeProbe([80.0, 32.0])
        result = discover_rpm(1, probe, config=self._cfg(), viscosity_table=[])
        if result["status"] == "uncalibrated_cell":
            self.skipTest("cell 1 not calibrated")
        self.assertEqual(result["status"], "converged")
        self.assertEqual(len(result["probes"]), 2)

    def test_over_range(self):
        probe = FakeProbe([90.0])
        cfg = self._cfg()
        cfg = DiscoveryConfig(
            k_bulk=cfg.k_bulk,
            target_torque=cfg.target_torque,
            torque_window=cfg.torque_window,
            hit_point_offset_mm=cfg.hit_point_offset_mm,
            valid_rpms=(0.5,),
            max_iterations=cfg.max_iterations,
            over_range_torque_pct=85.0,
            max_rpm_index_steps=4,
        )
        result = discover_rpm(1, probe, config=cfg, viscosity_table=[])
        if result["status"] == "uncalibrated_cell":
            self.skipTest("cell 1 not calibrated")
        self.assertEqual(result["status"], "over_range")

    def test_probe_failed(self):
        probe = FakeProbe([])
        result = discover_rpm(1, probe, config=self._cfg(), viscosity_table=[])
        if result["status"] == "uncalibrated_cell":
            self.skipTest("cell 1 not calibrated")
        self.assertEqual(result["status"], "probe_failed")


class TestEstimateInitialRpm(unittest.TestCase):
    def test_positive_eta(self):
        rpm = estimate_initial_rpm(10000.0, k_bulk=1e-3, valid_rpms=VALID)
        self.assertIn(rpm, VALID)

    def test_cold_start(self):
        self.assertEqual(cold_start_rpm(VALID, cold_start=5.0), 5.0)


class TestLoadConfig(unittest.TestCase):
    def test_loads_json(self):
        cfg = load_discovery_config()
        self.assertGreater(cfg.k_bulk, 0)
        self.assertGreater(len(cfg.valid_rpms), 0)


class TestWebDiscoverySafety(unittest.TestCase):
    def test_regular_run_clear_payload_disables_discovery(self):
        from web_interface import ViscometryWebInterface

        payload = ViscometryWebInterface._regular_run_mode_clear_payload()
        self.assertFalse(payload.get("discovery_mode_enabled"))


if __name__ == "__main__":
    unittest.main()

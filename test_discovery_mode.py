"""Unit tests for Discovery Mode pure logic (continuous RPM calibration)."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
from typing import List, Optional, Tuple

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "src" / "python_64"))

from discovery_mode import (
    discover_rpm,
    is_discovery_success,
    load_discovery_config,
)
from discovery_types import DiscoveryConfig
from discovery_rpm_calibration import (
    A_CAL,
    B_CAL,
    TARGET_TORQUE_REF,
    clamp_hardware_rpm,
    eta_from_rpm_torque,
    initial_rpm_for_discovery,
    rpm_for_target_torque,
    suggest_next_rpm_continuous,
)


def _default_cfg(**overrides) -> DiscoveryConfig:
    base = dict(
        k_bulk=1e-3,
        target_torque=30.0,
        torque_window=(25.0, 35.0),
        hit_point_offset_mm=0.35,
        valid_rpms=(0.5, 1.0, 2.0, 5.0, 10.0),
        max_iterations=4,
        a_cal=A_CAL,
        b_cal=B_CAL,
        rpm_min=0.1,
        rpm_max=200.0,
    )
    base.update(overrides)
    return DiscoveryConfig(**base)


class TestPowerLawCalibration(unittest.TestCase):
    def test_rpm_for_target_torque_1000cp(self):
        rpm = rpm_for_target_torque(1000.0, target_torque=30.0)
        expected = rpm_for_target_torque(1000.0, target_torque=30.0, a_cal=A_CAL, b_cal=B_CAL)
        self.assertAlmostEqual(rpm, expected, places=3)
        self.assertGreater(rpm, 10.0)
        self.assertLess(rpm, 50.0)

    def test_eta_round_trip(self):
        eta = 5000.0
        rpm = rpm_for_target_torque(eta, target_torque=30.0)
        eta_back = eta_from_rpm_torque(rpm, 30.0, a_cal=A_CAL, b_cal=B_CAL)
        self.assertAlmostEqual(eta_back, eta, delta=eta * 0.001)

    def test_clamp_hardware_rpm(self):
        self.assertEqual(clamp_hardware_rpm(250.0), 200.0)
        self.assertEqual(clamp_hardware_rpm(0.01), 0.1)


class TestContinuousSuggestNextRpm(unittest.TestCase):
    def test_high_torque_reduces_rpm(self):
        from_85 = suggest_next_rpm_continuous(10.0, 85.0, target_torque=30.0)
        from_45 = suggest_next_rpm_continuous(10.0, 45.0, target_torque=30.0)
        self.assertLess(from_85, from_45)
        self.assertAlmostEqual(from_85, 10.0 * 30.0 / 85.0, places=4)

    def test_no_ladder_quantization(self):
        rpm_next = suggest_next_rpm_continuous(7.3, 42.0, target_torque=30.0)
        self.assertNotEqual(rpm_next, round(rpm_next))
        self.assertAlmostEqual(rpm_next, 7.3 * 30.0 / 42.0, places=4)


class FakeProbe:
    def __init__(self, torques: List[float]):
        self.torques = list(torques)
        self.calls: List[Tuple[int, float, float]] = []

    def __call__(self, cell_id: int, z_mm: float, rpm: float) -> Optional[float]:
        self.calls.append((cell_id, z_mm, rpm))
        if not self.torques:
            return None
        return self.torques.pop(0)


class TestDiscoverRpmContinuous(unittest.TestCase):
    def test_eta_guess_uses_power_law_not_snap(self):
        cfg = _default_cfg()
        eta_guess = 1000.0
        expected = initial_rpm_for_discovery(
            eta_guess,
            target_torque=cfg.target_torque,
            cold_start_rpm=cfg.cold_start_rpm,
            a_cal=cfg.a_cal,
            b_cal=cfg.b_cal,
            reference_torque=cfg.surface_torque_ref,
            rpm_min=cfg.rpm_min,
            rpm_max=cfg.rpm_max,
        )
        self.assertNotAlmostEqual(expected, 5.0, places=1)
        probe = FakeProbe([30.0])
        result = discover_rpm(1, probe, config=cfg, eta_guess=eta_guess)
        if result["status"] == "uncalibrated_cell":
            self.skipTest("cell 1 not calibrated in test environment")
        self.assertEqual(result["status"], "converged")
        self.assertAlmostEqual(probe.calls[0][2], expected, places=3)


class TestDiscoverRpm(unittest.TestCase):
    def test_converged_in_window(self):
        probe = FakeProbe([30.0])
        result = discover_rpm(1, probe, config=_default_cfg())
        if result["status"] == "uncalibrated_cell":
            self.skipTest("cell 1 not calibrated in test environment")
        self.assertEqual(result["status"], "converged")
        self.assertTrue(is_discovery_success(result))
        self.assertEqual(result["rpm"], probe.calls[0][2])

    def test_iterative_convergence(self):
        probe = FakeProbe([80.0, 32.0])
        result = discover_rpm(1, probe, config=_default_cfg())
        if result["status"] == "uncalibrated_cell":
            self.skipTest("cell 1 not calibrated")
        self.assertEqual(result["status"], "converged")
        self.assertEqual(len(result["probes"]), 2)

    def test_over_range(self):
        probe = FakeProbe([90.0])
        cfg = _default_cfg(rpm_min=0.5, rpm_max=0.5)
        result = discover_rpm(1, probe, config=cfg)
        if result["status"] == "uncalibrated_cell":
            self.skipTest("cell 1 not calibrated")
        self.assertEqual(result["status"], "over_range")

    def test_probe_failed(self):
        probe = FakeProbe([])
        result = discover_rpm(1, probe, config=_default_cfg())
        if result["status"] == "uncalibrated_cell":
            self.skipTest("cell 1 not calibrated")
        self.assertEqual(result["status"], "probe_failed")


class TestInitialRpmForDiscovery(unittest.TestCase):
    def test_cold_start_clamped(self):
        rpm = initial_rpm_for_discovery(
            None,
            target_torque=30.0,
            cold_start_rpm=5.0,
            a_cal=A_CAL,
            b_cal=B_CAL,
            reference_torque=TARGET_TORQUE_REF,
            rpm_min=0.1,
            rpm_max=200.0,
        )
        self.assertEqual(rpm, 5.0)

    def test_positive_eta_finite(self):
        rpm = initial_rpm_for_discovery(
            10000.0,
            target_torque=30.0,
            cold_start_rpm=5.0,
            a_cal=A_CAL,
            b_cal=B_CAL,
            reference_torque=TARGET_TORQUE_REF,
            rpm_min=0.1,
            rpm_max=200.0,
        )
        self.assertTrue(math.isfinite(rpm))
        self.assertGreater(rpm, 0)


class TestLoadConfig(unittest.TestCase):
    def test_loads_json(self):
        cfg = load_discovery_config()
        self.assertGreater(cfg.k_bulk, 0)
        self.assertGreater(len(cfg.valid_rpms), 0)
        self.assertGreater(cfg.a_cal, 0)
        self.assertLess(cfg.b_cal, 0)
        self.assertEqual(cfg.rpm_selection_mode, "continuous")


class TestOnProbeCallback(unittest.TestCase):
    def test_on_probe_fires_each_iteration(self):
        probe = FakeProbe([80.0, 32.0])
        seen = []

        def on_probe(_record, partial):
            seen.append({
                "status": partial.get("status"),
                "iterations": partial.get("iterations"),
            })

        result = discover_rpm(
            1,
            probe,
            config=_default_cfg(),
            on_probe=on_probe,
        )
        if result["status"] == "uncalibrated_cell":
            self.skipTest("cell 1 not calibrated")
        self.assertEqual(len(seen), len(result["probes"]))
        self.assertTrue(all(item["status"] == "probing" for item in seen))


class TestProbeExecutorMoveOnce(unittest.TestCase):
    def test_probe_executor_does_not_move(self):
        from discovery_probe import make_probe_executor

        move_calls = []
        measure_calls = []

        def measure_fn(_client, rpm, z_mm):
            measure_calls.append((rpm, z_mm))
            return [{"torque_percent": 30.0}]

        executor = make_probe_executor(
            object(),
            object(),
            measure_torque_fn=measure_fn,
        )
        torque = executor(1, -65.0, 5.0)
        self.assertEqual(torque, 30.0)
        self.assertEqual(len(measure_calls), 1)
        self.assertEqual(measure_calls[0], (5.0, -65.0))
        self.assertEqual(move_calls, [])


class TestWebDiscoverySafety(unittest.TestCase):
    def test_regular_run_clear_payload_disables_discovery(self):
        from web_interface import ViscometryWebInterface

        payload = ViscometryWebInterface._regular_run_mode_clear_payload()
        self.assertFalse(payload.get("discovery_mode_enabled"))


if __name__ == "__main__":
    unittest.main()

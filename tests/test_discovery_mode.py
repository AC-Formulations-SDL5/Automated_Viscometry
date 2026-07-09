"""Unit tests for Discovery Mode pure logic (continuous RPM calibration)."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))
from typing import List, Optional, Tuple

from viscometry.discovery.mode import (
    discover_rpm,
    is_discovery_success,
    load_discovery_config,
)
from viscometry.discovery.types import DiscoveryConfig
from viscometry.discovery.rpm_calibration import (
    A_CAL,
    B_CAL,
    TARGET_TORQUE_REF,
    clamp_hardware_rpm,
    eta_from_rpm_torque,
    initial_rpm_for_discovery,
    round_rpm_2dp,
    rpm_for_target_torque,
    suggest_next_rpm_continuous,
)


def _assert_rpm_is_2dp(test_case, rpm):
    test_case.assertEqual(rpm, round(float(rpm), 2))


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
        discovery_stage2_enabled=False,
    )
    base.update(overrides)
    return DiscoveryConfig(**base)


class PowerLawFakeProbe:
    """Returns torque = k * rpm^n (deterministic ladder testing)."""

    def __init__(self, k: float = 8.0, n: float = 1.0):
        self.k = k
        self.n = n
        self.calls: List[Tuple[int, float, float]] = []

    def __call__(self, cell_id: int, z_mm: float, rpm: float) -> Optional[float]:
        self.calls.append((cell_id, z_mm, rpm))
        if rpm <= 0:
            return None
        return float(self.k * (rpm ** self.n))


class TestPowerLawCalibration(unittest.TestCase):
    def test_round_rpm_2dp(self):
        self.assertEqual(round_rpm_2dp(7.3456), 7.35)
        self.assertEqual(round_rpm_2dp(10.0), 10.0)

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
        expected = round_rpm_2dp(
            initial_rpm_for_discovery(
                eta_guess,
                target_torque=cfg.target_torque,
                cold_start_rpm=cfg.cold_start_rpm,
                a_cal=cfg.a_cal,
                b_cal=cfg.b_cal,
                reference_torque=cfg.surface_torque_ref,
                rpm_min=cfg.rpm_min,
                rpm_max=cfg.rpm_max,
            )
        )
        self.assertNotAlmostEqual(expected, 5.0, places=1)
        probe = FakeProbe([30.0])
        result = discover_rpm(1, probe, config=cfg, eta_guess=eta_guess)
        if result["status"] == "uncalibrated_cell":
            self.skipTest("cell 1 not calibrated in test environment")
        self.assertEqual(result["status"], "converged")
        self.assertAlmostEqual(probe.calls[0][2], expected, places=2)
        _assert_rpm_is_2dp(self, result["rpm"])
        for probe_row in result["probes"]:
            _assert_rpm_is_2dp(self, probe_row["rpm"])


class TestDiscoverRpm(unittest.TestCase):
    def test_converged_in_window(self):
        probe = FakeProbe([30.0])
        result = discover_rpm(1, probe, config=_default_cfg())
        if result["status"] == "uncalibrated_cell":
            self.skipTest("cell 1 not calibrated in test environment")
        self.assertEqual(result["status"], "converged")
        self.assertTrue(is_discovery_success(result))
        self.assertEqual(result["rpm"], probe.calls[0][2])
        _assert_rpm_is_2dp(self, result["rpm"])

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
        from viscometry.discovery.probe import make_probe_executor

        move_calls = []
        measure_calls = []

        def measure_fn(_client, rpm, z_mm, **kwargs):
            measure_calls.append((rpm, z_mm, kwargs))
            return [{"torque_percent": 30.0}]

        executor = make_probe_executor(
            object(),
            object(),
            measure_torque_fn=measure_fn,
        )
        torque = executor(1, -65.0, 5.0)
        self.assertEqual(torque, 30.0)
        self.assertEqual(len(measure_calls), 1)
        self.assertEqual(measure_calls[0][0], 5.0)
        self.assertEqual(measure_calls[0][1], -65.0)
        self.assertEqual(measure_calls[0][2], {})
        self.assertEqual(move_calls, [])


class TestProbeExecutorDuck(unittest.TestCase):
    def test_probe_executor_passes_duck_kwarg(self):
        from viscometry.discovery.probe import make_probe_executor

        captured = {}

        def measure_fn(_client, rpm, z_mm, **kwargs):
            captured.update(kwargs)
            return [{"torque_percent": 85.0}]

        executor = make_probe_executor(
            object(),
            object(),
            measure_torque_fn=measure_fn,
            duck_torque_pct=80.0,
        )
        torque = executor(1, -65.0, 5.0)
        self.assertEqual(torque, 85.0)
        self.assertEqual(captured.get("duck_above_pct_on_first_sample"), 80.0)

    def test_probe_executor_omits_duck_when_disabled(self):
        from viscometry.discovery.probe import make_probe_executor

        captured = {}

        def measure_fn(_client, rpm, z_mm, **kwargs):
            captured.update(kwargs)
            return [{"torque_percent": 30.0}]

        executor = make_probe_executor(
            object(),
            object(),
            measure_torque_fn=measure_fn,
            duck_torque_pct=0,
        )
        executor(1, -65.0, 5.0)
        self.assertEqual(captured, {})


class TestDiscoverRpmDuckStepping(unittest.TestCase):
    def test_high_first_probe_steps_down_to_convergence(self):
        probe = FakeProbe([85.0, 30.0])
        result = discover_rpm(1, probe, config=_default_cfg())
        if result["status"] == "uncalibrated_cell":
            self.skipTest("cell 1 not calibrated")
        self.assertEqual(result["status"], "converged")
        self.assertEqual(len(result["probes"]), 2)
        self.assertLess(probe.calls[1][2], probe.calls[0][2])


class TestTorqueLadderMath(unittest.TestCase):
    def test_torque_window_for_target(self):
        from viscometry.discovery.torque_ladder import torque_in_target_window, torque_window_for_target

        lo, hi = torque_window_for_target(30.0)
        self.assertAlmostEqual(lo, 27.5)
        self.assertAlmostEqual(hi, 32.5)
        self.assertTrue(torque_in_target_window(30.0, 30.0))
        self.assertFalse(torque_in_target_window(26.0, 30.0))

    def test_fit_n_probe_newtonian(self):
        from viscometry.discovery.torque_ladder import fit_n_probe

        fit = fit_n_probe([1.0, 2.0, 4.0, 8.0], [10.0, 20.0, 40.0, 80.0])
        self.assertAlmostEqual(fit["n_probe"], 1.0, delta=0.05)

    def test_fit_n_probe_shear_thinning(self):
        from viscometry.discovery.torque_ladder import fit_n_probe

        rpms = [1.0, 2.0, 4.0, 8.0, 16.0]
        torques = [8.0 * (r ** 0.5) for r in rpms]
        fit = fit_n_probe(rpms, torques)
        self.assertAlmostEqual(fit["n_probe"], 0.5, delta=0.08)

    def test_is_newtonian_threshold(self):
        from viscometry.discovery.torque_ladder import is_newtonian_probe

        self.assertFalse(is_newtonian_probe(0.974))
        self.assertTrue(is_newtonian_probe(0.975))

    def test_t_top_target_branches(self):
        from viscometry.discovery.torque_ladder import t_top_target

        self.assertAlmostEqual(t_top_target(1.0), 30.0)
        self.assertAlmostEqual(t_top_target(0.5), 50.0 * (0.6 ** 0.5), places=2)


class TestDiscoveryLanding(unittest.TestCase):
    def _mock_cell_data(self, hit_z: float, torque: float, rpm: float = 5.0):
        return {
            -65.0: {rpm: [{"torque_percent": 25.0}], "_metrics": {rpm: {"Hit_Detected": False}}},
            hit_z: {rpm: [{"torque_percent": torque}], "_metrics": {rpm: {"Hit_Detected": False}}},
            hit_z - 0.02: {
                rpm: [{"torque_percent": 60.0}],
                "_metrics": {rpm: {"Hit_Detected": True}},
            },
            hit_z - 0.04: {
                rpm: [{"torque_percent": 61.0}],
                "_metrics": {rpm: {"Hit_Detected": True}},
            },
            hit_z - 0.06: {
                rpm: [{"torque_percent": 62.0}],
                "_metrics": {rpm: {"Hit_Detected": True}},
            },
        }

    def test_extract_t_bottom_hit_detected(self):
        from viscometry.discovery.landing import extract_t_bottom

        data = self._mock_cell_data(-65.22, 48.0)
        out = extract_t_bottom(data, 5.0, "hit_detected")
        self.assertAlmostEqual(out["t_bottom"], 48.0)
        self.assertAlmostEqual(out["z_bottom_mm"], -65.22)

    def test_extract_t_bottom_fail_safe_na(self):
        from viscometry.discovery.landing import extract_t_bottom

        data = self._mock_cell_data(-65.22, 48.0)
        out = extract_t_bottom(data, 5.0, "fail_safe")
        self.assertIsNone(out["t_bottom"])

    def test_landing_ok_boundaries(self):
        from viscometry.discovery.landing import compute_landing_metrics

        ok = compute_landing_metrics(30.0, 50.0, "hit_detected")
        self.assertTrue(ok["landing_ok"])
        self.assertEqual(ok["landing_status"], "ok")
        high = compute_landing_metrics(30.0, 60.0, "hit_detected")
        self.assertEqual(high["landing_status"], "high")
        low = compute_landing_metrics(30.0, 40.0, "hit_detected")
        self.assertEqual(low["landing_status"], "low")
        na = compute_landing_metrics(30.0, 50.0, "manual_terminate")
        self.assertEqual(na["landing_status"], "na")


class TestDiscoverRpmStage2(unittest.TestCase):
    def test_stage2_newtonian_converges(self):
        from viscometry.discovery.mode import discover_rpm_stage2

        probe = PowerLawFakeProbe(k=6.0, n=1.0)
        cfg = _default_cfg(
            discovery_stage2_enabled=True,
            ladder_max_iterations_per_target=5,
            hello_probe_rpm=5.0,
        )
        result = discover_rpm_stage2(1, probe, config=cfg)
        if result["status"] == "uncalibrated_cell":
            self.skipTest("cell 1 not calibrated")
        self.assertEqual(result["status"], "converged")
        self.assertTrue(result.get("is_newtonian"))
        self.assertEqual(result.get("discovery_path"), "newtonian")
        self.assertIsNotNone(result.get("rpm_30"))
        self.assertIsNotNone(result.get("n_probe"))

    def test_stage2_shear_thinning_path(self):
        from viscometry.discovery.mode import discover_rpm_stage2

        probe = PowerLawFakeProbe(k=12.0, n=0.5)
        cfg = _default_cfg(
            discovery_stage2_enabled=True,
            ladder_max_iterations_per_target=6,
            hello_probe_rpm=2.0,
            min_power_law_r_squared=0.5,
        )
        result = discover_rpm_stage2(1, probe, config=cfg)
        if result["status"] == "uncalibrated_cell":
            self.skipTest("cell 1 not calibrated")
        self.assertEqual(result["status"], "converged")
        self.assertFalse(result.get("is_newtonian"))
        self.assertEqual(result.get("discovery_path"), "non_newtonian")
        self.assertGreater(result.get("T_top_target", 0), 30.0)

    def test_discovery_payload_stage2_fields(self):
        from viscometry.discovery.runner import discovery_result_to_web_payload

        payload = discovery_result_to_web_payload(
            3,
            {
                "rpm": 4.5,
                "status": "converged",
                "probes": [],
                "n_probe": 0.52,
                "T_top": 38.0,
                "T_bottom": 50.0,
                "S": 1.32,
                "landing_status": "ok",
            },
        )
        self.assertEqual(payload["n_probe"], 0.52)
        self.assertEqual(payload["T_top"], 38.0)
        self.assertEqual(payload["landing_status"], "ok")


class TestWebDiscoverySafety(unittest.TestCase):
    def test_regular_run_clear_payload_disables_discovery(self):
        from viscometry.web.app import ViscometryWebInterface

        payload = ViscometryWebInterface._regular_run_mode_clear_payload()
        self.assertFalse(payload.get("discovery_mode_enabled"))

    def test_runtime_discovery_defaults(self):
        from viscometry.web.app import ViscometryWebInterface

        iface = ViscometryWebInterface()
        settings = iface.get_runtime_settings()
        self.assertEqual(settings.get("discovery_probe_duration_s"), 60.0)
        self.assertEqual(settings.get("discovery_duck_torque_pct"), 80.0)
        self.assertEqual(settings.get("discovery_handoff_pause_s"), 10.0)


if __name__ == "__main__":
    unittest.main()

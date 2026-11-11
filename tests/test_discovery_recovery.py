"""Unit tests for Post-Overrange Torque Recovery and Discovery Planning settings."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from viscometry.web.app import ViscometryWebInterface
from viscometry.run.controller import wait_for_torque_relaxation


class TestDiscoveryRecoverySettings(unittest.TestCase):
    def test_default_settings_include_recovery(self):
        iface = ViscometryWebInterface()
        settings = iface.get_runtime_settings()
        self.assertIn("discovery_duck_recovery_enabled", settings)
        self.assertTrue(settings["discovery_duck_recovery_enabled"])
        self.assertEqual(settings["discovery_duck_recovery_target_pct"], 10.0)
        self.assertEqual(settings["discovery_duck_recovery_timeout_s"], 90.0)
        self.assertEqual(settings["discovery_duck_recovery_plateau_rate"], 0.1)

    def test_update_settings_recovery_clamping(self):
        iface = ViscometryWebInterface()
        payload = {
            "discovery_duck_recovery_enabled": False,
            "discovery_duck_recovery_target_pct": 5.5,
            "discovery_duck_recovery_timeout_s": 120.0,
            "discovery_duck_recovery_plateau_rate": 0.05,
        }
        updated = iface.update_runtime_settings(payload)
        self.assertFalse(updated["discovery_duck_recovery_enabled"])
        self.assertEqual(updated["discovery_duck_recovery_target_pct"], 5.5)
        self.assertEqual(updated["discovery_duck_recovery_timeout_s"], 120.0)
        self.assertEqual(updated["discovery_duck_recovery_plateau_rate"], 0.05)

    def test_update_settings_out_of_bounds(self):
        iface = ViscometryWebInterface()
        payload = {
            "discovery_duck_recovery_target_pct": 999.0,  # Max is 50.0
            "discovery_duck_recovery_timeout_s": -50.0,   # Min is 5.0
            "discovery_duck_recovery_plateau_rate": 5.0,  # Max is 2.0
        }
        updated = iface.update_runtime_settings(payload)
        self.assertEqual(updated["discovery_duck_recovery_target_pct"], 50.0)
        self.assertEqual(updated["discovery_duck_recovery_timeout_s"], 5.0)
        self.assertEqual(updated["discovery_duck_recovery_plateau_rate"], 2.0)


class TestWaitForTorqueRelaxation(unittest.TestCase):
    def test_safeguard1_target_reached(self):
        """Spindle stops, torque falls from 80% to 8%, exiting on target_reached."""
        mock_client = MagicMock()
        torques = [80.0, 50.0, 30.0, 15.0, 8.0]

        def fake_read(*args, **kwargs):
            val = torques.pop(0) if torques else 8.0
            return {"torque_valid": True, "torque_percent": val}

        with patch("viscometry.run.controller._read_valid_torque_packet", side_effect=fake_read), \
             patch("viscometry.run.controller.sleep_with_stop", return_value=None):
            result = wait_for_torque_relaxation(
                mock_client,
                target_pct=10.0,
                timeout_s=90.0,
                poll_interval_s=0.01,
            )
            mock_client.stop.assert_called_once()
            self.assertTrue(result["success"])
            self.assertEqual(result["reason"], "target_reached")
            self.assertLess(result["final_torque"], 10.0)

    def test_safeguard2_plateau_detection(self):
        """Torque levels off at 14% (above 10% target) with dτ/dt ~ 0; exits on plateau."""
        mock_client = MagicMock()
        clock = [100.0]

        def fake_time():
            return clock[0]

        def fake_sleep(s):
            clock[0] += float(s)

        def fake_read(*args, **kwargs):
            return {"torque_valid": True, "torque_percent": 14.0}

        with patch("viscometry.run.controller.time.time", side_effect=fake_time), \
             patch("viscometry.run.controller._read_valid_torque_packet", side_effect=fake_read), \
             patch("viscometry.run.controller.sleep_with_stop", side_effect=fake_sleep):
            result = wait_for_torque_relaxation(
                mock_client,
                target_pct=10.0,
                timeout_s=90.0,
                plateau_rate_pct_s=0.1,
                poll_interval_s=1.0,
                min_plateau_time_s=12.0,
                plateau_window_s=10.0,
            )
            self.assertTrue(result["success"])
            self.assertEqual(result["reason"], "plateau")
            self.assertAlmostEqual(result["final_torque"], 14.0, places=1)
            self.assertGreaterEqual(result["elapsed_s"], 12.0)

    def test_safeguard3_safety_timeout(self):
        """Torque never falls and never plateaus; exits when timeout is reached."""
        mock_client = MagicMock()
        clock = [100.0]

        def fake_time():
            return clock[0]

        def fake_sleep(s):
            clock[0] += float(s)

        def fake_read(*args, **kwargs):
            # Fluctuating torque so it never plateaus
            clock_val = clock[0]
            val = 80.0 + (5.0 if int(clock_val) % 2 == 0 else -5.0)
            return {"torque_valid": True, "torque_percent": val}

        with patch("viscometry.run.controller.time.time", side_effect=fake_time), \
             patch("viscometry.run.controller._read_valid_torque_packet", side_effect=fake_read), \
             patch("viscometry.run.controller.sleep_with_stop", side_effect=fake_sleep):
            result = wait_for_torque_relaxation(
                mock_client,
                target_pct=10.0,
                timeout_s=30.0,
                poll_interval_s=1.0,
                plateau_rate_pct_s=0.01,
                min_plateau_time_s=50.0,
            )
            self.assertFalse(result["success"])
            self.assertEqual(result["reason"], "timeout")
            self.assertGreaterEqual(result["final_torque"], 70.0)


if __name__ == "__main__":
    unittest.main()

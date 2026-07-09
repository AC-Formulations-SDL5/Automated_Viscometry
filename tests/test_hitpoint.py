"""Tests for universal hitpoint extraction."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

_ROOT = Path(__file__).resolve().parent


from viscometry.measurement.hitpoint import (
    build_z_hit_sequence,
    extract_hitpoint,
    extract_hitpoint_from_sequence,
    extract_rough_hitpoint,
)


def _cell_data_from_sequence(seq: list) -> dict:
    """Build minimal cell_z_rpm_data from (z, hit) pairs."""
    out = {}
    for z, is_hit in seq:
        out[float(z)] = {
            "_metrics": {
                1.0: {"Hit_Detected": bool(is_hit)},
            }
        }
    return out


class TestHitpoint(unittest.TestCase):
    def test_extract_from_sequence_clear_pattern(self):
        seq = [
            (-65.20, False),
            (-65.22, False),
            (-65.24, False),
            (-65.26, True),
            (-65.28, True),
            (-65.30, True),
            (-65.32, True),
        ]
        self.assertAlmostEqual(extract_hitpoint_from_sequence(seq), -65.24)

    def test_extract_last_matching_transition(self):
        seq = [
            (-65.20, False),
            (-65.22, True),
            (-65.24, True),
            (-65.26, True),
            (-65.28, False),
            (-65.30, True),
            (-65.32, True),
            (-65.34, True),
        ]
        self.assertAlmostEqual(extract_hitpoint_from_sequence(seq), -65.28)

    def test_no_pattern_returns_none(self):
        seq = [(-65.20, False), (-65.22, False), (-65.24, True)]
        self.assertIsNone(extract_hitpoint_from_sequence(seq))

    def test_fewer_than_four_levels_returns_none(self):
        self.assertIsNone(extract_hitpoint_from_sequence([(-65.2, False)]))

    def test_per_z_any_rpm_hit(self):
        cell = {
            -65.24: {"_metrics": {0.4: {"Hit_Detected": False}, 1.0: {"Hit_Detected": True}}},
            -65.26: {"_metrics": {0.4: {"Hit_Detected": True}}},
            -65.28: {"_metrics": {0.4: {"Hit_Detected": True}}},
            -65.30: {"_metrics": {0.4: {"Hit_Detected": True}}},
        }
        cell[-65.22] = {"_metrics": {0.4: {"Hit_Detected": False}}}
        self.assertAlmostEqual(extract_hitpoint(cell), -65.22)

    def test_extract_hitpoint_matches_rough_alias(self):
        cell = _cell_data_from_sequence([
            (-65.20, False),
            (-65.22, False),
            (-65.24, True),
            (-65.26, True),
            (-65.28, True),
        ])
        self.assertEqual(extract_hitpoint(cell), extract_rough_hitpoint(cell))

    def test_build_z_hit_sequence_descending_z(self):
        cell = _cell_data_from_sequence([
            (-65.28, True),
            (-65.20, False),
            (-65.24, True),
        ])
        seq = build_z_hit_sequence(cell)
        self.assertEqual([z for z, _ in seq], [-65.20, -65.24, -65.28])


if __name__ == "__main__":
    unittest.main()

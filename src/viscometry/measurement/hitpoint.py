"""
Hitpoint extraction: last non-hit Z-level before 3 consecutive hit Z-levels.

Used for experiment viscosity trimming (exclude deeper than hitpoint) and calibration (rough hitpoint alias).
Assumes descent decreases Z (Z_STEP_SIZE < 0): shallower points have larger Z.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def build_z_hit_sequence(cell_z_rpm_data: Dict[Any, Any]) -> List[Tuple[float, bool]]:
    """
    Build (z, any_hit) pairs in descent order (shallow to deep).

    A Z-level counts as hit if any RPM has Hit_Detected in _metrics.
    """
    z_levels = sorted(
        (float(k) for k in cell_z_rpm_data.keys() if k != "_metrics"),
        reverse=True,
    )
    hit_sequence: List[Tuple[float, bool]] = []
    for z in z_levels:
        rpm_data = cell_z_rpm_data[z]
        if not isinstance(rpm_data, dict):
            continue
        metrics = rpm_data.get("_metrics", {})
        any_hit = any(
            bool(metrics.get(rpm, {}).get("Hit_Detected", False))
            for rpm in metrics
            if rpm != "_metrics"
        )
        hit_sequence.append((z, any_hit))
    return hit_sequence


def extract_hitpoint_from_sequence(hit_sequence: List[Tuple[float, bool]]) -> Optional[float]:
    """
    Return the last Z where hit is False and the next 3 Z-levels are all True.

    hit_sequence must be ordered shallow to deep (descending Z values).
    """
    hitpoint: Optional[float] = None
    n = len(hit_sequence)
    for i in range(n - 3):
        z_val, is_hit = hit_sequence[i]
        if not is_hit and all(hit_sequence[j][1] for j in range(i + 1, i + 4)):
            hitpoint = z_val
    return hitpoint


def extract_hitpoint(cell_z_rpm_data: Dict[Any, Any]) -> Optional[float]:
    """
    Extract hitpoint Z from completed cell measurement data.

    Returns the Z-height (float) or None if no reliable hitpoint was found.
    """
    if not cell_z_rpm_data:
        return None
    return extract_hitpoint_from_sequence(build_z_hit_sequence(cell_z_rpm_data))


def extract_rough_hitpoint(cell_z_rpm_data: Dict[Any, Any]) -> Optional[float]:
    """Calibration-facing alias for extract_hitpoint (same algorithm)."""
    return extract_hitpoint(cell_z_rpm_data)

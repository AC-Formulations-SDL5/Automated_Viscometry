"""Torque-ladder math for Discovery Mode Stage 2 (power-law probe at bulk-offset Z)."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

LADDER_TARGETS: Tuple[float, ...] = (30.0, 40.0, 50.0, 60.0, 70.0)
DEFAULT_LADDER_TOLERANCE_PCT: float = 2.5
DEFAULT_NEWTONIAN_N_THRESHOLD: float = 0.975
DEFAULT_SQUEEZE_BOUNDARY_BASE: float = 0.6
DEFAULT_SURFACE_TORQUE_REF: float = 50.0
DEFAULT_NEWTONIAN_T_TOP_TARGET: float = 30.0


def torque_window_for_target(
    target_pct: float,
    *,
    tolerance_pct: float = DEFAULT_LADDER_TOLERANCE_PCT,
) -> Tuple[float, float]:
    """Inclusive torque window for a ladder target (e.g. 30% ± 2.5%)."""
    t = float(target_pct)
    tol = float(tolerance_pct)
    return (t - tol, t + tol)


def torque_in_target_window(
    torque_pct: float,
    target_pct: float,
    *,
    tolerance_pct: float = DEFAULT_LADDER_TOLERANCE_PCT,
) -> bool:
    lo, hi = torque_window_for_target(target_pct, tolerance_pct=tolerance_pct)
    return lo <= float(torque_pct) <= hi


def fit_n_probe(
    rpms: Sequence[float],
    torques: Sequence[float],
    *,
    min_points: int = 2,
) -> Dict[str, float]:
    """
    Fit Torque% ≈ K * RPM^n via log-log linear regression.

    Returns n_probe in [0, 1], k_coeff, r_squared. On failure uses fallback n=0.5.
    """
    points: List[Tuple[float, float]] = []
    for rpm, torque in zip(rpms, torques):
        r = float(rpm)
        t = float(torque)
        if r <= 0 or t <= 0:
            continue
        points.append((math.log(r), math.log(t)))

    if len(points) < min_points:
        return {
            "n_probe": 0.5,
            "k_coeff": 1.0,
            "r_squared": 0.0,
            "fit_method": "fallback_insufficient_points",
        }

    n_pts = len(points)
    sx = sum(x for x, _ in points)
    sy = sum(y for _, y in points)
    sxx = sum(x * x for x, _ in points)
    sxy = sum(x * y for x, y in points)
    denom = n_pts * sxx - sx * sx
    if abs(denom) < 1e-18:
        return {
            "n_probe": 0.5,
            "k_coeff": 1.0,
            "r_squared": 0.0,
            "fit_method": "fallback_degenerate",
        }

    n_probe = (n_pts * sxy - sx * sy) / denom
    log_k = (sy - n_probe * sx) / n_pts
    k_coeff = math.exp(log_k)
    n_probe = max(0.0, min(1.0, float(n_probe)))

    y_mean = sy / n_pts
    ss_tot = sum((y - y_mean) ** 2 for _, y in points)
    ss_res = sum((y - (log_k + n_probe * x)) ** 2 for x, y in points)
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    return {
        "n_probe": float(n_probe),
        "k_coeff": float(k_coeff),
        "r_squared": float(r_squared),
        "fit_method": "log_log_power_law",
    }


def is_newtonian_probe(
    n_probe: float,
    *,
    threshold: float = DEFAULT_NEWTONIAN_N_THRESHOLD,
) -> bool:
    return float(n_probe) >= float(threshold)


def t_top_target(
    n_probe: float,
    *,
    newtonian_threshold: float = DEFAULT_NEWTONIAN_N_THRESHOLD,
    squeeze_base: float = DEFAULT_SQUEEZE_BOUNDARY_BASE,
    surface_torque_ref: float = DEFAULT_SURFACE_TORQUE_REF,
    newtonian_target: float = DEFAULT_NEWTONIAN_T_TOP_TARGET,
) -> float:
    """Target torque at bulk-offset Z before descent."""
    if is_newtonian_probe(n_probe, threshold=newtonian_threshold):
        return float(newtonian_target)
    return float(surface_torque_ref * (squeeze_base ** float(n_probe)))


def suggest_rpm_for_torque_target(
    current_rpm: float,
    measured_torque_pct: float,
    target_torque: float,
    n_probe: float,
    *,
    rpm_min: float,
    rpm_max: float,
) -> float:
    """n-aware RPM step toward a ladder torque target."""
    from viscometry.discovery.rpm_calibration import clamp_hardware_rpm

    if measured_torque_pct <= 0:
        return clamp_hardware_rpm(current_rpm * 2.0, rpm_min=rpm_min, rpm_max=rpm_max)
    ratio = float(target_torque) / float(measured_torque_pct)
    n = float(n_probe)
    if n > 0.05:
        rpm_raw = current_rpm * (ratio ** (1.0 / n))
    else:
        rpm_raw = current_rpm * ratio
    return clamp_hardware_rpm(rpm_raw, rpm_min=rpm_min, rpm_max=rpm_max)


def solve_rpm_for_torque(
    k_coeff: float,
    n_probe: float,
    target_torque: float,
    *,
    rpm_min: float,
    rpm_max: float,
) -> float:
    """Solve K * RPM^n = target_torque."""
    from viscometry.discovery.rpm_calibration import clamp_hardware_rpm, round_rpm_2dp

    k = float(k_coeff)
    n = float(n_probe)
    t = float(target_torque)
    if k <= 0 or t <= 0:
        return float("nan")
    if n <= 0.05:
        return float("nan")
    rpm = (t / k) ** (1.0 / n)
    return round_rpm_2dp(clamp_hardware_rpm(rpm, rpm_min=rpm_min, rpm_max=rpm_max))


def ladder_target_field_names() -> List[Tuple[str, str]]:
    """Return (rpm_field, torque_field) pairs for ladder targets."""
    return [(f"rpm_{int(t)}", f"torque_{int(t)}") for t in LADDER_TARGETS]

"""Continuous RPM ↔ viscosity calibration for Discovery Mode (power-law at reference torque)."""

from __future__ import annotations

import math
from typing import Optional

# Defaults from manual CSV log-log fit (R² ≈ 0.9998); overridden by discovery_bulk_calibration.json
A_CAL: float = 49236.0731685857
B_CAL: float = -0.9994716233727539
TARGET_TORQUE_REF: float = 50.0
DEFAULT_RPM_MIN: float = 0.1
DEFAULT_RPM_MAX: float = 200.0


def rpm_at_reference_torque(
    eta_cp: float,
    *,
    a_cal: float = A_CAL,
    b_cal: float = B_CAL,
    reference_torque: float = TARGET_TORQUE_REF,
) -> float:
    """RPM that would yield reference_torque% at viscosity eta_cp (power-law fit)."""
    if eta_cp <= 0 or a_cal <= 0:
        return float("nan")
    # reference_torque is the torque level the fit was normalized to (typically 50%)
    _ = reference_torque  # fit is already at 50%; scaling applied in rpm_for_target_torque
    return float(a_cal * (eta_cp ** b_cal))


def rpm_for_target_torque(
    eta_cp: float,
    target_torque: float = 30.0,
    *,
    a_cal: float = A_CAL,
    b_cal: float = B_CAL,
    reference_torque: float = TARGET_TORQUE_REF,
) -> float:
    """Ideal RPM for eta_cp to hit target_torque%, using the 50% reference power-law fit."""
    rpm_ref = rpm_at_reference_torque(eta_cp, a_cal=a_cal, b_cal=b_cal, reference_torque=reference_torque)
    if not math.isfinite(rpm_ref) or reference_torque <= 0:
        return float("nan")
    return float(rpm_ref * (target_torque / reference_torque))


def clamp_hardware_rpm(
    rpm: float,
    *,
    rpm_min: float = DEFAULT_RPM_MIN,
    rpm_max: float = DEFAULT_RPM_MAX,
) -> float:
    """Clamp RPM to instrument operating range."""
    return float(max(rpm_min, min(rpm_max, rpm)))


def suggest_next_rpm_continuous(
    current_rpm: float,
    measured_torque_pct: float,
    *,
    target_torque: float = 30.0,
    rpm_min: float = DEFAULT_RPM_MIN,
    rpm_max: float = DEFAULT_RPM_MAX,
) -> float:
    """Proportional RPM correction without discrete ladder snapping."""
    if measured_torque_pct <= 0:
        return clamp_hardware_rpm(current_rpm * 2.0, rpm_min=rpm_min, rpm_max=rpm_max)
    rpm_raw = current_rpm * (target_torque / measured_torque_pct)
    return clamp_hardware_rpm(rpm_raw, rpm_min=rpm_min, rpm_max=rpm_max)


def eta_from_rpm_torque(
    rpm: float,
    torque_pct: float,
    *,
    a_cal: float = A_CAL,
    b_cal: float = B_CAL,
    reference_torque: float = TARGET_TORQUE_REF,
) -> float:
    """
    Estimate viscosity (cP) from measured RPM and torque using inverse power law.

    Torque-correct RPM to reference level, then invert RPM = A * eta^B.
    """
    if rpm <= 0 or torque_pct <= 0 or a_cal <= 0 or reference_torque <= 0:
        return float("nan")
    rpm_at_ref = rpm * (reference_torque / torque_pct)
    if rpm_at_ref <= 0:
        return float("nan")
    try:
        if abs(b_cal + 1.0) < 1e-6:
            return float(a_cal / rpm_at_ref)
        return float((rpm_at_ref / a_cal) ** (1.0 / b_cal))
    except (ValueError, ZeroDivisionError, OverflowError):
        return float("nan")


def initial_rpm_for_discovery(
    eta_guess: Optional[float],
    *,
    target_torque: float,
    cold_start_rpm: float,
    a_cal: float,
    b_cal: float,
    reference_torque: float,
    rpm_min: float,
    rpm_max: float,
) -> float:
    """Cold start or power-law initial RPM, clamped to hardware limits."""
    if eta_guess is not None and eta_guess > 0:
        rpm = rpm_for_target_torque(
            eta_guess,
            target_torque=target_torque,
            a_cal=a_cal,
            b_cal=b_cal,
            reference_torque=reference_torque,
        )
        if math.isfinite(rpm) and rpm > 0:
            return clamp_hardware_rpm(rpm, rpm_min=rpm_min, rpm_max=rpm_max)
    return clamp_hardware_rpm(cold_start_rpm, rpm_min=rpm_min, rpm_max=rpm_max)

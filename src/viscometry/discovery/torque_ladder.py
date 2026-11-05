"""Torque-ladder math for Discovery Mode Stage 2 (power-law probe at bulk-offset Z)."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

LADDER_TARGETS: Tuple[float, ...] = (20.0, 25.0, 30.0, 35.0, 40.0, 45.0)
DEFAULT_MAX_SCREENING_RPMS = 6
MAX_SCREENING_RPMS_LIMIT = 15
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


def _pick_logspaced(rpms: Sequence[float], count: int) -> List[float]:
    """Pick ``count`` speeds spaced in log RPM, always keeping both ends."""
    ordered = sorted(float(r) for r in rpms if float(r) > 0)
    if len(ordered) <= count:
        return ordered
    logs = [math.log(r) for r in ordered]
    targets = [
        logs[0] + (logs[-1] - logs[0]) * (i / (count - 1))
        for i in range(count)
    ]
    chosen: List[float] = []
    for target in targets:
        best_i = min(
            range(len(ordered)),
            key=lambda i: (abs(logs[i] - target), i),
        )
        rpm = ordered[best_i]
        if rpm not in chosen:
            chosen.append(rpm)
            continue
        for i in sorted(range(len(ordered)), key=lambda i: abs(logs[i] - target)):
            if ordered[i] not in chosen:
                chosen.append(ordered[i])
                break
    return sorted(chosen)


def clamp_max_screening_rpms(value: object, *, default: int = DEFAULT_MAX_SCREENING_RPMS) -> int:
    """Clamp the scan cap to 1–15."""
    try:
        n = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        n = int(default)
    return max(1, min(MAX_SCREENING_RPMS_LIMIT, n))


def select_screening_rpms(
    rungs: Sequence[Dict[str, object]],
    *,
    max_rpms: int = DEFAULT_MAX_SCREENING_RPMS,
    torque_lo: float = 20.0,
    torque_hi: float = 45.0,
    rpm_min: float = 0.1,
    rpm_max: float = 200.0,
) -> List[float]:
    """Choose scan speeds from ladder rungs that landed on target.

    When the cap is at most the number of landed rungs, speeds are log-spaced
    and both ends are kept. When the cap is larger, extra speeds are filled
    from the ladder fit between the slowest and fastest landed speeds. This
    does not request additional probes.
    """
    from viscometry.discovery.rpm_calibration import clamp_hardware_rpm, round_rpm_2dp

    cap = clamp_max_screening_rpms(max_rpms)
    landed: List[Tuple[float, float]] = []
    for row in rungs:
        if not isinstance(row, dict):
            continue
        if str(row.get("status") or "") != "on_target":
            continue
        try:
            rpm = float(row.get("rpm"))  # type: ignore[arg-type]
            torque = float(row.get("torque"))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        if rpm <= 0 or torque <= 0:
            continue
        landed.append((rpm, torque))
    if not landed:
        return []

    by_rpm: Dict[float, float] = {}
    for rpm, torque in landed:
        by_rpm[round_rpm_2dp(rpm)] = torque
    ordered = sorted(by_rpm.items())
    rpms = [rpm for rpm, _torque in ordered]
    torques = [torque for _rpm, torque in ordered]
    if len(rpms) >= cap:
        return [round_rpm_2dp(rpm) for rpm in _pick_logspaced(rpms, cap)]
    if cap == len(rpms) or rpms[-1] <= rpms[0]:
        return [round_rpm_2dp(rpm) for rpm in rpms]

    fit = fit_n_probe(rpms, torques)
    k_coeff = float(fit["k_coeff"])
    n_probe = float(fit["n_probe"])
    selected = list(rpms)
    slots = cap
    logs = [
        math.log(rpms[0]) + (math.log(rpms[-1]) - math.log(rpms[0])) * (i / (slots - 1))
        for i in range(slots)
    ]
    for log_rpm in logs:
        if len(selected) >= cap:
            break
        rpm = round_rpm_2dp(clamp_hardware_rpm(math.exp(log_rpm), rpm_min=rpm_min, rpm_max=rpm_max))
        if any(abs(rpm - have) < 0.015 for have in selected):
            continue
        if n_probe <= 0.05 or k_coeff <= 0:
            continue
        predicted = k_coeff * (rpm ** n_probe)
        if predicted < float(torque_lo) - 1e-6 or predicted > float(torque_hi) + 1e-6:
            continue
        selected.append(rpm)
    selected = sorted(set(round_rpm_2dp(rpm) for rpm in selected))
    if len(selected) > cap:
        return [round_rpm_2dp(rpm) for rpm in _pick_logspaced(selected, cap)]
    return selected

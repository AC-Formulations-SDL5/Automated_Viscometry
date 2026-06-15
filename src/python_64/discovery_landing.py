"""Post-descent landing metrics for Discovery Mode Stage 2."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from hitpoint import extract_hitpoint

_LANDING_NA_REASONS = frozenset({
    "fail_safe",
    "manual_terminate",
    "user_stop",
})


def _is_landing_na_termination(termination_reason: Optional[str]) -> bool:
    if not termination_reason:
        return True
    raw = str(termination_reason).strip().lower()
    if raw in _LANDING_NA_REASONS:
        return True
    if raw.startswith("discovery_"):
        return True
    return raw != "hit_detected"


def _latest_torque_at_z(
    cell_z_rpm_data: Dict[Any, Any],
    z_mm: float,
    discovery_rpm: float,
) -> Optional[float]:
    rpm_data = cell_z_rpm_data.get(z_mm)
    if not isinstance(rpm_data, dict):
        rpm_data = cell_z_rpm_data.get(round(float(z_mm), 3))
    if not isinstance(rpm_data, dict):
        return None

    rpm_key = discovery_rpm
    measurements = rpm_data.get(rpm_key)
    if measurements is None:
        for key, value in rpm_data.items():
            if key in ("_metrics", "_liquid_skip_probe_at_z", "_liquid_skip_torque_label"):
                continue
            try:
                if abs(float(key) - float(discovery_rpm)) < 1e-6:
                    measurements = value
                    break
            except (TypeError, ValueError):
                continue
    if not measurements:
        return None

    if isinstance(measurements, list) and measurements:
        last = measurements[-1]
        if isinstance(last, dict):
            t = last.get("torque_percent")
            if t is not None:
                return float(t)
    return None


def extract_t_bottom(
    cell_z_rpm_data: Dict[Any, Any],
    discovery_rpm: float,
    termination_reason: Optional[str],
) -> Dict[str, Optional[float]]:
    """
    Torque at hitpoint Z (last non-hit before 3 consecutive hits) for discovery RPM.

    Returns dict with t_bottom, z_bottom_mm (None when N/A).
    """
    empty: Dict[str, Optional[float]] = {"t_bottom": None, "z_bottom_mm": None}
    if _is_landing_na_termination(termination_reason):
        return empty
    if not cell_z_rpm_data or discovery_rpm <= 0:
        return empty

    hit_z = extract_hitpoint(cell_z_rpm_data)
    if hit_z is None:
        return empty

    torque = _latest_torque_at_z(cell_z_rpm_data, float(hit_z), float(discovery_rpm))
    if torque is None:
        return empty

    return {"t_bottom": float(torque), "z_bottom_mm": float(hit_z)}


def compute_landing_metrics(
    t_top: Optional[float],
    t_bottom: Optional[float],
    termination_reason: Optional[str],
    *,
    landing_window: tuple[float, float] = (45.0, 55.0),
) -> Dict[str, Any]:
    """
    Compute squeeze factor S and landing_ok / landing_status.

    landing_status: "ok" | "high" | "low" | "na"
    """
    lo, hi = float(landing_window[0]), float(landing_window[1])
    if _is_landing_na_termination(termination_reason):
        return {
            "S": None,
            "landing_ok": None,
            "landing_status": "na",
        }
    if t_top is None or t_bottom is None or t_top <= 0:
        return {
            "S": None,
            "landing_ok": None,
            "landing_status": "na",
        }

    s_val = float(t_bottom) / float(t_top)
    if lo <= float(t_bottom) <= hi:
        status = "ok"
        landing_ok = True
    elif float(t_bottom) > hi:
        status = "high"
        landing_ok = False
    else:
        status = "low"
        landing_ok = False

    return {
        "S": float(s_val),
        "landing_ok": landing_ok,
        "landing_status": status,
    }


def merge_landing_into_discovery_result(
    result: Dict[str, Any],
    cell_z_rpm_data: Dict[Any, Any],
    discovery_rpm: float,
    termination_reason: Optional[str],
    *,
    landing_window: tuple[float, float] = (45.0, 55.0),
) -> Dict[str, Any]:
    """Enrich a discovery result dict with post-descent landing fields."""
    merged = dict(result)
    bottom = extract_t_bottom(cell_z_rpm_data, discovery_rpm, termination_reason)
    t_top = merged.get("T_top")
    if t_top is None and merged.get("t_top") is not None:
        t_top = merged.get("t_top")
    landing = compute_landing_metrics(
        t_top,
        bottom.get("t_bottom"),
        termination_reason,
        landing_window=landing_window,
    )
    merged["T_bottom"] = bottom.get("t_bottom")
    merged["Z_bottom_mm"] = bottom.get("z_bottom_mm")
    merged["S"] = landing.get("S")
    merged["landing_ok"] = landing.get("landing_ok")
    merged["landing_status"] = landing.get("landing_status")
    return merged

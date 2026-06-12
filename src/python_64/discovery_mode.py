"""
Discovery Mode — pure RPM selection logic (no hardware dependencies).

Finds spindle RPM that yields 25–35% torque at bulk-offset Z (rough hit-point + offset).
Uses continuous power-law RPM ↔ viscosity calibration.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from calibration_store import load_calibration
from discovery_rpm_calibration import (
    A_CAL,
    B_CAL,
    DEFAULT_RPM_MAX,
    DEFAULT_RPM_MIN,
    TARGET_TORQUE_REF,
    clamp_hardware_rpm,
    eta_from_rpm_torque,
    initial_rpm_for_discovery,
    suggest_next_rpm_continuous,
)
from discovery_types import (
    DiscoveryConfig,
    DiscoveryProbeRecord,
    DiscoveryResult,
    ProbeExecutor,
)

_MODULE_DIR = Path(__file__).resolve().parent
_CONFIG_PATH = _MODULE_DIR / "calibration_data" / "discovery_bulk_calibration.json"

# Module-level defaults (overridden by DiscoveryConfig / JSON)
K_BULK: float = 6.047104982213263e-04
TARGET_TORQUE_BULK: float = 30.0
TORQUE_WINDOW_BULK: Tuple[float, float] = (25.0, 35.0)
HIT_POINT_OFFSET_MM: float = 0.35
VALID_RPM_LIST: Tuple[float, ...] = (
    0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0, 1.2, 1.3, 1.4, 1.7, 1.8,
    2.1, 2.2, 2.3, 2.6, 2.7, 3.5, 4.0, 4.2, 5.0, 5.5, 5.6, 5.8, 6.0, 8.0,
    8.3, 8.6, 9.0, 10.0, 15.0, 16.0, 34.0, 43.0, 47.0, 48.0, 90.0, 120.0, 200.0,
)
MAX_ITERATIONS: int = 3


def load_discovery_config(*, config_path: Optional[str] = None) -> DiscoveryConfig:
    """Load DiscoveryConfig from JSON; fall back to module constants if missing."""
    path = Path(config_path) if config_path else _CONFIG_PATH
    data: dict = {}
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                data = raw
        except Exception:
            pass

    tw = data.get("torque_window_bulk", list(TORQUE_WINDOW_BULK))
    if isinstance(tw, (list, tuple)) and len(tw) >= 2:
        torque_window = (float(tw[0]), float(tw[1]))
    else:
        torque_window = TORQUE_WINDOW_BULK

    valid = data.get("valid_rpms", list(VALID_RPM_LIST))
    if isinstance(valid, list) and valid:
        valid_rpms = tuple(float(v) for v in valid)
    else:
        valid_rpms = VALID_RPM_LIST

    return DiscoveryConfig(
        k_bulk=float(data.get("k_bulk", K_BULK)),
        target_torque=float(data.get("target_torque_bulk", TARGET_TORQUE_BULK)),
        torque_window=torque_window,
        hit_point_offset_mm=float(data.get("hit_point_offset_mm", HIT_POINT_OFFSET_MM)),
        valid_rpms=valid_rpms,
        max_iterations=int(data.get("max_iterations", MAX_ITERATIONS)),
        a_cal=float(data.get("a_cal", A_CAL)),
        b_cal=float(data.get("b_cal", B_CAL)),
        rpm_min=float(data.get("rpm_min", DEFAULT_RPM_MIN)),
        rpm_max=float(data.get("rpm_max", DEFAULT_RPM_MAX)),
        cold_start_rpm=float(data.get("cold_start_rpm", 5.0)),
        surface_torque_ref=float(data.get("surface_torque_ref", TARGET_TORQUE_REF)),
        a_cal_r_squared=float(data.get("a_cal_r_squared", 0.0)),
        rpm_selection_mode=str(data.get("rpm_selection_mode", "continuous")),
    )


def default_discovery_config() -> DiscoveryConfig:
    return load_discovery_config()


def get_bulk_probe_z(
    cell_id: int,
    *,
    offset_mm: float = HIT_POINT_OFFSET_MM,
    default_safe_z: Optional[float] = None,
) -> Optional[float]:
    """rough_hit_point(cell_id) + offset_mm; None if cell not calibrated."""
    try:
        cal = load_calibration()
        cells = cal.get("cells", {}) if isinstance(cal, dict) else {}
        key = str(int(cell_id))
        if key not in cells:
            return None
        rough_z = float(cells[key])
        return rough_z + float(offset_mm)
    except Exception:
        return None


def check_range_limits(
    torque_pct: float,
    rpm: float,
    *,
    rpm_min: float,
    rpm_max: float,
    over_range_torque_pct: float = 85.0,
    under_range_torque_pct: float = 5.0,
) -> Optional[str]:
    if rpm <= rpm_min + 1e-9 and torque_pct >= over_range_torque_pct:
        return "over_range"
    if rpm >= rpm_max - 1e-9 and torque_pct <= under_range_torque_pct:
        return "under_range"
    return None


def _torque_in_window(torque: float, window: Tuple[float, float]) -> bool:
    return window[0] <= torque <= window[1]


def discover_rpm(
    cell_id: int,
    probe: ProbeExecutor,
    *,
    eta_guess: Optional[float] = None,
    material_label: Optional[str] = None,
    config: Optional[DiscoveryConfig] = None,
    max_iterations: Optional[int] = None,
    on_probe: Optional[Callable[[DiscoveryProbeRecord, "DiscoveryResult"], None]] = None,
) -> DiscoveryResult:
    """Iterative bulk-offset RPM discovery using continuous power-law calibration."""
    cfg = config or default_discovery_config()
    max_iter = max_iterations if max_iterations is not None else cfg.max_iterations
    t_min, t_max = cfg.torque_window

    target_z = get_bulk_probe_z(cell_id, offset_mm=cfg.hit_point_offset_mm)
    empty: DiscoveryResult = {
        "rpm": None,
        "eta_estimate": None,
        "status": "uncalibrated_cell",
        "iterations": 0,
        "probes": [],
        "target_z_mm": target_z,
        "material_label": material_label,
        "from_cache": False,
    }
    if target_z is None:
        return empty

    rpm = initial_rpm_for_discovery(
        eta_guess,
        target_torque=cfg.target_torque,
        cold_start_rpm=cfg.cold_start_rpm,
        a_cal=cfg.a_cal,
        b_cal=cfg.b_cal,
        reference_torque=cfg.surface_torque_ref,
        rpm_min=cfg.rpm_min,
        rpm_max=cfg.rpm_max,
    )

    probes: List[DiscoveryProbeRecord] = []
    status: str = "max_iter_reached"
    final_rpm: Optional[float] = None
    final_eta: Optional[float] = None

    for iteration in range(1, max_iter + 1):
        torque = probe(cell_id, target_z, rpm)
        if torque is None:
            return {
                "rpm": None,
                "eta_estimate": None,
                "status": "probe_failed",
                "iterations": iteration,
                "probes": probes,
                "target_z_mm": target_z,
                "material_label": material_label,
                "from_cache": False,
            }

        eta_est = eta_from_rpm_torque(
            rpm,
            torque,
            a_cal=cfg.a_cal,
            b_cal=cfg.b_cal,
            reference_torque=cfg.surface_torque_ref,
        )
        probes.append(
            DiscoveryProbeRecord(
                rpm=float(rpm),
                torque=float(torque),
                eta_est=None if eta_est != eta_est else float(eta_est),
                z_mm=float(target_z),
            )
        )

        if on_probe is not None:
            partial: DiscoveryResult = {
                "rpm": float(rpm),
                "eta_estimate": None if eta_est != eta_est else float(eta_est),
                "status": "probing",
                "iterations": len(probes),
                "probes": list(probes),
                "target_z_mm": target_z,
                "material_label": material_label,
                "from_cache": False,
            }
            try:
                on_probe(probes[-1], partial)
            except Exception:
                pass

        range_status = check_range_limits(
            torque,
            rpm,
            rpm_min=cfg.rpm_min,
            rpm_max=cfg.rpm_max,
            over_range_torque_pct=cfg.over_range_torque_pct,
            under_range_torque_pct=cfg.under_range_torque_pct,
        )
        if range_status:
            return {
                "rpm": None,
                "eta_estimate": None,
                "status": range_status,
                "iterations": iteration,
                "probes": probes,
                "target_z_mm": target_z,
                "material_label": material_label,
                "from_cache": False,
            }

        if _torque_in_window(torque, cfg.torque_window):
            status = "converged"
            final_rpm = float(rpm)
            final_eta = None if eta_est != eta_est else float(eta_est)
            break

        rpm_next = suggest_next_rpm_continuous(
            rpm,
            torque,
            target_torque=cfg.target_torque,
            rpm_min=cfg.rpm_min,
            rpm_max=cfg.rpm_max,
        )

        if rpm > 0 and abs(rpm_next - rpm) / rpm < cfg.rpm_stability_rel_tol:
            status = "converged_by_stability"
            final_rpm = float(rpm_next)
            final_eta = None if eta_est != eta_est else float(eta_est)
            break

        rpm = rpm_next
    else:
        if probes:
            last = probes[-1]
            final_rpm = last["rpm"]
            final_eta = last.get("eta_est")

    return {
        "rpm": final_rpm,
        "eta_estimate": final_eta,
        "status": status,
        "iterations": len(probes),
        "probes": probes,
        "target_z_mm": target_z,
        "material_label": material_label,
        "from_cache": False,
    }


def is_discovery_success(result: DiscoveryResult) -> bool:
    return result.get("status") in ("converged", "converged_by_stability")

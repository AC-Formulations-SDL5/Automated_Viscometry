"""
Discovery Mode — pure RPM selection logic (no hardware dependencies).

Finds spindle RPM that yields 25–35% torque at bulk-offset Z (rough hit-point + offset).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from calibration_store import load_calibration
from discovery_types import (
    DiscoveryConfig,
    DiscoveryProbeRecord,
    DiscoveryResult,
    ProbeExecutor,
    ViscosityTableRow,
)

_MODULE_DIR = Path(__file__).resolve().parent
_CONFIG_PATH = _MODULE_DIR / "calibration_data" / "discovery_bulk_calibration.json"
_PROJECT_ROOT = _MODULE_DIR.parents[1]

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
MAX_ITERATIONS: int = 4


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
        cold_start_rpm=float(data.get("cold_start_rpm", 5.0)),
    )


def default_discovery_config() -> DiscoveryConfig:
    return load_discovery_config()


def load_viscosity_table_from_config(config: DiscoveryConfig) -> List[ViscosityTableRow]:
    """Load viscosity lookup table path from JSON sidecar if present."""
    path = _CONFIG_PATH
    table_path: Optional[Path] = None
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            rel = data.get("viscosity_table_path")
            if isinstance(rel, str) and rel.strip():
                candidate = _PROJECT_ROOT / rel.strip()
                if candidate.exists():
                    table_path = candidate
        except Exception:
            pass
    if table_path is None:
        default = _PROJECT_ROOT / "results" / "Viscosity Readings - Manual.csv"
        if default.exists():
            table_path = default
    if table_path is None:
        return []

    from discovery_calibration import load_manual_viscosity_rpm_table

    rows = load_manual_viscosity_rpm_table(table_path)
    return [
        ViscosityTableRow(
            viscosity_cp=r["viscosity_cp"],
            rpm=r["rpm"],
            torque_pct=r["torque_pct"],
        )
        for r in rows
    ]


def snap_rpm(rpm_ideal: float, valid_rpms: Sequence[float]) -> float:
    """Return nearest value in valid_rpms (tie -> lower RPM)."""
    if not valid_rpms:
        return float(rpm_ideal)
    best = float(valid_rpms[0])
    best_dist = abs(rpm_ideal - best)
    for rpm in valid_rpms[1:]:
        r = float(rpm)
        dist = abs(rpm_ideal - r)
        if dist < best_dist or (dist == best_dist and r < best):
            best = r
            best_dist = dist
    return best


def _rpm_index(rpm: float, valid_rpms: Sequence[float]) -> int:
    for i, v in enumerate(valid_rpms):
        if abs(float(v) - rpm) < 1e-9:
            return i
    return -1


def clamp_rpm_index_steps(
    current_rpm: float,
    target_rpm: float,
    valid_rpms: Sequence[float],
    max_steps: int,
) -> float:
    """Limit discrete RPM jump to max_steps slots on valid_rpms ladder."""
    if not valid_rpms or max_steps <= 0:
        return snap_rpm(target_rpm, valid_rpms)
    i_cur = _rpm_index(current_rpm, valid_rpms)
    i_tgt = _rpm_index(snap_rpm(target_rpm, valid_rpms), valid_rpms)
    if i_cur < 0 or i_tgt < 0:
        return snap_rpm(target_rpm, valid_rpms)
    delta = max(-max_steps, min(max_steps, i_tgt - i_cur))
    return float(valid_rpms[i_cur + delta])


def cold_start_rpm(valid_rpms: Sequence[float], *, cold_start: float = 5.0) -> float:
    return snap_rpm(cold_start, valid_rpms)


def estimate_initial_rpm(
    eta_guess: float,
    *,
    target_torque: float = TARGET_TORQUE_BULK,
    k_bulk: float = K_BULK,
    valid_rpms: Sequence[float] = VALID_RPM_LIST,
) -> float:
    """RPM_ideal = target_torque / (k_bulk * eta_guess); snap to valid_rpms."""
    if eta_guess <= 0 or k_bulk <= 0:
        return cold_start_rpm(valid_rpms)
    rpm_ideal = target_torque / (k_bulk * eta_guess)
    return snap_rpm(rpm_ideal, valid_rpms)


def initial_rpm_from_viscosity_table(
    eta_guess: float,
    viscosity_table: Sequence[ViscosityTableRow],
    *,
    target_torque_bulk: float = TARGET_TORQUE_BULK,
    surface_torque_ref: float = 50.0,
    valid_rpms: Sequence[float] = VALID_RPM_LIST,
    cold_start: float = 5.0,
) -> float:
    """Nearest-neighbor on Viscosity_cP, scale surface RPM to bulk target, snap."""
    if eta_guess <= 0 or not viscosity_table:
        return cold_start_rpm(valid_rpms, cold_start=cold_start)

    best_row: Optional[ViscosityTableRow] = None
    best_dist = float("inf")
    for row in viscosity_table:
        dist = abs(row["viscosity_cp"] - eta_guess)
        if dist < best_dist:
            best_dist = dist
            best_row = row
    if best_row is None:
        return cold_start_rpm(valid_rpms, cold_start=cold_start)

    rpm_csv = best_row["rpm"]
    scale = target_torque_bulk / surface_torque_ref if surface_torque_ref > 0 else 0.6
    return snap_rpm(rpm_csv * scale, valid_rpms)


def eta_from_probe(torque_pct: float, rpm: float, *, k_bulk: float = K_BULK) -> float:
    if rpm <= 0 or k_bulk <= 0:
        return float("nan")
    return torque_pct / (k_bulk * rpm)


def suggest_next_rpm(
    current_rpm: float,
    measured_torque_pct: float,
    *,
    target_torque: float = TARGET_TORQUE_BULK,
    valid_rpms: Sequence[float],
    max_index_steps: int = 2,
) -> float:
    """Proportional correction: rpm * (target / measured), snap, optional step cap."""
    if measured_torque_pct <= 0:
        return snap_rpm(current_rpm * 2.0, valid_rpms)
    rpm_raw = current_rpm * (target_torque / measured_torque_pct)
    if max_index_steps > 0:
        return clamp_rpm_index_steps(current_rpm, rpm_raw, valid_rpms, max_index_steps)
    return snap_rpm(rpm_raw, valid_rpms)


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
    valid_rpms: Sequence[float],
    *,
    over_range_torque_pct: float = 85.0,
    under_range_torque_pct: float = 5.0,
) -> Optional[str]:
    if not valid_rpms:
        return None
    min_rpm = min(valid_rpms)
    max_rpm = max(valid_rpms)
    if rpm <= min_rpm + 1e-9 and torque_pct >= over_range_torque_pct:
        return "over_range"
    if rpm >= max_rpm - 1e-9 and torque_pct <= under_range_torque_pct:
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
    viscosity_table: Optional[Sequence[ViscosityTableRow]] = None,
) -> DiscoveryResult:
    """Iterative bulk-offset RPM discovery using injected probe callable."""
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

    table = list(viscosity_table) if viscosity_table is not None else load_viscosity_table_from_config(cfg)
    if eta_guess is not None and eta_guess > 0:
        rpm = initial_rpm_from_viscosity_table(
            eta_guess,
            table,
            target_torque_bulk=cfg.target_torque,
            surface_torque_ref=cfg.surface_torque_ref,
            valid_rpms=cfg.valid_rpms,
            cold_start=cfg.cold_start_rpm,
        )
    else:
        rpm = cold_start_rpm(cfg.valid_rpms, cold_start=cfg.cold_start_rpm)

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

        eta_est = eta_from_probe(torque, rpm, k_bulk=cfg.k_bulk)
        probes.append(
            DiscoveryProbeRecord(
                rpm=float(rpm),
                torque=float(torque),
                eta_est=None if eta_est != eta_est else float(eta_est),
                z_mm=float(target_z),
            )
        )

        range_status = check_range_limits(
            torque,
            rpm,
            cfg.valid_rpms,
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

        rpm_next = suggest_next_rpm(
            rpm,
            torque,
            target_torque=cfg.target_torque,
            valid_rpms=cfg.valid_rpms,
            max_index_steps=cfg.max_rpm_index_steps,
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

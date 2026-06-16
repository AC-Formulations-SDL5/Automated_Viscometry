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
    round_rpm_2dp,
    suggest_next_rpm_continuous,
)
from discovery_torque_ladder import (
    LADDER_TARGETS,
    fit_n_probe,
    is_newtonian_probe,
    solve_rpm_for_torque,
    suggest_rpm_for_torque_target,
    t_top_target,
    torque_in_target_window,
    torque_window_for_target,
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
DEFAULT_LADDER_TARGETS: Tuple[float, ...] = LADDER_TARGETS
DEFAULT_LADDER_TOLERANCE_PCT: float = 2.5
DEFAULT_NEWTONIAN_N_THRESHOLD: float = 0.975
DEFAULT_SQUEEZE_BOUNDARY_BASE: float = 0.6
DEFAULT_LADDER_MAX_ITER_PER_TARGET: int = 3
DEFAULT_LANDING_TORQUE_WINDOW: Tuple[float, float] = (45.0, 55.0)
DEFAULT_MIN_LADDER_POINTS: int = 3
DEFAULT_MIN_POWER_LAW_R2: float = 0.85


def _parse_float_tuple(raw: object, default: Tuple[float, ...]) -> Tuple[float, ...]:
    if isinstance(raw, (list, tuple)) and raw:
        return tuple(float(v) for v in raw)
    return default


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

    lw = data.get("landing_torque_window", list(DEFAULT_LANDING_TORQUE_WINDOW))
    if isinstance(lw, (list, tuple)) and len(lw) >= 2:
        landing_window = (float(lw[0]), float(lw[1]))
    else:
        landing_window = DEFAULT_LANDING_TORQUE_WINDOW

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
        discovery_stage2_enabled=bool(data.get("discovery_stage2_enabled", True)),
        ladder_targets=_parse_float_tuple(
            data.get("ladder_targets"), DEFAULT_LADDER_TARGETS
        ),
        ladder_tolerance_pct=float(
            data.get("ladder_tolerance_pct", DEFAULT_LADDER_TOLERANCE_PCT)
        ),
        newtonian_n_threshold=float(
            data.get("newtonian_n_threshold", DEFAULT_NEWTONIAN_N_THRESHOLD)
        ),
        squeeze_boundary_base=float(
            data.get("squeeze_boundary_base", DEFAULT_SQUEEZE_BOUNDARY_BASE)
        ),
        hello_probe_rpm=float(data.get("hello_probe_rpm", 5.0)),
        ladder_max_iterations_per_target=int(
            data.get("ladder_max_iterations_per_target", DEFAULT_LADDER_MAX_ITER_PER_TARGET)
        ),
        landing_torque_window=landing_window,
        min_ladder_points_for_fit=int(
            data.get("min_ladder_points_for_fit", DEFAULT_MIN_LADDER_POINTS)
        ),
        min_power_law_r_squared=float(
            data.get("min_power_law_r_squared", DEFAULT_MIN_POWER_LAW_R2)
        ),
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

    rpm = round_rpm_2dp(
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
        rpm_recorded = round_rpm_2dp(rpm)
        probes.append(
            DiscoveryProbeRecord(
                rpm=rpm_recorded,
                torque=float(torque),
                eta_est=None if eta_est != eta_est else float(eta_est),
                z_mm=float(target_z),
            )
        )

        if on_probe is not None:
            partial: DiscoveryResult = {
                "rpm": rpm_recorded,
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
            final_rpm = rpm_recorded
            final_eta = None if eta_est != eta_est else float(eta_est)
            break

        rpm_next = round_rpm_2dp(
            suggest_next_rpm_continuous(
                rpm,
                torque,
                target_torque=cfg.target_torque,
                rpm_min=cfg.rpm_min,
                rpm_max=cfg.rpm_max,
            )
        )

        if rpm > 0 and abs(rpm_next - rpm) / rpm < cfg.rpm_stability_rel_tol:
            status = "converged_by_stability"
            final_rpm = rpm_next
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


def _empty_stage2_result(
    cell_id: int,
    target_z: Optional[float],
    material_label: Optional[str],
    status: str,
) -> DiscoveryResult:
    return DiscoveryResult(
        rpm=None,
        eta_estimate=None,
        status=status,
        iterations=0,
        probes=[],
        target_z_mm=target_z,
        material_label=material_label,
        from_cache=False,
        ladder_status="failed",
    )


def _append_probe_record(
    probes: List[DiscoveryProbeRecord],
    *,
    rpm: float,
    torque: float,
    z_mm: float,
    cfg: DiscoveryConfig,
    ladder_target_pct: Optional[float] = None,
) -> DiscoveryProbeRecord:
    eta_est = eta_from_rpm_torque(
        rpm,
        torque,
        a_cal=cfg.a_cal,
        b_cal=cfg.b_cal,
        reference_torque=cfg.surface_torque_ref,
    )
    record = DiscoveryProbeRecord(
        rpm=round_rpm_2dp(rpm),
        torque=float(torque),
        eta_est=None if eta_est != eta_est else float(eta_est),
        z_mm=float(z_mm),
        ladder_target_pct=ladder_target_pct,
    )
    probes.append(record)
    return record


def _emit_partial(
    on_probe: Optional[Callable[[DiscoveryProbeRecord, DiscoveryResult], None]],
    record: DiscoveryProbeRecord,
    partial: DiscoveryResult,
) -> None:
    if on_probe is None:
        return
    try:
        on_probe(record, partial)
    except Exception:
        pass


def _build_partial_result(
    probes: List[DiscoveryProbeRecord],
    *,
    target_z: float,
    material_label: Optional[str],
    status: str = "ladder_probing",
    extra: Optional[dict] = None,
) -> DiscoveryResult:
    partial: DiscoveryResult = DiscoveryResult(
        rpm=probes[-1]["rpm"] if probes else None,
        eta_estimate=probes[-1].get("eta_est") if probes else None,
        status=status,
        iterations=len(probes),
        probes=list(probes),
        target_z_mm=target_z,
        material_label=material_label,
        from_cache=False,
    )
    if extra:
        for key, val in extra.items():
            partial[key] = val  # type: ignore[literal-required]
    return partial


def _ladder_fields_from_converged(
    converged: Dict[float, Tuple[float, float]],
) -> dict:
    fields: dict = {}
    for target in LADDER_TARGETS:
        key = int(target)
        if target in converged:
            rpm_val, torque_val = converged[target]
            fields[f"rpm_{key}"] = float(rpm_val)
            fields[f"torque_{key}"] = float(torque_val)
    return fields


def discover_rpm_stage2(
    cell_id: int,
    probe: ProbeExecutor,
    *,
    eta_guess: Optional[float] = None,
    material_label: Optional[str] = None,
    config: Optional[DiscoveryConfig] = None,
    on_probe: Optional[Callable[[DiscoveryProbeRecord, DiscoveryResult], None]] = None,
) -> DiscoveryResult:
    """
    Stage 2 discovery: 5-point torque ladder, n_probe fit, Option B final RPM, T_top probe.
    """
    cfg = config or default_discovery_config()
    target_z = get_bulk_probe_z(cell_id, offset_mm=cfg.hit_point_offset_mm)
    if target_z is None:
        return _empty_stage2_result(
            cell_id, None, material_label, "uncalibrated_cell"
        )

    probes: List[DiscoveryProbeRecord] = []
    converged: Dict[float, Tuple[float, float]] = {}
    tol = cfg.ladder_tolerance_pct

    # Hello probe
    hello_rpm = round_rpm_2dp(
        clamp_hardware_rpm(cfg.hello_probe_rpm, rpm_min=cfg.rpm_min, rpm_max=cfg.rpm_max)
    )
    hello_torque = probe(cell_id, target_z, hello_rpm)
    if hello_torque is None:
        return _empty_stage2_result(
            cell_id, target_z, material_label, "probe_failed"
        )
    hello_record = _append_probe_record(
        probes,
        rpm=hello_rpm,
        torque=hello_torque,
        z_mm=target_z,
        cfg=cfg,
        ladder_target_pct=None,
    )
    _emit_partial(
        on_probe,
        hello_record,
        _build_partial_result(probes, target_z=target_z, material_label=material_label),
    )

    last_rpm = hello_rpm
    last_torque = float(hello_torque)
    n_estimate = 1.0

    for target_pct in cfg.ladder_targets:
        target = float(target_pct)
        if target == cfg.ladder_targets[0]:
            rpm_seed = round_rpm_2dp(
                initial_rpm_for_discovery(
                    eta_guess,
                    target_torque=target,
                    cold_start_rpm=last_rpm,
                    a_cal=cfg.a_cal,
                    b_cal=cfg.b_cal,
                    reference_torque=cfg.surface_torque_ref,
                    rpm_min=cfg.rpm_min,
                    rpm_max=cfg.rpm_max,
                )
            )
        else:
            rpm_seed = round_rpm_2dp(
                suggest_rpm_for_torque_target(
                    last_rpm,
                    last_torque,
                    target,
                    n_estimate,
                    rpm_min=cfg.rpm_min,
                    rpm_max=cfg.rpm_max,
                )
            )

        rpm = rpm_seed
        hit = False
        for _ in range(cfg.ladder_max_iterations_per_target):
            torque = probe(cell_id, target_z, rpm)
            if torque is None:
                return DiscoveryResult(
                    rpm=None,
                    eta_estimate=None,
                    status="probe_failed",
                    iterations=len(probes),
                    probes=probes,
                    target_z_mm=target_z,
                    material_label=material_label,
                    from_cache=False,
                    ladder_status="failed",
                    **_ladder_fields_from_converged(converged),
                )

            record = _append_probe_record(
                probes,
                rpm=rpm,
                torque=torque,
                z_mm=target_z,
                cfg=cfg,
                ladder_target_pct=target,
            )
            extra = _ladder_fields_from_converged(converged)
            if len(converged) >= 2:
                fit_pts = list(converged.values())
                fit_r = fit_n_probe(
                    [p[0] for p in fit_pts] + [rpm],
                    [p[1] for p in fit_pts] + [torque],
                )
                extra["n_probe"] = fit_r["n_probe"]
                n_estimate = fit_r["n_probe"]
            _emit_partial(
                on_probe,
                record,
                _build_partial_result(
                    probes,
                    target_z=target_z,
                    material_label=material_label,
                    status="ladder_probing",
                    extra=extra,
                ),
            )

            range_status = check_range_limits(
                torque,
                rpm,
                rpm_min=cfg.rpm_min,
                rpm_max=cfg.rpm_max,
                over_range_torque_pct=cfg.over_range_torque_pct,
                under_range_torque_pct=cfg.under_range_torque_pct,
            )
            if range_status == "over_range" and target <= cfg.ladder_targets[0]:
                return DiscoveryResult(
                    rpm=None,
                    eta_estimate=None,
                    status="ladder_over_range",
                    iterations=len(probes),
                    probes=probes,
                    target_z_mm=target_z,
                    material_label=material_label,
                    from_cache=False,
                    ladder_status="failed",
                    **_ladder_fields_from_converged(converged),
                )
            if range_status == "under_range" and target <= cfg.ladder_targets[0]:
                return DiscoveryResult(
                    rpm=None,
                    eta_estimate=None,
                    status="ladder_under_range",
                    iterations=len(probes),
                    probes=probes,
                    target_z_mm=target_z,
                    material_label=material_label,
                    from_cache=False,
                    ladder_status="failed",
                    **_ladder_fields_from_converged(converged),
                )

            if torque_in_target_window(torque, target, tolerance_pct=tol):
                converged[target] = (round_rpm_2dp(rpm), float(torque))
                last_rpm = round_rpm_2dp(rpm)
                last_torque = float(torque)
                hit = True
                break

            rpm = round_rpm_2dp(
                suggest_rpm_for_torque_target(
                    rpm,
                    torque,
                    target,
                    n_estimate,
                    rpm_min=cfg.rpm_min,
                    rpm_max=cfg.rpm_max,
                )
            )

        if not hit:
            if target <= cfg.ladder_targets[0]:
                return DiscoveryResult(
                    rpm=None,
                    eta_estimate=None,
                    status="ladder_failed",
                    iterations=len(probes),
                    probes=probes,
                    target_z_mm=target_z,
                    material_label=material_label,
                    from_cache=False,
                    ladder_status="failed",
                    **_ladder_fields_from_converged(converged),
                )
            # Higher targets may be skipped if unreachable at max RPM
            continue

    if len(converged) < cfg.min_ladder_points_for_fit:
        return DiscoveryResult(
            rpm=None,
            eta_estimate=None,
            status="ladder_failed",
            iterations=len(probes),
            probes=probes,
            target_z_mm=target_z,
            material_label=material_label,
            from_cache=False,
            ladder_status="failed",
            **_ladder_fields_from_converged(converged),
        )

    ladder_rpms = [converged[t][0] for t in sorted(converged.keys())]
    ladder_torques = [converged[t][1] for t in sorted(converged.keys())]
    fit = fit_n_probe(ladder_rpms, ladder_torques)
    n_probe = fit["n_probe"]
    k_coeff = fit["k_coeff"]
    power_law_r2 = fit["r_squared"]

    newtonian = is_newtonian_probe(n_probe, threshold=cfg.newtonian_n_threshold)
    if power_law_r2 < cfg.min_power_law_r_squared:
        newtonian = True

    t_target = t_top_target(
        n_probe,
        newtonian_threshold=cfg.newtonian_n_threshold,
        squeeze_base=cfg.squeeze_boundary_base,
        surface_torque_ref=cfg.surface_torque_ref,
        newtonian_target=cfg.target_torque,
    )
    discovery_path: str = "newtonian" if newtonian else "non_newtonian"

    ladder_status: str = (
        "complete" if len(converged) == len(cfg.ladder_targets) else "partial"
    )

    # Final RPM convergence toward T_top_target
    if newtonian:
        final_window = cfg.torque_window
        rpm = round_rpm_2dp(
            initial_rpm_for_discovery(
                eta_guess,
                target_torque=cfg.target_torque,
                cold_start_rpm=converged.get(float(cfg.ladder_targets[0]), (last_rpm, last_torque))[0]
                if float(cfg.ladder_targets[0]) in converged
                else last_rpm,
                a_cal=cfg.a_cal,
                b_cal=cfg.b_cal,
                reference_torque=cfg.surface_torque_ref,
                rpm_min=cfg.rpm_min,
                rpm_max=cfg.rpm_max,
            )
        )
        n_step = 1.0
    else:
        solved = solve_rpm_for_torque(
            k_coeff,
            n_probe,
            t_target,
            rpm_min=cfg.rpm_min,
            rpm_max=cfg.rpm_max,
        )
        rpm = solved if solved == solved else last_rpm
        final_window = torque_window_for_target(t_target, tolerance_pct=tol)
        n_step = n_probe

    final_rpm: Optional[float] = None
    final_eta: Optional[float] = None
    t_top_measured: Optional[float] = None
    status: str = "max_iter_reached"

    # Deduplication check: if first ladder target is already converged and within final window,
    # skip the T_top convergence loop and use that RPM directly (common for newtonian samples)
    first_target_pct = float(cfg.ladder_targets[0]) if cfg.ladder_targets else None
    if first_target_pct is not None and first_target_pct in converged:
        first_converged_rpm, first_converged_torque = converged[first_target_pct]
        if _torque_in_window(first_converged_torque, final_window):
            # Already converged at first target, and it's within our final window - reuse it
            final_rpm = round_rpm_2dp(first_converged_rpm)
            final_eta = None  # Would need to recalculate if needed
            t_top_measured = float(first_converged_torque)
            status = "converged"
            # Skip the convergence loop by using an empty range
            convergence_iterations = 0
        else:
            convergence_iterations = cfg.max_iterations
    else:
        convergence_iterations = cfg.max_iterations

    if convergence_iterations > 0:
        for _ in range(convergence_iterations):
            torque = probe(cell_id, target_z, rpm)
            if torque is None:
                return DiscoveryResult(
                    rpm=None,
                    eta_estimate=None,
                    status="probe_failed",
                    iterations=len(probes),
                    probes=probes,
                    target_z_mm=target_z,
                    material_label=material_label,
                    from_cache=False,
                    n_probe=n_probe,
                    is_newtonian=newtonian,
                    power_law_r2=power_law_r2,
                    discovery_path=discovery_path,
                    T_top_target=t_target,
                    ladder_status=ladder_status,
                    **_ladder_fields_from_converged(converged),
                )

            record = _append_probe_record(
                probes,
                rpm=rpm,
                torque=torque,
                z_mm=target_z,
                cfg=cfg,
                ladder_target_pct=None,
            )
            _emit_partial(
                on_probe,
                record,
                _build_partial_result(
                    probes,
                    target_z=target_z,
                    material_label=material_label,
                    status="probing",
                    extra={
                        "n_probe": n_probe,
                        "is_newtonian": newtonian,
                        "T_top_target": t_target,
                        "discovery_path": discovery_path,
                        **_ladder_fields_from_converged(converged),
                    },
                ),
            )

            range_status = check_range_limits(
                torque,
                rpm,
                rpm_min=cfg.rpm_min,
                rpm_max=cfg.rpm_max,
                over_range_torque_pct=cfg.over_range_torque_pct,
                under_range_torque_pct=cfg.under_range_torque_pct,
            )
            if range_status:
                return DiscoveryResult(
                    rpm=None,
                    eta_estimate=None,
                    status=range_status,
                    iterations=len(probes),
                    probes=probes,
                    target_z_mm=target_z,
                    material_label=material_label,
                    from_cache=False,
                    n_probe=n_probe,
                    is_newtonian=newtonian,
                    power_law_r2=power_law_r2,
                    discovery_path=discovery_path,
                    T_top_target=t_target,
                    ladder_status=ladder_status,
                    **_ladder_fields_from_converged(converged),
                )

            eta_est = record.get("eta_est")
            if _torque_in_window(torque, final_window):
                status = "converged"
                final_rpm = round_rpm_2dp(rpm)
                final_eta = eta_est
                t_top_measured = float(torque)
                break

            if newtonian:
                rpm = round_rpm_2dp(
                    suggest_next_rpm_continuous(
                        rpm,
                        torque,
                        target_torque=cfg.target_torque,
                        rpm_min=cfg.rpm_min,
                        rpm_max=cfg.rpm_max,
                    )
                )
            else:
                rpm = round_rpm_2dp(
                    suggest_rpm_for_torque_target(
                        rpm,
                        torque,
                        t_target,
                        n_step,
                        rpm_min=cfg.rpm_min,
                        rpm_max=cfg.rpm_max,
                    )
                )
        else:
            if probes:
                final_rpm = probes[-1]["rpm"]
                final_eta = probes[-1].get("eta_est")
                t_top_measured = probes[-1]["torque"]

    return DiscoveryResult(
        rpm=final_rpm,
        eta_estimate=final_eta,
        status=status,
        iterations=len(probes),
        probes=probes,
        target_z_mm=target_z,
        material_label=material_label,
        from_cache=False,
        n_probe=n_probe,
        is_newtonian=newtonian,
        power_law_r2=power_law_r2,
        discovery_path=discovery_path,
        T_top_target=t_target,
        T_top=t_top_measured,
        ladder_status=ladder_status,
        **_ladder_fields_from_converged(converged),
    )

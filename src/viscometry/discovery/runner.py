"""Per-cell Discovery Mode orchestration (hardware glue, lazy web emit)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from viscometry.discovery.mode import (
    discover_rpm,
    discover_rpm_stage2,
    get_bulk_probe_z,
    is_discovery_success,
    load_discovery_config,
)
from viscometry.discovery.probe import MeasureFn, MoveFn, RowResolver, make_probe_executor
from viscometry.discovery.rpm_calibration import round_rpm_2dp
from viscometry.discovery.types import DiscoveryConfig, DiscoveryProbeRecord, DiscoveryResult

_STAGE2_PAYLOAD_KEYS = (
    "n_probe",
    "is_newtonian",
    "power_law_r2",
    "discovery_path",
    "rpm_30",
    "rpm_40",
    "rpm_50",
    "rpm_60",
    "rpm_70",
    "torque_30",
    "torque_40",
    "torque_50",
    "torque_60",
    "torque_70",
    "T_top_target",
    "T_top",
    "T_bottom",
    "Z_bottom_mm",
    "S",
    "landing_ok",
    "landing_status",
    "ladder_status",
)


def discovery_result_to_web_payload(cell_id: int, result: DiscoveryResult) -> Dict[str, Any]:
    rpm = result.get("rpm")
    probes = result.get("probes", [])
    rounded_probes = []
    for probe_row in probes:
        if not isinstance(probe_row, dict):
            continue
        entry = dict(probe_row)
        if entry.get("rpm") is not None:
            entry["rpm"] = round_rpm_2dp(float(entry["rpm"]))
        rounded_probes.append(entry)
    payload: Dict[str, Any] = {
        "cell_id": int(cell_id),
        "rpm": round_rpm_2dp(float(rpm)) if rpm is not None else None,
        "eta_estimate": result.get("eta_estimate"),
        "status": result.get("status"),
        "iterations": result.get("iterations"),
        "probes": rounded_probes,
        "target_z_mm": result.get("target_z_mm"),
        "material_label": result.get("material_label"),
    }
    for key in _STAGE2_PAYLOAD_KEYS:
        if key in result:
            payload[key] = result.get(key)
    return payload


def _emit_discovery_update(cell_id: int, result: DiscoveryResult) -> None:
    try:
        from viscometry.web.app import web_interface

        payload = discovery_result_to_web_payload(cell_id, result)
        web_interface.emit_discovery_update(payload)
    except Exception:
        pass


def run_discovery_for_cell(
    cell_id: int,
    cnc: Any,
    client: Any,
    *,
    eta_guess: Optional[float] = None,
    material_label: Optional[str] = None,
    config: Optional[DiscoveryConfig] = None,
    move_fn: MoveFn,
    measure_fn: MeasureFn,
    row_resolver: RowResolver,
    measure_module: Any = None,
    probe_duration_s: float = 60.0,
    duck_torque_pct: float = 80.0,
    web_emit: bool = True,
) -> Tuple[DiscoveryResult, List[float]]:
    """
    Run RPM discovery for one cell.

    Returns (result, cell_rpms_for_full_scan). On failure cell_rpms is [].
    """
    cfg = config or load_discovery_config()

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
        if web_emit:
            _emit_discovery_update(cell_id, empty)
        return empty, []

    row_number, local_cell = row_resolver(cell_id)
    move_fn(cnc, row_number, local_cell, target_z)
    if measure_module is not None:
        settle_s = float(getattr(measure_module, "SETTLE_TIME", 1.0))
        sleep_fn = getattr(measure_module, "sleep_with_stop", None)
        if callable(sleep_fn):
            sleep_fn(settle_s)

    probe = make_probe_executor(
        cnc,
        client,
        measure_torque_fn=measure_fn,
        measure_module=measure_module,
        measurement_duration_s=probe_duration_s,
        sample_interval_s=min(5.0, probe_duration_s / 2.0) if probe_duration_s > 0 else None,
        duck_torque_pct=duck_torque_pct,
    )

    if web_emit:
        try:
            from viscometry.web.app import web_interface

            label = (
                "Stage 2 torque ladder"
                if cfg.discovery_stage2_enabled
                else "RPM probe"
            )
            web_interface.update_status(
                f"Discovery: Cell {cell_id} — {label} at Z={target_z:.3f} mm (bulk offset)"
            )
        except Exception:
            pass

    def _on_probe(_record: DiscoveryProbeRecord, partial: DiscoveryResult) -> None:
        if web_emit:
            _emit_discovery_update(cell_id, partial)

    discover_fn = discover_rpm_stage2 if cfg.discovery_stage2_enabled else discover_rpm
    result = discover_fn(
        cell_id,
        probe,
        eta_guess=eta_guess,
        material_label=material_label,
        config=cfg,
        on_probe=_on_probe if web_emit else None,
    )

    if web_emit:
        _emit_discovery_update(cell_id, result)

    if is_discovery_success(result) and result.get("rpm") is not None:
        return result, [round_rpm_2dp(float(result["rpm"]))]

    return result, []

"""Per-cell Discovery Mode orchestration (hardware glue, lazy web emit)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from discovery_mode import (
    discover_rpm,
    get_bulk_probe_z,
    is_discovery_success,
    load_discovery_config,
)
from discovery_probe import MeasureFn, MoveFn, RowResolver, make_probe_executor
from discovery_rpm_calibration import round_rpm_2dp
from discovery_types import DiscoveryConfig, DiscoveryProbeRecord, DiscoveryResult


def discovery_result_to_web_payload(cell_id: int, result: DiscoveryResult) -> Dict[str, Any]:
    rpm = result.get("rpm")
    probes = result.get("probes", [])
    rounded_probes = []
    for probe in probes:
        if not isinstance(probe, dict):
            continue
        entry = dict(probe)
        if entry.get("rpm") is not None:
            entry["rpm"] = round_rpm_2dp(float(entry["rpm"]))
        rounded_probes.append(entry)
    return {
        "cell_id": int(cell_id),
        "rpm": round_rpm_2dp(float(rpm)) if rpm is not None else None,
        "eta_estimate": result.get("eta_estimate"),
        "status": result.get("status"),
        "iterations": result.get("iterations"),
        "probes": rounded_probes,
        "target_z_mm": result.get("target_z_mm"),
        "material_label": result.get("material_label"),
    }


def _emit_discovery_update(cell_id: int, result: DiscoveryResult) -> None:
    try:
        from web_interface import web_interface

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
    probe_duration_s: float = 12.0,
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
    )

    if web_emit:
        try:
            from web_interface import web_interface

            web_interface.update_status(
                f"Discovery: Cell {cell_id} — probing RPM at Z={target_z:.3f} mm (bulk offset)"
            )
        except Exception:
            pass

    def _on_probe(_record: DiscoveryProbeRecord, partial: DiscoveryResult) -> None:
        if web_emit:
            _emit_discovery_update(cell_id, partial)

    result = discover_rpm(
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

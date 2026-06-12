"""Per-cell Discovery Mode orchestration (hardware glue, lazy web emit)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from discovery_mode import (
    discover_rpm,
    is_discovery_success,
    load_discovery_config,
    load_viscosity_table_from_config,
)
from discovery_probe import MeasureFn, MoveFn, RowResolver, make_probe_executor
from discovery_types import DiscoveryConfig, DiscoveryResult


def discovery_result_to_web_payload(cell_id: int, result: DiscoveryResult) -> Dict[str, Any]:
    return {
        "cell_id": int(cell_id),
        "rpm": result.get("rpm"),
        "eta_estimate": result.get("eta_estimate"),
        "status": result.get("status"),
        "iterations": result.get("iterations"),
        "probes": result.get("probes", []),
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
    table = load_viscosity_table_from_config(cfg)

    probe = make_probe_executor(
        cnc,
        client,
        move_to_cell_fn=move_fn,
        measure_torque_fn=measure_fn,
        row_resolver=row_resolver,
        measure_module=measure_module,
        measurement_duration_s=probe_duration_s,
        sample_interval_s=min(5.0, probe_duration_s / 2.0) if probe_duration_s > 0 else None,
    )

    if web_emit:
        try:
            from web_interface import web_interface

            web_interface.update_status(
                f"Discovery: Cell {cell_id} — probing RPM near Z={cfg.hit_point_offset_mm:.2f} mm offset"
            )
        except Exception:
            pass

    result = discover_rpm(
        cell_id,
        probe,
        eta_guess=eta_guess,
        material_label=material_label,
        config=cfg,
        viscosity_table=table,
    )

    if web_emit:
        _emit_discovery_update(cell_id, result)

    if is_discovery_success(result) and result.get("rpm") is not None:
        return result, [float(result["rpm"])]

    return result, []

"""CSV export and experiment history helpers."""

from __future__ import annotations

import csv
import time
from typing import Dict, List, Optional

from viscometry.paths import runs_dir_for_today
from viscometry.rheology.live_adapter import SUMMARY_KEY
from viscometry.run import settings
from viscometry.run.cells import global_cell_to_row_and_local

_RPM_DATA_META_KEYS = frozenset({
    "_metrics",
    "_liquid_skipped_z",
    "_liquid_skip_torque_label",
    "_liquid_skip_probe_at_z",
})


def _get_web_interface():
    from viscometry.web.app import web_interface
    return web_interface


def _resolve_csv_path(filename: str):
    return runs_dir_for_today() / filename


def _sanitize_experiment_slug(name: str) -> str:
    """Create a filename-safe slug for experiment output files."""
    cleaned = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in (name or '').strip())
    cleaned = '_'.join(part for part in cleaned.split('_') if part)
    return cleaned[:80] if cleaned else "experiment"


SUMMARY_CSV_HEADERS = [
    "row", "cell", "Cell_Label", "Z_Height_mm", "RPM",
    "Elapsed_Time_s", "Torque_%", "Rotational_Drag", "Hit_Detected",
]

TIMESERIES_CSV_HEADERS = [
    "row", "cell", "Cell_Label", "Z_Height_mm", "RPM",
    "Elapsed_Time_s", "Torque_%", "Rotational_Drag",
]


def _append_cell_termination_metadata(
    csv_writer,
    all_data: Dict[int, object],
    termination_by_cell: Optional[Dict[int, str]] = None,
) -> None:
    """Write per-cell termination methods into CSV metadata comments."""
    if not all_data:
        return
    term = termination_by_cell or {}
    cell_map = {cell: term.get(cell, "normal") for cell in sorted(all_data.keys())}
    csv_writer.writerow([f"# Cell termination methods: {cell_map}"])


def _liquid_skip_csv_row(row_number: int, global_cell: int, z_height: float, rpm: float, torque_label: str) -> List[str]:
    """One CSV row for a Z-level skipped due to low torque (no liquid contact)."""
    sk = "SKIPPED"
    return [
        str(row_number),
        str(global_cell),
        settings.CELL_CONTENT_MAP.get(global_cell, ""),
        f"{z_height:.3f}",
        f"{rpm:.1f}",
        sk,
        torque_label,
        sk,
        "False",
    ]


def _liquid_skip_torque_label(th: float) -> str:
    if abs(th - round(th)) < 1e-9:
        return f"<{int(round(th))}%"
    return f"<{th:.1f}%"


def _append_discovery_csv_metadata(csv_writer) -> None:
    """Write Discovery Mode RPM probe summary into CSV metadata comments."""
    if not settings.DISCOVERY_MODE_ENABLED:
        return
    try:
        results = dict(_get_web_interface().discovery_results_by_cell or {})
    except Exception:
        results = {}
    if not results:
        return

    csv_writer.writerow(["# Discovery Mode Results"])
    csv_writer.writerow([
        "# Cell,Cell_Label,n_probe,is_newtonian,T_top,T_top_target,T_bottom,Z_bottom_mm,S,"
        "landing_ok,landing_status,rpm_30,rpm_40,rpm_50,rpm_60,rpm_70,power_law_r2,"
        "discovery_path,status,Discovered_RPM,eta_est_cP,Target_Z_mm"
    ])
    for cell_key in sorted(results.keys(), key=lambda k: int(k)):
        entry = results.get(cell_key) or {}
        try:
            cell_id = int(cell_key)
        except (TypeError, ValueError):
            continue
        label = settings.CELL_CONTENT_MAP.get(cell_id, "")
        csv_writer.writerow([
            f"# {cell_id},{label},"
            f"{entry.get('n_probe', '')},"
            f"{entry.get('is_newtonian', '')},"
            f"{entry.get('T_top', '')},"
            f"{entry.get('T_top_target', '')},"
            f"{entry.get('T_bottom', '')},"
            f"{entry.get('Z_bottom_mm', '')},"
            f"{entry.get('S', '')},"
            f"{entry.get('landing_ok', '')},"
            f"{entry.get('landing_status', '')},"
            f"{entry.get('rpm_30', '')},"
            f"{entry.get('rpm_40', '')},"
            f"{entry.get('rpm_50', '')},"
            f"{entry.get('rpm_60', '')},"
            f"{entry.get('rpm_70', '')},"
            f"{entry.get('power_law_r2', '')},"
            f"{entry.get('discovery_path', '')},"
            f"{entry.get('status', '')},"
            f"{entry.get('rpm', '')},"
            f"{entry.get('eta_estimate', '')},"
            f"{entry.get('target_z_mm', '')}",
        ])
    csv_writer.writerow([
        "# Probe detail: Cell,Cell_Label,Probe#,Probe_RPM,Probe_Torque_%,"
        "Probe_eta_cP,Ladder_Target_%"
    ])
    for cell_key in sorted(results.keys(), key=lambda k: int(k)):
        entry = results.get(cell_key) or {}
        try:
            cell_id = int(cell_key)
        except (TypeError, ValueError):
            continue
        label = settings.CELL_CONTENT_MAP.get(cell_id, "")
        probes = entry.get("probes") or []
        for idx, probe in enumerate(probes, 1):
            p_rpm = probe.get("rpm", "")
            p_torque = probe.get("torque", "")
            p_eta = probe.get("eta_est", "")
            ladder_tgt = probe.get("ladder_target_pct", "")
            csv_writer.writerow([
                f"# {cell_id},{label},{idx},"
                f"{'' if p_rpm is None else p_rpm},"
                f"{'' if p_torque is None else p_torque},"
                f"{'' if p_eta is None else p_eta},"
                f"{'' if ladder_tgt is None else ladder_tgt}",
            ])
    csv_writer.writerow([])


def _append_predicted_viscosity_csv_metadata(csv_writer) -> None:
    """Write predicted viscosity summary rows into CSV metadata comments."""
    csv_writer.writerow([f"# Viscosity prediction mode: {settings.VISCOSITY_PREDICTION_MODE}"])
    if settings.VISCOSITY_PREDICTION_MODE == "off" or not settings.CELL_VISCOSITY_RESULTS:
        csv_writer.writerow([])
        return
    csv_writer.writerow(["# Predicted Viscosity Results"])
    csv_writer.writerow([
        "# Cell,Cell_Label,RPM,Viscosity_kCp,A,B,R2,regime,n,n_points_used,fit_success"
    ])
    for global_cell in sorted(settings.CELL_VISCOSITY_RESULTS.keys()):
        rpm_map = settings.CELL_VISCOSITY_RESULTS[global_cell]
        label = settings.CELL_CONTENT_MAP.get(global_cell, "")
        summary = rpm_map.get(SUMMARY_KEY) if isinstance(rpm_map, dict) else {}
        cell_regime = summary.get("regime") if isinstance(summary, dict) else ""
        cell_n = summary.get("n") if isinstance(summary, dict) else ""
        for rpm in sorted(k for k in rpm_map.keys() if k != SUMMARY_KEY):
            result = rpm_map[rpm]
            if not isinstance(result, dict):
                continue
            visc = result.get("viscosity_kcp")
            a_val = result.get("A")
            b_val = result.get("B")
            r2_val = result.get("R2")
            csv_writer.writerow([
                f"# {global_cell},{label},{rpm},"
                f"{'' if visc is None else visc},"
                f"{'' if a_val is None else a_val},"
                f"{'' if b_val is None else b_val},"
                f"{'' if r2_val is None else r2_val},"
                f"{cell_regime},"
                f"{'' if cell_n is None else cell_n},"
                f"{result.get('n_points_used', 0)},"
                f"{bool(result.get('success'))}",
            ])
    csv_writer.writerow([])


PARTIAL_TERMINATION_REASONS = frozenset({"user_stop", "manual_terminate"})


def is_partial_termination(reason: str) -> bool:
    """True when a cell ended before completing its full Z sweep."""
    return str(reason or "").strip().lower() in PARTIAL_TERMINATION_REASONS


def _z_keys_from_cell_data(cell_data: dict) -> List[float]:
    """Numeric Z-height keys from a cell's all_data entry (excludes metadata)."""
    out: List[float] = []
    for key in cell_data.keys():
        if isinstance(key, str):
            continue
        try:
            out.append(float(key))
        except (TypeError, ValueError):
            continue
    return out


def count_z_levels(all_data: Dict, cell_id: int) -> int:
    """Count Z levels with structured data for a cell in all_data."""
    cell_data = all_data.get(cell_id)
    if cell_data is None:
        try:
            cell_data = all_data.get(int(cell_id))
        except (TypeError, ValueError):
            cell_data = None
    if not isinstance(cell_data, dict):
        return 0
    return len(_z_keys_from_cell_data(cell_data))


def extract_latest_points_from_all_data(
    all_data: Dict,
    cell_ids: List[int],
    run_start_ts: Optional[float] = None,
) -> List[Dict]:
    """
    Extract the latest measurement per Z×RPM from all_data for experiment history.
    """
    points: List[Dict] = []
    for cell_id in cell_ids:
        cell_data = all_data.get(cell_id)
        if cell_data is None:
            try:
                cell_data = all_data.get(int(cell_id))
            except (TypeError, ValueError):
                cell_data = None
        if not isinstance(cell_data, dict):
            continue
        for z_height in sorted(_z_keys_from_cell_data(cell_data), reverse=True):
            rpm_data = cell_data.get(z_height)
            if not isinstance(rpm_data, dict):
                continue
            for rpm in sorted(k for k in rpm_data.keys() if k not in _RPM_DATA_META_KEYS):
                measurements = rpm_data.get(rpm)
                if not measurements:
                    continue
                latest = measurements[-1]
                torque_percent = float(latest.get("torque_percent") or 0)
                rpm_f = float(rpm)
                rotational_drag = abs(torque_percent) / rpm_f if rpm_f > 0 else 0.0
                ts = latest.get("timestamp")
                if ts is None:
                    elapsed = latest.get("elapsed_time")
                    if run_start_ts is not None and elapsed is not None:
                        try:
                            ts = float(run_start_ts) + float(elapsed)
                        except (TypeError, ValueError):
                            ts = time.time()
                    else:
                        ts = time.time()
                else:
                    try:
                        ts = float(ts)
                    except (TypeError, ValueError):
                        ts = time.time()
                points.append({
                    "timestamp": ts,
                    "cell_id": int(cell_id),
                    "height": float(z_height),
                    "torque_percent": torque_percent,
                    "rotational_drag": rotational_drag,
                    "rpm": rpm_f,
                    "is_final_save": True,
                })
    return points
def save_partial_data(all_data: Dict[int, Dict[float, Dict[float, Optional[List[Dict]]]]],
                     timestamp: str, mode: str, completed_cells: List[int], experiment_name: str,
                     termination_by_cell: Optional[Dict[int, str]] = None) -> str:
    """Deprecated wrapper — use save_dynamic_analysis_data(..., partial=True)."""
    csv_path = save_dynamic_analysis_data(
        all_data,
        timestamp,
        mode,
        experiment_name,
        termination_by_cell=termination_by_cell,
        partial=True,
        completed_cells=completed_cells,
    )
    maybe_save_timeseries_data(
        all_data,
        timestamp,
        mode,
        experiment_name,
        termination_by_cell=termination_by_cell,
        partial=True,
        completed_cells=completed_cells,
    )
    return csv_path


def save_dynamic_analysis_data(all_data: Dict[int, Dict[float, Dict[float, Optional[List[Dict]]]]],
                              timestamp: str, mode: str, experiment_name: str,
                              termination_by_cell: Optional[Dict[int, str]] = None,
                              partial: bool = False,
                              completed_cells: Optional[List[int]] = None) -> str:
    """Save dynamic analysis data — latest measurement per Z×RPM."""
    if not all_data:
        print("No data collected to save.")
        return ""

    slug = _sanitize_experiment_slug(experiment_name)
    if partial:
        print(f"\nSAVING PARTIAL RESULTS...")
        if completed_cells is not None:
            print(f"Completed cells: {completed_cells}")
        csv_filename = str(_resolve_csv_path(f"dynamic_analysis_{slug}_{mode}_PARTIAL_{timestamp}.csv"))
    else:
        csv_filename = str(_resolve_csv_path(f"dynamic_analysis_{slug}_{mode}_{timestamp}.csv"))

    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)

        # Write metadata header
        if partial:
            csv_writer.writerow([f"# Dynamic Analysis - Mode: {mode.upper()} (PARTIAL RESULTS)"])
        else:
            csv_writer.writerow([f"# Dynamic Analysis - Mode: {mode.upper()}"])
        csv_writer.writerow([f"# Experiment Name: {experiment_name}"])
        csv_writer.writerow([f"# Test RPMs (global fallback): {settings.TEST_RPMS}"])
        if settings.TESTING_MODE == "custom" and settings.CELL_RPM_MAP:
            csv_writer.writerow([f"# Per-cell RPM overrides: {settings.CELL_RPM_MAP}"])
        if settings.CELL_CONTENT_MAP:
            csv_writer.writerow([f"# Per-cell sample labels: {settings.CELL_CONTENT_MAP}"])
        csv_writer.writerow([f"# Timestamp: {timestamp}"])
        csv_writer.writerow([f"# Cell numbering: Row 1 = cells 1-6, Row 2 = cells 7-12, Row 3 = cells 13-18"])
        if partial and completed_cells is not None:
            csv_writer.writerow([f"# Completed cells: {completed_cells}"])
        csv_writer.writerow([f"# Feedback Control: {'ENABLED' if settings.FEEDBACK_CONTROL_ENABLED else 'DISABLED'}"])
        if settings.FEEDBACK_CONTROL_ENABLED:
            csv_writer.writerow([f"# Feedback R2 Thresholds: Drag = {settings.R2_DRAG_MIN}, CV = {settings.R2_CV_MIN}, Slope = {settings.R2_SLOPE_MIN}, Confidence = {settings.HIT_POINT_CONFIDENCE_THRESHOLD}"])
            csv_writer.writerow([f"# Confidence Weights: 2nd-Deriv(Drag/CV/Slope) = {settings.WEIGHT_2ND_DERIV_DRAG}/{settings.WEIGHT_2ND_DERIV_CV}/{settings.WEIGHT_2ND_DERIV_SLOPE}, R2(Drag/CV/Slope) = {settings.WEIGHT_R2_DRAG}/{settings.WEIGHT_R2_CV}/{settings.WEIGHT_R2_SLOPE}"])
        if settings.LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED:
            csv_writer.writerow([
                f"# Low-torque liquid-contact hunt: per RPM at each Z, skip RPM when first sample at "
                f"elapsed >= {settings.SAMPLE_INTERVAL:.1f}s is < "
                f"{settings.LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT:.2f}% (regular runs only); "
                f"skipped RPM rows use {_liquid_skip_torque_label(settings.LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT)} "
                "and SKIPPED metrics"
            ])
        if partial:
            csv_writer.writerow([
                "# WARNING: Experiment was terminated early - these are partial results"
            ])
        _append_discovery_csv_metadata(csv_writer)
        _append_predicted_viscosity_csv_metadata(csv_writer)
        _append_cell_termination_metadata(csv_writer, all_data, termination_by_cell)

        csv_writer.writerow(SUMMARY_CSV_HEADERS)

        for global_cell in sorted(all_data.keys()):
            row_number, local_cell = global_cell_to_row_and_local(global_cell)
            cell_data = all_data[global_cell]
            z_heights = sorted(_z_keys_from_cell_data(cell_data), reverse=True)
            
            for z_height in z_heights:
                if z_height in cell_data:
                    rpm_data = cell_data[z_height]
                    liquid_probe = bool(rpm_data.get("_liquid_skip_probe_at_z"))
                    tlab = rpm_data.get(
                        "_liquid_skip_torque_label",
                        _liquid_skip_torque_label(settings.LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT),
                    )
                    metrics_data = cell_data[z_height].get("_metrics", {})
                    for rpm in sorted(k for k in rpm_data.keys() if k not in _RPM_DATA_META_KEYS):
                        measurements = rpm_data.get(rpm)
                        if measurements is None:
                            if liquid_probe:
                                csv_writer.writerow(
                                    _liquid_skip_csv_row(
                                        row_number, global_cell, z_height, rpm, tlab
                                    )
                                )
                            continue
                        if measurements is not None:
                            rpm_metrics = metrics_data.get(rpm, {})
                            hit_detected = bool(rpm_metrics.get('Hit_Detected', False))

                            # Use LATEST measurement only (as requested by user)
                            latest_measurement = measurements[-1]
                            torque_percent = latest_measurement['torque_percent']
                            rotational_drag = abs(torque_percent) / rpm if rpm > 0 else float('inf')

                            csv_writer.writerow([
                                str(row_number),
                                str(global_cell),
                                settings.CELL_CONTENT_MAP.get(global_cell, ''),
                                f"{z_height:.3f}",
                                f"{rpm:.1f}",
                                f"{latest_measurement['elapsed_time']:.2f}",
                                f"{latest_measurement['torque_percent']:.3f}",
                                f"{rotational_drag:.6f}",
                                str(hit_detected),
                            ])

    if partial:
        print(f"Partial results saved to: {csv_filename}")
    else:
        print(f"All data saved to: {csv_filename}")
    return csv_filename


def save_timeseries_data(
    all_data: Dict[int, Dict[float, Dict[float, Optional[List[Dict]]]]],
    timestamp: str,
    mode: str,
    experiment_name: str,
    termination_by_cell: Optional[Dict[int, str]] = None,
    partial: bool = False,
    completed_cells: Optional[List[int]] = None,
) -> str:
    """Save every collected sample (one row per dwell reading) to a separate CSV."""
    if not all_data:
        return ""

    slug = _sanitize_experiment_slug(experiment_name)
    if partial:
        csv_filename = str(_resolve_csv_path(f"dynamic_analysis_{slug}_{mode}_PARTIAL_{timestamp}_timeseries.csv"))
    else:
        csv_filename = str(_resolve_csv_path(f"dynamic_analysis_{slug}_{mode}_{timestamp}_timeseries.csv"))

    with open(csv_filename, "w", newline="", encoding="utf-8") as csvfile:
        csv_writer = csv.writer(csvfile)
        if partial:
            csv_writer.writerow([f"# Timeseries - Mode: {mode.upper()} (PARTIAL RESULTS)"])
        else:
            csv_writer.writerow([f"# Timeseries - Mode: {mode.upper()}"])
        csv_writer.writerow([f"# Experiment Name: {experiment_name}"])
        csv_writer.writerow([f"# Timestamp: {timestamp}"])
        csv_writer.writerow(["# Save all sample data: ENABLED"])
        csv_writer.writerow([f"# Sample interval (s): {settings.SAMPLE_INTERVAL:.3f}"])
        csv_writer.writerow([f"# Measurement duration (s): {settings.MEASUREMENT_DURATION:.3f}"])
        if partial and completed_cells is not None:
            csv_writer.writerow([f"# Completed cells: {completed_cells}"])
        if partial:
            csv_writer.writerow([
                "# WARNING: Experiment was terminated early - these are partial results"
            ])
        _append_cell_termination_metadata(csv_writer, all_data, termination_by_cell)

        csv_writer.writerow(TIMESERIES_CSV_HEADERS)

        for global_cell in sorted(all_data.keys()):
            row_number, _local_cell = global_cell_to_row_and_local(global_cell)
            cell_data = all_data[global_cell]
            z_heights = sorted(_z_keys_from_cell_data(cell_data), reverse=True)
            for z_height in z_heights:
                rpm_data = cell_data.get(z_height)
                if not isinstance(rpm_data, dict):
                    continue
                for rpm in sorted(k for k in rpm_data.keys() if k not in _RPM_DATA_META_KEYS):
                    measurements = rpm_data.get(rpm)
                    if not measurements:
                        continue
                    for sample in measurements:
                        try:
                            torque_percent = float(sample.get("torque_percent", 0))
                            elapsed = float(sample.get("elapsed_time", 0))
                        except (TypeError, ValueError):
                            continue
                        rpm_f = float(rpm)
                        rotational_drag = abs(torque_percent) / rpm_f if rpm_f > 0 else 0.0
                        csv_writer.writerow([
                            str(row_number),
                            str(global_cell),
                            settings.CELL_CONTENT_MAP.get(global_cell, ""),
                            f"{float(z_height):.3f}",
                            f"{rpm_f:.1f}",
                            f"{elapsed:.2f}",
                            f"{torque_percent:.3f}",
                            f"{rotational_drag:.6f}",
                        ])

    print(f"Timeseries data saved to: {csv_filename}")
    return csv_filename


def maybe_save_timeseries_data(
    all_data: Dict,
    timestamp: str,
    mode: str,
    experiment_name: str,
    termination_by_cell: Optional[Dict[int, str]] = None,
    partial: bool = False,
    completed_cells: Optional[List[int]] = None,
    save_all: Optional[bool] = None,
) -> str:
    """Write timeseries CSV when save-all mode is enabled; never raises."""
    enabled = settings.SAVE_ALL_SAMPLE_DATA if save_all is None else bool(save_all)
    if not enabled or not all_data:
        return ""
    try:
        return save_timeseries_data(
            all_data,
            timestamp,
            mode,
            experiment_name,
            termination_by_cell=termination_by_cell,
            partial=partial,
            completed_cells=completed_cells,
        )
    except Exception as e:
        print(f"Warning: Failed to save timeseries CSV: {e}")
        return ""

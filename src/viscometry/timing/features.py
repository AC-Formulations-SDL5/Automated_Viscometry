"""Build timing training / prediction feature dicts from run context and history."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Sequence


def _summary_from_char_block(block: Any) -> Dict[str, Any]:
    if not isinstance(block, dict):
        return {}
    if isinstance(block.get("__summary__"), dict):
        return block["__summary__"]
    if "K_stress" in block or "pathway" in block or "mu_app_cP" in block:
        return block
    return {}


def _mu_cp_from_summary(summary: Dict[str, Any]) -> Optional[float]:
    mu = summary.get("mu_app_cP")
    if mu is not None:
        try:
            f = float(mu)
            return f if f > 0 and f == f else None
        except (TypeError, ValueError):
            pass
    vk = summary.get("viscosity_kcp")
    if vk is not None:
        try:
            f = float(vk) * 1000.0
            return f if f > 0 and f == f else None
        except (TypeError, ValueError):
            pass
    return None


def _mu_by_rpm_from_block(block: Any) -> Dict[float, float]:
    out: Dict[float, float] = {}
    if not isinstance(block, dict):
        return out
    for key, val in block.items():
        if key == "__summary__" or not isinstance(val, dict):
            continue
        try:
            rpm = float(key)
        except (TypeError, ValueError):
            continue
        mu = val.get("mu_app_cP")
        if mu is None and val.get("viscosity_kcp") is not None:
            try:
                mu = float(val["viscosity_kcp"]) * 1000.0
            except (TypeError, ValueError):
                mu = None
        try:
            if mu is not None and float(mu) > 0:
                out[rpm] = float(mu)
        except (TypeError, ValueError):
            continue
    return out


def build_cell_training_row(
    *,
    sample_label: str,
    experiment_id: str,
    cell_id: int,
    settings: Dict[str, Any],
    run_type: str,
    rpms: Sequence[float],
    n_z: Optional[int],
    hit_z: Optional[float],
    actual_duration_s: Optional[float],
    predicted_duration_s: Optional[float],
    char_block: Any = None,
    intercell_gap_s: Optional[float] = None,
    n_rpms_requested: Optional[int] = None,
) -> Dict[str, Any]:
    summary = _summary_from_char_block(char_block)
    mu_by_rpm = _mu_by_rpm_from_block(char_block)
    mu_cp = _mu_cp_from_summary(summary)
    residual = None
    if actual_duration_s is not None and predicted_duration_s is not None:
        try:
            residual = float(actual_duration_s) - float(predicted_duration_s)
        except (TypeError, ValueError):
            residual = None
    accepted = len(list(rpms)) if rpms is not None else None
    return {
        "sample_label": sample_label or "",
        "experiment_id": experiment_id or "",
        "cell_id": int(cell_id),
        "row_level": "cell",
        "run_type": run_type or "regular",
        "measurement_duration_s": settings.get("measurement_duration"),
        "sample_interval_s": settings.get("sample_interval"),
        "dwell_s": settings.get("dwell_seconds"),
        "inter_rpm_pause_s": settings.get("inter_rpm_pause"),
        "z_step_mm": settings.get("z_step_size"),
        "discovery_mode": bool(settings.get("discovery_mode_enabled")),
        "max_screening_rpms": settings.get("max_screening_rpms"),
        "n_rpms_requested": n_rpms_requested if n_rpms_requested is not None else accepted,
        "n_rpms_accepted": accepted,
        "n_z": n_z,
        "hit_z": hit_z,
        "pathway": summary.get("pathway"),
        "mu_cp": mu_cp,
        "mu_cp_by_rpm_json": json.dumps(mu_by_rpm, sort_keys=True) if mu_by_rpm else "",
        "rpm": "",
        "z_height": "",
        "n_samples": "",
        "window_elapsed_s": "",
        "duration_cap_s": "",
        "smart_exit": "",
        "censored": "",
        "actual_duration_s": actual_duration_s,
        "predicted_duration_s": predicted_duration_s,
        "residual_s": residual,
        "intercell_gap_s": intercell_gap_s,
        "saved_at_unix": int(time.time()),
    }


def build_window_training_row(
    *,
    sample_label: str,
    experiment_id: str,
    cell_id: int,
    settings: Dict[str, Any],
    run_type: str,
    window: Dict[str, Any],
    mu_cp: Optional[float] = None,
) -> Dict[str, Any]:
    return {
        "sample_label": sample_label or "",
        "experiment_id": experiment_id or "",
        "cell_id": int(cell_id),
        "row_level": "window",
        "run_type": run_type or "regular",
        "measurement_duration_s": settings.get("measurement_duration"),
        "sample_interval_s": settings.get("sample_interval"),
        "dwell_s": settings.get("dwell_seconds"),
        "inter_rpm_pause_s": settings.get("inter_rpm_pause"),
        "z_step_mm": settings.get("z_step_size"),
        "discovery_mode": bool(settings.get("discovery_mode_enabled")),
        "max_screening_rpms": settings.get("max_screening_rpms"),
        "n_rpms_requested": "",
        "n_rpms_accepted": "",
        "n_z": "",
        "hit_z": "",
        "pathway": "",
        "mu_cp": mu_cp if mu_cp is not None else window.get("mu_cp"),
        "mu_cp_by_rpm_json": "",
        "rpm": window.get("rpm"),
        "z_height": window.get("z"),
        "n_samples": window.get("n_samples"),
        "window_elapsed_s": window.get("elapsed_s"),
        "duration_cap_s": window.get("duration_cap_s"),
        "smart_exit": window.get("smart_exit"),
        "censored": window.get("censored"),
        "actual_duration_s": window.get("elapsed_s"),
        "predicted_duration_s": "",
        "residual_s": "",
        "intercell_gap_s": "",
        "saved_at_unix": int(time.time()),
    }


def rows_from_commit(
    experiment_entry: Dict[str, Any],
    *,
    run_context: Optional[Dict[str, Any]] = None,
    frozen_prediction_s: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Build cell + window training rows from a committed history entry."""
    rows: List[Dict[str, Any]] = []
    try:
        settings = dict(experiment_entry.get("settings") or {})
        sample_label = str(settings.get("experiment_name") or "")
        experiment_id = str(experiment_entry.get("id") or "")
        run_type = str(experiment_entry.get("run_type") or "regular")
        cells = experiment_entry.get("cells") or []
        rpms = experiment_entry.get("rpms") or []
        cell_durations = experiment_entry.get("cellDurations") or {}
        char = experiment_entry.get("characterization") or experiment_entry.get("predicted_viscosity") or {}
        latest = experiment_entry.get("latestPerZ") or []
        windows_by_cell = {}
        if isinstance(run_context, dict):
            windows_by_cell = run_context.get("timing_windows_by_cell") or {}

        # n_z / hit from latestPerZ
        by_cell_pts: Dict[int, List[dict]] = {}
        for m in latest:
            try:
                cid = int(m["cell_id"])
            except (KeyError, TypeError, ValueError):
                continue
            by_cell_pts.setdefault(cid, []).append(m)

        pred_per_cell = None
        if frozen_prediction_s is not None and cells:
            try:
                pred_per_cell = float(frozen_prediction_s) / max(1, len(cells))
            except (TypeError, ValueError):
                pred_per_cell = None
        if pred_per_cell is None and isinstance(run_context, dict):
            frozen = run_context.get("eta_prediction_frozen") or {}
            try:
                total = frozen.get("expected_s")
                if total is not None:
                    pred_per_cell = float(total) / max(1, len(cells))
            except (TypeError, ValueError):
                pass

        for cell_id in cells:
            cid = int(cell_id)
            key = str(cid)
            ms = cell_durations.get(key)
            if ms is None:
                ms = cell_durations.get(cid)
            actual_s = float(ms) / 1000.0 if ms is not None else None
            pts = by_cell_pts.get(cid) or []
            zs = {round(float(p["height"]), 3) for p in pts if p.get("height") is not None}
            n_z = len(zs) if zs else None
            hit_z = min(zs) if zs else None  # deepest measured as proxy
            char_block = char.get(key) or char.get(cid)
            row = build_cell_training_row(
                sample_label=sample_label,
                experiment_id=experiment_id,
                cell_id=cid,
                settings=settings,
                run_type=run_type,
                rpms=rpms,
                n_z=n_z,
                hit_z=hit_z,
                actual_duration_s=actual_s,
                predicted_duration_s=pred_per_cell,
                char_block=char_block,
            )
            rows.append(row)

            mu_cp = row.get("mu_cp")
            win_list = windows_by_cell.get(key) or windows_by_cell.get(cid) or []
            for w in win_list:
                if isinstance(w, dict):
                    rows.append(
                        build_window_training_row(
                            sample_label=sample_label,
                            experiment_id=experiment_id,
                            cell_id=cid,
                            settings=settings,
                            run_type=run_type,
                            window=w,
                            mu_cp=mu_cp,
                        )
                    )
    except Exception as exc:
        print(f"Warning: timing feature build failed ({exc})")
    return rows

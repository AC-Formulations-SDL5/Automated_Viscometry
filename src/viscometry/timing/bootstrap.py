"""One-shot seed of the timing training CSV from experiment history."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from viscometry.paths import EXPERIMENT_HISTORY_PATH, TIMING_TRAINING_CSV
from viscometry.timing.features import build_cell_training_row, z_geometry_from_heights
from viscometry.timing.model import load_posterior, predict_cell_seconds, save_posterior
from viscometry.timing.training_store import append_rows, ensure_headers, row_count


def _load_history(path: Path) -> List[Dict[str, Any]]:
    try:
        if not path.is_file():
            return []
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except Exception as exc:
        print(f"Warning: could not load experiment history for timing bootstrap ({exc})")
        return []


def bootstrap_from_history(
    *,
    history_path: Optional[Path] = None,
    training_path: Optional[Path] = None,
    force: bool = False,
) -> int:
    """
    If the training CSV is missing/empty, seed one cell-level row per history cell.

    Never deletes or rewrites existing training rows unless force=True (tests only).
    """
    target = Path(training_path) if training_path is not None else TIMING_TRAINING_CSV
    try:
        if not force and target.is_file() and row_count(target) > 0:
            return 0
        ensure_headers(target)
        history = _load_history(Path(history_path) if history_path is not None else EXPERIMENT_HISTORY_PATH)
        if not history:
            return 0

        posterior = load_posterior()
        rows: List[Dict[str, Any]] = []
        for entry in history:
            if not isinstance(entry, dict):
                continue
            settings = dict(entry.get("settings") or {})
            sample_label = str(settings.get("experiment_name") or "")
            experiment_id = str(entry.get("id") or "")
            run_type = str(entry.get("run_type") or "regular")
            cells = entry.get("cells") or []
            rpms = entry.get("rpms") or []
            cell_durations = entry.get("cellDurations") or {}
            char = entry.get("characterization") or entry.get("predicted_viscosity") or {}
            latest = entry.get("latestPerZ") or []
            by_cell: Dict[int, list] = {}
            for m in latest:
                try:
                    by_cell.setdefault(int(m["cell_id"]), []).append(m)
                except (KeyError, TypeError, ValueError):
                    continue

            meas = float(settings.get("measurement_duration") or 40.0)
            interval = float(settings.get("sample_interval") or 5.0)
            dwell = float(settings.get("dwell_seconds") or 2.0)
            pause = float(settings.get("inter_rpm_pause") or 2.0)

            for cell_id in cells:
                try:
                    cid = int(cell_id)
                except (TypeError, ValueError):
                    continue
                key = str(cid)
                ms = cell_durations.get(key, cell_durations.get(cid))
                actual_s = float(ms) / 1000.0 if ms is not None else None
                pts = by_cell.get(cid) or []
                heights = [p["height"] for p in pts if p.get("height") is not None]
                geom = z_geometry_from_heights(heights)
                n_z = int(geom["n_z"]) if geom.get("n_z") is not None else None
                char_block = char.get(key) or char.get(cid)
                pred = predict_cell_seconds(
                    n_rpms=max(1, len(rpms)),
                    n_z=float(n_z) if n_z else None,
                    measurement_duration_s=meas,
                    sample_interval_s=interval,
                    dwell_s=dwell,
                    inter_rpm_pause_s=pause,
                    posterior=posterior,
                )
                rows.append(
                    build_cell_training_row(
                        sample_label=sample_label,
                        experiment_id=experiment_id,
                        cell_id=cid,
                        settings=settings,
                        run_type=run_type,
                        rpms=rpms,
                        n_z=n_z,
                        hit_z=geom.get("hit_z"),
                        start_z=geom.get("start_z"),
                        hit_relative_mm=geom.get("hit_relative_mm"),
                        actual_duration_s=actual_s,
                        predicted_duration_s=pred.get("expected_s"),
                        char_block=char_block,
                    )
                )

        written = append_rows(rows, path=target)
        if written:
            print(f"Timing training bootstrap: wrote {written} rows to {target}")
        return written
    except Exception as exc:
        print(f"Warning: timing bootstrap failed ({exc})")
        return 0


def ensure_training_file(
    *,
    history_path: Optional[Path] = None,
    training_path: Optional[Path] = None,
) -> Path:
    """Ensure CSV exists; bootstrap from history when empty."""
    target = Path(training_path) if training_path is not None else TIMING_TRAINING_CSV
    try:
        ensure_headers(target)
        if row_count(target) == 0:
            bootstrap_from_history(history_path=history_path, training_path=target)
        # Ensure a posterior file exists for the ETA path
        save_posterior(load_posterior())
    except Exception as exc:
        print(f"Warning: ensure_training_file failed ({exc})")
    return target

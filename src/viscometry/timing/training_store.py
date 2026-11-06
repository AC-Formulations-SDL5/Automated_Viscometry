"""Append-only CSV store for timing prediction training rows."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from viscometry.paths import TIMING_TRAINING_CSV

TRAINING_COLUMNS: List[str] = [
    "sample_label",
    "experiment_id",
    "cell_id",
    "row_level",
    "run_type",
    "measurement_duration_s",
    "sample_interval_s",
    "dwell_s",
    "inter_rpm_pause_s",
    "z_step_mm",
    "discovery_mode",
    "max_screening_rpms",
    "n_rpms_requested",
    "n_rpms_accepted",
    "n_z",
    "start_z",
    "hit_z",
    "hit_relative_mm",
    "pathway",
    "mu_cp",
    "mu_cp_by_rpm_json",
    "rpm",
    "z_height",
    "n_samples",
    "window_elapsed_s",
    "duration_cap_s",
    "smart_exit",
    "censored",
    "actual_duration_s",
    "predicted_duration_s",
    "residual_s",
    "intercell_gap_s",
    "saved_at_unix",
]


def ensure_headers(path: Optional[Path] = None) -> Path:
    """
    Create the CSV with headers if missing.

    If the file exists with an older header, migrate by rewriting rows with
    padded new columns — never drops existing data rows.
    """
    target = Path(path) if path is not None else TIMING_TRAINING_CSV
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.stat().st_size == 0:
            with target.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=TRAINING_COLUMNS)
                writer.writeheader()
            return target

        with target.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            old_fields = list(reader.fieldnames or [])
            rows = list(reader)

        if old_fields == TRAINING_COLUMNS:
            return target

        # Preserve unknown legacy columns at the end so nothing is deleted.
        merged = list(TRAINING_COLUMNS)
        for col in old_fields:
            if col not in merged:
                merged.append(col)
        tmp = target.with_suffix(target.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=merged, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                out = {col: row.get(col, "") for col in merged}
                writer.writerow(out)
        tmp.replace(target)
    except Exception as exc:
        print(f"Warning: could not ensure timing training CSV headers ({exc})")
    return target


def append_rows(
    rows: Sequence[Dict[str, Any]],
    *,
    path: Optional[Path] = None,
) -> int:
    """Append training rows. Returns number of rows written. Never deletes existing rows."""
    if not rows:
        return 0
    target = ensure_headers(path)
    written = 0
    try:
        # Honor whatever header is on disk after migration.
        with target.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader, None) or list(TRAINING_COLUMNS)
        fieldnames = list(header)
        with target.open("a", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            for row in rows:
                if not isinstance(row, dict):
                    continue
                out = {col: row.get(col, "") for col in fieldnames}
                writer.writerow(out)
                written += 1
    except Exception as exc:
        print(f"Warning: timing training append failed ({exc})")
        return 0
    return written


def row_count(path: Optional[Path] = None) -> int:
    """Count data rows (excluding header)."""
    target = Path(path) if path is not None else TIMING_TRAINING_CSV
    if not target.is_file():
        return 0
    try:
        with target.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            next(reader, None)
            return sum(1 for _ in reader)
    except Exception:
        return 0

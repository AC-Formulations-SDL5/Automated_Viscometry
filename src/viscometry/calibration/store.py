"""
calibration_store.py

Manage persistent per-cell Z-height calibration data for the automated viscometry platform.

The calibration data is stored as JSON at:
    ./calibration_data/per_cell_z_calibration.json
relative to the directory containing this module (the project root / main script folder).

All file I/O is wrapped in try/except and uses only the Python standard library.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from viscometry.paths import CALIBRATION_DIR, PROJECT_ROOT, calibration_file, ensure_calibration_dir

CALIBRATION_FILE_PATH: str = str(CALIBRATION_DIR / "per_cell_z_calibration.json")

_DEFAULT_CAL = {"version": 1, "calibrated_at": None, "cell_calibrated_at": {}, "cells": {}}

_LEGACY_READ_RELATIVE = (
    Path("src") / "python_64" / "calibration_data" / "per_cell_z_calibration.json",
    Path("calibration_data") / "per_cell_z_calibration.json",
)


def _legacy_read_paths() -> tuple[Path, ...]:
    return tuple(PROJECT_ROOT / rel for rel in _LEGACY_READ_RELATIVE)


def _canonical_path() -> Path:
    return calibration_file("per_cell_z_calibration.json")


def _get_path() -> Path:
    """Resolve read path: canonical location, then pre-restructure legacy paths."""
    canonical = _canonical_path()
    if canonical.is_file():
        return canonical
    for legacy in _legacy_read_paths():
        if legacy.is_file():
            return legacy
    return canonical


def _maybe_migrate_legacy_calibration(source: Path) -> None:
    """Copy legacy calibration JSON into data/calibration/ on first read."""
    canonical = _canonical_path()
    if canonical.is_file() or not source.is_file():
        return
    try:
        ensure_calibration_dir()
        shutil.copy2(source, canonical)
        print(f"Migrated per-cell calibration from {source} to {canonical}")
    except Exception as exc:
        print(f"Warning: could not migrate calibration from {source}: {exc}")


def _write_path() -> Path:
    """Write path always under data/calibration/."""
    ensure_calibration_dir()
    return CALIBRATION_DIR / "per_cell_z_calibration.json"

def _local_iso_now() -> str:
    """Return current local timestamp with timezone offset."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def is_calibrated() -> bool:
    """Return True if the calibration file exists and has at least one cell entry."""
    path = _get_path()
    try:
        if not path.exists():
            return False
        cal = load_calibration()
        cells = cal.get("cells") if isinstance(cal, dict) else None
        return bool(cells) and isinstance(cells, dict) and len(cells) > 0
    except Exception as e:
        print(f"is_calibrated: error checking calibration file: {e}")
        return False


def load_calibration() -> Dict[str, Any]:
    """Load and return the calibration dict from disk.

    Returns a default structure if the file does not exist or is malformed.
    """
    path = _get_path()
    if not path.exists():
        return dict(_DEFAULT_CAL)

    if path != _canonical_path():
        _maybe_migrate_legacy_calibration(path)
        path = _canonical_path() if _canonical_path().is_file() else path

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Basic validation
        if not isinstance(data, dict):
            raise ValueError("Calibration file content is not a JSON object")

        version = data.get("version", 1)
        calibrated_at = data.get("calibrated_at")
        cells = data.get("cells", {})
        cell_calibrated_at = data.get("cell_calibrated_at", {})
        if not isinstance(cells, dict):
            raise ValueError("Calibration 'cells' must be a mapping")
        if not isinstance(cell_calibrated_at, dict):
            cell_calibrated_at = {}

        # Normalize keys to strings and values to floats where possible
        norm_cells: Dict[str, float] = {}
        for k, v in cells.items():
            try:
                key_str = str(int(k)) if isinstance(k, (int, float, str)) and str(k).isdigit() else str(k)
            except Exception:
                key_str = str(k)
            try:
                norm_cells[key_str] = float(v)
            except Exception:
                # Skip non-numeric values
                continue

        norm_cell_times: Dict[str, str] = {}
        for k, v in cell_calibrated_at.items():
            try:
                key_str = str(int(k)) if isinstance(k, (int, float, str)) and str(k).isdigit() else str(k)
            except Exception:
                key_str = str(k)
            if isinstance(v, str) and v.strip():
                norm_cell_times[key_str] = v.strip()

        return {
            "version": int(version),
            "calibrated_at": calibrated_at,
            "cell_calibrated_at": norm_cell_times,
            "cells": norm_cells,
        }

    except Exception as e:
        print(f"load_calibration: failed to load calibration file '{path}': {e}")
        return dict(_DEFAULT_CAL)


def save_calibration(cells: Dict[int, float], calibrated_at: str | None = None) -> None:
    """Save calibration data to disk atomically.

    - `cells` maps integer cell IDs to float Z values.
    - `calibrated_at` defaults to current UTC ISO timestamp if not supplied.
    """
    path = _write_path()
    dirpath = path.parent
    try:
        dirpath.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"save_calibration: failed to create directory '{dirpath}': {e}")
        return

    if calibrated_at is None:
        calibrated_at = _local_iso_now()

    # Convert keys to strings for JSON
    cells_out: Dict[str, float] = {}
    for k, v in cells.items():
        try:
            key_str = str(int(k))
            cells_out[key_str] = float(v)
        except Exception:
            print(f"save_calibration: skipping invalid cell entry {k}: {v}")
            continue

    cell_times_out = {cell_id: calibrated_at for cell_id in cells_out.keys()}
    payload = {
        "version": 1,
        "calibrated_at": calibrated_at,
        "cell_calibrated_at": cell_times_out,
        "cells": cells_out,
    }

    tmp_path = path.with_suffix(".tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        # Atomic replace
        try:
            shutil.move(str(tmp_path), str(path))
        except Exception:
            # Fallback to os.replace
            os.replace(str(tmp_path), str(path))
    except Exception as e:
        print(f"save_calibration: failed to write calibration file '{path}': {e}")
        # Clean up tmp file if present
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass


def get_safe_z_for_cell(cell_id: int, default_safe_z: float, offset: float = 0.4) -> float:
    """Return a safety starting Z for a given cell.

    If a rough hitpoint exists for the cell, returns rough_hitpoint_z + offset.
    Otherwise returns `default_safe_z`.
    """
    try:
        cal = load_calibration()
        cells = cal.get("cells", {}) if isinstance(cal, dict) else {}
        key = str(int(cell_id))
        if key in cells:
            try:
                return float(cells[key]) + float(offset)
            except Exception:
                pass
        return float(default_safe_z)
    except Exception as e:
        print(f"get_safe_z_for_cell: error retrieving calibration for cell {cell_id}: {e}")
        return float(default_safe_z)


def get_calibration_summary() -> Dict[str, Any]:
    """Return a JSON-serialisable summary of the calibration state."""
    try:
        cal = load_calibration()
        cells = cal.get("cells", {}) if isinstance(cal, dict) else {}
        cell_times = cal.get("cell_calibrated_at", {}) if isinstance(cal, dict) else {}
        return {
            "is_calibrated": bool(cells) and len(cells) > 0,
            "calibrated_at": cal.get("calibrated_at"),
            "cell_count": len(cells),
            "cell_calibrated_at": {str(k): str(v) for k, v in cell_times.items()},
            "cells": {str(k): float(v) for k, v in cells.items()},
        }
    except Exception as e:
        print(f"get_calibration_summary: error producing summary: {e}")
        return {
            "is_calibrated": False,
            "calibrated_at": None,
            "cell_count": 0,
            "cell_calibrated_at": {},
            "cells": {},
        }


def update_calibration_for_cells(cells: Dict[int, float], calibrated_at: str | None = None) -> None:
    """Update calibration data for specific cells without affecting others.
    
    - Loads existing calibration data
    - Merges in the new cells (overwrites only those specified)
    - Saves the merged result back to disk
    - `cells` maps integer cell IDs to float Z values.
    - `calibrated_at` defaults to current UTC ISO timestamp if not supplied.
    """
    # Load existing calibration
    existing_cal = load_calibration()
    existing_cells = existing_cal.get("cells", {}) if isinstance(existing_cal, dict) else {}
    existing_cell_times = existing_cal.get("cell_calibrated_at", {}) if isinstance(existing_cal, dict) else {}
    
    # Merge: existing cells + new cells (new cells override)
    merged_cells: Dict[str, float] = {}
    
    # Add all existing cells
    for k, v in existing_cells.items():
        try:
            merged_cells[str(int(k))] = float(v)
        except Exception:
            continue
    
    # Override with new cells
    for k, v in cells.items():
        try:
            key_str = str(int(k))
            merged_cells[key_str] = float(v)
        except Exception:
            print(f"update_calibration_for_cells: skipping invalid cell entry {k}: {v}")
            continue
    
    # Merge existing per-cell timestamps
    merged_cell_times: Dict[str, str] = {}
    for k, v in existing_cell_times.items():
        try:
            key_str = str(int(k))
        except Exception:
            key_str = str(k)
        if isinstance(v, str) and v.strip():
            merged_cell_times[key_str] = v.strip()

    # Now save the merged result
    if calibrated_at is None:
        calibrated_at = _local_iso_now()
    for cell_key in cells.keys():
        try:
            merged_cell_times[str(int(cell_key))] = calibrated_at
        except Exception:
            continue
    
    path = _write_path()
    dirpath = path.parent
    try:
        dirpath.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"update_calibration_for_cells: failed to create directory '{dirpath}': {e}")
        return
    
    payload = {
        "version": 1,
        "calibrated_at": calibrated_at,
        "cell_calibrated_at": merged_cell_times,
        "cells": merged_cells,
    }
    
    tmp_path = path.with_suffix(".tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        # Atomic replace
        try:
            shutil.move(str(tmp_path), str(path))
        except Exception:
            os.replace(str(tmp_path), str(path))
    except Exception as e:
        print(f"update_calibration_for_cells: failed to write calibration file '{path}': {e}")
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass


def clear_calibration() -> None:
    """Delete the calibration file if it exists."""
    path = _write_path()
    try:
        if path.exists():
            path.unlink()
    except Exception as e:
        print(f"clear_calibration: failed to delete calibration file '{path}': {e}")


if __name__ == "__main__":
    # Quick self-check when run directly
    print("Calibration file path:", CALIBRATION_FILE_PATH)
    print("Currently calibrated:", is_calibrated())
    print("Summary:", get_calibration_summary())

"""Persistent taught poses for the lid pickup tool."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from viscometry.paths import calibration_file, ensure_calibration_dir

LID_CALIBRATION_NAME = "lid_tool_calibration.json"


def empty_lid_calibration() -> dict[str, Any]:
    return {
        "version": 1,
        "clearance_z": 0.0,
        "updated_at": None,
        "cell1_large": None,
        "cell1_small": None,
        "parking_row1": None,
        "parking_row4": None,
    }


def _calibration_path():
    return calibration_file(LID_CALIBRATION_NAME)


def load_lid_calibration() -> dict[str, Any]:
    """Load taught lid poses. Missing or unreadable files return an empty record."""
    path = _calibration_path()
    base = empty_lid_calibration()
    if not path.is_file():
        return base
    try:
        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, json.JSONDecodeError, UnicodeError):
        return base
    if not isinstance(raw, dict):
        return base
    merged = dict(base)
    merged.update({key: raw.get(key, base[key]) for key in base})
    merged["version"] = 1
    merged["clearance_z"] = 0.0
    return merged


def save_lid_calibration(data: dict[str, Any]) -> dict[str, Any]:
    ensure_calibration_dir()
    payload = empty_lid_calibration()
    payload.update({key: data.get(key) for key in payload})
    payload["version"] = 1
    payload["clearance_z"] = 0.0
    payload["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    path = _calibration_path()
    text = json.dumps(payload, indent=2) + "\n"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
    return payload

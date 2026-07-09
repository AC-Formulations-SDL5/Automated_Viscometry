"""Tests for legacy calibration path resolution."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from viscometry.calibration import store


def test_legacy_calibration_migration(tmp_path, monkeypatch):
    legacy_dir = tmp_path / "src" / "python_64" / "calibration_data"
    legacy_dir.mkdir(parents=True)
    legacy_file = legacy_dir / "per_cell_z_calibration.json"
    payload = {
        "version": 1,
        "calibrated_at": "2026-01-01T00:00:00",
        "cell_calibrated_at": {"1": "2026-01-01T00:00:00"},
        "cells": {"1": -66.0},
    }
    legacy_file.write_text(json.dumps(payload), encoding="utf-8")

    new_cal_dir = tmp_path / "data" / "calibration"
    monkeypatch.setattr(store, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(store, "CALIBRATION_DIR", new_cal_dir)
    monkeypatch.setattr(
        store,
        "calibration_file",
        lambda name: new_cal_dir / name,
    )
    monkeypatch.setattr(store, "ensure_calibration_dir", lambda: new_cal_dir.mkdir(parents=True, exist_ok=True) or new_cal_dir)

    summary = store.get_calibration_summary()
    assert summary["cell_count"] == 1
    assert (new_cal_dir / "per_cell_z_calibration.json").is_file()

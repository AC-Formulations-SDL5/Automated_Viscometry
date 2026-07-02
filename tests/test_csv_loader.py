"""Tests for CSV loader with row,cell header offset."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from viscometry.analysis.csv_loader import load_rotational_drag_csv


def test_load_rotational_drag_csv_finds_archive_file():
  csv = "dynamic_analysis_12_5kcP_Reproducibility_Brush_custom_20260506_114319.csv"
  df = load_rotational_drag_csv(csv)
  assert "cell" in df.columns
  assert "Z_Height_mm" in df.columns
  assert "Rotational_Drag" in df.columns
  assert len(df) > 0

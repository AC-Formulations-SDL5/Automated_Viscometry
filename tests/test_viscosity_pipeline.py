"""Smoke test for offline viscosity pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from viscometry.analysis.viscosity_pipeline import run_viscosity_pipeline
from viscometry.paths import PROJECT_ROOT


def test_run_viscosity_pipeline_no_visualize():
    csv = PROJECT_ROOT / "results" / "auto_runs" / "37kcP_reproducibility_20260525_091234.csv"
    if not csv.is_file():
        return
    out = run_viscosity_pipeline(
        str(csv),
        real_viscosity_map={1: 37000.0},
        visualize=False,
    )
    assert "predictions" in out
    assert len(out["predictions"]) > 0

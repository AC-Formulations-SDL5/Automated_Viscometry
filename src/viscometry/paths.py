"""Central path constants for the viscometry package."""

from __future__ import annotations

import datetime
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parents[1]

RUNS_DIR = PROJECT_ROOT / "results" / "runs"
CALIBRATION_DIR = PROJECT_ROOT / "data" / "calibration"
REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"
WEB_TEMPLATES = PROJECT_ROOT / "web" / "templates"
WEB_STATIC = PROJECT_ROOT / "web" / "static"
WORKER32_DIR = PACKAGE_DIR / "hardware" / "viscometer" / "worker32"
LOCATIONS_YAML = PROJECT_ROOT / "config" / "locations.yaml"
EXPERIMENT_HISTORY_PATH = PROJECT_ROOT / "results" / "web_experiment_history.json"


def runs_dir_for_today() -> Path:
    """Return (and create) today's run output directory under results/runs/."""
    day = datetime.date.today().isoformat()
    path = RUNS_DIR / day
    path.mkdir(parents=True, exist_ok=True)
    return path


def calibration_file(name: str) -> Path:
    """Resolve a calibration JSON path under data/calibration/."""
    return CALIBRATION_DIR / name


def ensure_calibration_dir() -> Path:
    """Create data/calibration/ if needed."""
    CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)
    return CALIBRATION_DIR

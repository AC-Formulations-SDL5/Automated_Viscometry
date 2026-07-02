# Repository Migration Guide

## Entry point (Ctrl+R / Run Python File)

Open [`run_viscometry.py`](run_viscometry.py) at the repo root and run it, or:

```bash
python run_viscometry.py
python -m viscometry
```

Install editable package (recommended):

```bash
python3 -m pip install -e ".[analysis,dev]"
```

For notebooks and offline CSV analysis, the `[analysis]` extra includes pandas, matplotlib, scikit-learn, statsmodels, and optional fit libraries.

## Directory layout

| Purpose | Path |
|---------|------|
| Python package | `src/viscometry/` |
| Run CSV outputs | `results/runs/YYYY-MM-DD/` |
| Web experiment history | `results/web_experiment_history.json` |
| Z calibration JSON | `data/calibration/per_cell_z_calibration.json` |
| Discovery calibration JSON | `data/calibration/discovery_bulk_calibration.json` |
| Reference viscosity CSV | `data/reference/Viscosity Readings - Manual.csv` |
| Web UI assets | `web/templates/`, `web/static/` |
| Analysis notebooks | `notebooks/` |
| Rheology research project | `research/rheology_newtonian/` |
| Simulation (no hardware) | `examples/simulation/` |
| ESP32 firmware | `firmware/esp32/` |
| Maintenance scripts | `scripts/` |
| Offline analysis pipelines | `src/viscometry/analysis/` |

## Archived run CSVs

Root-level `dynamic_analysis_*.csv` files were moved to `results/runs/archive/`.

## Removed legacy code

Old experiment scripts under `src/python_64/` and `src/python_32/` were removed after migration to `src/viscometry/`. The 32-bit viscometer worker now lives at `src/viscometry/hardware/viscometer/worker32/`.

Offline batch helpers that previously lived in `results/auto_runs/` (`viscosity_pipeline_helper.py`, `rheology_pipeline_core.py`) are now in `src/viscometry/analysis/`:

```python
from viscometry.analysis import run_viscosity_pipeline, RheologyPipeline, create_default_pipeline
```

Shared CSV parsing utilities are in `src/viscometry/io/csv_text.py`.

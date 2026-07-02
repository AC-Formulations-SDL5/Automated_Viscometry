# Repository Migration Guide

## Entry point (Ctrl+R / Run Python File)

Open [`run_viscometry.py`](run_viscometry.py) at the repo root and run it, or:

```bash
python run_viscometry.py
python -m viscometry
```

Install editable package (recommended):

```bash
python3 -m pip install -e .
```

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

## Archived run CSVs

Root-level `dynamic_analysis_*.csv` files were moved to `results/runs/archive/`.

## Removed legacy code

Old experiment scripts under `src/python_64/` and `src/python_32/` were removed after migration to `src/viscometry/`. The 32-bit viscometer worker now lives at `src/viscometry/hardware/viscometer/worker32/`.

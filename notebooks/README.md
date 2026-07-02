# Analysis Notebooks

Canonical copies live here. Duplicate `.ipynb` files were removed from `results/` (CSV data remains).

## Setup

Install the package with analysis dependencies:

```bash
pip install -e ".[analysis,dev]"
```

Run notebooks from any directory — each notebook resolves the repo root automatically.

## Bootstrap pattern

Every notebook includes a bootstrap cell that sets:

```python
PROJECT_ROOT   # repo root (contains src/viscometry)
AUTO_RUNS      # results/auto_runs/
AUTO_RUNS_LEGACY  # results/Auto-runs/
ARCHIVE        # results/runs/archive/
```

## Imports (offline analysis)

| Old import | New import |
|------------|------------|
| `from viscosity_pipeline_helper import run_viscosity_pipeline` | `from viscometry.analysis.viscosity_pipeline import run_viscosity_pipeline` |
| `from rheology_pipeline_core import RheologyPipeline, create_default_pipeline` | `from viscometry.analysis.rheology_pipeline import RheologyPipeline, create_default_pipeline` |

## Path mapping

| Old location | New location |
|--------------|--------------|
| `dynamic_analysis_*.csv` (repo root) | `results/runs/archive/` or `ARCHIVE / "..."` |
| New run CSVs | `results/runs/YYYY-MM-DD/` |
| `results/Viscosity Readings - Manual.csv` | `data/reference/Viscosity Readings - Manual.csv` |
| `height_normalized.csv` (cwd-relative) | `AUTO_RUNS_LEGACY / "height_normalized.csv"` |
| `results/auto_runs/*.csv` | `AUTO_RUNS / "..."` |

## Output directories

Rheology notebooks write figures/outputs under `results/Auto-runs/figures_rheology/` and `outputs_rheology/` by default.

## Subfolders

- `runs/` — experiment analysis notebooks (rheology, reproducibility, pipelines)
- `figures/` — figure-generation notebooks from `Images/`

Newtonian/non-Newtonian rheology project: `research/rheology_newtonian/`

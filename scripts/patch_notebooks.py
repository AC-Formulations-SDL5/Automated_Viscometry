#!/usr/bin/env python3
"""One-off notebook path/import updater for post-restructure migration."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BOOTSTRAP = '''import sys
from pathlib import Path

def _find_repo_root() -> Path:
    for p in [Path.cwd(), *Path.cwd().parents]:
        if (p / "src" / "viscometry").is_dir():
            return p
    raise RuntimeError("Could not locate repo root (expected src/viscometry)")

PROJECT_ROOT = _find_repo_root()
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

AUTO_RUNS = PROJECT_ROOT / "results" / "auto_runs"
AUTO_RUNS_LEGACY = PROJECT_ROOT / "results" / "Auto-runs"
ARCHIVE = PROJECT_ROOT / "results" / "runs" / "archive"
'''

REPLACEMENTS = [
    (r"from viscosity_pipeline_helper import run_viscosity_pipeline",
     "from viscometry.analysis.viscosity_pipeline import run_viscosity_pipeline"),
    (r"from rheology_pipeline_core import create_default_pipeline, RheologyPipeline",
     "from viscometry.analysis.rheology_pipeline import create_default_pipeline, RheologyPipeline"),
    (r"from rheology_pipeline_core import (.+)",
     r"from viscometry.analysis.rheology_pipeline import \1"),
    (r'DATA_PATH = Path\("height_normalized\.csv"\)',
     'DATA_PATH = AUTO_RUNS_LEGACY / "height_normalized.csv"'),
    (r'Path\("height_normalized\.csv"\)',
     'AUTO_RUNS_LEGACY / "height_normalized.csv"'),
    (r'FIG_DIR = Path\("figures_rheology"\)',
     'FIG_DIR = AUTO_RUNS_LEGACY / "figures_rheology"'),
    (r'OUT_DIR = Path\("outputs_rheology"\)',
     'OUT_DIR = AUTO_RUNS_LEGACY / "outputs_rheology"'),
    (r'DATA_FILE_PATH = "dynamic_analysis_11_61kcP_custom_20260615_085140\.csv"',
     'DATA_FILE_PATH = str(PROJECT_ROOT / "results" / "auto_runs" / "rheology_pipeline" / "dynamic_analysis_11_61kcP_custom_20260615_085140.csv")'),
    (r'CALIBRATION_FILE_PATH = "\.\./\.\./Auto-runs/height_normalized\.csv"',
     'CALIBRATION_FILE_PATH = str(AUTO_RUNS_LEGACY / "height_normalized.csv")'),
    (r'"results/auto_runs/hitpoints\.csv"',
     'str(AUTO_RUNS / "hitpoints.csv")'),
    (r'"../results/Auto-runs/hitpoints\.csv"',
     'str(AUTO_RUNS_LEGACY / "hitpoints.csv")'),
    (r'"Data/Manual_Auto/timing_v2\.csv"',
     'str(AUTO_RUNS / "timing_v2.csv")'),
    (r'c:\\\\Users\\\\mrast\\\\OneDrive[^"]*\\\\Images',
     'str(PROJECT_ROOT / "Images")'),
    (r'"full_run_260428\.csv"',
     'str(AUTO_RUNS / "full_run_260428.csv")'),
    (r'"timing_v2\.csv"',
     'str(AUTO_RUNS / "timing_v2.csv")'),
    (r'"dynamic_analysis_full_run_custom_20260513_093259\.csv"',
     'str(AUTO_RUNS / "dynamic_analysis_full_run_custom_20260513_093259.csv")'),
    (r'"37kcP_reproducibility_20260525_091234\.csv"',
     'str(AUTO_RUNS / "37kcP_reproducibility_20260525_091234.csv")'),
    (r'"dynamic_analysis_L60kcP_siltech_A37kcP_custom_20260511_085338\.csv"',
     'str(AUTO_RUNS_LEGACY / "dynamic_analysis_L60kcP_siltech_A37kcP_custom_20260511_085338.csv")'),
    (r'"dynamic_analysis_L10000cP_siltech_A11860cP_custom_20260512_090217\.csv"',
     'str(AUTO_RUNS / "dynamic_analysis_L10000cP_siltech_A11860cP_custom_20260512_090217.csv")'),
    (r'"../dynamic_analysis_L60kcP_siltech_A37kcP_custom_20260511_085338\.csv"',
     'str(AUTO_RUNS_LEGACY / "dynamic_analysis_L60kcP_siltech_A37kcP_custom_20260511_085338.csv")'),
    (r'"torque_vs_h\.csv"',
     'str(AUTO_RUNS / "Simulation" / "torque_vs_h.csv")'),
]

# Remove old sys.path hunt blocks for deleted helpers
HUNT_PATTERNS = [
    r"# Ensure this notebook's directory is on sys\.path for rheology_pipeline_core\n.*?from viscometry\.analysis\.rheology_pipeline import",
    r"RUN_DIR = None.*?from viscometry\.analysis\.viscosity_pipeline import",
]


def patch_source(src: str) -> str:
    if "PROJECT_ROOT = _find_repo_root()" not in src:
        if src.strip():
            src = BOOTSTRAP + "\n" + src
        else:
            src = BOOTSTRAP

    for old, new in REPLACEMENTS:
        src = re.sub(old, new, src)

    # Strip legacy helper path hunting (simplified line-based)
    lines = src.splitlines()
    out: list[str] = []
    skip = False
    for i, line in enumerate(lines):
        if "viscosity_pipeline_helper.py" in line or "rheology_pipeline_core.py" in line:
            skip = True
            continue
        if skip:
            if "from viscometry" in line or "import run_viscosity_pipeline" in line:
                skip = False
                out.append(line)
            elif line.strip() == "" or line.strip().startswith("#") or "sys.path" in line or "RUN_DIR" in line or "NOTEBOOK_DIR" in line or "candidate" in line or "raise FileNotFoundError" in line:
                continue
            else:
                skip = False
                out.append(line)
        else:
            out.append(line)
    return "\n".join(out)


def patch_notebook(path: Path) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = False
    for cell in data.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        new_src = patch_source(src)
        if new_src != src:
            cell["source"] = [line + "\n" for line in new_src.splitlines()]
            if cell["source"]:
                cell["source"][-1] = cell["source"][-1].rstrip("\n")
            changed = True
    if changed:
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return changed


def main() -> int:
    nb_root = ROOT / "notebooks"
    count = 0
    for nb in sorted(nb_root.rglob("*.ipynb")):
        if patch_notebook(nb):
            print(f"patched: {nb.relative_to(ROOT)}")
            count += 1
    print(f"Updated {count} notebooks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

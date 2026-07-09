"""CSV loading helpers for rotational-drag experiment exports."""

from __future__ import annotations

import unicodedata
from io import StringIO
from pathlib import Path
from typing import List, Optional

import pandas as pd

from viscometry.io.csv_text import (
    find_row_cell_header_index,
    read_text_lines_with_fallback,
    resolve_existing_csv_path,
)
from viscometry.paths import PROJECT_ROOT


def _normalize_object_columns(df: pd.DataFrame) -> pd.DataFrame:
    """NFKC-normalize string columns so legacy R² bytes decode consistently."""
    out = df.copy()
    for col in out.select_dtypes(include=["object"]).columns:
        out[col] = out[col].map(
            lambda v: unicodedata.normalize("NFKC", str(v)) if pd.notna(v) else v
        )
    return out


def load_rotational_drag_csv(
    csv_path: str,
    cell_col: str = "cell",
    x_col: str = "Z_Height_mm",
    y_col: str = "Rotational_Drag",
    *,
    search_dirs: Optional[List[Path]] = None,
) -> pd.DataFrame:
    """Load a rotational-drag dataset and validate required columns."""
    default_dirs = [
        PROJECT_ROOT / "results" / "auto_runs",
        PROJECT_ROOT / "results" / "Auto-runs",
        PROJECT_ROOT / "results" / "runs" / "archive",
    ]
    dirs = list(search_dirs or []) + default_dirs
    resolved = resolve_existing_csv_path(csv_path, search_dirs=dirs)
    if not resolved.is_file():
        raise FileNotFoundError(f"CSV file not found: {csv_path} (resolved: {resolved})")

    lines, _encoding = read_text_lines_with_fallback(resolved)
    try:
        header_row = find_row_cell_header_index(lines)
    except ValueError as exc:
        raise ValueError(f"Could not load rotational-drag CSV {resolved!r}") from exc

    df = pd.read_csv(StringIO("\n".join(lines[header_row:])))
    df = _normalize_object_columns(df)
    required = {cell_col, x_col, y_col}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    out = df.copy()
    if y_col in out.columns:
        out = out[out[y_col].astype(str).str.upper() != "SKIPPED"].copy()
    out[cell_col] = pd.to_numeric(out[cell_col], errors="coerce")
    out[x_col] = pd.to_numeric(out[x_col], errors="coerce")
    out[y_col] = pd.to_numeric(out[y_col], errors="coerce")
    out = out.dropna(subset=[cell_col, x_col, y_col]).copy()
    out[cell_col] = out[cell_col].astype(int)
    out = out.sort_values([cell_col, x_col]).reset_index(drop=True)
    return out

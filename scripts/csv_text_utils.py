"""Deprecated shim — use viscometry.io.csv_text instead."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from viscometry.io.csv_text import (  # noqa: E402, F401
    find_row_cell_header_index,
    normalize_csv_text,
    read_text_lines_with_fallback,
    resolve_existing_csv_path,
)

"""Helpers for reading/writing instrument CSV exports with mixed encodings."""

from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


def normalize_csv_text(value: object) -> str:
    """
    Normalize text for CSV fields: NFKC, map superscript-2 to ^2, keep UTF-8 safe chars.
    """
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = text.replace("\u00b2", "^2").replace("²", "^2")
    return text


def read_text_lines_with_fallback(path: Path | str) -> Tuple[List[str], str]:
    """
    Read a text file as lines, trying common encodings then UTF-8 with replacement.

    Returns (lines_without_line_ending_chars, encoding_label).
    """
    raw = Path(path).read_bytes()
    if not raw:
        return [], "empty"

    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
            return text.splitlines(), encoding
        except UnicodeDecodeError:
            continue

    text = raw.decode("utf-8", errors="replace")
    return text.splitlines(), "utf-8-replace"


def find_row_cell_header_index(lines: Iterable[str]) -> int:
    """Return 0-based index of the data header row (starts with row,cell)."""
    for index, line in enumerate(lines):
        stripped = line.strip().strip('"').lstrip("#").strip()
        if stripped.lower().startswith("row,cell"):
            return index
    raise ValueError("No 'row,cell' header row found in CSV")


def resolve_existing_csv_path(csv_path: str, *, search_dirs: Optional[List[Path]] = None) -> Path:
    """
    Resolve a CSV path that may be relative to cwd, script dir, or results/auto_runs.
    """
    raw = Path(csv_path)
    candidates: List[Path] = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.append(raw)
        candidates.append(Path.cwd() / raw)
        if search_dirs:
            for directory in search_dirs:
                candidates.append(directory / raw)
                candidates.append(directory / raw.name)
        default_dirs = [
            Path.cwd() / "results" / "auto_runs",
            Path(__file__).resolve().parent.parent.parent / "results" / "auto_runs",
        ]
        for directory in default_dirs:
            candidates.append(directory / raw)
            candidates.append(directory / raw.name)

    seen = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved

    return raw.resolve() if raw.is_absolute() else (Path.cwd() / raw).resolve()

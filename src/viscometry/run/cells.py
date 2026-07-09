"""Cell numbering helpers for the 18-cell platform."""

from typing import Tuple


def global_cell_to_row_and_local(global_cell: int) -> Tuple[int, int]:
    """Convert global cell number (1-18) to row number (1-3) and local cell number (1-6)."""
    if global_cell < 1 or global_cell > 18:
        raise ValueError(f"Global cell number must be between 1 and 18, got {global_cell}")
    row = ((global_cell - 1) // 6) + 1
    local_cell = ((global_cell - 1) % 6) + 1
    return row, local_cell


def row_and_local_to_global_cell(row: int, local_cell: int) -> int:
    """Convert row number (1-3) and local cell number (1-6) to global cell number (1-18)."""
    if row < 1 or row > 3:
        raise ValueError(f"Row number must be between 1 and 3, got {row}")
    if local_cell < 1 or local_cell > 6:
        raise ValueError(f"Local cell number must be between 1 and 6, got {local_cell}")
    return (row - 1) * 6 + local_cell

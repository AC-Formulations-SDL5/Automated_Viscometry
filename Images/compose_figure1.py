"""Compose Figure_1.svg from six individual panel SVGs.

Layout (2 rows x 3 columns):
    A: normalized_rotational_drag.svg      B: plot1_raw_overview.svg          C: plot2_trimmed_hyperbola.svg
    D: plot3_prediction_accuracy.svg       E: plot4_error_distribution.svg    F: timeline_breakdown_bar.svg

Each panel is rescaled to a common width so the borders / column edges of
the resulting figure are aligned.  An "A"..."F" label is overlaid on the
top-left corner of every panel using the same Google-Material font styling
used inside the source plots.

Run:
    python Images/compose_figure1.py

Requires:  pip install svgutils lxml
"""

from __future__ import annotations

import re
from pathlib import Path

from svgutils.transform import SVGFigure, fromfile, TextElement


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent

# Order in the figure (row-major: A B C / D E F)
PANEL_FILES = [
    ("A", "normalized_rotational_drag.svg"),
    ("B", "plot1_raw_overview.svg"),
    ("C", "plot2_trimmed_hyperbola.svg"),
    ("D", "plot3_prediction_accuracy.svg"),
    ("E", "plot4_error_distribution.svg"),
    ("F", "timeline_breakdown_bar.svg"),
]

N_COLS = 3
N_ROWS = 2

# Target *panel* width in pt.  All panels are scaled uniformly to this width
# so the column edges of the composed figure line up perfectly.
PANEL_WIDTH_PT = 620.0

# Inter-panel gutters (pt)
COL_GUTTER_PT = 30.0
ROW_GUTTER_PT = 30.0

# Outer margins (pt)
MARGIN_PT = 20.0

# Subplot label styling (matches the Google Material theme used in the
# plotting notebook: bold sans-serif, ~36 pt -- a touch larger than tick
# labels so it reads clearly when the figure is scaled for print).
LABEL_FONT_FAMILY = "DejaVu Sans, Arial, sans-serif"
LABEL_FONT_SIZE = 32      # pt
LABEL_FONT_WEIGHT = "bold"
LABEL_COLOR = "#202124"   # Google Material near-black
LABEL_OFFSET_X = 6.0      # pt from panel left edge
LABEL_OFFSET_Y = 30.0     # pt from panel top edge (baseline)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_UNIT_RE = re.compile(r"^\s*([0-9.+\-eE]+)\s*([a-zA-Z%]*)\s*$")

# Conversion factors -> points (1 pt is the SVG user-space unit svgutils uses)
_UNIT_TO_PT = {
    "":   1.0,        # bare number  -> assume user units == pt
    "pt": 1.0,
    "px": 0.75,       # 1 px = 0.75 pt (CSS default 96 dpi)
    "in": 72.0,
    "mm": 72.0 / 25.4,
    "cm": 72.0 / 2.54,
    "pc": 12.0,
}


def _to_pt(value: str | float | int) -> float:
    """Parse a length string from an SVG (e.g. '638.76pt', '480px') -> pt."""
    if isinstance(value, (int, float)):
        return float(value)
    m = _UNIT_RE.match(str(value))
    if not m:
        raise ValueError(f"Cannot parse SVG length: {value!r}")
    num, unit = m.group(1), m.group(2).lower()
    if unit not in _UNIT_TO_PT:
        raise ValueError(f"Unsupported SVG unit {unit!r} in length {value!r}")
    return float(num) * _UNIT_TO_PT[unit]


def _load_panel(path: Path) -> tuple["object", float, float]:
    """Return (root_group, width_pt, height_pt) for an SVG file."""
    fig = fromfile(str(path))
    w_raw, h_raw = fig.get_size()
    w_pt, h_pt = _to_pt(w_raw), _to_pt(h_raw)
    root = fig.getroot()
    return root, w_pt, h_pt


def _make_label(text: str, x: float, y: float) -> TextElement:
    """Create a styled A/B/C/... panel label."""
    el = TextElement(
        x, y, text,
        size=LABEL_FONT_SIZE,
        font=LABEL_FONT_FAMILY,
        weight=LABEL_FONT_WEIGHT,
        color=LABEL_COLOR,
    )
    return el


# ---------------------------------------------------------------------------
# Main composition
# ---------------------------------------------------------------------------
def compose(output_path: Path = HERE / "Figure_1.svg") -> Path:
    panels: list[tuple[str, object, float, float, float]] = []
    # tuple: (label, root_element, scaled_width, scaled_height, scale)

    for label, fname in PANEL_FILES:
        path = HERE / fname
        if not path.exists():
            raise FileNotFoundError(f"Missing panel SVG: {path}")
        root, w_pt, h_pt = _load_panel(path)

        scale = PANEL_WIDTH_PT / w_pt
        new_w = PANEL_WIDTH_PT
        new_h = h_pt * scale
        root.scale(scale)
        panels.append((label, root, new_w, new_h, scale))

    # Row heights: tallest scaled panel per row dictates row height so all
    # panel top edges in a row align (and the bottom borders of the figure
    # column also align nicely between rows).
    row_heights = []
    for r in range(N_ROWS):
        row_panels = panels[r * N_COLS : (r + 1) * N_COLS]
        row_heights.append(max(p[3] for p in row_panels))

    total_w = (
        2 * MARGIN_PT
        + N_COLS * PANEL_WIDTH_PT
        + (N_COLS - 1) * COL_GUTTER_PT
    )
    total_h = (
        2 * MARGIN_PT
        + sum(row_heights)
        + (N_ROWS - 1) * ROW_GUTTER_PT
    )

    # Place each panel and its label
    placed_elements = []
    for idx, (label, root, w, h, _scale) in enumerate(panels):
        r = idx // N_COLS
        c = idx % N_COLS
        x = MARGIN_PT + c * (PANEL_WIDTH_PT + COL_GUTTER_PT)
        # Top-align panels within their row so column edges line up.
        y = MARGIN_PT + sum(row_heights[:r]) + r * ROW_GUTTER_PT

        root.moveto(x, y)
        placed_elements.append(root)

        # Label sits just inside the top-left of each panel.
        label_el = _make_label(
            label,
            x + LABEL_OFFSET_X,
            y + LABEL_OFFSET_Y,
        )
        placed_elements.append(label_el)

    fig = SVGFigure(f"{total_w}pt", f"{total_h}pt")
    # Set viewBox so external viewers / LaTeX render at the correct aspect.
    fig.root.set("viewBox", f"0 0 {total_w} {total_h}")
    fig.append(placed_elements)
    fig.save(str(output_path))
    return output_path


if __name__ == "__main__":
    out = compose()
    print(f"Wrote {out}")

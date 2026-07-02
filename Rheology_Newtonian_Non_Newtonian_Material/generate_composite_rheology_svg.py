#!/usr/bin/env python3
"""Build a single composite SVG for Newtonian and Non-Newtonian materials.

Layout requested by user:
- 5 columns
- Row 1: Newtonian Materials (col 1), Non-Newtonian Materials (cols 2-5)
- Row 2: category boxes
- Row 3: schematics (lubricant, rheology modifier, TIM)
- Remaining rows: plot panels from exported figure SVG files

The output is a self-contained SVG by embedding source SVG files as base64 data URIs.
"""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
from typing import Optional
from xml.dom import minidom
from xml.etree import ElementTree as ET


GOOGLE_BLUE = "#4285F4"
GOOGLE_RED = "#EA4335"
GOOGLE_YELLOW = "#FBBC05"
GOOGLE_GREEN = "#34A853"
GOOGLE_ORANGE = "#FF6D00"
GOOGLE_TEAL = "#46BDC6"

ROOT_BG = "#F8F9FA"
HEADER_BG = "#E8F0FE"
GROUP_BG = "#FFFFFF"
BORDER = "#DADCE0"
TEXT_DARK = "#202124"
TEXT_MUTED = "#5F6368"

CANVAS_BG = "#DCE3EF"
CARD_BLUE = "#C2D2EE"
CARD_GREEN = "#CBE7D6"
CARD_BEIGE = "#F4E6BE"



def _svg_root(width: int, height: int) -> ET.Element:
    root = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "version": "1.1",
            "viewBox": f"0 0 {width} {height}",
            "width": str(width),
            "height": str(height),
        },
    )
    return root


def _add_styles(root: ET.Element) -> None:
    style = ET.SubElement(root, "style")
    style.text = (
        ".h1{font-family:Arial,sans-serif;font-size:50px;font-weight:800;fill:#101418;letter-spacing:1px;}"
        ".h2{font-family:Arial,sans-serif;font-size:46px;font-weight:800;fill:#101418;letter-spacing:0.6px;}"
        ".h3{font-family:Arial,sans-serif;font-size:25px;font-weight:800;fill:#101418;}"
        ".h3Lub{font-family:Arial,sans-serif;font-size:40px;font-weight:800;fill:#2F5D9B;}"
        ".h3RM{font-family:Arial,sans-serif;font-size:40px;font-weight:800;fill:#2E6B3D;}"
        ".h3TIM{font-family:Arial,sans-serif;font-size:40px;font-weight:800;fill:#9A6A00;}"
        ".panelLetter{font-family:Arial,sans-serif;font-size:34px;font-weight:400;fill:#101418;}"
        ".subtitle{font-family:Arial,sans-serif;font-size:15px;font-weight:600;fill:#5F6368;}"
    )


def _pretty_write_svg(root: ET.Element, output_path: Path) -> None:
    raw = ET.tostring(root, encoding="utf-8")
    pretty = minidom.parseString(raw).toprettyxml(indent="  ")
    output_path.write_text(pretty, encoding="utf-8")


def _add_rect(
    parent: ET.Element,
    x: float,
    y: float,
    w: float,
    h: float,
    fill: str,
    stroke: str,
    stroke_w: float = 1.8,
    rx: float = 14,
) -> ET.Element:
    return ET.SubElement(
        parent,
        "rect",
        {
            "x": f"{x:.2f}",
            "y": f"{y:.2f}",
            "width": f"{w:.2f}",
            "height": f"{h:.2f}",
            "rx": f"{rx:.2f}",
            "ry": f"{rx:.2f}",
            "fill": fill,
            "stroke": stroke,
            "stroke-width": f"{stroke_w:.2f}",
        },
    )


def _add_text(
    parent: ET.Element,
    text: str,
    x: float,
    y: float,
    klass: str,
    anchor: str = "middle",
) -> ET.Element:
    t = ET.SubElement(
        parent,
        "text",
        {
            "x": f"{x:.2f}",
            "y": f"{y:.2f}",
            "class": klass,
            "text-anchor": anchor,
            "dominant-baseline": "middle",
        },
    )
    t.text = text
    return t


def _svg_data_uri(path: Path) -> str:
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"




def _place_svg_image(
    parent: ET.Element,
    path: Path,
    x: float,
    y: float,
    w: float,
    h: float,
    preserve_aspect_ratio: str = "xMidYMid meet",
) -> None:
    href = _svg_data_uri(path)
    ET.SubElement(
        parent,
        "image",
        {
            "x": f"{x:.2f}",
            "y": f"{y:.2f}",
            "width": f"{w:.2f}",
            "height": f"{h:.2f}",
            "href": href,
            "preserveAspectRatio": preserve_aspect_ratio,
        },
    )


def _draw_group_brace(
    parent: ET.Element,
    x_left: float,
    x_right: float,
    y_top: float,
    y_base: float,
    color: str,
) -> None:
    mid = (x_left + x_right) / 2.0
    d = (
        f"M {x_left:.2f} {y_base:.2f} "
        f"L {x_left:.2f} {y_top + 34:.2f} "
        f"Q {x_left:.2f} {y_top:.2f} {x_left + 34:.2f} {y_top:.2f} "
        f"L {mid - 54:.2f} {y_top:.2f} "
        f"Q {mid:.2f} {y_top:.2f} {mid:.2f} {y_top - 34:.2f} "
        f"Q {mid:.2f} {y_top:.2f} {mid + 54:.2f} {y_top:.2f} "
        f"L {x_right - 34:.2f} {y_top:.2f} "
        f"Q {x_right:.2f} {y_top:.2f} {x_right:.2f} {y_top + 34:.2f} "
        f"L {x_right:.2f} {y_base:.2f}"
    )
    ET.SubElement(
        parent,
        "path",
        {
            "d": d,
            "fill": "none",
            "stroke": color,
            "stroke-width": "8",
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
        },
    )


def _figure_path(figures_dir: Path, fig_id: int) -> Path:
    matches = sorted(figures_dir.glob(f"{fig_id}_*.svg"))
    if not matches:
        raise FileNotFoundError(f"Could not find SVG for figure ID {fig_id} in {figures_dir}")
    return matches[0]


def _draw_layout(base_dir: Path, output_path: Path, width: int, height: int) -> None:
    figures_dir = base_dir / "figures_svg"

    schematic_lubricant = base_dir / "lubricant_schematic.svg"
    schematic_rm = base_dir / "Rheology_modifier_schematic.svg"
    schematic_tim = base_dir / "TIM_schematic.svg"

    required = [
        schematic_lubricant,
        schematic_rm,
        schematic_tim,
    ]
    for p in required:
        if not p.exists():
            raise FileNotFoundError(f"Required file missing: {p}")

    # Figure IDs by column, top to bottom.
    # Empty slots are None to keep row alignment across columns.
    columns: list[list[Optional[int]]] = [
        [117, 103, None, None],
        [118, 105, 120, 109],
        [119, 107, 121, 111],
        [122, 113, 124, 114],
        [123, 115, None, None],
    ]

    root = _svg_root(width, height)
    _add_styles(root)

    g = ET.SubElement(root, "g")

    # Solid white backdrop so exported SVG never renders with transparency.
    _add_rect(g, 0, 0, width, height, fill="#FFFFFF", stroke="none", stroke_w=0, rx=0)

    outer_margin_x = 10  #36
    outer_margin_y = 30 #28
    col_gap = 18
    n_cols = 5
    col_w = (width - 2 * outer_margin_x - (n_cols - 1) * col_gap) / n_cols

    # Vertical geometry
    h_row1 = 90     # Top material family text
    h_brace = 86    # Brace connectors area
    h_row2 = 76     # Category group boxes
    h_row3 = 320    # Schematics (increased)
    h_plot = 450    # Plot row height (+50%)
    row_gap = 30
    plot_row_gap = 10  # Highly small spacing between plot rows.

    # Compute y anchors
    y1 = outer_margin_y
    y_brace = y1 + h_row1 + 4
    y2 = y_brace + h_brace + 10
    y3 = y2 + h_row2 + row_gap
    y_plot0 = y3 + h_row3 + row_gap

    # x starts
    col_x = [outer_margin_x + i * (col_w + col_gap) for i in range(n_cols)]
    rm_x = col_x[1]
    rm_w = 2 * col_w + col_gap
    tim_x = col_x[3]
    tim_w = 2 * col_w + col_gap

    # Row 1 titles
    _add_text(g, "NEWTONIAN MATERIALS", col_x[0] + col_w / 2 + 130, y1 + h_row1 / 2, "h1")

    nn_x = col_x[1]
    nn_w = 4 * col_w + 3 * col_gap
    _add_text(g, "NON-NEWTONIAN MATERIALS", nn_x + nn_w / 2, y1 + h_row1 / 2, "h1")

    # Brace connectors from material families to category chips
    _draw_group_brace(
        g,
        x_left=col_x[0] + col_w * 0.12,
        x_right=rm_x + rm_w * 0.05,
        y_top=y_brace + 10,
        y_base=y2 - 8,
        color="#5F98DF",
    )
    _draw_group_brace(
        g,
        x_left=rm_x + rm_w * 0.05,
        x_right=col_x[4] + col_w * 0.50,
        y_top=y_brace + 10,
        y_base=y2 - 8,
        color="#59B47D",
    )

    # Row 2 category boxes
    _add_rect(g, col_x[0], y2, col_w, h_row2, fill="#84ABE8", stroke="none", stroke_w=0, rx=16)
    _add_text(g, "LUBRICANTS", col_x[0] + col_w / 2, y2 + h_row2 / 2, "h3Lub")

    _add_rect(g, rm_x, y2, rm_w, h_row2, fill="#8FCC9A", stroke="none", stroke_w=0, rx=16)
    _add_text(g, "RHEOLOGY MODIFIERS", rm_x + rm_w / 2, y2 + h_row2 / 2, "h3RM")

    _add_rect(g, tim_x, y2, tim_w, h_row2, fill="#F6D98D", stroke="none", stroke_w=0, rx=16)
    _add_text(g, "THERMAL INTERFACE MATERIALS", tim_x + tim_w / 2, y2 + h_row2 / 2, "h3TIM")

    # Row 3 schematics
    _add_rect(g, col_x[0], y3, col_w, h_row3, fill=CARD_BLUE, stroke="none", stroke_w=0, rx=24)
    _add_rect(g, rm_x, y3, rm_w, h_row3, fill=CARD_GREEN, stroke="none", stroke_w=0, rx=24)
    _add_rect(g, tim_x, y3, tim_w, h_row3, fill=CARD_BEIGE, stroke="none", stroke_w=0, rx=24)

    pad = 8
    _place_svg_image(
        g,
        schematic_lubricant,
        col_x[0] + pad,
        y3 + pad,
        col_w - 2 * pad,
        h_row3 - 2 * pad,
        preserve_aspect_ratio="xMidYMid slice",
    )
    _place_svg_image(
        g,
        schematic_rm,
        rm_x + pad,
        y3 + pad,
        rm_w - 2 * pad,
        h_row3 - 2 * pad,
        preserve_aspect_ratio="xMidYMid slice",
    )
    _place_svg_image(
        g,
        schematic_tim,
        tim_x + pad,
        y3 + pad,
        tim_w - 2 * pad,
        h_row3 - 2 * pad,
        preserve_aspect_ratio="xMidYMid slice",
    )

    # Plot panels with custom labels in row-major placement order.
    panel_labels = iter(
        [
            "A1",
            "B1",
            "C1",
            "F1",
            "G1",
            "A2",
            "B2",
            "C2",
            "F2",
            "G2",
            "D1",
            "E1",
            "H1",
            "D2",
            "E2",
            "H2",
        ]
    )

    for r in range(4):
        y = y_plot0 + r * (h_plot + plot_row_gap)
        for c in range(5):
            fig_id = columns[c][r]
            if fig_id is None:
                continue

            x = col_x[c]

            panel_label = next(panel_labels)
            _add_text(g, panel_label, x + 20, y + 22, "panelLetter", anchor="start")

            # Place each exported SVG directly in its slot (no extra frame or color strip).
            img_pad_x = 2
            img_top = 34
            img_h = h_plot - img_top - 2

            fig_path = _figure_path(figures_dir, fig_id)
            _place_svg_image(
                g,
                fig_path,
                x + img_pad_x,
                y + img_top,
                col_w - 2 * img_pad_x,
                img_h,
                preserve_aspect_ratio="xMidYMid meet",
            )

    _pretty_write_svg(root, output_path)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate the composite rheology figure SVG.")
    p.add_argument(
        "--base-dir",
        default=None,
        help="Directory containing schematics and figures_svg (defaults to script directory).",
    )
    p.add_argument(
        "--output",
        default=None,
        help="Output SVG path (default: composite_rheology_overview.svg in base dir).",
    )
    p.add_argument("--width", type=int, default=2600, help="Canvas width in px.")
    p.add_argument("--height", type=int, default=2400, help="Canvas height in px.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    base_dir = Path(args.base_dir).resolve() if args.base_dir else script_dir
    output_path = Path(args.output).resolve() if args.output else (base_dir / "composite_rheology_overview.svg")

    _draw_layout(base_dir=base_dir, output_path=output_path, width=args.width, height=args.height)
    print(f"Composite SVG written to: {output_path}")


if __name__ == "__main__":
    main()

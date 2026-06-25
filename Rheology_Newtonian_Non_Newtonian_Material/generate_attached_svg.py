#!/usr/bin/env python3
"""Generate an SVG that recreates the attached bead-chain sketch style.

Usage:
    python generate_attached_svg.py
    python generate_attached_svg.py --output my_image.svg --width 516 --height 387
"""

from __future__ import annotations

import argparse
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree as ET


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

    ET.SubElement(
        root,
        "rect",
        {
            "x": "0",
            "y": "0",
            "width": str(width),
            "height": str(height),
            "fill": "#e7e7e7",
        },
    )

    return root


def _add_styles(root: ET.Element) -> None:
    style = ET.SubElement(root, "style")
    style.text = (
        ".chain{fill:none;stroke:#111;stroke-width:3.5;stroke-linecap:round;stroke-linejoin:round;}"
        ".bead{fill:#b9c7cb;stroke:#111;stroke-width:2;}"
        ".hatch{stroke:#4f5659;stroke-width:1.6;stroke-linecap:round;}"
        ".arrow{stroke:#111;stroke-width:3.5;fill:none;stroke-linecap:round;}"
        ".arrowhead{fill:#111;}"
    )


def _add_chain_path(group: ET.Element, points: list[tuple[float, float]], bend: float = 0.22) -> None:
    if len(points) < 2:
        return

    d = [f"M {points[0][0]} {points[0][1]}"]
    for i in range(1, len(points)):
        x0, y0 = points[i - 1]
        x1, y1 = points[i]
        mx = (x0 + x1) / 2
        my = (y0 + y1) / 2
        dx = x1 - x0
        dy = y1 - y0
        seg_len = (dx * dx + dy * dy) ** 0.5 or 1.0
        nx = -dy / seg_len
        ny = dx / seg_len

        # Alternate bend direction to emulate hand-drawn, wavy polymer chains.
        sign = 1 if i % 2 else -1
        amp = bend * seg_len * sign

        c1x = x0 + dx / 3 + nx * amp
        c1y = y0 + dy / 3 + ny * amp
        c2x = x0 + 2 * dx / 3 + nx * amp
        c2y = y0 + 2 * dy / 3 + ny * amp
        d.append(f"C {c1x} {c1y} {c2x} {c2y} {x1} {y1}")

    ET.SubElement(group, "path", {"class": "chain", "d": " ".join(d)})


def _add_bead(root: ET.Element, group: ET.Element, bead_id: str, x: float, y: float, r: float = 14) -> None:
    clip = ET.SubElement(root, "clipPath", {"id": f"clip_{bead_id}"})
    ET.SubElement(clip, "circle", {"cx": str(x), "cy": str(y), "r": str(r)})

    ET.SubElement(
        group,
        "circle",
        {
            "class": "bead",
            "cx": str(x),
            "cy": str(y),
            "r": str(r),
        },
    )

    hatch_group = ET.SubElement(group, "g", {"clip-path": f"url(#clip_{bead_id})"})
    offsets = (-6, -1, 4)
    for offset in offsets:
        ET.SubElement(
            hatch_group,
            "line",
            {
                "class": "hatch",
                "x1": str(x - r + offset),
                "y1": str(y - r),
                "x2": str(x + r + offset),
                "y2": str(y + r),
            },
        )


def _add_arrow(group: ET.Element, x1: float, y1: float, x2: float, y2: float) -> None:
    ET.SubElement(
        group,
        "line",
        {
            "class": "arrow",
            "x1": str(x1),
            "y1": str(y1),
            "x2": str(x2),
            "y2": str(y2),
        },
    )

    dx = x2 - x1
    dy = y2 - y1
    length = (dx * dx + dy * dy) ** 0.5 or 1.0
    ux, uy = dx / length, dy / length
    px, py = -uy, ux

    head_len = 14
    head_w = 7
    bx = x2 - ux * head_len
    by = y2 - uy * head_len

    p1 = (x2, y2)
    p2 = (bx + px * head_w, by + py * head_w)
    p3 = (bx - px * head_w, by - py * head_w)

    ET.SubElement(
        group,
        "polygon",
        {
            "class": "arrowhead",
            "points": f"{p1[0]},{p1[1]} {p2[0]},{p2[1]} {p3[0]},{p3[1]}",
        },
    )


def build_svg(width: int, height: int) -> ET.Element:
    root = _svg_root(width, height)
    _add_styles(root)

    g = ET.SubElement(root, "g")

    # Top-left chain
    _add_chain_path(g, [(18, 112), (52, 136), (88, 126), (122, 96), (160, 84), (198, 86), (236, 84), (278, 58)])
    for i, (x, y) in enumerate([(58, 136), (116, 126), (168, 96), (226, 84)]):
        _add_bead(root, g, f"tl_{i}", x, y)

    # Mid-right chain
    _add_chain_path(g, [(224, 153), (246, 131), (280, 141), (314, 167), (350, 143), (390, 149), (430, 135), (466, 150), (492, 132)])
    for i, (x, y) in enumerate([(250, 137), (298, 145), (344, 170), (390, 150), (440, 144)]):
        _add_bead(root, g, f"mr_{i}", x, y)

    # Mid-left chain
    _add_chain_path(g, [(20, 215), (46, 235), (80, 220), (116, 205), (154, 226), (193, 227), (229, 206), (270, 220)])
    for i, (x, y) in enumerate([(94, 218), (136, 206), (190, 226), (236, 208)]):
        _add_bead(root, g, f"ml_{i}", x, y)

    # Bottom-center chain
    _add_chain_path(g, [(63, 300), (95, 321), (126, 307), (160, 277), (198, 255), (236, 279), (278, 293), (319, 272), (362, 281), (401, 263), (447, 244), (478, 262)])
    for i, (x, y) in enumerate([(106, 314), (153, 280), (206, 260), (255, 281), (299, 286), (345, 273)]):
        _add_bead(root, g, f"bc_{i}", x, y)

    # Decorative chain tails
    _add_chain_path(g, [(378, 327), (404, 332), (433, 323), (462, 300), (488, 281)])

    arrows = ET.SubElement(root, "g")
    _add_arrow(arrows, 130, 70, 278, 28)
    _add_arrow(arrows, 128, 167, 250, 133)
    _add_arrow(arrows, 416, 225, 340, 247)
    _add_arrow(arrows, 130, 348, 237, 287)
    _add_arrow(arrows, 390, 327, 470, 287)

    return root


def write_svg(output_path: str, width: int, height: int) -> None:
    root = build_svg(width, height)
    rough = ET.tostring(root, encoding="utf-8")
    pretty = minidom.parseString(rough).toprettyxml(indent="  ")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(pretty)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an SVG from the attached bead-chain sketch style.")
    parser.add_argument("--output", default=None, help="Output SVG file path.")
    parser.add_argument("--width", type=int, default=516, help="SVG width in pixels.")
    parser.add_argument("--height", type=int, default=387, help="SVG height in pixels.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = args.output
    if output_path is None:
        output_path = str(Path(__file__).resolve().with_name("lubricant_schematic.svg"))
    write_svg(output_path, args.width, args.height)
    print(f"SVG written to: {output_path}")


if __name__ == "__main__":
    main()

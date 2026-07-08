#!/usr/bin/env python3
"""Generate an SVG resembling the attached TIM schematic.

Usage:
    python generate_tim_schematic_svg.py
    python generate_tim_schematic_svg.py --output custom.svg --width 591 --height 387
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree as ET


def make_root(width: int, height: int) -> ET.Element:
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


def add_style(root: ET.Element) -> None:
    style = ET.SubElement(root, "style")
    style.text = (
        ".chain{fill:none;stroke:#222;stroke-width:3.3;stroke-linecap:round;stroke-linejoin:round;opacity:0.95;}"
        ".small{stroke:#2f343b;stroke-width:2.6;}"
        ".large{stroke:#2f343b;stroke-width:4.2;}"
    )


def curved_segment(a: tuple[float, float], b: tuple[float, float], bend: float) -> str:
    x0, y0 = a
    x1, y1 = b
    dx = x1 - x0
    dy = y1 - y0
    seg_len = math.hypot(dx, dy) or 1.0
    nx = -dy / seg_len
    ny = dx / seg_len

    amp = bend * seg_len
    c1x = x0 + dx / 3 + nx * amp
    c1y = y0 + dy / 3 + ny * amp
    c2x = x0 + 2 * dx / 3 + nx * amp
    c2y = y0 + 2 * dy / 3 + ny * amp
    return f"C {c1x:.2f} {c1y:.2f} {c2x:.2f} {c2y:.2f} {x1:.2f} {y1:.2f}"


def add_chain(group: ET.Element, points: list[tuple[float, float]], bends: list[float] | None = None) -> None:
    if len(points) < 2:
        return
    if bends is None:
        bends = [0.18 if i % 2 else -0.18 for i in range(len(points) - 1)]

    d = [f"M {points[0][0]:.2f} {points[0][1]:.2f}"]
    for i in range(1, len(points)):
        d.append(curved_segment(points[i - 1], points[i], bends[i - 1]))
    ET.SubElement(group, "path", {"class": "chain", "d": " ".join(d)})


def add_circle_with_highlight(
    group: ET.Element,
    x: float,
    y: float,
    r: float,
    fill: str,
    cls: str = "small",
    alpha: float = 1.0,
) -> None:
    ET.SubElement(
        group,
        "circle",
        {
            "class": cls,
            "cx": f"{x:.2f}",
            "cy": f"{y:.2f}",
            "r": f"{r:.2f}",
            "fill": fill,
            "fill-opacity": f"{alpha:.2f}",
        },
    )

    # Soft highlight for a hand-drawn glossy look.
    ET.SubElement(
        group,
        "circle",
        {
            "cx": f"{x - 0.23 * r:.2f}",
            "cy": f"{y - 0.25 * r:.2f}",
            "r": f"{0.62 * r:.2f}",
            "fill": "#ffffff",
            "fill-opacity": "0.10",
        },
    )


def build_svg(width: int, height: int) -> ET.Element:
    root = make_root(width, height)
    add_style(root)

    # Draw directly in the full viewBox so the schematic uses the available area.
    g_scene = ET.SubElement(root, "g")
    g_chain = ET.SubElement(g_scene, "g")
    g_nodes = ET.SubElement(g_scene, "g")

    # Color palette mirroring the attached TIM sketch.
    blue = "#1C9DD3"
    red = "#C41423"
    green = "#4DA251"
    dark_gray = "#5F6368"
    peach = "#F2BC93"
    light_blue = "#5EB7E6"
    steel = "#7EA5C2"
    pale_green = "#A5BF84"
    mist = "#AFD9E7"

    # Curvy polymer-like backbones.
    chains = [
        [(30, 96), (82, 120), (136, 102), (172, 138), (232, 128), (286, 156), (338, 130), (394, 170), (450, 142), (514, 168)],
        [(42, 168), (104, 156), (168, 188), (230, 174), (286, 196), (340, 182), (408, 204), (470, 178), (552, 202)],
        [(24, 246), (76, 212), (136, 236), (196, 214), (258, 238), (324, 226), (392, 252), (462, 228), (528, 246)],
        [(8, 342), (46, 306), (98, 282), (150, 322), (206, 338), (262, 332), (316, 356), (372, 320)],
        [(120, 198), (104, 240), (72, 278), (34, 314)],
        [(488, 42), (486, 86), (494, 132), (488, 172), (470, 208), (500, 248), (540, 286), (586, 286)],
        [(226, 74), (206, 114), (222, 152), (262, 176), (302, 156), (326, 182), (362, 200), (402, 174)],
        [(136, 224), (180, 194), (222, 192), (262, 214), (302, 250), (278, 284), (236, 300), (198, 328)],
    ]

    for idx, pts in enumerate(chains):
        bends = []
        for i in range(len(pts) - 1):
            sign = 1 if (i + idx) % 2 else -1
            bends.append(sign * (0.15 + 0.05 * ((i + 1) % 3)))
        add_chain(g_chain, pts, bends)

    # Big droplets/particles.
    for x, y, r, c in [
        (42, 212, 44, red),
        (138, 252, 56, blue),
        (288, 54, 46, dark_gray),
        (392, 90, 54, blue),
        (542, 212, 52, red),
        (222, 182, 40, dark_gray),
    ]:
        add_circle_with_highlight(g_nodes, x, y, r, c, cls="large")

    # Medium particles.
    for x, y, r, c in [
        (258, 276, 34, green),
        (468, 228, 32, green),
        (350, 252, 30, red),
        (334, 218, 29, green),
        (214, 278, 31, green),
    ]:
        add_circle_with_highlight(g_nodes, x, y, r, c, cls="large")

    # Small nodes on chains.
    small_nodes = [
        (80, 120, 18, peach), (136, 102, 18, light_blue), (172, 144, 18, light_blue),
        (228, 130, 18, red), (356, 160, 10, mist), (372, 182, 11, steel),
        (400, 182, 11, peach), (430, 178, 11, steel), (514, 168, 18, light_blue),
        (514, 92, 18, peach), (98, 172, 21, red), (96, 226, 15, peach),
        (178, 214, 18, steel), (266, 218, 18, pale_green), (50, 316, 17, light_blue),
        (102, 322, 16, steel), (160, 354, 17, peach), (224, 330, 18, steel),
        (296, 356, 11, mist), (372, 318, 18, steel), (438, 300, 18, light_blue),
        (518, 286, 18, steel),
    ]

    for x, y, r, c in small_nodes:
        add_circle_with_highlight(g_nodes, x, y, r, c)

    # Tiny interstitial particles.
    for x, y, r, c in [
        (332, 356, 10, mist), (78, 274, 7, steel), (286, 160, 7, peach),
        (438, 170, 8, peach), (472, 156, 8, mist), (548, 252, 8, mist),
    ]:
        add_circle_with_highlight(g_nodes, x, y, r, c, alpha=0.95)

    return root


def write_svg(path: str, width: int, height: int) -> None:
    root = build_svg(width, height)
    rough = ET.tostring(root, encoding="utf-8")
    pretty = minidom.parseString(rough).toprettyxml(indent="  ")
    with open(path, "w", encoding="utf-8") as f:
        f.write(pretty)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate TIM-style schematic SVG.")
    parser.add_argument("--output", default=None, help="Output SVG file path.")
    parser.add_argument("--width", type=int, default=591, help="SVG width in pixels.")
    parser.add_argument("--height", type=int, default=387, help="SVG height in pixels.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output
    if output is None:
        output = str(Path(__file__).resolve().with_name("TIM_schematic.svg"))
    write_svg(output, args.width, args.height)
    print(f"SVG written to: {output}")


if __name__ == "__main__":
    main()

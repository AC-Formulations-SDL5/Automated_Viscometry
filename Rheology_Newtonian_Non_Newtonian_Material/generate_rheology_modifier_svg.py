#!/usr/bin/env python3
"""Generate an SVG resembling a dense rheology-modifier polymer network.

Usage:
    python generate_rheology_modifier_svg.py
    python generate_rheology_modifier_svg.py --output custom.svg --width 1120 --height 387
"""

from __future__ import annotations

import argparse
import math
import random
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
    ET.SubElement(
        root,
        "rect",
        {
            "x": "0",
            "y": "0",
            "width": str(width),
            "height": str(height),
            "fill": "#ffffff",
        },
    )
    return root


def add_style(root: ET.Element) -> None:
    style = ET.SubElement(root, "style")
    style.text = (
        ".edge{fill:none;stroke:#111;stroke-width:2.25;stroke-linecap:round;stroke-linejoin:round;opacity:0.95;}"
        ".node{stroke:#2f3a44;stroke-width:1.8;}"
    )


def cubic_from_segment(a: tuple[float, float], b: tuple[float, float], bend: float) -> str:
    x0, y0 = a
    x1, y1 = b
    dx = x1 - x0
    dy = y1 - y0
    seg_len = (dx * dx + dy * dy) ** 0.5 or 1.0
    nx = -dy / seg_len
    ny = dx / seg_len

    amp = bend * seg_len
    c1x = x0 + dx / 3 + nx * amp
    c1y = y0 + dy / 3 + ny * amp
    c2x = x0 + 2 * dx / 3 + nx * amp
    c2y = y0 + 2 * dy / 3 + ny * amp
    return f"C {c1x:.2f} {c1y:.2f} {c2x:.2f} {c2y:.2f} {x1:.2f} {y1:.2f}"


def add_curved_edge(group: ET.Element, a: tuple[float, float], b: tuple[float, float], bend: float) -> None:
    x0, y0 = a
    path_data = f"M {x0:.2f} {y0:.2f} {cubic_from_segment(a, b, bend)}"
    ET.SubElement(group, "path", {"class": "edge", "d": path_data})


def point_in_void(x: float, y: float, voids: list[tuple[float, float, float]]) -> bool:
    for cx, cy, r in voids:
        if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
            return True
    return False


def pick_node_color(rng: random.Random) -> str:
    # Google-inspired palette distribution with blue as the dominant network color.
    u = rng.random()
    if u < 0.68:
        return "#4285F4"  # Google blue
    if u < 0.80:
        return "#34A853"  # Google green
    if u < 0.90:
        return "#FBBC05"  # Google yellow
    return "#EA4335"      # Google red


def build_svg(width: int, height: int, seed: int) -> ET.Element:
    rng = random.Random(seed)
    root = make_root(width, height)
    add_style(root)

    g_edges = ET.SubElement(root, "g")
    g_nodes = ET.SubElement(root, "g")

    # Large pores/voids inside the polymer network.
    voids = [
        (width * 0.16, height * 0.14, 42),
        (width * 0.40, height * 0.20, 48),
        (width * 0.68, height * 0.23, 52),
        (width * 0.53, height * 0.66, 66),
        (width * 0.78, height * 0.72, 55),
        (width * 0.29, height * 0.80, 62),
    ]

    spacing = 41
    jitter = 9

    points: list[tuple[float, float]] = []
    cols = int(width / spacing) + 3
    rows = int(height / spacing) + 3

    for r in range(rows):
        for c in range(cols):
            x = c * spacing + rng.uniform(-jitter, jitter)
            y = r * spacing + rng.uniform(-jitter, jitter)
            if point_in_void(x, y, voids):
                continue
            if -15 <= x <= width + 15 and -15 <= y <= height + 15:
                points.append((x, y))

    # Index points on a coarse grid for local neighbor search.
    bucket_size = spacing * 1.4
    buckets: dict[tuple[int, int], list[int]] = {}
    for i, (x, y) in enumerate(points):
        key = (int(x / bucket_size), int(y / bucket_size))
        buckets.setdefault(key, []).append(i)

    edges: set[tuple[int, int]] = set()
    for i, (x, y) in enumerate(points):
        key = (int(x / bucket_size), int(y / bucket_size))
        candidates: list[int] = []
        for ky in (key[1] - 1, key[1], key[1] + 1):
            for kx in (key[0] - 1, key[0], key[0] + 1):
                candidates.extend(buckets.get((kx, ky), []))

        # Sort by distance and connect to a handful of nearby nodes.
        near = sorted(
            ((j, (points[j][0] - x) ** 2 + (points[j][1] - y) ** 2) for j in candidates if j != i),
            key=lambda t: t[1],
        )

        target_links = 2 + (1 if rng.random() < 0.35 else 0)
        made = 0
        for j, d2 in near:
            if d2 < 11 ** 2 or d2 > 68 ** 2:
                continue
            a, b = (i, j) if i < j else (j, i)
            if (a, b) in edges:
                continue
            if rng.random() < 0.82:
                edges.add((a, b))
                made += 1
            if made >= target_links:
                break

    for a, b in edges:
        pa = points[a]
        pb = points[b]
        sign = 1.0 if rng.random() < 0.5 else -1.0
        bend = sign * rng.uniform(0.12, 0.28)
        add_curved_edge(g_edges, pa, pb, bend)

    node_r = 5.8
    for x, y in points:
        ET.SubElement(
            g_nodes,
            "circle",
            {
                "class": "node",
                "cx": f"{x:.2f}",
                "cy": f"{y:.2f}",
                "r": f"{node_r:.2f}",
                "fill": pick_node_color(rng),
            },
        )

    # Add a denser knot region near the bottom-right to match the source sketch.
    knot_center = (width * 0.84, height * 0.72)
    knot_points: list[tuple[float, float]] = []
    for _ in range(26):
        ang = rng.uniform(0, 2 * math.pi)
        rad = rng.uniform(8, 54)
        kx = knot_center[0] + math.cos(ang) * rad
        ky = knot_center[1] + math.sin(ang) * rad
        knot_points.append((kx, ky))

    for i in range(len(knot_points) - 1):
        add_curved_edge(g_edges, knot_points[i], knot_points[i + 1], rng.uniform(-0.35, 0.35))
    for x, y in knot_points:
        ET.SubElement(
            g_nodes,
            "circle",
            {
                "class": "node",
                "cx": f"{x:.2f}",
                "cy": f"{y:.2f}",
                "r": "5.4",
                "fill": pick_node_color(rng),
            },
        )

    return root


def write_svg(path: str, width: int, height: int, seed: int) -> None:
    root = build_svg(width, height, seed)
    rough = ET.tostring(root, encoding="utf-8")
    pretty = minidom.parseString(rough).toprettyxml(indent="  ")
    with open(path, "w", encoding="utf-8") as f:
        f.write(pretty)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a rheology modifier network SVG schematic.")
    parser.add_argument("--output", default=None, help="Output SVG file path.")
    parser.add_argument("--width", type=int, default=1120, help="SVG width in pixels.")
    parser.add_argument("--height", type=int, default=387, help="SVG height in pixels.")
    parser.add_argument("--seed", type=int, default=7, help="Random seed for deterministic layout.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output
    if output is None:
        output = str(Path(__file__).resolve().with_name("Rheology_modifier_schematic.svg"))
    write_svg(output, args.width, args.height, args.seed)
    print(f"SVG written to: {output}")


if __name__ == "__main__":
    main()

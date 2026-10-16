"""Generate Figure 2 (manual descent acquisition) as a single editable SVG.

Panel A is a vector schematic of the manual protocol in the style of Figures 3 and 5;
panels B-D are re-plotted from the manually recorded descent data
("Viscosity Readings - manual_vs_auto_drag.csv").

Usage:  python Images/figure2_v2.py <manual_vs_auto_drag.csv> [out_dir]
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from workflow_figures_v2 import ARROW, BAND, C, Canvas  # noqa: E402

W = 2000
GRAY = "#C9CED6"
DARK = "#5F6773"
INK = "#1F1F1F"
SAMPLE = "#F6D27A"

SERIES = [  # label in CSV, legend, colour
    ("sigma_60000", "60 kcP (0.7 rpm)", "#3B7DDD"),
    ("sigma_10000", "10 kcP (4.3 rpm)", "#E0433A"),
    ("sigma_1000", "1 kcP (45 rpm)", "#F2B705"),
]


# ----------------------------------------------------------------------------- panel A pieces

def cup(cx, top, w=150, h=46):
    return (f'<path d="M{cx - w / 2},{top}V{top + h}H{cx + w / 2}V{top}" fill="#E9ECF0" stroke="{DARK}" stroke-width="3"/>'
            f'<rect x="{cx - w / 2 + 3}" y="{top + 14}" width="{w - 6}" height="{h - 17}" fill="{SAMPLE}"/>'
            f'<path d="M{cx - w / 2 + 3},{top + 14}H{cx + w / 2 - 3}" stroke="#E3B44E" stroke-width="2"/>')


def spindle(cx, cone_tip, opacity=1.0, head=True):
    """Viscometer head + shaft + 3-degree-style cone whose tip sits at y=cone_tip."""
    top = cone_tip - 190
    s = f'<g opacity="{opacity}">'
    if head:
        s += (f'<rect x="{cx - 62}" y="{top - 70}" width="124" height="96" rx="12" fill="#EEF0F3" stroke="{DARK}" stroke-width="3"/>'
              f'<rect x="{cx - 40}" y="{top - 50}" width="80" height="26" rx="4" fill="#9FB3C8"/>'
              f'<rect x="{cx - 30}" y="{top + 26}" width="60" height="34" rx="5" fill="{DARK}"/>')
    s += (f'<rect x="{cx - 6}" y="{top + 60}" width="12" height="{cone_tip - top - 92}" fill="#8E96A3"/>'
          f'<path d="M{cx - 58},{cone_tip - 32}H{cx + 58}L{cx},{cone_tip}Z" fill="#B7BEC8" stroke="{DARK}" stroke-width="3" stroke-linejoin="round"/>'
          "</g>")
    return s


def viscometer(cx, plate_y):
    """Bench viscometer: base, column, head, cone above a sample cup."""
    return (f'<rect x="{cx - 150}" y="{plate_y + 46}" width="300" height="34" rx="10" fill="{GRAY}" stroke="{DARK}" stroke-width="3"/>'
            f'<rect x="{cx + 92}" y="{plate_y - 330}" width="34" height="378" rx="6" fill="{GRAY}" stroke="{DARK}" stroke-width="3"/>'
            f'<rect x="{cx + 20}" y="{plate_y - 290}" width="80" height="26" fill="{GRAY}" stroke="{DARK}" stroke-width="3"/>'
            + cup(cx - 20, plate_y) + spindle(cx - 20, plate_y + 6))


def pipette(cx, tip_y):
    return (f'<rect x="{cx - 9}" y="{tip_y - 250}" width="18" height="34" rx="4" fill="{C["blue"]}"/>'
            f'<rect x="{cx - 16}" y="{tip_y - 216}" width="32" height="120" rx="10" fill="#DDE6F6" stroke="{DARK}" stroke-width="3"/>'
            f'<path d="M{cx - 12},{tip_y - 96}H{cx + 12}L{cx + 4},{tip_y}H{cx - 4}Z" fill="#F4F6F8" stroke="{DARK}" stroke-width="3" stroke-linejoin="round"/>'
            f'<path d="M{cx},{tip_y + 14}c-9,14 -9,26 0,26c9,0 9,-12 0,-26Z" fill="{SAMPLE}" stroke="#E3B44E" stroke-width="2"/>')


def wash_bottle(x, y):
    return (f'<rect x="{x}" y="{y}" width="74" height="120" rx="18" fill="#DFF0FA" stroke="{DARK}" stroke-width="3"/>'
            f'<path d="M{x + 25},{y}V{y - 22}H{x + 49}V{y}" fill="#DFF0FA" stroke="{DARK}" stroke-width="3"/>'
            f'<path d="M{x + 37},{y - 22}L{x - 20},{y - 60}" stroke="{DARK}" stroke-width="4" stroke-linecap="round"/>'
            + "".join(f'<circle cx="{x - 32 - 14 * i}" cy="{y - 58 + 11 * i + (i % 2) * 6}" r="{4.5 - 0.3 * i:.1f}" fill="#5AAEE0"/>'
                      for i in range(7)))


def panel_a() -> str:
    cv = Canvas(W, 760)
    band = "M60,0H1920A60,60 0 0 1 1980,60V640A60,60 0 0 1 1920,700H60A60,60 0 0 1 0,640V60A60,60 0 0 1 60,0Z"
    steps = [  # centre x, colour, title, bullets
        (250, "blue", "1. Load sample", ["Fill flat-bottom cup", "Fixed sample volume"]),
        (700, "green", "2. Initialize viscometer", ["Zero the gap by feel", "Set spindle speed"]),
        (1240, "purple", "3. Step the cone–plate gap", ["13 µm increments (33 → −3)",
                                                          "Record torque and viscosity"]),
        (1760, "teal", "4. Clean the cone", ["Wipe and rinse by hand", "before the next sample"]),
    ]
    for cx, col, title, bullets in steps:
        cv.node(f"s{cx}", cx, -999, 70, title, [], col, "gear")  # register title extents
    cv.body.clear()  # titles are re-drawn below without icon rings

    plate = 470
    art = [
        cup(250, plate) + pipette(250, plate - 70),
        viscometer(720, plate),
        "",
        wash_bottle(1840, plate - 110)
        + f'<path d="M1650,{plate + 40}H1760" stroke="{DARK}" stroke-width="3"/>'
        + spindle(1705, plate + 10, head=False)
        + f'<path d="M1668,{plate - 10}c10,-18 30,-20 44,-8c14,-12 34,-6 36,10c-8,14 -70,16 -80,-2Z" fill="{SAMPLE}" stroke="#E3B44E" stroke-width="2"/>',
    ]
    # Step 3: ghosted cone positions descending onto the sample.
    cup3 = 1400
    levels = [(1110, 260, "10 mm", 0.25), (1200, 330, "1 mm", 0.45), (1290, 400, "100 µm", 0.7),
              (cup3, plate + 6, "13 µm", 1.0)]
    s3 = cup(cup3, plate)
    for x, tip, lab, op in levels:
        s3 += spindle(x, tip, opacity=op, head=(op == 1.0))
        s3 += (f'<path d="M{1000},{tip}H{x - 8}" stroke="{DARK}" stroke-width="1.6" stroke-dasharray="5 5"/>'
               f'<text x="{992}" y="{tip + 7}" text-anchor="end" font-size="21" fill="{DARK}">{lab}</text>')
    art[2] = s3

    for (cx, col, title, bullets), a in zip(steps, art):
        cv.add(a)
        c = C[col]
        cv.add(f'<text x="{cx}" y="70" text-anchor="middle" font-size="30" font-weight="bold" fill="{c}">{title}</text>')
        for i, b in enumerate(bullets):
            cv.add(f'<text x="{cx}" y="{596 + i * 30}" text-anchor="middle" font-size="22" fill="{INK}">{b}</text>')

    for x0, x1 in ((420, 600), (905, 1060), (1510, 1640)):  # clear lane above the artwork
        cv.arrow(f"M{x0},200H{x1}", (x0, 200), (x1, 200), (x0, 200))

    pill = "Manual protocol: 37 heights per material · ≈ 4.5 h · operator-controlled gap"
    cv.add(f'<rect x="560" y="676" width="880" height="48" rx="24" fill="#FFFFFF" stroke="{ARROW}" stroke-width="2.5"/>'
           f'<text x="1000" y="708" text-anchor="middle" font-size="23" font-weight="bold" fill="{ARROW}">{pill}</text>')
    svg = cv.svg(band)
    return svg


# ----------------------------------------------------------------------------- panels B-D

def panels_bcd(csv_path: Path) -> str:
    df = pd.read_csv(csv_path, header=1)
    m = df.iloc[:, :7].copy()
    m.columns = ["label", "inc", "h", "rpm", "visc", "torque", "drag"]
    m["label"] = m["label"].ffill()
    m = m.dropna(subset=["inc"])

    plt.rcParams.update({"font.family": "Arial", "font.size": 15, "axes.linewidth": 1.2,
                         "xtick.major.width": 1.1, "ytick.major.width": 1.1, "svg.fonttype": "none"})
    fig, axes = plt.subplots(1, 3, figsize=(20, 6.2))
    specs = [("torque", "Torque T (%)", False, "B"), ("drag", "Rotational drag D = T/Ω", True, "C"),
             ("visc", "Viscosity (kcP)", True, "D")]
    for ax, (col, ylab, logy, tag) in zip(axes, specs):
        for lab, leg, colr in SERIES:
            g = m[m.label == lab]
            y = g[col] / (1000.0 if col == "visc" else 1.0)
            ax.plot(g.h, y, "o", ms=7, mfc=colr, mec="white", mew=0.8, color=colr, label=leg)
        if logy:
            ax.set_yscale("log")
        ax.set_xlabel("Height h (mm)", fontsize=18)
        ax.set_ylabel(ylab, fontsize=18)
        ax.grid(alpha=0.25, which="both")
        ax.text(-0.17, 1.04, tag, transform=ax.transAxes, fontsize=30, fontweight="bold", va="bottom")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].legend(frameon=False, fontsize=15, loc="upper right")
    axes[0].annotate("speed set per oil to\nkeep T within 30–57%", xy=(0.2, 36.5), xytext=(0.22, 47),
                     fontsize=14, color="#555", arrowprops=dict(arrowstyle="->", color="#777"))
    fig.tight_layout(w_pad=4)
    buf = io.StringIO()
    fig.savefig(buf, format="svg", transparent=True)
    return buf.getvalue()


def nest(svg: str, x, y, w, h) -> str:
    """Embed a full SVG document as a positioned nested <svg>."""
    svg = re.sub(r"<\?xml[^>]*\?>|<!DOCTYPE[^>]*>", "", svg, flags=re.S).strip()
    vb = re.search(r'viewBox="([^"]+)"', svg).group(1)
    inner = svg[svg.index(">", svg.index("<svg")) + 1: svg.rindex("</svg>")]
    return (f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="{vb}" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" preserveAspectRatio="xMidYMid meet">{inner}</svg>')


def main():
    csv_path = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent
    panel_a_png = Path(sys.argv[3]) if len(sys.argv) > 3 else None  # raster panel A (original BioRender artwork)
    bcd = panels_bcd(csv_path)
    if panel_a_png:
        import base64
        from PIL import Image
        w, h = Image.open(panel_a_png).size
        ah = round(2020 * h / w)
        uri = "data:image/png;base64," + base64.b64encode(panel_a_png.read_bytes()).decode()
        top = f'<image x="20" y="10" width="2020" height="{ah}" href="{uri}"/>'
    else:
        ah = 760
        top = '<text x="14" y="48" font-size="40" font-weight="bold">A</text>' + nest(panel_a(), 40, 10, 2020, 760)
    y_bcd = ah + 30
    H = y_bcd + 637
    doc = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W + 60}" '
           f'height="{H}" viewBox="0 0 {W + 60} {H}" font-family="Arial, Helvetica, sans-serif">'
           f'<rect width="{W + 60}" height="{H}" fill="#FFFFFF"/>'
           + top + nest(bcd, 20, y_bcd, W + 20, 627) + "</svg>")
    path = out / "Figure2_manual_v2.svg"
    path.write_text(doc, encoding="utf-8")
    print("wrote", path, "height", H)


if __name__ == "__main__":
    main()

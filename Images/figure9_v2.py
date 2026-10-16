"""Generate Figure 9: master flow curves (A), automated-viscometry landscape (B), closed-loop role (C).

Panel A re-uses the existing master flow-curve SVG; B is plotted from the benchmark values
quoted in the manuscript; C is drawn in the style of Figures 3 and 5.

Usage:  python Images/figure9_v2.py <existing Figure 9.svg> [out_dir]
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use("svg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).parent))
from figure2_v2 import nest  # noqa: E402
from workflow_figures_v2 import ARROW, C, Canvas  # noqa: E402

GREY = "#9AA3AE"
BLUE = C["blue"]

# name, min cP, max cP, output, error, colour  (values as quoted in the manuscript)
METHODS = [
    ("OT-2 dispense-rate proxy [ref46]", 1.5e3, 1.2e4, "single μ (Newtonian)", "6.5%", GREY),
    ("OT-2 + non-Newtonian extension [ref47]", 20, 2e4, "single apparent μ", "≈8%", GREY),
    ("Inverted-vial video + ML [ref49]", 10, 1e6, "single μ", "±15–25%", GREY),
    ("This work", 1, 1.25e5, "flow curve, n", "3.4%†", BLUE),
]


def panel_b(refs: dict[str, str]) -> str:
    plt.rcParams.update({"font.family": "Arial", "font.size": 19, "svg.fonttype": "none"})
    fig, ax = plt.subplots(figsize=(10.4, 6.9))
    n = len(METHODS)
    ax.add_patch(Rectangle((1e3, -0.6), 1e5 - 1e3, n + 0.2, color="#EEF3FC", zorder=0))
    ax.text(1e4, n - 0.22, "high-viscosity regime", ha="center", fontsize=17, color="#5A7BB5")
    for i, (name, lo, hi, out, err, col) in enumerate(reversed(METHODS)):
        y = i
        ours = col == BLUE
        ax.plot([lo, hi], [y, y], color=col, lw=18 if ours else 12, solid_capstyle="round", zorder=2)
        label = name
        for k, v in refs.items():
            label = label.replace(k, v)
        ax.text(lo, y + 0.3, label, fontsize=20, fontweight="bold" if ours else "normal", color="#1F1F1F")
        style = dict(fontsize=19, va="center", color=col if ours else "#444", fontweight="bold" if ours else "normal")
        ax.text(3e6, y, out, **style)
        ax.text(1.6e10, y, err, ha="right", **style)
    ax.text(3e6, n - 0.32, "Output", fontsize=19, fontweight="bold", color="#333")
    ax.text(1.6e10, n - 0.32, "Error", fontsize=19, fontweight="bold", color="#333", ha="right")
    ax.set_xscale("log")
    ax.set_xlim(0.5, 1.6e10)
    ax.set_ylim(-0.6, n - 0.1)
    ax.set_xticks([1, 1e1, 1e2, 1e3, 1e4, 1e5, 1e6])
    ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax.tick_params(labelsize=18)
    ax.set_yticks([])
    ax.set_xlabel("Viscosity range (cP)", fontsize=22, x=0.33)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_bounds(0.5, 2e6)
    ax.text(0.5, -1.45, "† mean absolute error on Newtonian calibration standards", fontsize=16, color="#555")
    fig.tight_layout()
    buf = io.StringIO()
    fig.savefig(buf, format="svg", transparent=True)
    return buf.getvalue()


def panel_c() -> str:
    import workflow_figures_v2 as wf
    from PIL import ImageFont

    saved = (wf.TITLE_PX, wf.BULLET_PX, wf.LINE_H, wf._bold)
    wf.TITLE_PX, wf.BULLET_PX, wf.LINE_H = 40, 29, 37
    wf._bold = ImageFont.truetype("arialbd.ttf", 40)
    try:
        cv = Canvas(2000, 480)
        band = "M60,0H1920A60,60 0 0 1 1980,60V400A60,60 0 0 1 1920,460H60A60,60 0 0 1 0,400V60A60,60 0 0 1 60,0Z"
        cv.add(f'<rect x="1000" y="14" width="580" height="330" rx="28" fill="#FFFFFF" stroke="{BLUE}" stroke-width="3"/>'
               f'<text x="1290" y="382" text-anchor="middle" font-size="28" font-weight="bold" fill="{BLUE}">'
               f"measurement layer delivered by this work</text>")
        nodes = [
            ("p", 255, "1. AI Planner", ["Bayesian optimization", "Active learning"], "cyan", "network"),
            ("f", 760, "2. Robotic Formulation", ["Dispense and blend", "a candidate batch"], "green", "flask"),
            ("r", 1290, "3. Autonomous Rheometry", ["Flow curve τ = Kγ̇ⁿ", "μ_{app}(γ̇) and regime",
                                                  "No operator-set gap"], "blue", "gauge"),
            ("m", 1775, "4. Model Update", ["Update surrogate", "Propose next batch"], "purple", "fit"),
        ]
        for key, cx, title, bullets, col, icon in nodes:
            cv.node(key, cx, 90, 200, title, bullets, col, icon)
        r = wf.ICON_R + 28
        for (_, x0, *_), (_, x1, *_) in zip(nodes, nodes[1:]):
            cv.arrow(f"M{x0 + r},90H{x1 - r}", (x0 + r, 90), (x1 - r, 90), (x0 + r, 90))
        cv.arrow("M1775,335V425Q1775,438 1762,438H268Q255,438 255,425V335", (1775, 335), (255, 337), (255, 355),
                 dashed=True, fade=False)
        cv.add('<rect x="330" y="420" width="470" height="36" fill="#EEF3FC"/>')
        cv.add(f'<text x="565" y="447" text-anchor="middle" font-size="25" font-style="italic" fill="{ARROW}">'
               "closed loop, no operator in the cycle</text>")
        return cv.svg(band)
    finally:
        wf.TITLE_PX, wf.BULLET_PX, wf.LINE_H, wf._bold = saved


def main():
    fig9 = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent
    refs = {"[ref46]": "[46]", "[ref47]": "[47]", "[ref49]": "[49]"}
    if len(sys.argv) > 3:  # optional renumbering, e.g. "46=42,47=43,49=45"
        for kv in sys.argv[3].split(","):
            k, v = kv.split("=")
            refs[f"[ref{k}]"] = f"[{v}]"
    a = fig9.read_text(encoding="utf-8")
    b = panel_b(refs)
    c = panel_c()
    W, H = 2060, 1270
    lab = '<text x="{x}" y="{y}" font-size="40" font-weight="bold">{t}</text>'
    doc = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" '
           f'height="{H}" viewBox="0 0 {W} {H}" font-family="Arial, Helvetica, sans-serif">'
           f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>'
           + nest(a, 30, 40, 820, 683) + lab.format(x=14, y=48, t="A")
           + nest(b, 880, 40, 1170, 666) + lab.format(x=870, y=48, t="B")
           + lab.format(x=14, y=790, t="C") + nest(c, 40, 770, 2010, 482) + "</svg>")
    path = out / "Figure9_flowcurves_v2.svg"
    path.write_text(doc, encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()

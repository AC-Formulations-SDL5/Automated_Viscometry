"""Generate Figure 3 (platform workflow) and Figure 5 (inference pipeline) as editable SVGs.

Serpentine-band style of the manuscript figures: light-blue band, dashed icon rings,
coloured step titles, bulleted details and fading blue arrows. Text is kept as live
<text> so the SVGs remain editable in Inkscape / Illustrator.

Usage:  python Images/workflow_figures_v2.py [out_dir]
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

from PIL import ImageFont

FONT = "Arial, Helvetica, sans-serif"
BAND = "#EEF3FC"
ARROW = "#3B7DDD"
TITLE_PX = 30
BULLET_PX = 21.5
LINE_H = 28
ICON_R = 62

C = {
    "blue": "#3B7DDD",
    "green": "#1E9E50",
    "orange": "#EE7B30",
    "purple": "#A1309B",
    "yellow": "#F2B705",
    "cyan": "#1C96D3",
    "teal": "#1D5C7E",
    "red": "#C00000",
    "dgreen": "#2E7D32",
    "gray": "#8C8C8C",
}

_bold = ImageFont.truetype("arialbd.ttf", TITLE_PX)


def _plain(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    return re.sub(r"[_^]\{(.+?)\}", r"\1", s)


def title_width(s: str) -> float:
    return _bold.getlength(_plain(s))


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rich(s: str, color: str) -> str:
    """**x** -> bold in step colour, _{x} -> subscript, ^{x} -> superscript."""
    out = []
    for tok in re.split(r"(\*\*.+?\*\*|_\{.+?\}|\^\{.+?\})", s):
        if not tok:
            continue
        if tok.startswith("**"):
            out.append(f'<tspan font-weight="bold" fill="{color}">{rich(tok[2:-2], color)}</tspan>')
        elif tok.startswith("_{"):
            out.append(f'<tspan baseline-shift="-18%" font-size="70%">{esc(tok[2:-1])}</tspan>')
        elif tok.startswith("^{"):
            out.append(f'<tspan baseline-shift="35%" font-size="70%">{esc(tok[2:-1])}</tspan>')
        else:
            out.append(esc(tok))
    return "".join(out)


# ----------------------------------------------------------------------------- icons
# Each icon is drawn in local coordinates (roughly +-32) around the ring centre.

def _gear():
    pts = []
    for i in range(16):
        r = 31 if i % 2 == 0 else 23
        for da in (-0.13, 0.13):
            a = i * math.pi / 8 + da
            pts.append(f"{r * math.cos(a):.1f},{r * math.sin(a):.1f}")
    return f'<polygon points="{" ".join(pts)}"/><circle r="10"/>'


ICONS = {
    "gear": _gear(),
    "target": '<circle r="26"/><circle r="15"/><circle r="4" class="f"/>'
              '<path d="M0,-36V-20M0,20V36M-36,0H-20M20,0H36"/>',
    "checklist": '<rect x="-21" y="-31" width="42" height="62" rx="2"/>'
                 + "".join(f'<path d="M-14,{y}l4,4l7,-8M2,{y + 1}H14"/>' for y in (-20, -6, 8, 22)),
    "stairs": '<path d="M-26,-26H-12V-12H2V2H16V16H30"/><path d="M-24,-6L-6,12"/>'
              '<path d="M-6,1V12H-17"/>',
    "gauge": '<path d="M-30,10A30,30 0 1 1 30,10"/>'
             + "".join(
                 f'<path d="M{24 * math.cos(a):.1f},{24 * math.sin(a):.1f}L{30 * math.cos(a):.1f},{30 * math.sin(a):.1f}"/>'
                 for a in [math.radians(d) for d in (200, 230, 260, 290, 320, 340)])
             + '<path d="M2,4L-17,-17"/><circle cx="2" cy="4" r="4"/>',
    "cradle": '<path d="M-30,-24H24M-26,-24V24M20,-24V24M-32,26H26"/>'
              '<path d="M-17,-24V12M-7,-24V12M3,-24V12M13,-24L28,4"/>'
              '<circle cx="-17" cy="16" r="5"/><circle cx="-7" cy="16" r="5"/>'
              '<circle cx="3" cy="16" r="5"/><circle cx="30" cy="8" r="5"/>',
    "descent": '<path d="M-22,-28H22L0,-4Z"/><path d="M-22,-2H22L0,22Z"/><path d="M-22,30H22"/>',
    "bullseye": '<circle cx="-4" cy="4" r="26"/><circle cx="-4" cy="4" r="16"/><circle cx="-4" cy="4" r="6"/>'
                '<path d="M-4,4L26,-26M18,-30L26,-26L30,-18"/>',
    "funnel": '<path d="M-28,-24H28L6,2V28L-6,20V2Z"/>',
    "shower": '<path d="M-24,30V-10A16,16 0 0 1 8,-10V-6"/><path d="M-10,8A18,14 0 0 1 26,8Z"/>'
              '<path d="M-6,16L-10,30M2,16L0,30M10,16L10,30M18,16L20,30"/>',
    "exit": '<path d="M-26,-30H4V-12M4,12V30H-26Z"/><path d="M-26,-30L-6,-22V24L-26,30"/>'
            '<path d="M2,0H30M22,-8L30,0L22,8"/>',
    "flask": '<path d="M-8,-20V-6L-24,24H24L8,-6V-20M-12,-20H12"/><path d="M-17,10H17"/>'
             '<circle cx="2" cy="-30" r="3"/><circle cx="10" cy="-38" r="4"/><circle cx="-4" cy="-40" r="2.5"/>',
    "scatter": '<path d="M-28,-28V26H30"/>'
               + "".join(f'<circle cx="{x}" cy="{y}" r="2.6" class="f"/>'
                         for x, y in ((-16, 14), (-8, 6), (0, 8), (6, -2), (14, -6), (20, -14))),
    "bell": '<path d="M-30,26H30"/><path d="M-28,24C-14,24 -10,-28 0,-28C10,-28 14,24 28,24"/>'
            '<path d="M0,-26V24" stroke-dasharray="4 4"/>',
    "fit": '<path d="M-28,-28V26H30"/><path d="M-20,18C-6,18 2,12 8,4L26,-18"/><path d="M14,-18H26V-6"/>',
    "abacus": '<rect x="-28" y="-26" width="56" height="52" rx="3"/><path d="M-28,-8H28"/>'
              + "".join(f'<path d="M{x},-26V26"/><rect x="{x - 6}" y="-21" width="12" height="8" rx="4"/>'
                        f'<rect x="{x - 6}" y="{y}" width="12" height="8" rx="4"/>'
                        for x, y in ((-14, 14), (0, -2), (14, 8))),
    "chip": '<rect x="-20" y="-20" width="40" height="40" rx="3"/><rect x="-11" y="-11" width="22" height="22"/>'
            + "".join(f'<path d="M{p},-20V-30M{p},20V30M-20,{p}H-30M20,{p}H30"/>' for p in (-12, -4, 4, 12)),
    "linear": '<path d="M-28,-28V26H30"/><path d="M-18,16L22,-22"/><path d="M8,-22H22V-8"/>',
    "curves": '<path d="M-28,-30V26H30M18,18L30,26L22,32"/><path d="M-22,-28C-14,2 0,16 26,20"/>'
              '<path d="M-20,20C0,14 14,0 22,-24M14,-18L22,-26L26,-16"/>',
    "hammer": '<path d="M-24,28L10,-8"/><path d="M2,-18L18,-34L34,-18L18,-2Z"/>'
              '<path d="M-36,32H-10M-30,32L-34,22M-22,32L-22,22M-16,32L-12,24"/>',
    "network": '<circle r="7"/>'
               + "".join(f'<path d="M{9 * math.cos(a):.1f},{9 * math.sin(a):.1f}L{22 * math.cos(a):.1f},{22 * math.sin(a):.1f}"/>'
                         f'<circle cx="{28 * math.cos(a):.1f}" cy="{28 * math.sin(a):.1f}" r="6"/>'
                         for a in [math.radians(d) for d in (-90, -30, 30, 90, 150, 210)]),
}


# ----------------------------------------------------------------------------- drawing

class Canvas:
    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.defs: list[str] = []
        self.body: list[str] = []
        self._gid = 0
        self.titles: dict[str, tuple[float, float, float]] = {}  # key -> (left, right, y)

    def add(self, s: str):
        self.body.append(s)

    def node(self, key, cx, cy, ty, title, bullets, color, icon, bx=None):
        """Icon ring at (cx, cy); title centred at cx on baseline ty; bullets below."""
        c = C[color]
        self.add(f'<g transform="translate({cx},{cy})">'
                 f'<circle r="{ICON_R}" fill="#FFFFFF" stroke="{c}" stroke-width="1.6" stroke-dasharray="6 5"/>'
                 f'<g fill="none" stroke="{c}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">'
                 f'{ICONS[icon]}</g></g>')
        w = title_width(title)
        self.titles[key] = (cx - w / 2, cx + w / 2, ty)
        self.add(f'<text x="{cx}" y="{ty}" text-anchor="middle" font-size="{TITLE_PX}" font-weight="bold" '
                 f'fill="{c}">{rich(title, c)}</text>')
        bx = cx - w / 2 + 8 if bx is None else bx
        for i, b in enumerate(bullets):
            y = ty + 36 + i * LINE_H
            if b.startswith("  "):  # continuation line, no bullet
                self.add(f'<text x="{bx + 26}" y="{y}" font-size="{BULLET_PX}" fill="#1F1F1F">{rich(b.strip(), c)}</text>')
                continue
            self.add(f'<text x="{bx}" y="{y}" font-size="{BULLET_PX}" fill="#1F1F1F">•</text>'
                     f'<text x="{bx + 26}" y="{y}" font-size="{BULLET_PX}" fill="#1F1F1F">{rich(b, c)}</text>')

    def disc(self, cx, cy, label):
        self.add(f'<circle cx="{cx}" cy="{cy}" r="96" fill="#FFFFFF"/>'
                 f'<text x="{cx}" y="{cy + 16}" text-anchor="middle" font-size="46" font-weight="bold" '
                 f'fill="{C["blue"]}">{label}</text>')

    def arrow(self, d, tail, head, prev, dashed=False, fade=True, head_on=True):
        """Path `d` from tail to head; `prev` is a point just before head (sets the arrowhead direction)."""
        self._gid += 1
        gid = f"g{self._gid}"
        if fade:
            self.defs.append(
                f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{tail[0]}" y1="{tail[1]}" '
                f'x2="{head[0]}" y2="{head[1]}"><stop offset="0" stop-color="{ARROW}" stop-opacity="0.05"/>'
                f'<stop offset="0.55" stop-color="{ARROW}" stop-opacity="1"/></linearGradient>')
            stroke = f"url(#{gid})"
        else:
            stroke = ARROW
        dash = ' stroke-dasharray="10 8"' if dashed else ""
        self.add(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="4.5" stroke-linecap="round"{dash}/>')
        if head_on:
            ang = math.atan2(head[1] - prev[1], head[0] - prev[0])
            L, Wd = 20, 10
            bx, by = head[0] - L * math.cos(ang), head[1] - L * math.sin(ang)
            px, py = -math.sin(ang) * Wd, math.cos(ang) * Wd
            self.add(f'<polygon points="{head[0] + 3 * math.cos(ang):.1f},{head[1] + 3 * math.sin(ang):.1f} '
                     f'{bx + px:.1f},{by + py:.1f} {bx - px:.1f},{by - py:.1f}" fill="{ARROW}"/>')

    def hflow(self, a, b, dy=-10, gap=22):
        """Straight arrow between the titles of steps a and b (direction inferred)."""
        la, ra, y = self.titles[a]
        lb, rb, _ = self.titles[b]
        y += dy
        if lb > ra:
            x0, x1 = ra + gap, lb - gap
        else:
            x0, x1 = la - gap, rb + gap
        self.arrow(f"M{x0:.1f},{y}H{x1:.1f}", (x0, y), (x1, y), (x0, y))

    def label(self, x, y, text, anchor="middle"):
        self.add(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="19" font-style="italic" '
                 f'fill="{ARROW}">{rich(text, ARROW)}</text>')

    def svg(self, band: str, slots: str = "") -> str:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" font-family="{FONT}">\n'
                f'<defs>{"".join(self.defs)}</defs>\n'
                f'<rect width="{self.w}" height="{self.h}" fill="#FFFFFF"/>\n'
                f'<g transform="translate(10,10)">\n<path d="{band}" fill="{BAND}"/>\n{slots}\n'
                + "\n".join(self.body) + "\n</g>\n</svg>\n")


# ----------------------------------------------------------------------------- Figure 3

def figure3() -> str:
    cv = Canvas(2020, 1150)
    # Three-row serpentine: rows 310 px thick, 100 px slots, semicircular turns.
    band = ("M155,0H1640A360,360 0 0 1 1640,720H360A50,50 0 0 0 360,820H1845"
            "A155,155 0 0 1 1845,1130H360A360,360 0 0 1 360,410H1640A50,50 0 0 0 1640,310H155"
            "A155,155 0 0 1 155,0Z")
    cv.disc(155, 155, "Start")
    cv.disc(1845, 975, "End")

    r1, r2, r3 = (82, 170), (487, 575), (890, 985)
    cv.node("1", 450, *r1, "1. System Initialization",
            ["CNC homing", "Viscometer initialization", "Washing-station initialization"], "blue", "gear")
    cv.node("2", 840, *r1, "2. Calibration",
            ["Safe height determination", "Spindle-floor reference heights", "Store per-cell calibration map"],
            "green", "target")
    cv.node("3", 1215, *r1, "3. Cell Selection",
            ["Select full/row/custom cells", "Assign RPM profiles"], "orange", "checklist")
    cv.node("4", 1640, *r1, "4. Automated Z-Descent",
            ["Move spindle above sample", "Incremental Z-step descent", "Standardized ~0.4 mm window"],
            "purple", "stairs")

    cv.node("5", 1545, *r2, "5. RPM Sweep and Torque",
            ["Apply rotational speeds", "Measure torque vs. time", "Compute drag D = T_{%}/Ω",
             "Live data streaming"], "yellow", "gauge")
    cv.node("6", 1015, *r2, "6. Physics-Constrained Feedback",
            ["Six drag-based diagnostics", "Confidence-weighted hit score", "Hit if score ≥ 0.8 for 3 frames",
             "Torque-overload protection"], "cyan", "cradle")
    cv.node("7A", 470, *r2, "7A. Continue Descent",
            ["No hit flagged", "Step to next Z increment"], "teal", "descent")

    cv.node("7B", 322, *r3, "7B. Hit-point Detected",
            ["Trim post-contact data", "End current cell"], "red", "bullseye")
    cv.node("8", 760, *r3, "8. Viscosity Evaluation",
            ["Regularized hyperbolic drag fit", "Physics-informed viscosity", "Power-law flow curve",
             "Data logging and export"], "blue", "funnel")
    cv.node("9", 1185, *r3, "9. Automated Washing",
            ["Detergent / water / IPA rinse", "Concurrent with CNC travel", "Cross-contamination prevention"],
            "dgreen", "shower")
    cv.node("10", 1565, *r3, "10. Move to Next Cell",
            ["Repeat automated cycle"], "gray", "exit")

    for a, b in (("1", "2"), ("2", "3"), ("3", "4"), ("5", "6"), ("6", "7A"),
                 ("7B", "8"), ("8", "9"), ("9", "10")):
        cv.hflow(a, b)
    cv.label((cv.titles["6"][0] + cv.titles["7A"][1]) / 2, 600, "no hit")

    # 4 -> 5 around the right-hand turn
    cv.arrow("M1880,290C1905,360 1895,420 1850,470", (1880, 290), (1850, 470), (1870, 452))
    # 7A -> 5 loop (next Z increment), routed through the white slot between rows 1 and 2
    cv.arrow("M470,422V385Q470,360 495,360H1520Q1545,360 1545,385V420", (470, 422), (1545, 420),
             (1545, 405), dashed=True, fade=False)
    cv.add(f'<rect x="845" y="346" width="350" height="28" fill="#FFFFFF"/>')
    cv.label(1020, 367, "repeat sweep at the next Z increment")
    # 6 -> 7B when the contact criteria are met
    cv.arrow("M820,712C760,790 560,830 395,872", (820, 712), (395, 872), (430, 862))
    cv.label(800, 768, "hit detected", anchor="start")
    return cv.svg(band)


# ----------------------------------------------------------------------------- Figure 5

def figure5() -> str:
    cv = Canvas(2020, 1560)
    band = ("M155,0H1640A360,360 0 0 1 2000,360V975A155,155 0 0 1 1845,1130H875V1230"
            "A155,155 0 0 1 875,1540H360A360,360 0 0 1 0,1180V770A360,360 0 0 1 360,410"
            "H1640A50,50 0 0 0 1640,310H155A155,155 0 0 1 155,0Z")
    w = "#FFFFFF"
    slots = (f'<rect x="310" y="720" width="435" height="100" rx="50" fill="{w}"/>'      # R2 | 7B lobe
             f'<rect x="1425" y="720" width="265" height="100" rx="50" fill="{w}"/>'     # R2 | 5B lobe
             f'<rect x="310" y="1130" width="800" height="100" rx="50" fill="{w}"/>'     # 7B lobe | R4
             f'<rect x="1055" y="770" width="55" height="400" rx="27.5" fill="{w}"/>'    # 7B | 5B notch
             f'<path d="M1055,975V1131H900A155,155 0 0 0 1055,975Z" fill="{w}"/>'
             f'<path d="M1110,975V1131H1265A155,155 0 0 1 1110,975Z" fill="{w}"/>')
    cv.disc(155, 155, "Start")
    cv.disc(875, 1385, "End")

    r1, r2, r3, r4 = (82, 170), (487, 575), (897, 990), (1305, 1395)
    cv.node("1", 450, *r1, "1. New Sample",
            ["Time series of (h, T, RPM)", "One or more RPM sweeps", "Unknown rheology"], "blue", "flask")
    cv.node("2", 840, *r1, "2. Preprocess",
            ["Trim post-contact data", "Re-zero h to its minimum", "One curve per RPM sweep",
             "Compute shear rate γ̇"], "green", "scatter")
    cv.node("3", 1215, *r1, "3. Build Drag Profile",
            ["Drag D = T_{%}/Ω", "Average replicates per height", "Single D(h) curve per RPM"],
            "orange", "bell")
    cv.node("4", 1655, *r1, "4. Hyperbola Fit (fixed h_{c}^{⋆})",
            ["D(h) = A/(h + h_{c}) + B", "Recover A for every RPM sweep", "Reject sweep if R^{2} < 0.7",
             "Use calibrated **h_{c}^{⋆}**"], "purple", "fit")

    cv.node("5A", 1550, *r2, "5A. Amplitude → Apparent Viscosity",
            ["Invert calibration: μ_{app} = (A/k)^{1/p}", "One μ_{app} per RPM sweep",
             "Use calibrated **k** and **p**"], "yellow", "abacus")
    cv.node("6", 1025, *r2, "6. Fit Power Law",
            ["Single RPM → Newtonian", "≥ 2 RPMs → fit ln A vs. ln γ̇"], "cyan", "chip")
    cv.node("7A", 493, *r2, "7A. Newtonian",
            ["Report μ_{app} as viscosity", "Flow index fixed at n = 1", "Generate rheology formula"],
            "teal", "linear")

    cv.node("7B", 492, *r3, "7B. Non-Newtonian",
            ["ln A = ln A_{0} + (n − 1) ln γ̇", "Recover n and consistency K",
             "μ_{app} as a function of γ̇"], "red", "curves")
    cv.node("5B", 1555, *r3, "5B. Torque → Shear Stress",
            ["Cone-plate conversion", "τ = c_{τ} T_{%} per RPM sweep", "Use calibrated **c_{τ}**"],
            "dgreen", "hammer")

    cv.node("8", 545, *r4, "8. Classify Rheology Regime",
            ["n > 1.05 → Shear-thickening", "0.95 ≤ n ≤ 1.05 → Newtonian",
             "n < 0.95 → Shear-thinning", "< 2 valid RPMs → Undetermined"], "blue", "network")

    for a, b in (("1", "2"), ("2", "3"), ("3", "4"), ("6", "7A")):
        cv.hflow(a, b)

    # 4 -> 5A and 4 -> 5B down the right-hand column
    y5 = r2[1] - 10
    l5a = cv.titles["5A"][1] + 22
    cv.arrow(f"M1915,285V{y5}H{l5a:.1f}", (1915, 285), (l5a, y5), (l5a + 10, y5))
    cv.arrow(f"M1915,{y5}V780C1915,870 1820,895 1640,897", (1915, y5), (1640, 897), (1660, 897), fade=False)
    # 5A -> 6, with 5B merging into the same arrow
    r6 = cv.titles["6"][1] + 22
    l5 = cv.titles["5A"][0] - 22
    cv.arrow(f"M{l5:.1f},{y5}H{r6:.1f}", (l5, y5), (r6, y5), (l5, y5))
    xm = 1240
    cv.arrow(f"M1478,900C1330,900 {xm},850 {xm},740V{y5 + 4}", (1478, 900), (xm, y5 + 4), (xm, y5 + 30),
             head_on=False)
    # 6 -> 7B (multi-RPM)
    r7b = cv.titles["7B"][1] + 22
    cv.arrow(f"M930,660C930,820 860,950 {r7b:.1f},978", (930, 660), (r7b, 978), (r7b + 20, 972))
    cv.label(cv.titles["6"][0] - 30, 600, "single RPM", anchor="end")
    cv.label(960, 790, "≥ 2 RPMs", anchor="start")
    # 7A / 7B -> 8 down the left-hand column
    l7a = cv.titles["7A"][0] - 22
    l7b = cv.titles["7B"][0] - 22
    l8 = cv.titles["8"][0] - 18
    cv.arrow(f"M{l7a:.1f},{y5}H200Q178,{y5} 178,{y5 + 22}V1250C178,1330 240,1378 {l8:.1f},1385",
             (l7a, y5), (l8, 1385), (l8 - 20, 1383), fade=False)
    cv.arrow(f"M{l7b:.1f},980H178", (l7b, 980), (178, 980), (190, 980), head_on=False)
    return cv.svg(band, slots)


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    out.mkdir(parents=True, exist_ok=True)
    (out / "Figure3_workflow_v2.svg").write_text(figure3(), encoding="utf-8")
    (out / "Figure5_pipeline_v2.svg").write_text(figure5(), encoding="utf-8")
    print("wrote", out / "Figure3_workflow_v2.svg", out / "Figure5_pipeline_v2.svg")


if __name__ == "__main__":
    main()

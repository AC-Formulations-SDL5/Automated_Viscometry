"""
Cone-and-plate viscometer physics: 5-step horizontal pipeline figure.

Panels (left -> right):
    1. Physics Overview          (raster PNG)
    2. Axisymmetric Analysis
    3. Velocity Profile
    4. Shear Stress Distribution
    5. Torque Generation

Output:  Images/physics_concept_figure.svg / .png
Run:     python Images/physics_concept_figure.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import (
    Arc,
    Circle,
    FancyArrowPatch,
    Polygon,
    Rectangle,
    Wedge,
)

# --------------------------------------------------------------------------- #
# Google Material style                                                       #
# --------------------------------------------------------------------------- #
plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Roboto", "Google Sans", "Product Sans",
                            "Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 16,
        "mathtext.fontset": "cm",
        "mathtext.default": "it",
        "axes.linewidth": 1.0,
        # Convert all text to vector paths in the SVG so math glyphs (alpha,
        # tau, omega, mu, integrals, etc.) render correctly even on systems
        # that don't have Computer Modern / STIX fonts installed.
        "svg.fonttype": "path",
    }
)

# Google Material palette
G_BLUE     = "#4285F4"
G_BLUE_DK  = "#1A73E8"
G_BLUE_LT  = "#D2E3FC"
G_RED      = "#EA4335"
G_RED_LT   = "#FCE8E6"
G_GREY_900 = "#202124"
G_GREY_700 = "#5F6368"
G_GREY_300 = "#DADCE0"
G_GREY_100 = "#F1F3F4"

ARROW_C = G_GREY_700
TEXT_C  = G_GREY_900
AXIS_C  = G_GREY_700

# Font sizes (centralized so easy to bump)
FS_TITLE  = 25
FS_EQ     = 20
FS_LABEL  = 20
FS_AXIS   = 20
FS_NOTE   = 16

HERE = Path(__file__).parent
PHYSICS_PNG = HERE / "physics_overview.png"
OUT_SVG = HERE / "physics_concept_figure.svg"


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #
def panel_title(ax, text, y=0.95):
    ax.text(
        0.5, y, text,
        transform=ax.transAxes,
        ha="center", va="bottom",
        fontsize=FS_TITLE, color=TEXT_C,
    )


def caption(ax, text, y=-0.05):
    ax.text(
        0.5, y, text,
        transform=ax.transAxes,
        ha="center", va="top",
        fontsize=FS_EQ + 2, color=TEXT_C,
    )


def clean(ax):
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])


def add_flow_arrow(fig, xy_from, xy_to, color=ARROW_C, lw=2.6, rad=0.0):
    arr = FancyArrowPatch(
        xy_from, xy_to,
        transform=fig.transFigure,
        arrowstyle="-|>", mutation_scale=28,
        color=color, lw=lw,
        connectionstyle=f"arc3,rad={rad}",
        clip_on=False,
    )
    fig.patches.append(arr)


def axis_arrow(ax, xy_from, xy_to):
    ax.annotate("", xy=xy_to, xytext=xy_from,
                arrowprops=dict(arrowstyle="->", color=AXIS_C, lw=1.4))


# --------------------------------------------------------------------------- #
# Panel 1 - Physics Overview                                                  #
# --------------------------------------------------------------------------- #
def draw_overview(ax):
    """2-D side-view schematic of the cone-and-plate apparatus.

    A small-angle cone (apex pointing down) rotates above a stationary
    flat plate; the wedge-shaped gap between the cone bottom and the
    plate is filled with the test liquid.  Drawn in Google Material style.
    """
    clean(ax)
    # Same axes window as panels 2 & 3 so all diagrams sit at a consistent
    # height (top-aligned, horizontally centered).
    ax.set_xlim(-0.13, 1.13)
    ax.set_ylim(-0.18, 0.72)

    # ------- Geometry (schematic; angle exaggerated for clarity) -------
    plate_y = 0.00
    h       = 0.05            # central gap (apex - plate)
    R       = 0.42            # cone radius (half-width)
    xc      = 0.50            # horizontal centre
    alpha   = np.deg2rad(16)  # cone half-angle (exaggerated)
    H_R     = h + R * np.tan(alpha)   # gap at edge
    body_h  = 0.16            # cone tool body thickness
    cone_top = plate_y + H_R + body_h

    # ------- Stationary bottom plate (hatched) -------
    plate_h = 0.05
    ax.add_patch(Rectangle(
        (xc - R - 0.18, plate_y - plate_h),
        2 * R + 0.36, plate_h,
        facecolor=G_GREY_300, edgecolor=G_GREY_700,
        lw=1.0, hatch="///", zorder=1,
    ))

    # ------- Liquid domain (wedge-shaped gap) -------
    liquid_poly = [
        [xc - R, plate_y + H_R],
        [xc - R, plate_y],
        [xc + R, plate_y],
        [xc + R, plate_y + H_R],
        [xc,     plate_y + h],
    ]
    ax.add_patch(Polygon(
        liquid_poly, closed=True,
        facecolor=G_BLUE_LT, edgecolor=G_BLUE, lw=1.4,
        alpha=0.85, zorder=2,
    ))

    # ------- Cone tool body (V-shaped underside) -------
    cone_poly = [
        [xc - R, cone_top],
        [xc + R, cone_top],
        [xc + R, plate_y + H_R],
        [xc,     plate_y + h],
        [xc - R, plate_y + H_R],
    ]
    ax.add_patch(Polygon(
        cone_poly, closed=True,
        facecolor=G_GREY_300, edgecolor=G_GREY_900, lw=2.0,
        zorder=3,
    ))

    # ------- Drive shaft -------
    shaft_w = 0.07
    shaft_h = 0.10
    ax.add_patch(Rectangle(
        (xc - shaft_w / 2, cone_top),
        shaft_w, shaft_h,
        facecolor=G_GREY_300, edgecolor=G_GREY_900, lw=1.6,
        zorder=4,
    ))

    # ------- Rotation arrow (omega) above the shaft -------
    # Ellipse (flattened circle) suggests rotation about the vertical
    # z-axis viewed in perspective.
    arc_cy = cone_top + shaft_h + 0.05
    arc_a  = 0.095          # horizontal semi-axis (wider)
    arc_b  = 0.038          # vertical semi-axis (squashed)
    ax.add_patch(Arc(
        (xc, arc_cy), 2 * arc_a, 2 * arc_b,
        theta1=20, theta2=320,
        color=G_BLUE_DK, lw=2.2, zorder=5,
    ))
    # arrow-head at the open end of the arc (theta = 20 deg)
    a_tip  = np.deg2rad(15)
    a_tail = np.deg2rad(35)
    ax.annotate(
        "",
        xy=(xc + arc_a * np.cos(a_tip),  arc_cy + arc_b * np.sin(a_tip)),
        xytext=(xc + arc_a * np.cos(a_tail), arc_cy + arc_b * np.sin(a_tail)),
        arrowprops=dict(arrowstyle="-|>", color=G_BLUE_DK,
                        lw=2.0, mutation_scale=18),
        zorder=6,
    )
    ax.text(xc + arc_a + 0.04, arc_cy, r"$\omega$",
            fontsize=FS_LABEL + 4, color=G_BLUE_DK,
            va="center", fontweight="bold")

    # ------- Labels with leader lines -------
    ax.annotate(
        "Cone",
        xy=(xc + R * 0.55, cone_top - body_h * 0.5),
        xytext=(xc -0.075, cone_top - body_h * 0.4),
        fontsize=FS_NOTE+4, color=TEXT_C, va="center",
    )
    ax.annotate(
        "Liquid sample",
        xy=(xc - R * 0.45, plate_y + h * 0.55),
        xytext=(xc - R - 0.20, plate_y + 0.08),
        fontsize=FS_NOTE+4, color=G_BLUE_DK, va="center"
    )
    ax.text(xc, plate_y - plate_h - 0.04, "Stationary plate",
            ha="center", va="top",
            fontsize=FS_NOTE+4, color=G_GREY_700)

    panel_title(ax, "Physics Overview")
    caption(ax,
            "Cone-and-plate geometry\n"
            r"with rotation rate $\omega$")


# --------------------------------------------------------------------------- #
# Panel 2 - Axisymmetric Analysis                                             #
# --------------------------------------------------------------------------- #
def draw_axisymmetric(ax):
    clean(ax)
    # Top-aligned + horizontally centered limits.
    ax.set_xlim(-0.13, 1.13)
    ax.set_ylim(-0.18, 0.72)

    h = 0.10
    R = 0.95
    alpha = np.deg2rad(22)
    H_R = h + R * np.tan(alpha)
    z_top = H_R + 0.18

    axis_arrow(ax, (0, 0), (1.10, 0))
    axis_arrow(ax, (0, 0), (0, z_top))
    ax.text(1.13, -0.02, "$r$", fontsize=FS_AXIS, va="top", color=TEXT_C)
    ax.text(-0.05, z_top, "$z$",
            fontsize=FS_AXIS, ha="right", color=TEXT_C)
    ax.text(-0.04, -0.04, "0",
            fontsize=FS_NOTE, ha="right", va="top", color=TEXT_C)

    ax.add_patch(Polygon(
        [[0, 0], [R, 0], [R, H_R], [0, h]],
        facecolor=G_BLUE_LT, edgecolor=G_BLUE, lw=1.4, alpha=0.9,
    ))
    ax.add_patch(Rectangle((0, -0.05), R, 0.05,
                           facecolor=G_GREY_300, edgecolor=G_GREY_700,
                           lw=0.9, hatch="///"))

    ax.plot([0, R], [h, H_R], color=G_GREY_900, lw=2.6)
    ang_deg = np.rad2deg(np.arctan2(H_R - h, R - 0))

    ax.text(R * 0.50, h + R * 0.50 * np.tan(alpha) + 0.06,
            "Cone surface", color=G_GREY_900,
            fontsize=FS_NOTE+4, rotation=ang_deg+5)


    ax.annotate("", xy=(0.0, h), xytext=(0.0, 0),
                arrowprops=dict(arrowstyle="<->", color=G_RED, lw=1.4))
    ax.text(0.03, h / 2, "$h$",
            color=G_RED, fontsize=FS_LABEL+4, va="center")

    ax.add_patch(Wedge((0, h), 0.24, 0, np.rad2deg(alpha),
                       facecolor="none", edgecolor=G_BLUE_DK, lw=1.6))
    ax.text(0.27, h + 0.05, r"$\alpha$",
            color=G_BLUE_DK, fontsize=FS_LABEL + 4, fontweight="bold")

    ax.annotate("", xy=(R, H_R), xytext=(R, 0),
                arrowprops=dict(arrowstyle="<->", color=G_RED, lw=1.4))
    ax.text(R + 0.03, H_R / 2, "$H(r)$",
            color=G_RED, fontsize=FS_LABEL+4, va="center")

    ax.text(R, -0.08, "$R$",
            fontsize=FS_AXIS, ha="center", va="top", color=TEXT_C)
    ax.text(R * 0.40, h + 0.05, "Liquid domain",
            fontsize=FS_NOTE+4, color=G_BLUE_DK, style="italic")

    panel_title(ax, "Axisymmetric Analysis")
    caption(ax,
            "Local gap thickness:\n"
            r"$H(r) = h + r\,\tan\alpha$")


# --------------------------------------------------------------------------- #
# Panel 3 - Velocity Profile                                                  #
# --------------------------------------------------------------------------- #
def draw_velocity(ax):
    clean(ax)
    # Top-aligned + horizontally centered limits.
    ax.set_xlim(-0.13, 1.27)
    ax.set_ylim(-0.25, 0.72)

    h = 0.10
    R = 0.95
    alpha = np.deg2rad(22)
    H_R = h + R * np.tan(alpha)
    z_top = H_R + 0.18

    axis_arrow(ax, (0, 0), (1.18, 0))
    axis_arrow(ax, (0, 0), (0, z_top))
    ax.text(1.20, -0.02, "$r$", fontsize=FS_AXIS, va="top", color=TEXT_C)
    ax.text(-0.05, z_top, "$z$",
            fontsize=FS_AXIS, ha="right", color=TEXT_C)
    ax.text(-0.04, -0.04, "0",
            fontsize=FS_NOTE, ha="right", va="top", color=TEXT_C)

    ax.add_patch(Rectangle((0, -0.05), R, 0.05,
                           facecolor=G_GREY_300, edgecolor=G_GREY_700,
                           lw=0.9, hatch="///"))
    ax.add_patch(Polygon(
        [[0, 0], [R, 0], [R, H_R], [0, h]],
        facecolor=G_BLUE_LT, edgecolor=G_BLUE, lw=1.1, alpha=0.5,
    ))
    ax.plot([0, R], [h, H_R], color=G_GREY_900, lw=2.6)

    # cone-surface label, rotated parallel to the cone line in data coords
    mid_x = R * 0.50
    mid_y = h + mid_x * np.tan(alpha)
    ang_deg = np.rad2deg(np.arctan2(H_R - h, R - 0))
    ax.text(mid_x, mid_y + 0.04,
            r"Velocity $= \omega\,r$",
            color=G_GREY_900, fontsize=FS_NOTE+4,
            rotation=ang_deg,
            rotation_mode="anchor",
            transform_rotates_text=True,
            ha="center", va="bottom")
    ax.text(0.04, -0.16,
            r"Bottom plate (velocity $= 0$)",
            color=G_GREY_900, fontsize=FS_NOTE+4)

    # Velocity is azimuthal (out of the r-z plane, +theta direction).  We
    # use the standard convention "circle-with-dot" to indicate flow coming
    # out of the page; the marker size grows linearly with z (zero at the
    # bottom plate, maximum = omega*r at the cone surface).
    n_stations = 4
    r_stations = np.linspace(0.20, R - 0.05, n_stations)
    n_markers = 5
    size_max = 220.0   # marker area at z = H(r), r = R
    for r0 in r_stations:
        H_r = h + r0 * np.tan(alpha)
        z_vals = np.linspace(0.10 * H_r, H_r, n_markers)
        for z in z_vals:
            mag = (r0 / R) * (z / H_r)        # u_theta normalised
            s = max(20.0, mag * size_max)
            # outer ring
            ax.scatter([r0], [z], s=s, facecolors="white",
                       edgecolors=G_BLUE_DK, linewidths=1.4, zorder=4)
            # inner dot (out-of-page)
            ax.scatter([r0], [z], s=s * 0.18, color=G_BLUE_DK, zorder=5)

    # H(r) label at right edge
    ax.annotate("", xy=(R + 0.05, H_R), xytext=(R + 0.05, 0),
                arrowprops=dict(arrowstyle="<->", color=G_RED, lw=1.4))
    ax.text(R + 0.08, H_R / 2, "$H(r)$",
            color=G_RED, fontsize=FS_LABEL, va="center")

    # explanatory note - velocity is perpendicular to r-z plane.
    # Place it ABOVE the cone surface and connect it with an arrow to one
    # of the out-of-page markers so the symbol meaning is unambiguous.
    note_xy = (0.34, z_top - 0.04)
    ax.text(note_xy[0], note_xy[1],
            r"$\odot\;u_\theta$  (out of $r$-$z$ plane)",
            color=G_BLUE_DK, fontsize=FS_NOTE+4, style="italic",
            ha="left", va="top")
    # marker we point to: middle station, top of gap
    r_pick = r_stations[1]
    z_pick = h + r_pick * np.tan(alpha)
    ax.annotate("", xy=(r_pick, z_pick),
                xytext=(note_xy[0] + 0.02, note_xy[1] - 0.05),
                arrowprops=dict(arrowstyle="->", color=G_BLUE_DK,
                                lw=1.2, shrinkA=2, shrinkB=4),
                zorder=6)

    panel_title(ax, "Velocity Profile")
    caption(ax,
            "Velocity Profile:\n"
            r"$u_\theta(r,z) = \omega\,r\;\dfrac{z}{H(r)}$",
            y=-0.05)

# --------------------------------------------------------------------------- #
# Panel 4 - Shear Stress Distribution                                         #
# --------------------------------------------------------------------------- #
def draw_shear(ax):
    clean(ax)
    # Top-aligned + horizontally centered limits.  Content (curve + axes)
    # spans roughly x in [-0.04, 0.90] and y in [-0.04, 0.94]; we pick lims
    # so its midpoint sits at the axes midpoint and the top of the curve
    # is near the top of the axes box.
    ax.set_xlim(-0.20, 1.10)
    ax.set_ylim(-0.25, 1.05)

    R_max = 0.78
    tau_max = 0.78
    axis_arrow(ax, (0, 0), (R_max + 0.10, 0))
    axis_arrow(ax, (0, 0), (0, tau_max + 0.13))
    ax.text(R_max + 0.12, -0.02, "$R$",
            fontsize=FS_AXIS, va="top", color=TEXT_C)
    ax.text(-0.04, tau_max + 0.16, r"$\tau(r)$",
            fontsize=FS_AXIS, ha="right", color=TEXT_C)
    ax.text(-0.03, -0.04, "0",
            fontsize=FS_NOTE, ha="right", va="top", color=TEXT_C)

    h = 0.05
    alpha = np.deg2rad(20)
    r = np.linspace(0, R_max, 200)
    tau = r / (h + r * np.tan(alpha))
    tau = tau / tau.max() * tau_max
    ax.plot(r, tau, color=G_RED, lw=3.0)
    ax.fill_between(r, 0, tau, color=G_RED, alpha=0.10)

    panel_title(ax, "Shear Stress Distribution")
    caption(ax,
            "Shear Stress:\n"
            r"$\tau(r) = \mu\,\dfrac{\omega\,r}{H(r)}$")


# --------------------------------------------------------------------------- #
# Panel 5 - Torque Generation                                                 #
# --------------------------------------------------------------------------- #
def draw_torque(ax):
    clean(ax)
    # Aspect ratio of the panel slot (width/height in fig coords) is ~1.06,
    # so set xlim/ylim manually with a matching span so the disk stays round
    # WITHOUT calling set_aspect('equal') (which would shrink the axes box).
    ax.set_xlim(-1.485, 1.485)
    ax.set_ylim(-1.70, 1.10)

    # Scale factor to shrink the disk (frees room for the equation block).
    s = 0.55
    # Push the disk up to the TOP of the panel so it lines up with the
    # diagrams in the other panels.
    disk_cy = 0.15
    disk_R = 1.0 * s
    ring_outer = 0.78 * s
    ring_inner = 0.62 * s

    # disk
    ax.add_patch(Circle((0, disk_cy), disk_R, facecolor=G_GREY_100,
                        edgecolor=G_BLUE_DK, lw=1.8))

    # annular ring
    theta = np.linspace(0, 2 * np.pi, 200)
    ax.fill(
        np.concatenate([ring_outer * np.cos(theta),
                        ring_inner * np.cos(theta[::-1])]),
        np.concatenate([ring_outer * np.sin(theta) + disk_cy,
                        ring_inner * np.sin(theta[::-1]) + disk_cy]),
        color=G_BLUE, alpha=0.45, edgecolor=G_BLUE_DK, lw=1.2,
    )

    # r: arrow from origin into the inner region (with arrow head)
    ang_r = np.pi / 6
    r_end = (ring_inner * 0.95 * np.cos(ang_r),
             ring_inner * 0.95 * np.sin(ang_r) + disk_cy)
    ax.annotate("", xy=r_end, xytext=(0, disk_cy),
                arrowprops=dict(arrowstyle="-|>", color=G_GREY_900,
                                lw=1.8, mutation_scale=22),
                zorder=5)
    ax.text(0.36 * s * np.cos(ang_r) - 0.07,
            0.36 * s * np.sin(ang_r) + disk_cy + 0.05,
            "$r$", fontsize=FS_LABEL+4, color=TEXT_C, zorder=6)

    # r+dr: plain line from origin all the way to the outer circle (wider angle)
    ang_rdr = ang_r + 0.60
    ax.plot([0, disk_R * np.cos(ang_rdr)],
            [disk_cy, disk_R * np.sin(ang_rdr) + disk_cy],
            color=G_GREY_900, lw=1.6, zorder=5)
    ax.text(disk_R * np.cos(ang_rdr) + 0.02,
            disk_R * np.sin(ang_rdr) + disk_cy + 0.04,
            "$r+dr$", fontsize=FS_NOTE+4, color=TEXT_C, zorder=6)

    ax.text(0, disk_cy - 1.5*disk_R - 0.10, "Top view", ha="center",
            fontsize=FS_NOTE+4, style="italic", color=G_GREY_700)

    panel_title(ax, "Torque Generation")
    # Render the LAST equation as a regular caption so it's perfectly
    # in-line with the single-line captions in the other panels.  Stack
    # the first three labelled equations directly above it.
    last_line = (
        r"Total Torque:   $T = 2\pi\mu\omega"
        r"\int_{0}^{R}\dfrac{r^{3}}{h + r\tan\alpha}\,dr$"
    )
    caption(ax, last_line)

    first_three = (
        r"Area of Ring:   $dA = 2\pi\,r\,dr$"           "\n"
        r"Shear Force on Ring:   $dF = \tau(r)\,dA$"    "\n"
        r"Torque Contribution:   $dT = r\,dF$"
    )
    # Anchor BOTTOM of the 3-line block one caption-line-height above the
    # caption's TOP (= y = -0.05 in transAxes), in points so it's exact
    # regardless of figure size.
    from matplotlib.transforms import offset_copy
    fs_cap = FS_EQ + 1  # caption() uses this size
    line_h_pt = 1.1 * fs_cap
    trans = offset_copy(ax.transAxes, fig=ax.figure,
                        x=0, y=line_h_pt, units="points")
    ax.text(0.5, -0.0, first_three, transform=trans,
            ha="center", va="bottom",
            fontsize=fs_cap, color=TEXT_C, linespacing=1.4)


# --------------------------------------------------------------------------- #
# Compose                                                                     #
# --------------------------------------------------------------------------- #
def build_figure() -> Path:
    # 5 panels in a single horizontal row.
    fig = plt.figure(figsize=(28.0, 8.5), facecolor="white")

    # Equal-width slots; small interior margin for arrows.
    n = 5
    left_margin = 0.025
    right_margin = 0.015
    gap = 0.018
    total_gap = gap * (n - 1)
    panel_w = (1.0 - left_margin - right_margin - total_gap) / n
    bottom = 0.32
    height = 0.55

    axes = []
    for i in range(n):
        left = left_margin + i * (panel_w + gap)
        axes.append(fig.add_axes([left, bottom, panel_w, height]))

    draw_overview(axes[0])
    draw_axisymmetric(axes[1])
    draw_velocity(axes[2])
    draw_shear(axes[3])
    draw_torque(axes[4])

    # Flow arrows between adjacent panels (figure coords)
    arrow_y = bottom + height / 2
    for i in range(n - 1):
        x_from = left_margin + (i + 1) * panel_w + i * gap + gap * 0.10
        x_to   = x_from + gap * 0.80
        add_flow_arrow(fig, (x_from, arrow_y), (x_to, arrow_y))

    fig.savefig(OUT_SVG, format="svg", bbox_inches="tight",
                facecolor="white")
    fig.savefig(OUT_SVG.with_suffix(".png"), format="png",
                dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return OUT_SVG


if __name__ == "__main__":
    out = build_figure()
    print(f"Wrote {out}")

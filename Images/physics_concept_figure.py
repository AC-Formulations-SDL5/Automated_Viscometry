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
    Ellipse,
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
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 16,
        # Keep formulas (mathtext) in Computer Modern italic — only regular
        # text uses Arial.
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
G_GREEN    = "#34A853"  # Google Material green
G_ORANGE   = "#FFA500"  # Google Material orange

ARROW_C = G_GREY_700
TEXT_C  = G_GREY_900
AXIS_C  = G_GREY_700

# Font sizes (centralized so easy to bump)
FS_TITLE  = 32
FS_EQ     = 26
FS_LABEL  = 26
FS_AXIS   = 26
FS_NOTE   = 22

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
def draw_overview(
    ax,
    *,
    show_title: bool = True,
    show_caption: bool = True,
    cone_label_position: str = "left",      # "left" or "top"
    plate_label_offset_below: float = 0.04,  # extra distance below plate bottom
    h_dimension_style: str = "inline",       # "inline" or "left_extension"
):
    """Pseudo-3-D perspective schematic of the cone-and-plate viscometer.

    A small-angle cone (apex pointing down) rotates about the vertical
    z-axis above a stationary circular plate.  The wedge-shaped gap
    between the cone underside and the plate is filled with the test
    liquid.  Cone angle is exaggerated for visual clarity; tangential
    velocity vectors at the rim indicate the rotation direction, and
    the cone half-angle alpha and disk radius R are annotated.

    Parameters
    ----------
    show_title, show_caption : bool
        Toggle the "Physics Overview" title and the equation caption.
    cone_label_position : {"left", "top"}
        Place the "Cone" label to the left of the body or on top of the
        visible top cap disk.
    plate_label_offset_below : float
        Extra vertical offset below the plate's lowest visible edge for
        the "Stationary plate" label.
    h_dimension_style : {"inline", "left_extension"}
        "inline" draws the h double-arrow at the axis with the label
        beside it; "left_extension" draws horizontal extension lines
        leftward from the cone tip and the plate centre and places the
        arrow and label between them (engineering-drawing style).
    """
    clean(ax)
    # Match the axes window used by panels 2 & 3 so all sub-figures
    # sit at a consistent height.
    ax.set_xlim(-0.13, 1.13)
    ax.set_ylim(-0.18, 0.72)

    xc = 0.50

    # ------- Geometry (perspective; angle exaggerated) -------
    plate_top_y  = 0.07
    plate_thick  = 0.035
    plate_rx     = 0.50
    plate_ry     = 0.10            # perspective squash of circular plate

    apex_y       = plate_top_y + 0.075  # cone apex raised to expose the gap
    cone_top_y   = 0.40
    cone_rx      = 0.38
    cone_ry      = 0.080           # perspective squash of cone top disk

    shaft_rx     = 0.120  # was 0.060
    shaft_ry     = 0.028  # was 0.014
    shaft_h      = 0.13

    # ------- Stationary plate (disk in perspective) -------
    plate_bot_y = plate_top_y - plate_thick
    theta_front = np.linspace(0.0, -np.pi, 80)   # front (lower) arc
    top_arc = np.array([
        (xc + plate_rx * np.cos(t), plate_top_y + plate_ry * np.sin(t))
        for t in theta_front
    ])
    bot_arc = np.array([
        (xc + plate_rx * np.cos(t), plate_bot_y + plate_ry * np.sin(t))
        for t in theta_front
    ])
    plate_side = np.vstack([top_arc, bot_arc[::-1]])
    ax.add_patch(Polygon(
        plate_side, closed=True,
        facecolor=G_GREY_300, edgecolor=G_GREY_700, lw=1.2, zorder=1,
    ))
    # Plate top: radial gradient darkening toward the axis of rotation
    # (light grey at the rim -> dark grey at r = 0).
    n_grad = 32
    c_outer = np.array([241, 243, 244]) / 255.0   # G_GREY_100
    c_inner = np.array([ 80,  83,  88]) / 255.0   # slightly darker than G_GREY_700
    for i in range(n_grad):
        frac  = i / (n_grad - 1)        # 0 = outermost, 1 = centre
        scale = 1.0 - frac * 0.97       # keep a tiny non-zero core
        rx_i  = plate_rx * scale
        ry_i  = plate_ry * scale
        t     = frac ** 0.85            # mild nonlinear darkening
        color = tuple(c_outer + (c_inner - c_outer) * t)
        ax.add_patch(Ellipse(
            (xc, plate_top_y), 2 * rx_i, 2 * ry_i,
            facecolor=color, edgecolor="none",
            zorder=2.0 + i * 0.001,
        ))
    # Outer rim outline of the plate top
    ax.add_patch(Ellipse(
        (xc, plate_top_y), 2 * plate_rx, 2 * plate_ry,
        facecolor="none", edgecolor=G_GREY_700, lw=1.2, zorder=2.4,
    ))

    # ------- Liquid domain: transparent cylinder enclosing the cone -------
    # Bounding cylindrical region from the plate up to the cone's top disk.
    # Drawn in two halves so the back wall sits behind the cone and the
    # front wall sits in front of it, giving a glass-cylinder appearance.
    cyl_rx = cone_rx + 0.010
    cyl_ry = cone_ry + 0.006
    cyl_top_y = cone_top_y
    cyl_bot_y = plate_top_y

    # Back half (theta in [0, pi])
    back_t = np.linspace(0.0, np.pi, 80)
    back_top = np.array([
        (xc + cyl_rx * np.cos(t), cyl_top_y + cyl_ry * np.sin(t)) for t in back_t
    ])
    back_bot = np.array([
        (xc + cyl_rx * np.cos(t), cyl_bot_y + cyl_ry * np.sin(t)) for t in back_t
    ])
    ax.add_patch(Polygon(
        np.vstack([back_top, back_bot[::-1]]), closed=True,
        facecolor=G_BLUE_LT, edgecolor="none", alpha=0.22, zorder=2.5,
    ))
    # Back edges (dashed = hidden in 3-D)
    ax.add_patch(Arc(
        (xc, cyl_top_y), 2 * cyl_rx, 2 * cyl_ry,
        theta1=0, theta2=180, color=G_BLUE, lw=0.9, ls="--",
        alpha=0.7, zorder=2.6,
    ))
    ax.add_patch(Arc(
        (xc, cyl_bot_y), 2 * cyl_rx, 2 * cyl_ry,
        theta1=0, theta2=180, color=G_BLUE, lw=0.9, ls="--",
        alpha=0.7, zorder=2.6,
    ))

    # Front half (theta in [-pi, 0]) — drawn ABOVE the cone in z-order
    front_t = np.linspace(0.0, -np.pi, 80)
    front_top = np.array([
        (xc + cyl_rx * np.cos(t), cyl_top_y + cyl_ry * np.sin(t)) for t in front_t
    ])
    front_bot = np.array([
        (xc + cyl_rx * np.cos(t), cyl_bot_y + cyl_ry * np.sin(t)) for t in front_t
    ])
    ax.add_patch(Polygon(
        np.vstack([front_top, front_bot[::-1]]), closed=True,
        facecolor=G_BLUE_LT, edgecolor="none", alpha=0.28, zorder=6.4,
    ))
    # Front edges (solid)
    ax.add_patch(Arc(
        (xc, cyl_top_y), 2 * cyl_rx, 2 * cyl_ry,
        theta1=180, theta2=360, color=G_BLUE, lw=1.2,
        alpha=0.85, zorder=6.5,
    ))
    ax.add_patch(Arc(
        (xc, cyl_bot_y), 2 * cyl_rx, 2 * cyl_ry,
        theta1=180, theta2=360, color=G_BLUE, lw=1.2,
        alpha=0.85, zorder=6.5,
    ))
    # Vertical side generators at the rim (left and right silhouette)
    for sx in (xc - cyl_rx, xc + cyl_rx):
        ax.plot([sx, sx], [cyl_bot_y, cyl_top_y],
                color=G_BLUE, lw=1.2, alpha=0.85, zorder=6.5)

    # ------- Cone body (apex down) -------
    apex  = (xc, apex_y)
    left  = (xc - cone_rx, cone_top_y)
    right = (xc + cone_rx, cone_top_y)
    cone_front_arc = np.array([
        (xc + cone_rx * np.cos(t), cone_top_y + cone_ry * np.sin(t))
        for t in np.linspace(-np.pi, 0.0, 80)
    ])
    cone_poly = np.vstack([[right], [apex], [left], cone_front_arc])
    ax.add_patch(Polygon(
        cone_poly, closed=True,
        facecolor="#C9CCD1", edgecolor=G_GREY_900, lw=1.8, zorder=5,
    ))
    # Soft shadow on the left half for 3-D illusion
    shadow_poly = np.vstack([[apex], [left], cone_front_arc[: len(cone_front_arc) // 2 + 1]])
    ax.add_patch(Polygon(
        shadow_poly, closed=True,
        facecolor=G_GREY_700, edgecolor="none", alpha=0.32, zorder=5.5,
    ))
    # Specular highlight on the right half
    highlight_poly = np.vstack([[apex], [right], cone_front_arc[len(cone_front_arc) // 2 :][::-1]])
    ax.add_patch(Polygon(
        highlight_poly, closed=True,
        facecolor="white", edgecolor="none", alpha=0.20, zorder=5.6,
    ))
    # Cone top cap (visible disk)
    ax.add_patch(Ellipse(
        (xc, cone_top_y), 2 * cone_rx, 2 * cone_ry,
        facecolor=G_GREY_300, edgecolor=G_GREY_900, lw=1.5, zorder=6,
    ))

    # ------- Drive shaft (short cylinder above cone) -------
    shaft_top_y = cone_top_y + shaft_h
    sh_top_arc = np.array([
        (xc + shaft_rx * np.cos(t), shaft_top_y + shaft_ry * np.sin(t))
        for t in np.linspace(0.0, -np.pi, 40)
    ])
    sh_bot_arc = np.array([
        (xc + shaft_rx * np.cos(t), cone_top_y + shaft_ry * np.sin(t))
        for t in np.linspace(0.0, -np.pi, 40)
    ])
    ax.add_patch(Polygon(
        np.vstack([sh_top_arc, sh_bot_arc[::-1]]), closed=True,
        facecolor=G_GREY_300, edgecolor=G_GREY_900, lw=1.3, zorder=7,
    ))
    ax.add_patch(Ellipse(
        (xc, shaft_top_y), 2 * shaft_rx, 2 * shaft_ry,
        facecolor=G_GREY_100, edgecolor=G_GREY_900, lw=1.3, zorder=8,
    ))

    # ------- Rotation indicator above the shaft (omega) -------
    arc_cy = shaft_top_y + 0.075
    arc_a, arc_b = 0.105, 0.038
    ax.add_patch(Arc(
        (xc, arc_cy), 2 * arc_a, 2 * arc_b,
        theta1=20, theta2=340, color=G_BLUE_DK, lw=2.4, zorder=9,
    ))
    a_tip  = np.deg2rad(18)
    a_tail = np.deg2rad(38)
    ax.annotate(
        "",
        xy=(xc + arc_a * np.cos(a_tip),  arc_cy + arc_b * np.sin(a_tip)),
        xytext=(xc + arc_a * np.cos(a_tail), arc_cy + arc_b * np.sin(a_tail)),
        arrowprops=dict(arrowstyle="-|>", color=G_BLUE_DK,
                        lw=2.0, mutation_scale=20),
        zorder=10,
    )
    ax.text(xc + arc_a + 0.04, arc_cy, r"$\omega$",
            fontsize=FS_LABEL + 6, color=G_BLUE_DK,
            va="center", fontweight="bold")

    # ------- Tangential velocity vectors around cone rim -------
    rim_arrow_len = 0.075
    for phi_deg in (-155, -115, -90, -65, -25):
        phi = np.deg2rad(phi_deg)
        px = xc + cone_rx * np.cos(phi)
        py = cone_top_y + cone_ry * np.sin(phi)
        tx = -cone_rx * np.sin(phi)
        ty =  cone_ry * np.cos(phi)
        n = np.hypot(tx, ty)
        tx, ty = (tx / n) * rim_arrow_len, (ty / n) * rim_arrow_len
        ax.annotate(
            "",
            xy=(px + tx, py + ty), xytext=(px, py),
            arrowprops=dict(arrowstyle="-|>", color=G_ORANGE,
                            lw=3.0, mutation_scale=20),
            zorder=8.0,
        )

    # ------- Velocity profile vs z at the front rim (phi = -90) -------
    prof_x      = xc
    prof_y_top  = cone_top_y - cone_ry
    prof_y_bot  = plate_top_y
    n_profile   = 5
    for i in range(1, n_profile):
        frac = i / n_profile
        py_i = prof_y_bot + frac * (prof_y_top - prof_y_bot)
        L_i  = frac * rim_arrow_len
        ax.annotate(
            "",
            xy=(prof_x + L_i, py_i), xytext=(prof_x, py_i),
            arrowprops=dict(arrowstyle="-|>", color=G_ORANGE,
                            lw=2.2, mutation_scale=14, alpha=0.95),
            zorder=8.0,
        )
        ax.plot([prof_x, prof_x + rim_arrow_len],
            [prof_y_bot, prof_y_top],
            color=G_ORANGE, lw=1.2, ls="--", alpha=0.9, zorder=8.0)
        # Add tangential velocity profile label in orange, shifted right and up
        ax.text(prof_x + rim_arrow_len + 0.325,
            (prof_y_top + prof_y_bot) / 2 + 0.225,
            r"$u_\theta = r\,\omega$",
            fontsize=FS_LABEL + 6, color=G_ORANGE,
            ha="left", va="center", fontweight="bold")
    # ------- Cone half-angle alpha at the apex -------
    ang_deg = float(np.degrees(np.arctan2(cone_top_y - apex_y, cone_rx)))
    arc_r = 0.11
    ax.plot([apex[0], apex[0] + arc_r], [apex[1], apex[1]],
            color=G_GREEN, lw=2.0, ls="-", zorder=11)
    ax.add_patch(Arc(
        apex, 2 * arc_r, 2 * arc_r,
        theta1=0, theta2=ang_deg,
        color=G_GREEN, lw=2.6, zorder=11,
    ))
    ax.text(apex[0] + arc_r * 1.05, apex_y + arc_r * 0.5,
            r"$\alpha$", fontsize=FS_LABEL + 4, color=G_GREEN, va="center")

    # ------- Plate centre marker + gap h between cone tip and plate -------
    # Vertical centre line (dashed) from plate centre up through cone apex.
    ax.plot([xc, xc], [plate_top_y, apex_y],
            color=G_RED, lw=1.0, ls=(0, (2, 2)), alpha=0.85, zorder=11.4)

    if h_dimension_style == "left_extension":
        # Engineering-style dimension: horizontal extension lines from the
        # cone tip and plate centre running leftward, with the double-arrow
        # and label placed between them at the extension end.
        h_dim_x = xc - 0.22
        ext_inner = xc - 0.010      # small gap so lines don't touch the axis
        ext_outer = h_dim_x - 0.025
        for y_h in (apex_y, plate_top_y):
            ax.plot([ext_inner, ext_outer], [y_h, y_h],
                    color=G_RED, lw=2.2, alpha=0.9, zorder=11.5)
        ax.annotate(
            "",
            xy=(h_dim_x, apex_y), xytext=(h_dim_x, plate_top_y),
            arrowprops=dict(arrowstyle="<->", color=G_RED,
                            lw=3.2, mutation_scale=22),
            zorder=11.6,
        )
        ax.text(h_dim_x - 0.020, (apex_y + plate_top_y) / 2,
                r"$h$", color=G_RED, fontsize=FS_LABEL + 4,
                ha="right", va="center", zorder=11.7)
    else:
        # Inline double-arrow at the axis with the label placed beside it.
        ax.annotate(
            "",
            xy=(xc, apex_y), xytext=(xc, plate_top_y),
            arrowprops=dict(arrowstyle="<->", color=G_RED,
                            lw=3.2, mutation_scale=22),
            zorder=11.6,
        )
        ax.text(xc + 0.022, (apex_y + plate_top_y) / 2,
                r"$h$", color=G_RED, fontsize=FS_LABEL + 4,
                ha="left", va="center", zorder=11.7)

    # ------- Total gap H(r) dimension at the rim (r = R) -------
    H_x = xc + cyl_rx + 0.05
    # Thin dotted extension lines from cylinder edge out to the dimension
    ax.plot([xc + cyl_rx, H_x + 0.005], [plate_top_y, plate_top_y],
            color=G_BLUE_DK, lw=1.8, ls=":", alpha=0.8, zorder=10.8)
    ax.plot([xc + cyl_rx, H_x + 0.005], [cone_top_y, cone_top_y],
            color=G_BLUE_DK, lw=1.8, ls=":", alpha=0.8, zorder=10.8)
    ax.annotate(
        "",
        xy=(H_x, cone_top_y), xytext=(H_x, plate_top_y),
        arrowprops=dict(arrowstyle="<->", color=G_BLUE_DK,
                        lw=3.2, mutation_scale=22),
        zorder=11,
    )
    ax.text(H_x + 0.015, (cone_top_y + plate_top_y) / 2,
            r"$H(r)$", color=G_BLUE_DK, fontsize=FS_LABEL + 4,
            ha="left", va="center")

    # ------- Radius dimension R across top of cone -------
    dim_y = cone_top_y + cone_ry + 0.045
    ax.annotate(
        "",
        xy=(xc + cone_rx, dim_y), xytext=(xc, dim_y),
        arrowprops=dict(arrowstyle="<|-|>", color=G_GREY_700,
                        lw=1.2, mutation_scale=12),
        zorder=11,
    )
    ax.text(xc + cone_rx / 2, dim_y + 0.012, r"$R$",
            fontsize=FS_LABEL, color=G_GREY_900,
            ha="center", va="bottom")

    # ------- Labels -------
    if cone_label_position == "top":
        # On the visible front portion of the top cap, below the shaft so
        # the drive-shaft cylinder does not hide the label.
        ax.text(xc-0.2, cone_top_y+0.05 - cone_ry * 0.55, "Cone",
                fontsize=FS_NOTE + 4, color=TEXT_C,
                ha="center", va="center", zorder=9)
    else:
        ax.text(xc - cone_rx - 0.04, (cone_top_y + apex_y) / 2 + 0.02,
                "Cone", fontsize=FS_NOTE + 4, color=TEXT_C,
                ha="right", va="center")
    # Place 'Liquid Domain' left of blue cylinder, no line
    ax.text(xc - cyl_rx, (cyl_top_y + cyl_bot_y) / 2,
            "Fluid \n Domain", fontsize=FS_LABEL + 6, color=G_BLUE_DK,
            ha="right", va="center")
    # Stationary plate label, anchored a configurable distance below the
    # plate's bottom-back edge.  The default reproduces the original layout
    # used by the multi-panel figure.
    plate_label_y = plate_bot_y - plate_label_offset_below
    ax.text(xc, plate_label_y+0.06, "Stationary plate",
            ha="center", va="top",
            fontsize=FS_NOTE + 8, color=G_GREY_700)

    if show_title:
        panel_title(ax, "Physics Overview")
    if show_caption:
        caption(ax,
                "Cone-and-plate geometry\n"
                r"rotation rate $\omega$, half-angle $\alpha$")


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

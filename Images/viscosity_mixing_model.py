"""
Viscosity mixing model for silicone oil blends — Type I.

Formula (weighted log-linear mixing rule):
    ln(η_m) = (x1 · ln(η1) + α · x2 · ln(η2)) / (x1 + α · x2)

    α = (ρ1/ρ2)^J · (ln η1 / ln η2)^n
    Type I: J = 0, n = 0.2
    Same-density silicone oils → (ρ1/ρ2)^J = 1
        ∴  α = (ln η1 / ln η2)^0.2

x-axis : x1 — volume/mole fraction of component 1 (0 → 1)
y-axis : η_m — mixture viscosity (cP)

Output : Images/viscosity_mixing_model.svg  /  .png
Run    : python Images/viscosity_mixing_model.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from cycler import cycler

# --------------------------------------------------------------------------- #
# Google Material style — identical palette to pipeline_svg.ipynb             #
# --------------------------------------------------------------------------- #
GOOGLE_COLORS = [
    "#4285F4",  # Google Blue
    "#EA4335",  # Google Red
    "#FBBC04",  # Google Yellow
    "#34A853",  # Google Green
    "#FF6D01",  # Orange
    "#46BDC6",  # Teal
    "#7B1FA2",  # Purple
    "#9E9D24",  # Olive
    "#795548",  # Brown
    "#5F6368",  # Google Grey
]

google_rc: dict = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Google Sans", "Roboto", "Product Sans", "Arial", "DejaVu Sans"],
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "medium",
    "axes.labelsize": 11,
    "axes.labelweight": "regular",
    "legend.fontsize": 10,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.titlesize": 15,
    "figure.titleweight": "medium",
    # Surfaces
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "figure.dpi": 110,
    "savefig.dpi": 200,
    "figure.autolayout": True,
    # Axes chrome
    "axes.edgecolor": "#DADCE0",
    "axes.linewidth": 1.0,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.labelcolor": "#202124",
    "axes.titlecolor": "#202124",
    "axes.titlepad": 12,
    "axes.axisbelow": True,
    # Grid
    "axes.grid": True,
    "grid.color": "#E8EAED",
    "grid.linestyle": "-",
    "grid.linewidth": 0.8,
    "grid.alpha": 0.9,
    # Ticks
    "xtick.color": "#5F6368",
    "ytick.color": "#5F6368",
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.size": 4,
    "ytick.major.size": 4,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    # Lines
    "lines.linewidth": 2.2,
    "lines.markersize": 6,
    "lines.markeredgewidth": 0,
    # Legend
    "legend.frameon": True,
    "legend.facecolor": "white",
    "legend.edgecolor": "#DADCE0",
    "legend.framealpha": 0.95,
    "legend.borderpad": 0.6,
    # Color cycle
    "axes.prop_cycle": cycler(color=GOOGLE_COLORS),
    # SVG: embed glyphs so math renders correctly without installed fonts
    "svg.fonttype": "path",
    "mathtext.fontset": "cm",
    "mathtext.default": "it",
}

# --------------------------------------------------------------------------- #
# Physics                                                                      #
# --------------------------------------------------------------------------- #
J = 0      # Type I
N = 0.2    # Type I exponent


def alpha(eta1: float, eta2: float) -> float:
    """Compute α for same-density silicone oils (ρ1/ρ2 = 1)."""
    # (ρ1/ρ2)^J = 1  →  α = (ln η1 / ln η2)^n
    return (np.log(eta1) / np.log(eta2)) ** N


def eta_mix(x1: np.ndarray, eta1: float, eta2: float) -> np.ndarray:
    """Return mixture viscosity array given x1 values (Type I model)."""
    x2 = 1.0 - x1
    a = alpha(eta1, eta2)
    ln_eta_m = (x1 * np.log(eta1) + a * x2 * np.log(eta2)) / (x1 + a * x2)
    return np.exp(ln_eta_m)


# --------------------------------------------------------------------------- #
# Silicone oil pairs to plot                                                   #
# (η1, η2) in cP  — same density, so α depends only on viscosity ratio        #
# --------------------------------------------------------------------------- #
PAIRS: list[tuple[float, float]] = [(10_000, 60_000)]

# --------------------------------------------------------------------------- #
# Build figure                                                                 #
# --------------------------------------------------------------------------- #
x1 = np.linspace(0.0, 1.0, 500)

with mpl.rc_context(google_rc):
    fig, ax = plt.subplots(figsize=(8, 8))

    # Square, all four spines visible (same convention as pipeline_svg)
    ax.set_box_aspect(1)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(True)
        ax.spines[side].set_color("black")
        ax.spines[side].set_linewidth(1.5)

    # Remove the default Google-rc top/right suppression inside the context
    ax.spines["top"].set_visible(True)
    ax.spines["right"].set_visible(True)

    ax.grid(True, color="#E8EAED", linewidth=0.8, alpha=0.9)

    for (eta1, eta2), color in zip(PAIRS, GOOGLE_COLORS):
        y = eta_mix(x1, eta1, eta2)
        label = (
            rf"$\eta_1={eta1/1_000:.1f}$, $\eta_2={eta2/1_000:.1f}$ k cP"
        )
        ax.plot(x1, y, color=color, linewidth=2.4, label=label)

        # Mark pure-component endpoints
        ax.scatter([0.0, 1.0], [eta2, eta1],
                   color=color, s=55, zorder=5, edgecolors="white", linewidths=0.8)

    # ---- axes labels --------------------------------------------------------
    ax.set_xlabel(r"$x_1$  (mole fraction of component 1)", fontsize=22, color="#202124")
    ax.set_ylabel(r"$\eta_m$  (k cP)", fontsize=22, color="#202124")
    ax.tick_params(axis="both", which="major", labelsize=16, color="black", labelcolor="black")
    # Write y-ticks in kilo-centipoise for readability
    yticks = ax.get_yticks()
    ax.set_yticklabels([f"{ytick/1_000:.1f}" for ytick in yticks])

    # Log scale — mixture spans many decades across pairs
    #ax.set_yscale("log")
    ax.set_xlim(-0.02, 1.02)

    # ---- legend ------------------------------------------------------------
    leg = ax.legend(
        fontsize=13,
        loc="upper right",
        frameon=True,
        framealpha=0.95,
        edgecolor="#DADCE0",
    )

    plt.tight_layout()

    out_dir = Path(__file__).parent
    fig.savefig(out_dir / "viscosity_mixing_model.svg", format="svg", bbox_inches="tight")
    fig.savefig(out_dir / "viscosity_mixing_model.png", bbox_inches="tight")
    print(f"Saved → {out_dir / 'viscosity_mixing_model.svg'}")
    print(f"Saved → {out_dir / 'viscosity_mixing_model.png'}")

    plt.show()

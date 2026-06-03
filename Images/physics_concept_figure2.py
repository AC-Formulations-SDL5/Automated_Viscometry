"""
Standalone large-scale rendering of Step 1 (Physics Overview) only.

Reuses `draw_overview` from physics_concept_figure.py so the schematic
stays in sync with the multi-panel figure, but renders it by itself on
a much larger canvas.

Output:  Images/physics_concept_figure2.svg / .png
Run:     python Images/physics_concept_figure2.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from physics_concept_figure import draw_overview

HERE = Path(__file__).parent
OUT_SVG = HERE / "physics_concept_figure2.svg"


def build_figure():
    # Large square-ish canvas so the single panel reads big and clean.
    fig, ax = plt.subplots(figsize=(14, 12), dpi=150)
    fig.subplots_adjust(left=0.04, right=0.96, top=0.94, bottom=0.08)

    draw_overview(
        ax,
        show_title=False,
        show_caption=False,
        cone_label_position="top",
        plate_label_offset_below=0.18,   # well below the plate's front edge
        h_dimension_style="left_extension",
    )

    fig.savefig(OUT_SVG, format="svg", bbox_inches="tight")
    fig.savefig(OUT_SVG.with_suffix(".png"), format="png",
                bbox_inches="tight", dpi=200)
    print(f"Wrote {OUT_SVG}")
    return fig


if __name__ == "__main__":
    build_figure()

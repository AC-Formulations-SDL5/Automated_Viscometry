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

import physics_concept_figure as pcf

HERE = Path(__file__).parent
OUT_SVG = HERE / "physics_concept_figure2.svg"


def build_figure():
    # Force a much larger, uniform text scale for subplot A.
    pcf.FS_TITLE = 45
    pcf.FS_EQ = 45
    pcf.FS_LABEL = 45
    pcf.FS_AXIS = 45
    pcf.FS_NOTE = 45

    # Large square-ish canvas so the single panel reads big and clean.
    fig, ax = plt.subplots(figsize=(14, 12), dpi=150)
    fig.subplots_adjust(left=0.04, right=0.96, top=0.94, bottom=0.08)

    pcf.draw_overview(
        ax,
        show_title=False,
        show_caption=False,
        cone_label_position="top",
        plate_label_offset_below=0.18,   # well below the plate's front edge
        h_dimension_style="left_extension",
    )

    # Enforce the same large text size for any text added to this axes.
    for txt in ax.texts:
        txt.set_fontsize(45)

    fig.savefig(OUT_SVG, format="svg", bbox_inches="tight")
    fig.savefig(OUT_SVG.with_suffix(".png"), format="png",
                bbox_inches="tight", dpi=200)
    print(f"Wrote {OUT_SVG}")
    return fig


if __name__ == "__main__":
    build_figure()

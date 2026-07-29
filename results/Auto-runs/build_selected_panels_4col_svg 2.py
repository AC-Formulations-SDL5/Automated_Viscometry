from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from typing import List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


if os.name == "nt":
    # Ensure Cairo DLLs from conda env are discoverable by cairocffi/cairosvg.
    dll_dir = Path(sys.prefix) / "Library" / "bin"
    if dll_dir.exists() and hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(dll_dir))
        os.environ["CAIROCFFI_DLL_DIRECTORIES"] = str(dll_dir)
        os.environ["PATH"] = str(dll_dir) + os.pathsep + os.environ.get("PATH", "")

try:
    import cairosvg
except Exception:
    cairosvg = None


def load_rgb_image(path: Path, allow_png_fallback: bool = True) -> np.ndarray:
    """Load SVG/PNG as RGB numpy array.

    When `allow_png_fallback` is False and SVG rendering backend is unavailable,
    this function raises instead of silently switching to PNG.
    """
    if path.suffix.lower() == ".svg":
        if cairosvg is not None:
            png_bytes = cairosvg.svg2png(bytestring=path.read_bytes())
            return np.asarray(Image.open(io.BytesIO(png_bytes)).convert("RGB"))

        if allow_png_fallback:
            png_fallback = path.with_suffix(".png")
            if png_fallback.exists():
                return np.asarray(Image.open(png_fallback).convert("RGB"))

        raise RuntimeError(
            f"Cannot load SVG {path}. Install cairosvg with cairo runtime."
        )

    return np.asarray(Image.open(path).convert("RGB"))


def trim_whitespace(img: np.ndarray, threshold: int = 245, pad: int = 8) -> np.ndarray:
    gray = np.mean(img, axis=2)
    mask = gray < threshold

    if not np.any(mask):
        return img

    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]

    r0, r1 = rows[0], rows[-1] + 1
    c0, c1 = cols[0], cols[-1] + 1

    r0 = max(0, r0 - pad)
    c0 = max(0, c0 - pad)
    r1 = min(img.shape[0], r1 + pad)
    c1 = min(img.shape[1], c1 + pad)

    return img[r0:r1, c0:c1]


def fit_to_canvas(img: np.ndarray, target_h: int, target_w: int) -> np.ndarray:
    """Scale preserving aspect and center on white square canvas."""
    h, w = img.shape[:2]
    scale = min(target_w / w, target_h / h)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))

    resized = np.asarray(
        Image.fromarray(img).resize((new_w, new_h), resample=Image.Resampling.LANCZOS)
    )

    canvas = np.full((target_h, target_w, 3), 255, dtype=np.uint8)
    y0 = (target_h - new_h) // 2
    x0 = (target_w - new_w) // 2
    canvas[y0 : y0 + new_h, x0 : x0 + new_w] = resized
    return canvas


def style_axis(ax: plt.Axes, panel_label: str) -> None:
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.text(
        -0.03,
        0.985,
        panel_label,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=16,
        fontweight="normal",
        fontfamily="Arial",
        color="#202124",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9, "pad": 2},
        clip_on=False,
        zorder=6,
    )


def build_svg(output_svg: Path) -> None:
    root = Path(__file__).resolve().parent
    figs = root / "figures_rheology"
    images = root.parents[1] / "Images"

    # Requested order with two prepended panels:
    # A: physics_concept_figure2.svg
    # B: hitpoints_histogram.svg
    # then current panels shifted by +2 labels.
    panel_specs: List[Tuple[str, Path]] = [
        ("A", images / "physics_concept_figure2.svg"),
        ("B", images / "hitpoints_histogram.svg"),
        ("C", figs / "02_loglog_focus_logspace.svg"),  # Plot 3
        ("D", figs / "02_loglog_focus_local_slope.svg"),  # Plot 4
        ("E", figs / "02b_slope_vs_B.svg"),  # Plot 5
        ("F", figs / "04_direct_fits.svg"),  # Plot 6
        ("G", figs / "06_residuals_best_1.svg"),  # Plot 8
        ("H", figs / "06_residuals_best_2.svg"),  # Plot 9
        ("I", figs / "06_residuals_best_3.svg"),  # Plot 10
        ("J", figs / "06_residuals_best_4.svg"),  # Plot 11
        ("K", figs / "13_master_mean.svg"),  # H2
    ]

    panels: List[np.ndarray] = []
    labels: List[str] = []

    for label, src in panel_specs:
        if not src.exists():
            raise FileNotFoundError(f"Missing source panel: {src}")
        # Subplot B must always use the SVG source directly (no PNG fallback).
        img = load_rgb_image(src, allow_png_fallback=(label != "B"))
        panels.append(trim_whitespace(img))
        labels.append(label)

    max_h = max(panel.shape[0] for panel in panels)
    max_w = max(panel.shape[1] for panel in panels)
    side = max(max_h, max_w)
    panels = [fit_to_canvas(panel, side, side) for panel in panels]

    ncols = 4
    nrows = int(np.ceil(len(panels) / ncols))

    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "#F8F9FA",
            "savefig.facecolor": "white",
            "font.family": "Arial",
            "font.size": 11,
            "axes.edgecolor": "#DADCE0",
        }
    )

    cell_size_in = 3.0
    fig_w = ncols * cell_size_in
    fig_h = nrows * cell_size_in

    fig, axes = plt.subplots(nrows, ncols, figsize=(fig_w, fig_h), squeeze=False)
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.03, top=0.97, wspace=0.06, hspace=0.08)

    flat_axes = axes.ravel()
    for ax, panel, label in zip(flat_axes, panels, labels):
        ax.imshow(panel, interpolation="antialiased", aspect="equal")
        ax.set_box_aspect(1)
        style_axis(ax, label)

    for ax in flat_axes[len(panels) :]:
        ax.axis("off")

    output_svg.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_svg, format="svg", dpi=300)
    plt.close(fig)


def main() -> None:
    out = (
        Path(__file__).resolve().parent
        / "figures_rheology"
        / "Figure_selected_4col_A_to_K.svg"
    )
    build_svg(out)
    print(f"Saved integrated SVG: {out}")


if __name__ == "__main__":
    main()

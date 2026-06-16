from __future__ import annotations

import io
import re
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

try:
    import cairosvg
except ImportError:
    cairosvg = None


GOOGLE_PALETTE = ["#4285F4", "#DB4437", "#F4B400", "#0F9D58"]


def load_rgb_image(path: Path) -> np.ndarray:
    """Load raster image or render SVG as RGB numpy array."""
    if path.suffix.lower() == ".svg":
        if cairosvg is not None:
            svg_text = path.read_text(encoding="utf-8")
            svg_text = remap_svg_plot_colors(svg_text)
            png_bytes = cairosvg.svg2png(bytestring=svg_text.encode("utf-8"))
            return np.asarray(Image.open(io.BytesIO(png_bytes)).convert("RGB"))

        png_fallback = path.with_suffix(".png")
        if png_fallback.exists():
            return np.asarray(Image.open(png_fallback).convert("RGB"))

        raise RuntimeError(
            f"Cannot load SVG {path}. Install cairosvg or provide PNG fallback at {png_fallback}."
        )

    return np.asarray(Image.open(path).convert("RGB"))


def is_neutral_color(hex_color: str) -> bool:
    """Return True for white/black/gray-like colors that should stay unchanged."""
    value = hex_color.lstrip("#")
    if len(value) != 6:
        return True
    r = int(value[0:2], 16)
    g = int(value[2:4], 16)
    b = int(value[4:6], 16)

    # Keep neutral tones (axes, text, background) untouched.
    spread = max(r, g, b) - min(r, g, b)
    avg = (r + g + b) / 3.0
    return spread < 18 or avg < 35 or avg > 240


def remap_svg_plot_colors(svg_text: str) -> str:
    """Remap non-neutral SVG colors to Google palette for plot traces/markers/bars."""
    color_pat = re.compile(r"#([0-9a-fA-F]{6})")
    ordered_colors: List[str] = []

    for match in color_pat.finditer(svg_text):
        color = f"#{match.group(1).upper()}"
        if color not in ordered_colors and not is_neutral_color(color):
            ordered_colors.append(color)

    if not ordered_colors:
        return svg_text

    mapping = {
        old: GOOGLE_PALETTE[idx % len(GOOGLE_PALETTE)]
        for idx, old in enumerate(ordered_colors)
    }

    def repl(match: re.Match[str]) -> str:
        found = f"#{match.group(1).upper()}"
        return mapping.get(found, found)

    return color_pat.sub(repl, svg_text)


def fit_to_canvas(img: np.ndarray, target_h: int, target_w: int) -> np.ndarray:
    """Scale while preserving aspect and center on a white canvas (no stretching)."""
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


def trim_whitespace(img: np.ndarray, threshold: int = 245, pad: int = 6) -> np.ndarray:
    """Trim near-white border around a subplot crop to maximize data area."""
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


def split_two_horizontal(img: np.ndarray) -> List[np.ndarray]:
    """Split a 1x2 layout image into left and right subplots."""
    h, w = img.shape[:2]
    mid = w // 2
    left = trim_whitespace(img[:, :mid])
    right = trim_whitespace(img[:, mid:])
    return [left, right]


def split_four_grid(img: np.ndarray) -> List[np.ndarray]:
    """Split a 2x2 layout image into top-left, top-right, bottom-left, bottom-right."""
    h, w = img.shape[:2]
    mid_h = h // 2
    mid_w = w // 2

    tl = trim_whitespace(img[:mid_h, :mid_w])
    tr = trim_whitespace(img[:mid_h, mid_w:])
    bl = trim_whitespace(img[mid_h:, :mid_w])
    br = trim_whitespace(img[mid_h:, mid_w:])
    return [tl, tr, bl, br]


def style_axis(ax: plt.Axes, panel_label: str) -> None:
    """Apply clean Google-style panel framing and label."""
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.text(
        0.01,
        0.985,
        panel_label,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=15,
        fontfamily="Arial",
        fontweight="bold",
        color="#202124",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9, "pad": 2},
        zorder=6,
    )


def build_figure(base_dir: Path, output_svg: Path) -> None:
    """Assemble integrated Figure 6 panels A-J from manuscript source figures."""
    figure_6a_path = Path(
        r"C:\Users\mrast\OneDrive\Documents\GitHub\Automated_Viscometry\results\Auto-runs\figures_rheology\02_loglog_focus.svg"
    )
    figure_6b_path = Path(
        r"C:\Users\mrast\OneDrive\Documents\GitHub\Automated_Viscometry\results\Auto-runs\figures_rheology\02b_slope_vs_B.svg"
    )
    figure_6c_path = Path(
        r"C:\Users\mrast\OneDrive\Documents\GitHub\Automated_Viscometry\results\Auto-runs\figures_rheology\04_direct_fits.svg"
    )
    figure_6d_path = Path(
        r"C:\Users\mrast\OneDrive\Documents\GitHub\Automated_Viscometry\results\Auto-runs\figures_rheology\06_residuals_best.svg"
    )
    figure_6f_path = Path(
        r"C:\Users\mrast\OneDrive\Documents\GitHub\Automated_Viscometry\results\Auto-runs\figures_rheology\13_master_overlay_and_mean.svg"
    )

    fig_6a = load_rgb_image(figure_6a_path)
    fig_6b = load_rgb_image(figure_6b_path)
    fig_6c = load_rgb_image(figure_6c_path)
    fig_6d = load_rgb_image(figure_6d_path)
    fig_6f = load_rgb_image(figure_6f_path)

    panels = []
    panels.extend(split_two_horizontal(fig_6a))  # A, B
    panels.append(trim_whitespace(fig_6b))  # C
    panels.append(trim_whitespace(fig_6c))  # D
    panels.extend(split_four_grid(fig_6d))  # E, F, G, H
    panels.extend(split_two_horizontal(fig_6f))  # I, J

    if len(panels) != 10:
        raise RuntimeError(f"Expected 10 panels, got {len(panels)}")

    max_h = max(panel.shape[0] for panel in panels)
    max_w = max(panel.shape[1] for panel in panels)
    square_side = max(max_h, max_w)
    panels = [fit_to_canvas(panel, square_side, square_side) for panel in panels]

    labels = list("ABCDEFGHIJ")

    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "font.family": "Arial",
            "font.size": 11,
        }
    )

    ncols = 3
    nrows = int(np.ceil(len(panels) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(12, 16), squeeze=False)
    fig.subplots_adjust(left=0.03, right=0.97, bottom=0.015, top=0.985, wspace=0.05, hspace=0.005)

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
    script_dir = Path(__file__).resolve().parent
    output = script_dir / "figures_rheology" / "Figure6_integrated_A_to_J.svg"
    build_figure(script_dir, output)
    print(f"Saved integrated SVG: {output}")


if __name__ == "__main__":
    main()

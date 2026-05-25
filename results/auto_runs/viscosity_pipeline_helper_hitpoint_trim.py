from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_HELPER_DIR = Path(__file__).resolve().parent
_SRC_DIR = _HELPER_DIR.parent.parent / "src" / "python_64"
if _SRC_DIR.is_dir() and str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from viscosity_pipeline_helper import (
    _plot_prediction_accuracy,
    _plot_trimmed_with_fits,
    fit_cell_models,
)


def load_rotational_drag_csv(
    csv_path: str,
    cell_col: str = "cell",
    x_col: str = "Z_Height_mm",
    y_col: str = "Rotational_Drag",
) -> pd.DataFrame:
    """Load a rotational-drag dataset (delegates to viscosity_pipeline_helper)."""
    from viscosity_pipeline_helper import load_rotational_drag_csv as _load

    out = _load(csv_path=csv_path, cell_col=cell_col, x_col=x_col, y_col=y_col)
    if "Torque_%" in out.columns:
        out["Torque_%"] = pd.to_numeric(out["Torque_%"], errors="coerce")
    if "Hit_Detected" in out.columns:
        out["Hit_Detected"] = (
            out["Hit_Detected"].astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y", "t"})
        )
    return out


def normalize_height_by_cell(
    df: pd.DataFrame,
    cell_col: str = "cell",
    x_col: str = "Z_Height_mm",
) -> pd.DataFrame:
    """Normalize x-axis so each cell starts at x=0."""
    out = df.copy()
    out[x_col] = out.groupby(cell_col)[x_col].transform(lambda s: s - s.min())
    return out


def _extract_rough_hitpoint_from_frame(
    cell_df: pd.DataFrame,
    x_col: str = "Z_Height_mm",
    hit_col: str = "Hit_Detected",
) -> Optional[float]:
    """Mirror the runtime rough-hitpoint heuristic using per-row hit detections."""
    if hit_col not in cell_df.columns:
        return None

    ordered = cell_df.sort_values(x_col, ascending=False).reset_index(drop=True)
    hit_sequence = [(float(row[x_col]), bool(row.get(hit_col, False))) for _, row in ordered.iterrows()]

    rough_hitpoint = None
    n = len(hit_sequence)
    for i in range(max(0, n - 3)):
        z_val, is_hit = hit_sequence[i]
        if not is_hit and all(hit_sequence[j][1] for j in range(i + 1, min(i + 4, n))):
            rough_hitpoint = z_val

    return rough_hitpoint


def trim_stat_middle(
    df: pd.DataFrame,
    cell_col: str = "cell",
    x_col: str = "Z_Height_mm",
    y_col: str = "Rotational_Drag",
    torque_col: str = "Torque_%",
    hit_col: str = "Hit_Detected",
    torque_floor: float = 25.0,
    max_window_mm: float = 0.3,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Trim each cell using the backend hitpoint and torque-floor rules."""
    out, rep = [], []

    for cid, g in df.groupby(cell_col, sort=True):
        g = g.sort_values(x_col).reset_index(drop=True)
        if g.empty:
            continue

        torque_values = pd.to_numeric(g[torque_col], errors="coerce") if torque_col in g.columns else pd.to_numeric(g[y_col], errors="coerce")
        hitpoint_z = _extract_rough_hitpoint_from_frame(g, x_col=x_col, hit_col=hit_col)

        if hitpoint_z is None:
            selected = g[torque_values > torque_floor].copy()
            trim_mode = "torque-floor-only"
        else:
            selected = g[(torque_values > torque_floor) & (g[x_col] >= hitpoint_z)].copy()
            trim_mode = "hitpoint+torque"
            if not selected.empty and float(selected[x_col].max() - selected[x_col].min()) > max_window_mm:
                selected = selected[selected[x_col] <= hitpoint_z + max_window_mm].copy()
                trim_mode = "hitpoint+torque+window"

        if selected.empty:
            selected = g.tail(min(3, len(g))).copy()
            trim_mode = f"fallback-{trim_mode}"

        selected = selected.sort_values(x_col).reset_index(drop=True)
        selected[x_col] = selected[x_col] - selected[x_col].min()
        out.append(selected)
        rep.append(
            {
                "cell": int(cid),
                "start": 0,
                "end": int(len(selected) - 1),
                "kept": int(len(selected)),
                "quality": np.nan,
                "hitpoint_z": float(hitpoint_z) if hitpoint_z is not None else None,
                "trim_mode": trim_mode,
            }
        )

    return pd.concat(out, ignore_index=True), pd.DataFrame(rep)


def _plot_raw_overview(
    raw_df: pd.DataFrame,
    cell_col: str,
    x_col: str,
    y_col: str,
    title: str,
) -> None:
    """Plot all cells' raw rotational-drag vs height curves on a single axes."""
    fig, ax = plt.subplots(figsize=(10, 6))
    cells = sorted(raw_df[cell_col].dropna().unique())
    cmap = plt.get_cmap("tab10")
    for idx, c in enumerate(cells):
        g = raw_df[raw_df[cell_col].eq(c)].sort_values(x_col)
        if g.empty:
            continue
        color = cmap(idx % cmap.N)
        ax.plot(
            g[x_col].to_numpy(float),
            g[y_col].to_numpy(float),
            marker="o",
            ms=3,
            lw=1.2,
            alpha=0.85,
            color=color,
            label=f"Cell {int(c)}",
        )
    ax.set_xlabel("Height (mm)", fontsize=12)
    ax.set_ylabel("Rotational Drag", fontsize=12)
    ax.set_title(f"{title}: Raw Rotational Drag vs Height (all cells)", fontsize=13, fontweight="bold")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9, loc="best", ncol=2)
    plt.tight_layout()
    plt.show()


def run_viscosity_pipeline(
    csv_path: str,
    real_viscosity_map: Dict[int, float],
    cell_col: str = "cell",
    x_col: str = "Z_Height_mm",
    y_col: str = "Rotational_Drag",
    m_poly: float = 0.592,
    m_hyp: float = 2.330,
    visualize: bool = True,
    viscosity_prediction_mode: str = "Non-Newtonian",
) -> Dict[str, object]:
    """
    End-to-end pipeline for rotational-drag vs height datasets.

    Steps:
    1) Import CSV
    2) Normalize x-axis per cell
    3) Trim before-hit and after-contact zones
    4) Fit 2nd-order polynomial and power-law hyperbola per cell
    5) Map user-provided real viscosities
    6) Convert fitted factors to viscosity using provided scales
    7) Extrapolate viscosity for unknown cells
    8) Plot fitting overlays and prediction accuracy for both methods
    """
    data_path = Path(csv_path)
    if not data_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df_raw = load_rotational_drag_csv(
        csv_path=str(data_path),
        cell_col=cell_col,
        x_col=x_col,
        y_col=y_col,
    )
    df_norm = normalize_height_by_cell(df_raw, cell_col=cell_col, x_col=x_col)
    df_trimmed, trim_report = trim_stat_middle(df_norm, cell_col=cell_col, x_col=x_col, y_col=y_col)
    fit_df = fit_cell_models(
        df_trimmed,
        cell_col=cell_col,
        x_col=x_col,
        y_col=y_col,
        viscosity_prediction_mode=viscosity_prediction_mode,
    )

    fit_df["real_viscosity"] = fit_df["cell"].map(real_viscosity_map)
    fit_df["real_viscosity_kcp"] = fit_df["real_viscosity"] / 1000.0
    fit_df["is_calibration"] = fit_df["real_viscosity"].notna()

    fit_df["predicted_visc_pol"] = np.abs(fit_df["a_poly2"]) * m_poly
    fit_df["predicted_visc_hyp"] = np.abs(fit_df["a_hyperbola"]) * m_hyp

    fit_df["rel_error_pol"] = (
        np.abs(fit_df["real_viscosity_kcp"] - fit_df["predicted_visc_pol"])
        / fit_df["real_viscosity_kcp"]
        * 100.0
    )
    fit_df["rel_error_hyp"] = (
        np.abs(fit_df["real_viscosity_kcp"] - fit_df["predicted_visc_hyp"])
        / fit_df["real_viscosity_kcp"]
        * 100.0
    )

    if visualize:
        _plot_raw_overview(
            raw_df=df_raw,
            cell_col=cell_col,
            x_col=x_col,
            y_col=y_col,
            title=data_path.name,
        )
        _plot_trimmed_with_fits(
            trimmed_df=df_trimmed,
            fit_df=fit_df,
            cell_col=cell_col,
            x_col=x_col,
            y_col=y_col,
            title=f"{data_path.name}: Selected Raw Segment + Fits",
            viscosity_prediction_mode=viscosity_prediction_mode,
        )
        _plot_prediction_accuracy(fit_df, m_hyp=m_hyp, m_pol2=m_poly)

    return {
        "raw_df": df_raw,
        "normalized_df": df_norm,
        "trimmed_df": df_trimmed,
        "trim_report": trim_report,
        "predictions": fit_df,
        "scales": {"poly": m_poly, "hyperbola": m_hyp},
    }

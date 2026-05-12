from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from scipy.optimize import curve_fit


@dataclass
class FitResult:
    cell: int
    a_poly2: float
    poly_coeffs: Optional[np.ndarray]
    a_hyperbola: float
    hyperbola_params: Optional[np.ndarray]


def _hyperbola(x: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
    return a / (x - b) + c


def load_rotational_drag_csv(
    csv_path: str,
    cell_col: str = "cell",
    x_col: str = "Z_Height_mm",
    y_col: str = "Rotational_Drag",
) -> pd.DataFrame:
    """Load a rotational-drag dataset and validate required columns."""
    df = pd.read_csv(csv_path)
    required = {cell_col, x_col, y_col}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    out = df.copy()
    out[cell_col] = pd.to_numeric(out[cell_col], errors="coerce")
    out[x_col] = pd.to_numeric(out[x_col], errors="coerce")
    out[y_col] = pd.to_numeric(out[y_col], errors="coerce")
    out = out.dropna(subset=[cell_col, x_col, y_col]).copy()
    out[cell_col] = out[cell_col].astype(int)
    out = out.sort_values([cell_col, x_col]).reset_index(drop=True)
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


def trim_stat_middle(
    df: pd.DataFrame,
    cell_col: str = "cell",
    x_col: str = "Z_Height_mm",
    y_col: str = "Rotational_Drag",
    q: float = 0.65,
    win: int = 5,
    min_keep_frac: float = 0.5,
    max_keep_frac: float = 0.8,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Trim before-hit and after-contact zones by keeping the smooth middle segment."""
    out, rep, eps = [], [], 1e-9

    for cid, g in df.groupby(cell_col, sort=True):
        g = g.sort_values(x_col).reset_index(drop=True)
        x, y, n = g[x_col].to_numpy(float), g[y_col].to_numpy(float), len(g)

        if n < 6:
            sel = g.copy()
            sel[x_col] -= sel[x_col].min()
            out.append(sel)
            rep.append({"cell": cid, "start": 0, "end": n - 1, "kept": n, "quality": np.nan})
            continue

        ys = pd.Series(y)
        y_sm = ys.rolling(win, center=True, min_periods=2).mean().bfill().ffill().to_numpy()
        sd = ys.rolling(win, center=True, min_periods=2).std().fillna(0).to_numpy()
        dy = np.gradient(y_sm, x)
        d2 = np.gradient(dy, x)

        cv = np.abs(sd / (np.abs(y_sm) + eps))
        d1_dev = np.abs(dy - np.nanmedian(dy))
        d2_abs = np.abs(d2)
        t_cv, t_d1, t_d2 = [np.nanquantile(v, q) for v in (cv, d1_dev, d2_abs)]
        neg = np.clip(-dy, 0, None)
        t_neg = max(np.nanquantile(neg, q), eps)

        raw = (
            cv / (t_cv + eps)
            + d1_dev / (t_d1 + eps)
            + d2_abs / (t_d2 + eps)
            + 2.0 * np.clip(dy, 0, None) / t_neg
            - 0.8 * neg / t_neg
        )

        min_k = max(5, int(np.ceil(min_keep_frac * n)))
        max_frac = 0.92 if n <= 14 else max_keep_frac
        max_k = min(n, max(min_k, int(np.floor(max_frac * n))))
        mid = 0.5 * (n - 1)

        best = (np.inf, 0, n)
        for length in range(min_k, max_k + 1):
            for i in range(0, n - length + 1):
                j = i + length
                dy_w = dy[i:j]
                pos_w = np.clip(dy_w, 0, None)
                neg_strength = float(np.nanmean(np.clip(-dy_w, 0, None)) / (t_neg + eps))
                score = float(np.nanmean(raw[i:j]))
                score += 1.8 * float(np.nanmean(pos_w / (t_neg + eps)))
                score += 0.9 * max(0.0, float(np.mean(dy_w > 0)) - 0.15)
                score += 0.35 * max(0.0, 0.55 - neg_strength)
                score += 0.10 * abs((i + j - 1) * 0.5 - mid) / max(n, 1)
                if score < best[0]:
                    best = (score, i, j)

        score, i, j = best
        sel = g.iloc[i:j].copy()
        sel[x_col] -= sel[x_col].min()

        out.append(sel)
        rep.append(
            {
                "cell": int(cid),
                "start": int(i),
                "end": int(j - 1),
                "kept": int(j - i),
                "quality": float(score),
            }
        )

    return pd.concat(out, ignore_index=True), pd.DataFrame(rep)


def fit_cell_models(
    df: pd.DataFrame,
    cell_col: str = "cell",
    x_col: str = "Z_Height_mm",
    y_col: str = "Rotational_Drag",
) -> pd.DataFrame:
    """Fit per-cell 2nd-order polynomial and hyperbola and return coefficients."""
    rows = []

    for cid, g in df.groupby(cell_col, sort=True):
        g = g.sort_values(x_col)
        x = g[x_col].to_numpy(float)
        y = g[y_col].to_numpy(float)

        poly_a = np.nan
        poly_coeffs = None
        hyp_a = np.nan
        hyp_params = None

        if len(g) >= 3:
            try:
                poly_coeffs = np.polyfit(x, y, 2)
                poly_a = float(poly_coeffs[0])
            except Exception:
                poly_coeffs = None

        if len(g) >= 4 and np.ptp(x) > 0:
            b0 = float(np.min(x) - 0.5 * max(np.ptp(x), 1e-6))
            a0 = float((y[0] - y[-1]) * max(np.ptp(x), 1e-6))
            c0 = float(np.nanmedian(y))
            lower_b = float(np.min(x) - 5.0 * max(np.ptp(x), 1e-6))
            upper_b = float(np.min(x) - 1e-6)
            try:
                hyp_params, _ = curve_fit(
                    _hyperbola,
                    x,
                    y,
                    p0=[a0, b0, c0],
                    bounds=([-np.inf, lower_b, -np.inf], [np.inf, upper_b, np.inf]),
                    maxfev=20000,
                )
                hyp_a = float(hyp_params[0])
            except Exception:
                hyp_params = None

        rows.append(
            FitResult(
                cell=int(cid),
                a_poly2=poly_a,
                poly_coeffs=poly_coeffs,
                a_hyperbola=hyp_a,
                hyperbola_params=hyp_params,
            )
        )

    rows_df = pd.DataFrame(
        [
            {
                "cell": r.cell,
                "a_poly2": r.a_poly2,
                "a_hyperbola": r.a_hyperbola,
                "poly_coeffs": r.poly_coeffs,
                "hyperbola_params": r.hyperbola_params,
            }
            for r in rows
        ]
    )
    return rows_df.sort_values("cell").reset_index(drop=True)


def _fit_origin_scale(x: np.ndarray, y: np.ndarray) -> float:
    denom = float(np.sum(x ** 2))
    if denom <= 0:
        return np.nan
    return float(np.sum(x * y) / denom)


def _plot_trimmed_with_fits(
    trimmed_df: pd.DataFrame,
    fit_df: pd.DataFrame,
    cell_col: str,
    x_col: str,
    y_col: str,
    title: str,
) -> None:
    n_cells = int(max(trimmed_df[cell_col].max(), 1))
    n_cols = 3
    n_rows = int(np.ceil(n_cells / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, max(5 * n_rows, 6)))
    axes = np.atleast_1d(axes).ravel()

    by_cell = fit_df.set_index("cell")

    for idx, ax in enumerate(axes, start=1):
        g = trimmed_df[trimmed_df[cell_col].eq(idx)].sort_values(x_col)
        if g.empty:
            ax.axis("off")
            continue

        x = g[x_col].to_numpy(float)
        y = g[y_col].to_numpy(float)
        ax.scatter(x, y, s=24, alpha=0.8, label="Selected raw", zorder=3)

        row = by_cell.loc[idx] if idx in by_cell.index else None
        x_line = np.linspace(x.min(), x.max(), 120)

        if row is not None and isinstance(row["poly_coeffs"], np.ndarray):
            y_poly = np.polyval(row["poly_coeffs"], x_line)
            ax.plot(x_line, y_poly, color="#1f77b4", linestyle="--", lw=2.0, label="Poly2 fit")

        if row is not None and isinstance(row["hyperbola_params"], np.ndarray):
            y_hyp = _hyperbola(x_line, *row["hyperbola_params"])
            ax.plot(x_line, y_hyp, color="#d62728", linestyle=":", lw=2.0, label="Hyperbola fit")

        ax.set_title(f"Cell {idx}")
        ax.set_xlabel("Normalized Height (mm)")
        ax.set_ylabel("Rotational Drag")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8, loc="best")

    fig.suptitle(title, y=0.995)
    plt.tight_layout()
    plt.show()


def _plot_prediction_accuracy(df_pred: pd.DataFrame, method: str, slope: float) -> None:
    y_col = f"predicted_visc_{method}"
    err_col = f"rel_error_{method}"

    known = df_pred.dropna(subset=["real_viscosity", y_col]).copy()
    if known.empty:
        print(f"No known-viscosity rows to plot for method: {method}")
        return

    cells = known["cell"].astype(int).to_numpy()
    real = known["real_viscosity"].to_numpy(float) / 1000.0
    pred = known[y_col].to_numpy(float) / 1000.0
    errs = known[err_col].to_numpy(float)
    x = np.arange(len(cells))
    bw = 0.35

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(x - bw / 2, real, bw, color="#1f77b4", alpha=0.65, edgecolor="k", lw=0.7, label="Real")
    ax.bar(x + bw / 2, pred, bw, color="#ff7f0e", alpha=0.65, edgecolor="k", lw=0.7, label="Predicted")
    ax.set_ylabel("Viscosity (k cP)")
    ax.set_xlabel("Cell")
    ax.set_xticks(x)
    ax.set_xticklabels(cells)
    ax.set_title(f"{method.upper()} Accuracy (scale={slope:.4f})")
    ax.grid(axis="y", alpha=0.2)

    ax2 = ax.twinx()
    ax2.scatter(x, errs, color="#2ca02c", s=80, edgecolor="k", lw=0.7, zorder=5)
    ax2.plot(x, errs, color="#444", lw=1.0, linestyle="--", alpha=0.5)
    ax2.set_ylabel("Relative Error (%)")
    ax2.set_ylim(0, max(100, float(np.nanmax(errs)) * 1.2))
    ax2.axhline(10, color="#2ca02c", linestyle=":", lw=1.2, alpha=0.7)

    handles = [
        Patch(facecolor="#1f77b4", alpha=0.65, edgecolor="k", label="Real viscosity"),
        Patch(facecolor="#ff7f0e", alpha=0.65, edgecolor="k", label="Predicted viscosity"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#2ca02c", markeredgecolor="k", label="Relative error", markersize=7),
    ]
    ax.legend(handles=handles, loc="upper left", frameon=False)
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
) -> Dict[str, object]:
    """
    End-to-end pipeline for rotational-drag vs height datasets.

    Steps:
    1) Import CSV
    2) Normalize x-axis per cell
    3) Trim before-hit and after-contact zones
    4) Fit 2nd-order polynomial and hyperbola per cell
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
    fit_df = fit_cell_models(df_trimmed, cell_col=cell_col, x_col=x_col, y_col=y_col)

    fit_df["real_viscosity"] = fit_df["cell"].map(real_viscosity_map)
    fit_df["is_calibration"] = fit_df["real_viscosity"].notna()

    fit_df["predicted_visc_pol"] = np.abs(fit_df["a_poly2"]) * m_poly
    fit_df["predicted_visc_hyp"] = np.abs(fit_df["a_hyperbola"]) * m_hyp

    fit_df["rel_error_pol"] = (
        np.abs(fit_df["real_viscosity"] - fit_df["predicted_visc_pol"])
        / fit_df["real_viscosity"]
        * 100.0
    )
    fit_df["rel_error_hyp"] = (
        np.abs(fit_df["real_viscosity"] - fit_df["predicted_visc_hyp"])
        / fit_df["real_viscosity"]
        * 100.0
    )

    if visualize:
        _plot_trimmed_with_fits(
            trimmed_df=df_trimmed,
            fit_df=fit_df,
            cell_col=cell_col,
            x_col=x_col,
            y_col=y_col,
            title=f"{data_path.name}: Selected Raw Segment + Fits",
        )
        _plot_prediction_accuracy(fit_df, method="pol", slope=m_poly)
        _plot_prediction_accuracy(fit_df, method="hyp", slope=m_hyp)

    return {
        "raw_df": df_raw,
        "normalized_df": df_norm,
        "trimmed_df": df_trimmed,
        "trim_report": trim_report,
        "predictions": fit_df,
        "scales": {"poly": m_poly, "hyperbola": m_hyp},
    }

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from scipy.optimize import curve_fit


def _hyperbola_2param(x: np.ndarray, a: float, b: float) -> np.ndarray:
    """2-parameter hyperbola: a / (x - b)"""
    return a / (x - b)


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
    def hyperbola(x, a, b):
        return a / (x - b)

    rows = []
    for cid, g in df.groupby(cell_col, sort=True):
        g = g.sort_values(x_col)
        x = g[x_col].to_numpy(float)
        y = g[y_col].to_numpy(float)

        poly_a = np.nan
        hyp_a = np.nan

        if len(g) >= 3:
            poly_a = float(np.polyfit(x, y, 2)[0])

        if len(g) >= 4 and np.ptp(x) > 0:
            # Initialize b away from x domain to avoid singularity during fitting.
            b0 = float(np.min(x) - 0.5 * max(np.ptp(x), 1e-6))
            a0 = float((y[0] - y[-1]) * max(np.ptp(x), 1e-6))
            lower_b = float(np.min(x) - 5.0 * max(np.ptp(x), 1e-6))
            upper_b = float(np.min(x) - 1e-6)

            try:
                p, _ = curve_fit(
                    hyperbola,
                    x,
                    y,
                    p0=[a0, b0],
                    bounds=([-np.inf, lower_b], [np.inf, upper_b]),
                    maxfev=20000,
                )
                hyp_a = float(p[0])
            except Exception:
                hyp_a = np.nan

        rows.append({"cell": int(cid), "a_poly2": poly_a, "a_hyperbola": hyp_a})

    return pd.DataFrame(rows).sort_values("cell").reset_index(drop=True)


def _plot_trimmed_with_fits(
    trimmed_df: pd.DataFrame,
    fit_df: pd.DataFrame,
    cell_col: str,
    x_col: str,
    y_col: str,
    title: str,
) -> None:
    """Plot trimmed data with polynomial and hyperbola fits overlaid."""
    from scipy.optimize import curve_fit

    cc, xc, yc = cell_col, x_col, y_col

    def hyperbola(x, a, b):
        return a / (x - b)

    n_cells = int(max(trimmed_df[cc].max(), 1))
    n_cols = 3
    n_rows = int(np.ceil(n_cells / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, max(5 * n_rows, 6)))
    axes = np.atleast_1d(axes).ravel()

    for i, ax in enumerate(axes, 1):
        g = trimmed_df[trimmed_df[cc].eq(i)].sort_values(xc)
        if g.empty:
            ax.axis("off")
            continue

        x = g[xc].to_numpy(float)
        y = g[yc].to_numpy(float)

        # Plot raw data
        ax.scatter(x, y, lw=1.5, alpha=0.7, label="Data", zorder=3)

        # Fit and plot polynomial
        if len(g) >= 3:
            p_poly = np.polyfit(x, y, 2)
            x_line = np.linspace(x.min(), x.max(), 100)
            y_poly = np.polyval(p_poly, x_line)
            ax.plot(x_line, y_poly, color="#4285F4", lw=2, linestyle="--", label="Poly2", zorder=2)

        # Fit and plot hyperbola
        if len(g) >= 4 and np.ptp(x) > 0:
            b0 = float(np.min(x) - 0.5 * max(np.ptp(x), 1e-6))
            a0 = float((y[0] - y[-1]) * max(np.ptp(x), 1e-6))
            lower_b = float(np.min(x) - 5.0 * max(np.ptp(x), 1e-6))
            upper_b = float(np.min(x) - 1e-6)
            try:
                p, _ = curve_fit(
                    hyperbola,
                    x,
                    y,
                    p0=[a0, b0],
                    bounds=([-np.inf, lower_b], [np.inf, upper_b]),
                    maxfev=20000,
                )
                x_line = np.linspace(x.min(), x.max(), 100)
                y_hyp = hyperbola(x_line, *p)
                ax.plot(x_line, y_hyp, color="#EA4335", lw=2, linestyle=":", label="Hyperbola", zorder=2)
            except Exception:
                pass

        ax.set_title(f"Cell {i}", fontsize=12, fontweight="bold")
        ax.grid(alpha=0.25)
        ax.set_xlabel("Height (mm)", fontsize=10)
        ax.set_ylabel("Rotational Drag", fontsize=10)
        ax.legend(fontsize=9, loc="best")

    fig.suptitle(f"{title}: Trimmed Data with Fitted Curves", y=0.995, fontsize=14)
    plt.tight_layout()
    plt.show()


def _plot_prediction_accuracy(df_pred: pd.DataFrame, m_hyp: float, m_pol2: float) -> None:
    req_cols = ["predicted_visc_hyp", "predicted_visc_pol", "rel_error_hyp", "rel_error_pol"]
    all_pred = df_pred.dropna(subset=req_cols, how="any").copy()
    if all_pred.empty:
        print("No predictions found for plotting accuracy.")
        return

    cells = all_pred["cell"].astype(int).to_numpy()
    if "real_viscosity_kcp" in all_pred.columns:
        real = all_pred["real_viscosity_kcp"].to_numpy(float)
    else:
        real = all_pred["real_viscosity"].to_numpy(float) / 1000.0

    pred_hyp = all_pred["predicted_visc_hyp"].to_numpy(float)
    pred_pol = all_pred["predicted_visc_pol"].to_numpy(float)
    errs_hyp = all_pred["rel_error_hyp"].to_numpy(float)
    errs_pol = all_pred["rel_error_pol"].to_numpy(float)
    if "provider" in all_pred.columns:
        prov = all_pred["provider"].fillna("").astype(str).str.lower().to_numpy()
    else:
        prov = np.array([""] * len(all_pred))

    x = np.arange(len(cells))
    bw = 0.35

    fig, (ax_hyp, ax_pol) = plt.subplots(1, 2, figsize=(20, 6), sharey=False)

    def draw_panel(ax, real_vals, pred_vals, errs, providers, cell_ids, x_vals, bar_w, title):
        has_real = ~np.isnan(real_vals)
        for i in range(len(cell_ids)):
            h = "//" if providers[i] == "sdl5" else None
            if has_real[i]:
                ax.bar(x_vals[i] - bar_w / 2, real_vals[i], bar_w, color="#4285F4", alpha=0.6, hatch=h, edgecolor="k", lw=0.8)
            ax.bar(x_vals[i] + bar_w / 2, pred_vals[i], bar_w, color="#E37400", alpha=0.6, hatch=h, edgecolor="k", lw=0.8)

        finite_real = real_vals[has_real]
        y_real_max = float(np.nanmax(finite_real)) if finite_real.size else 0.0
        y_pred_max = float(np.nanmax(pred_vals)) if pred_vals.size else 0.0
        y_max = max(y_real_max, y_pred_max, 1e-9)
        for i, p in enumerate(providers):
            if p:
                ax.text(x_vals[i] + 0.06, y_max * 1.05, p, ha="center", va="bottom", fontsize=10, rotation=90)

        ax.set_ylabel("Viscosity (k cP)", fontsize=14)
        ax.set_xlabel("Cell", fontsize=14)
        ax.set_xticks(x_vals)
        ax.set_xticklabels(cell_ids.astype(int), fontsize=11)
        ax.set_ylim(0, y_max * 1.35)
        ax.grid(False)
        ax.set_title(title, fontsize=14, fontweight="bold")

        ax2 = ax.twinx()
        colors = ["#34A853" if e <= 10 else "#9E9E9E" if e <= 50 else "#EA4335" for e in errs]
        ax2.scatter(x_vals, errs, color=colors, s=130, zorder=5, edgecolor="k", lw=0.8)
        ax2.plot(x_vals, errs, color="#3C4043", lw=1.2, linestyle="--", alpha=0.4)
        ax2.set_ylabel("Relative Error (%)", fontsize=14)
        ax2.axhline(10, color="#34A853", linestyle=":", lw=1.3, alpha=0.7)
        ax2.axhline(50, color="#9E9E9E", linestyle=":", lw=1.3, alpha=0.7)
        ax2.set_ylim(0, 100)

        leg = [
            Patch(facecolor="#4285F4", alpha=0.6, edgecolor="k", label="Real Visc."),
            Patch(facecolor="#E37400", alpha=0.6, edgecolor="k", label="Pred. Visc."),
            Patch(facecolor="white", hatch="//", edgecolor="k", label="SDL5"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor="#34A853", markeredgecolor="k", markersize=8, label="Error ≤10%"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor="#9E9E9E", markeredgecolor="k", markersize=8, label="10%<Error≤50%"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor="#EA4335", markeredgecolor="k", markersize=8, label="Error>50%"),
        ]
        ax.legend(handles=leg, fontsize=10, frameon=False)

        for sp in ax.spines.values():
            sp.set_linewidth(1.5)

    draw_panel(ax_hyp, real, pred_hyp, errs_hyp, prov, cells, x, bw, f"Hyperbola Fit  (m={m_hyp})")
    draw_panel(ax_pol, real, pred_pol, errs_pol, prov, cells, x, bw, f"Polynomial Fit  (m={m_pol2})")

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
        _plot_trimmed_with_fits(
            trimmed_df=df_trimmed,
            fit_df=fit_df,
            cell_col=cell_col,
            x_col=x_col,
            y_col=y_col,
            title=f"{data_path.name}: Selected Raw Segment + Fits",
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

"""
Three-pathway cell-level characterization (Newtonian, mild mix, strong stress).

Shared by live_engine and live_adapter so batch and streaming paths stay aligned.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from viscometry.rheology.constants import (
    CP_TO_PAS,
    NEWTONIAN_N_HIGH,
    NEWTONIAN_N_LOW,
    STRONG_THINNING_N_MAX,
    THICKENING_THRESHOLD,
    THINNING_THRESHOLD,
    shear_rate,
)
from viscometry.rheology.prediction import amplitude_to_viscosity, fit_powerlaw
from viscometry.rheology.stress_powerlaw import fit_stress_powerlaw, stage_powerlaw_points


def _json_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if np.isfinite(f) else None


def _regime_label(n_flow: float) -> str:
    if n_flow > THICKENING_THRESHOLD:
        return "shear-thickening"
    if n_flow < THINNING_THRESHOLD:
        return "shear-thinning"
    return "Newtonian"


def _pathway_from_n_stress(n_stress: Optional[float], n_rpms: int) -> str:
    if n_rpms < 2:
        return "newtonian"
    n = _json_float(n_stress)
    if n is None:
        return "newtonian"
    if n > NEWTONIAN_N_HIGH:
        return "shear_thickening"
    if n >= NEWTONIAN_N_LOW:
        return "newtonian"
    if n >= STRONG_THINNING_N_MAX:
        return "mild_shear_thinning"
    return "strong_shear_thinning"


def _build_stress_rows(fits: Dict[float, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for rpm, fit in fits.items():
        tau = _json_float(fit.get("tau_Pa_hit"))
        if tau is None or tau <= 0:
            continue
        g = float(shear_rate(rpm))
        rows.append(
            {
                "RPM": float(rpm),
                "gamma_dot_1_s": g,
                "tau_Pa": tau,
                "R2_drag": _json_float(fit.get("R2")) or 0.0,
                "A": _json_float(fit.get("A")),
            }
        )
    return rows


def _per_rpm_viscosity_cp(
    pathway: str,
    rpms: List[float],
    fits: Dict[float, Dict[str, Any]],
    *,
    n_stress: Optional[float],
    n_idx: Optional[float],
    k_stress: Optional[float],
) -> Dict[float, float]:
    """Return apparent viscosity (cP) per RPM for the selected pathway."""
    out: Dict[float, float] = {}
    g_arr = {rpm: float(shear_rate(rpm)) for rpm in rpms}

    if pathway == "newtonian":
        for rpm in rpms:
            a_val = _json_float(fits[rpm].get("A"))
            if a_val is None or a_val <= 0:
                continue
            mu = float(amplitude_to_viscosity([a_val])[0])
            if np.isfinite(mu) and mu > 0:
                out[rpm] = mu
        return out

    if pathway == "strong_shear_thinning":
        for rpm in rpms:
            tau = _json_float(fits[rpm].get("tau_Pa_hit"))
            g = g_arr[rpm]
            if tau is None or tau <= 0 or g <= 0:
                continue
            mu = tau / g * 1000.0
            if np.isfinite(mu) and mu > 0:
                out[rpm] = mu
        return out

    if pathway == "mild_shear_thinning":
        n_val = _json_float(n_stress)
        if n_val is None:
            return out
        rpms_sorted = sorted(rpms, key=lambda r: g_arr[r])
        g_min = g_arr[rpms_sorted[0]]
        a_min = _json_float(fits[rpms_sorted[0]].get("A"))
        if a_min is None or a_min <= 0 or g_min <= 0:
            return out
        mu_ref = float(amplitude_to_viscosity([a_min])[0])
        if not np.isfinite(mu_ref) or mu_ref <= 0:
            return out
        for rpm in rpms:
            g = g_arr[rpm]
            if g <= 0:
                continue
            mu = mu_ref * (g / g_min) ** (n_val - 1.0)
            if np.isfinite(mu) and mu > 0:
                out[rpm] = mu
        return out

    # shear_thickening: amplitude power-law curve
    n_val = _json_float(n_idx)
    if n_val is None:
        return out
    as_arr = np.array([_json_float(fits[r].get("A")) or np.nan for r in rpms], dtype=float)
    g_list = np.array([g_arr[r] for r in rpms], dtype=float)
    valid = np.isfinite(as_arr) & (as_arr > 0)
    if not np.any(valid):
        return out
    mu0 = float(amplitude_to_viscosity([as_arr[valid][np.argmin(g_list[valid])]])[0])
    g0 = float(g_list[valid].min())
    if not np.isfinite(mu0) or mu0 <= 0 or g0 <= 0:
        return out
    k_cp = mu0 * (g0 ** (1.0 - n_val))
    for rpm in rpms:
        g = g_arr[rpm]
        if g <= 0:
            continue
        mu = k_cp * (g ** (n_val - 1.0))
        if np.isfinite(mu) and mu > 0:
            out[rpm] = mu
    return out


def compute_cell_characterization(
    fits: Dict[float, Dict[str, Any]],
    *,
    cell_id: int,
    provisional: bool = False,
    is_partial: bool = False,
) -> Dict[str, Any]:
    """
    Route characterization into Newtonian / mild / strong / thickening pathways.

    Each fit dict must include successful drag-fit fields plus tau_Pa_hit from
    the hitpoint (h_norm = 0 after pretrim).
    """
    base: Dict[str, Any] = {
        "cell_id": int(cell_id),
        "success": False,
        "error": None,
        "provisional": provisional,
        "is_partial": is_partial,
        "pathway": None,
        "mode": None,
        "regime": "undetermined",
        "n_idx": None,
        "n": None,
        "K_Pas_n": None,
        "R2_amplitude": None,
        "R2_powerlaw": None,
        "K_stress": None,
        "n_stress": None,
        "R2_stress": None,
        "viscosity_kcp": None,
        "mu_app_cP": None,
        "A_per_rpm": [],
    }

    good = {
        rpm: f
        for rpm, f in fits.items()
        if f.get("success") and _json_float(f.get("A")) is not None
    }
    if not good:
        base["error"] = "No valid RPM sweeps passed quality gate"
        return base

    rpms = sorted(good.keys())
    as_arr = np.array([float(good[r]["A"]) for r in rpms])
    g_arr = shear_rate(np.array(rpms))

    stress_rows = _build_stress_rows(good)
    k_stress = n_stress = r2_stress = None
    if len(stress_rows) >= 2:
        staged = stage_powerlaw_points(stress_rows)
        if len(staged) >= 2:
            pl_st = fit_stress_powerlaw(
                [r["gamma_dot_1_s"] for r in staged],
                [r["tau_Pa"] for r in staged],
            )
            k_stress = _json_float(pl_st.get("K_stress"))
            n_stress = _json_float(pl_st.get("n_stress"))
            r2_stress = _json_float(pl_st.get("R2_stress"))
    elif len(stress_rows) == 1:
        pl_st = fit_stress_powerlaw(
            [stress_rows[0]["gamma_dot_1_s"]],
            [stress_rows[0]["tau_Pa"]],
        )
        k_stress = _json_float(pl_st.get("K_stress"))
        n_stress = _json_float(pl_st.get("n_stress"))
        r2_stress = _json_float(pl_st.get("R2_stress"))

    pathway = _pathway_from_n_stress(n_stress, len(rpms))

    n_idx = None
    r2_amp = None
    k_pas = None
    if len(rpms) >= 2:
        pl_amp = fit_powerlaw(g_arr, as_arr)
        n_idx = _json_float(pl_amp.get("n"))
        r2_amp = _json_float(pl_amp.get("R2"))

    per_rpm_mu = _per_rpm_viscosity_cp(
        pathway,
        rpms,
        good,
        n_stress=n_stress,
        n_idx=n_idx,
        k_stress=k_stress,
    )

    for rpm in rpms:
        mu_cp = per_rpm_mu.get(rpm)
        if mu_cp is not None:
            good[rpm]["viscosity_kcp"] = mu_cp / 1000.0
            good[rpm]["mu_app_cP"] = mu_cp

    if pathway == "newtonian":
        if len(rpms) == 1:
            mu_cp = per_rpm_mu.get(rpms[0])
            if mu_cp is None:
                base["error"] = "Could not estimate Newtonian viscosity"
                return base
            base.update(
                {
                    "success": True,
                    "pathway": "newtonian",
                    "mode": "newtonian",
                    "regime": "Newtonian",
                    "n_idx": 1.0,
                    "n": 1.0,
                    "K_Pas_n": mu_cp * CP_TO_PAS,
                    "K_stress": k_stress,
                    "n_stress": n_stress,
                    "R2_stress": r2_stress,
                    "viscosity_kcp": mu_cp / 1000.0,
                    "mu_app_cP": mu_cp,
                    "A_per_rpm": [[rpms[0], float(as_arr[0])]],
                }
            )
        else:
            mu_cp = per_rpm_mu.get(rpms[np.argmin(g_arr)])
            if mu_cp is None:
                base["error"] = "Could not estimate Newtonian viscosity"
                return base
            base.update(
                {
                    "success": True,
                    "pathway": "newtonian",
                    "mode": "newtonian",
                    "regime": "Newtonian",
                    "n_idx": 1.0,
                    "n": 1.0,
                    "K_Pas_n": mu_cp * CP_TO_PAS,
                    "R2_amplitude": r2_amp,
                    "R2_powerlaw": r2_amp,
                    "K_stress": k_stress,
                    "n_stress": n_stress,
                    "R2_stress": r2_stress,
                    "viscosity_kcp": mu_cp / 1000.0,
                    "mu_app_cP": mu_cp,
                    "A_per_rpm": [[float(r), float(good[r]["A"])] for r in rpms],
                }
            )
    elif pathway == "strong_shear_thinning":
        mu_cp = per_rpm_mu.get(rpms[np.argmin(g_arr)])
        if mu_cp is None or k_stress is None or n_stress is None:
            base["error"] = "Could not estimate strong shear-thinning characterization"
            return base
        base.update(
            {
                "success": True,
                "pathway": "strong_shear_thinning",
                "mode": "stress_powerlaw",
                "regime": "shear-thinning",
                "n_idx": n_stress,
                "n": n_stress,
                "K_Pas_n": k_stress,
                "R2_amplitude": r2_amp,
                "R2_powerlaw": r2_amp,
                "K_stress": k_stress,
                "n_stress": n_stress,
                "R2_stress": r2_stress,
                "viscosity_kcp": mu_cp / 1000.0,
                "mu_app_cP": mu_cp,
                "A_per_rpm": [[float(r), float(good[r]["A"])] for r in rpms],
            }
        )
    elif pathway == "mild_shear_thinning":
        mu_cp = per_rpm_mu.get(rpms[np.argmin(g_arr)])
        if mu_cp is None or n_stress is None:
            base["error"] = "Could not estimate mild shear-thinning characterization"
            return base
        g0 = float(g_arr.min())
        k_cp = mu_cp * (g0 ** (1.0 - n_stress))
        base.update(
            {
                "success": True,
                "pathway": "mild_shear_thinning",
                "mode": "mixed",
                "regime": "shear-thinning",
                "n_idx": n_stress,
                "n": n_stress,
                "K_Pas_n": k_cp * CP_TO_PAS,
                "R2_amplitude": r2_amp,
                "R2_powerlaw": r2_amp,
                "K_stress": k_stress,
                "n_stress": n_stress,
                "R2_stress": r2_stress,
                "viscosity_kcp": mu_cp / 1000.0,
                "mu_app_cP": mu_cp,
                "A_per_rpm": [[float(r), float(good[r]["A"])] for r in rpms],
            }
        )
    else:  # shear_thickening
        if n_idx is None:
            base["error"] = "Could not estimate shear-thickening characterization"
            return base
        mu_cp = per_rpm_mu.get(rpms[np.argmin(g_arr)])
        if mu_cp is None:
            base["error"] = "Could not estimate shear-thickening viscosity"
            return base
        g0 = float(g_arr.min())
        k_cp = mu_cp * (g0 ** (1.0 - n_idx))
        base.update(
            {
                "success": True,
                "pathway": "shear_thickening",
                "mode": "powerlaw",
                "regime": _regime_label(n_idx),
                "n_idx": n_idx,
                "n": n_idx,
                "K_Pas_n": k_cp * CP_TO_PAS,
                "R2_amplitude": r2_amp,
                "R2_powerlaw": r2_amp,
                "K_stress": k_stress,
                "n_stress": n_stress,
                "R2_stress": r2_stress,
                "viscosity_kcp": mu_cp / 1000.0,
                "mu_app_cP": mu_cp,
                "A_per_rpm": [[float(r), float(good[r]["A"])] for r in rpms],
            }
        )

    return base

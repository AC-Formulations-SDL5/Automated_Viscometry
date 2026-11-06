"""
Structured timer + lightweight Bayesian updates for experiment duration.

Protocol sandwich per window:
  dwell + n_samples * sample_interval + inter_rpm_pause (+ z_move when Z steps)

n_samples ≈ clip(a + b * log10(mu_cP), window_min, floor(duration / interval))
with a thin-fluid prior that stays near the smart-exit floor until ~1e4 cP.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from viscometry.paths import TIMING_MODEL_POSTERIOR

# Hand priors from experiment_history analysis
_DEFAULT = {
    "version": 1,
    "wash_s": {"mean": 220.0, "var": 40.0**2, "n": 9.0},
    "bookend_s": {"mean": 45.0, "var": 20.0**2, "n": 66.0},
    "z_move_s": {"mean": 2.3, "var": 0.5**2, "n": 100.0},
    "n_z": {"mean": 21.0, "var": 6.0**2, "n": 100.0},
    # n_samples = a + b * log10(mu); prior keeps ~3 samples below ~1e4 cP
    "n_samples_a": {"mean": -1.0, "var": 1.0**2, "n": 20.0},
    "n_samples_b": {"mean": 1.0, "var": 0.3**2, "n": 20.0},
    "updates": 0,
}

# Ignore aborted/partial cells when updating n_z; keep prediction from collapsing.
N_Z_MIN_FOR_UPDATE = 10
N_Z_PRED_FLOOR = 15.0
# Discovery ladder wall-clock prior (~4 min for typical 6-rung early-exit probing).
DISCOVERY_PROBE_PHASE_CAP_S = 240.0
DISCOVERY_PROBE_PER_RUNG_S = 35.0


def default_posterior() -> Dict[str, Any]:
    return json.loads(json.dumps(_DEFAULT))


def _param_mean(posterior: Dict[str, Any], key: str, fallback: float) -> float:
    block = posterior.get(key) or {}
    try:
        return float(block.get("mean", fallback))
    except (TypeError, ValueError):
        return float(fallback)


def _param_std(posterior: Dict[str, Any], key: str, fallback: float) -> float:
    block = posterior.get(key) or {}
    try:
        var = float(block.get("var", fallback**2))
        return math.sqrt(max(var, 0.0))
    except (TypeError, ValueError):
        return float(fallback)


def load_posterior(path: Optional[Path] = None) -> Dict[str, Any]:
    target = Path(path) if path is not None else TIMING_MODEL_POSTERIOR
    try:
        if target.is_file():
            with target.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict) and "wash_s" in data:
                base = default_posterior()
                base.update(data)
                # Repair collapsed n_z from partial-row updates without wiping other params.
                try:
                    nz = base.get("n_z") or {}
                    if float(nz.get("mean", 0)) < N_Z_PRED_FLOOR:
                        nz = dict(nz)
                        nz["mean"] = float(N_Z_PRED_FLOOR)
                        nz["var"] = max(float(nz.get("var", 36.0)), 36.0)
                        base["n_z"] = nz
                except Exception:
                    pass
                return base
    except Exception as exc:
        print(f"Warning: timing posterior load failed ({exc}); using hand priors")
    return default_posterior()


def estimate_discovery_probe_phase_s(
    *,
    max_screening_rpms: int = 6,
    probe_duration_s: float = 60.0,
) -> float:
    """Conservative ladder-phase duration before accepted RPMs are known."""
    n = max(1, int(max_screening_rpms))
    per = min(float(DISCOVERY_PROBE_PER_RUNG_S), max(15.0, float(probe_duration_s) * 0.55))
    return float(min(DISCOVERY_PROBE_PHASE_CAP_S, n * per))


def save_posterior(posterior: Dict[str, Any], path: Optional[Path] = None) -> None:
    target = Path(path) if path is not None else TIMING_MODEL_POSTERIOR
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as fh:
            json.dump(posterior, fh, indent=2, ensure_ascii=True)
    except Exception as exc:
        print(f"Warning: timing posterior save failed ({exc})")


def _n_samples_for_viscosity(
    mu_cp: Optional[float],
    *,
    duration_s: float,
    sample_interval_s: float,
    posterior: Dict[str, Any],
) -> float:
    window_min = 3.0
    if sample_interval_s <= 0:
        sample_interval_s = 5.0
    window_max = max(window_min, math.floor(max(duration_s, 0.0) / sample_interval_s))
    a = _param_mean(posterior, "n_samples_a", -1.0)
    b = _param_mean(posterior, "n_samples_b", 1.0)
    if mu_cp is None or not math.isfinite(mu_cp) or mu_cp <= 0:
        return window_min
    n = a + b * math.log10(float(mu_cp))
    return float(min(window_max, max(window_min, n)))


def _window_seconds(
    n_samples: float,
    *,
    dwell_s: float,
    sample_interval_s: float,
    pause_s: float,
    z_move_s: float = 0.0,
) -> float:
    # Last sample lands near n_samples * interval; wall time ≈ that plus dwell/pause.
    sampling = max(0.0, float(n_samples)) * max(0.0, float(sample_interval_s))
    return float(dwell_s) + sampling + float(pause_s) + float(z_move_s)


def predict_cell_seconds(
    *,
    n_rpms: int,
    n_z: Optional[float] = None,
    mu_cp: Optional[float] = None,
    mu_by_rpm: Optional[Dict[float, float]] = None,
    measurement_duration_s: float = 40.0,
    sample_interval_s: float = 5.0,
    dwell_s: float = 2.0,
    inter_rpm_pause_s: float = 2.0,
    discovery_probe_s: float = 0.0,
    posterior: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    """Predict one cell sweep duration (seconds) with a low/high band from n_z."""
    post = posterior if isinstance(posterior, dict) else load_posterior()
    if n_z is not None and math.isfinite(float(n_z)):
        n_z_mean = float(n_z)
    else:
        n_z_mean = max(_param_mean(post, "n_z", 21.0), float(N_Z_PRED_FLOOR))
    n_z_std = _param_std(post, "n_z", 6.0)
    z_move = _param_mean(post, "z_move_s", 2.3)
    n_rpms = max(1, int(n_rpms))

    def _per_rpm_cost(rpm_mu: Optional[float], include_z_move: bool) -> float:
        n_samp = _n_samples_for_viscosity(
            rpm_mu if rpm_mu is not None else mu_cp,
            duration_s=measurement_duration_s,
            sample_interval_s=sample_interval_s,
            posterior=post,
        )
        return _window_seconds(
            n_samp,
            dwell_s=dwell_s,
            sample_interval_s=sample_interval_s,
            pause_s=inter_rpm_pause_s,
            z_move_s=z_move if include_z_move else 0.0,
        )

    def _cell_for_nz(nz: float) -> float:
        nz = max(1.0, float(nz))
        # At each Z: first RPM may include Z move from previous height; approximate
        # one z_move per height (after first) distributed across the RPM loop.
        total = float(discovery_probe_s)
        for zi in range(int(round(nz))):
            for ri in range(n_rpms):
                rpm_mu = None
                if mu_by_rpm:
                    # use mean of provided viscosities as fallback per slot
                    try:
                        rpm_mu = float(next(iter(mu_by_rpm.values())))
                    except StopIteration:
                        rpm_mu = None
                include_z = zi > 0 and ri == 0
                if mu_by_rpm and len(mu_by_rpm) == n_rpms:
                    keys = sorted(mu_by_rpm.keys())
                    rpm_mu = mu_by_rpm.get(keys[ri])
                total += _per_rpm_cost(rpm_mu, include_z)
        return total

    expected = _cell_for_nz(n_z_mean)
    low = _cell_for_nz(max(1.0, n_z_mean - n_z_std))
    high = _cell_for_nz(n_z_mean + n_z_std)
    return {
        "expected_s": float(expected),
        "low_s": float(min(low, expected, high)),
        "high_s": float(max(low, expected, high)),
        "n_z_mean": float(n_z_mean),
    }


def predict_run_seconds(
    *,
    n_cells: int,
    n_rpms: int,
    mu_cp: Optional[float] = None,
    mu_by_rpm: Optional[Dict[float, float]] = None,
    measurement_duration_s: float = 40.0,
    sample_interval_s: float = 5.0,
    dwell_s: float = 2.0,
    inter_rpm_pause_s: float = 2.0,
    discovery_probe_s: float = 0.0,
    n_z: Optional[float] = None,
    remaining_cells: Optional[int] = None,
    elapsed_completed_s: float = 0.0,
    posterior: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    """Predict total run time including wash and bookend overhead."""
    post = posterior if isinstance(posterior, dict) else load_posterior()
    n_cells = max(1, int(n_cells))
    rem = int(remaining_cells) if remaining_cells is not None else n_cells
    rem = max(0, min(rem, n_cells))

    cell = predict_cell_seconds(
        n_rpms=n_rpms,
        n_z=n_z,
        mu_cp=mu_cp,
        mu_by_rpm=mu_by_rpm,
        measurement_duration_s=measurement_duration_s,
        sample_interval_s=sample_interval_s,
        dwell_s=dwell_s,
        inter_rpm_pause_s=inter_rpm_pause_s,
        discovery_probe_s=discovery_probe_s,
        posterior=post,
    )
    wash = _param_mean(post, "wash_s", 220.0)
    bookend = _param_mean(post, "bookend_s", 45.0)

    # Remaining work: rem cells + rem bookends + (rem-1) washes if rem>0 among unfinished.
    # For initial prediction rem==n_cells: n_cells*bookend + (n_cells-1)*wash + n_cells*cell
    remaining_sweep = rem * cell["expected_s"]
    remaining_bookend = rem * bookend
    remaining_wash = max(0, rem - 1) * wash if rem > 0 else 0.0
    # If some cells already done, washes between completed|remaining already spent are in elapsed.
    predicted_total = float(elapsed_completed_s) + remaining_sweep + remaining_bookend + remaining_wash

    low = float(elapsed_completed_s) + rem * cell["low_s"] + remaining_bookend + remaining_wash
    high = float(elapsed_completed_s) + rem * cell["high_s"] + remaining_bookend + remaining_wash
    return {
        "expected_s": predicted_total,
        "low_s": min(low, predicted_total, high),
        "high_s": max(low, predicted_total, high),
        "cell_expected_s": cell["expected_s"],
        "wash_s": wash,
        "bookend_s": bookend,
    }


def _gaussian_update(block: Dict[str, Any], observation: float, obs_var: float = 1.0) -> Dict[str, Any]:
    """Conjugate Normal-Normal update with known observation variance."""
    try:
        prior_mean = float(block.get("mean"))
        prior_var = float(block.get("var"))
        n = float(block.get("n", 1.0))
    except (TypeError, ValueError):
        return block
    if prior_var <= 0 or obs_var <= 0 or not math.isfinite(observation):
        return block
    post_var = 1.0 / (1.0 / prior_var + 1.0 / obs_var)
    post_mean = post_var * (prior_mean / prior_var + observation / obs_var)
    return {"mean": post_mean, "var": post_var, "n": n + 1.0}


def update_posterior_from_rows(
    rows: Sequence[Dict[str, Any]],
    *,
    posterior: Optional[Dict[str, Any]] = None,
    path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Update posterior from saved cell-level training rows.

    Uses actual vs predicted residuals and observed n_z / window sample counts when present.
    """
    post = posterior if isinstance(posterior, dict) else load_posterior()
    try:
        for row in rows:
            if not isinstance(row, dict):
                continue
            level = str(row.get("row_level") or "cell")
            if level == "window":
                mu = row.get("mu_cp")
                n_samp = row.get("n_samples")
                try:
                    if mu is not None and n_samp is not None and float(mu) > 0:
                        # Soft update of a,b via residual of n_samples vs a+b*log10(mu)
                        a = _param_mean(post, "n_samples_a", -1.0)
                        b = _param_mean(post, "n_samples_b", 1.0)
                        pred = a + b * math.log10(float(mu))
                        err = float(n_samp) - pred
                        # Attribute error mostly to intercept
                        post["n_samples_a"] = _gaussian_update(
                            post.get("n_samples_a") or _DEFAULT["n_samples_a"],
                            a + err,
                            obs_var=4.0,
                        )
                except Exception:
                    continue
                continue

            # cell-level
            try:
                n_z = row.get("n_z")
                if n_z is not None and float(n_z) >= float(N_Z_MIN_FOR_UPDATE):
                    post["n_z"] = _gaussian_update(
                        post.get("n_z") or _DEFAULT["n_z"],
                        float(n_z),
                        obs_var=16.0,
                    )
            except Exception:
                pass

            try:
                actual = row.get("actual_duration_s")
                predicted = row.get("predicted_duration_s")
                if actual is not None and predicted is not None:
                    residual = float(actual) - float(predicted)
                    # Softly nudge bookend with a fraction of residual
                    book = _param_mean(post, "bookend_s", 45.0)
                    post["bookend_s"] = _gaussian_update(
                        post.get("bookend_s") or _DEFAULT["bookend_s"],
                        book + 0.25 * residual,
                        obs_var=900.0,
                    )
            except Exception:
                pass

            try:
                inter = row.get("intercell_gap_s")
                if inter is not None and float(inter) > 30:
                    post["wash_s"] = _gaussian_update(
                        post.get("wash_s") or _DEFAULT["wash_s"],
                        float(inter),
                        obs_var=2500.0,
                    )
            except Exception:
                pass

        post["updates"] = int(post.get("updates") or 0) + len(rows)
        save_posterior(post, path=path)
    except Exception as exc:
        print(f"Warning: timing posterior update failed ({exc})")
    return post

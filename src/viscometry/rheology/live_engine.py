"""
Incremental streaming rheology characterization engine.

Controller thread is the sole writer. Reuses live_adapter and prediction math
so batch and live analyses cannot drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from viscometry.rheology.constants import (
    CP_TO_PAS,
    FIT_R2_MIN,
    THICKENING_THRESHOLD,
    THINNING_THRESHOLD,
    shear_rate,
)
from viscometry.rheology.live_adapter import SUMMARY_KEY, fit_sweep_drag, prepare_sweep_arrays
from viscometry.rheology.prediction import amplitude_to_viscosity, fit_powerlaw
from viscometry.rheology.stress_powerlaw import fit_stress_powerlaw, stage_powerlaw_points

SUMMARY_KEY_ALIAS = SUMMARY_KEY


@dataclass
class _SweepPoint:
    h_mm: float
    torque_pct: float
    drag: float
    timestamp: float = 0.0

    def as_measurement_dict(self) -> Dict[str, Any]:
        return {
            "height": self.h_mm,
            "rotational_drag": self.drag,
            "torque_percent": self.torque_pct,
            "timestamp": self.timestamp,
        }


def _h_key(h: float) -> str:
    return f"{float(h):.3f}"


def _json_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if np.isfinite(f) else None


class LiveCellSession:
    """Per-cell incremental characterization state."""

    def __init__(
        self,
        cell_id: int,
        rpms: Sequence[float],
        *,
        torque_floor_pct: float = 0.0,
    ) -> None:
        self.cell_id = int(cell_id)
        self.rpms = [float(r) for r in rpms]
        self.torque_floor_pct = float(torque_floor_pct)
        self.hit_point_z: Optional[float] = None
        self._buffers: Dict[float, Dict[str, _SweepPoint]] = {
            float(r): {} for r in self.rpms
        }
        self._rpm_fits: Dict[float, Dict[str, Any]] = {}
        self._summary: Dict[str, Any] = {}
        self.finalized = False

    def reset(self) -> List[Dict[str, Any]]:
        self.hit_point_z = None
        self._buffers = {float(r): {} for r in self.rpms}
        self._rpm_fits = {}
        self._summary = {}
        self.finalized = False
        return [{"type": "reset", "cell_id": self.cell_id}]

    def _points_for_rpm(self, rpm: float) -> List[Dict[str, Any]]:
        buf = self._buffers.get(float(rpm), {})
        ordered = sorted(buf.values(), key=lambda p: p.h_mm)
        return [p.as_measurement_dict() for p in ordered]

    def _running_h_norm(self, rpm: float, h_mm: float) -> float:
        heights = [p.h_mm for p in self._buffers.get(float(rpm), {}).values()]
        heights.append(float(h_mm))
        h_min = min(heights)
        return float(h_mm) - h_min

    def add_point(
        self,
        h_mm: float,
        rpm: float,
        torque_pct: float,
        *,
        timestamp: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        rpm_f = float(rpm)
        drag = abs(float(torque_pct)) / rpm_f if rpm_f > 0 else 0.0
        ts = float(timestamp or 0.0)

        if rpm_f not in self._buffers:
            self._buffers[rpm_f] = {}

        key = _h_key(h_mm)
        prev = self._buffers[rpm_f].get(key)
        if prev is not None and ts < prev.timestamp:
            return []

        self._buffers[rpm_f][key] = _SweepPoint(
            h_mm=float(h_mm),
            torque_pct=float(torque_pct),
            drag=drag,
            timestamp=ts,
        )

        return [
            {
                "type": "point",
                "cell_id": self.cell_id,
                "rpm": rpm_f,
                "h": float(h_mm),
                "h_norm": self._running_h_norm(rpm_f, h_mm),
                "drag": drag,
                "provisional": not self.finalized,
            }
        ]

    def on_z_slice_complete(self, z_mm: float) -> List[Dict[str, Any]]:
        """Emit status only; analysis runs solely in finalize_cell."""
        return [
            {
                "type": "z_slice",
                "cell_id": self.cell_id,
                "z": float(z_mm),
                "rpms_tested": list(self.rpms),
                "per_rpm_point_counts": {
                    str(r): len(self._buffers.get(r, {})) for r in self.rpms
                },
            }
        ]

    def set_hit_point_z(self, z: Optional[float]) -> List[Dict[str, Any]]:
        """Store hit-point Z for use at finalize; do not fit mid-cell."""
        if z is not None:
            self.hit_point_z = float(z)
        return []

    def finalize_cell(self, *, is_partial: bool = False) -> List[Dict[str, Any]]:
        self.finalized = True
        events: List[Dict[str, Any]] = []
        for rpm in self.rpms:
            fit_evt = self._fit_rpm(rpm, provisional=False)
            if fit_evt:
                events.append(fit_evt)
        summary_evt = self._compute_and_emit_summary(provisional=False, is_partial=is_partial)
        if summary_evt:
            events.append(summary_evt)
        return events

    def _fit_rpm(self, rpm: float, *, provisional: bool) -> Optional[Dict[str, Any]]:
        points = self._points_for_rpm(rpm)
        if len(points) < 4:
            return None

        h_norm, torque_pct, _drag, norm_offset, pretrim_z, pretrim_drag = prepare_sweep_arrays(
            points,
            self.torque_floor_pct,
            self.hit_point_z,
        )
        fit = fit_sweep_drag(h_norm, torque_pct, rpm, norm_offset)
        fit["cell_id"] = self.cell_id
        fit["provisional"] = provisional
        fit["pretrim_z"] = pretrim_z
        fit["pretrim_drag"] = pretrim_drag
        self._rpm_fits[float(rpm)] = fit

        return {
            "type": "rpm_fit",
            "cell_id": self.cell_id,
            "rpm": float(rpm),
            "provisional": provisional,
            "success": bool(fit.get("success")),
            "error": fit.get("error"),
            "A": _json_float(fit.get("A")),
            "B": _json_float(fit.get("B")),
            "hc": _json_float(fit.get("hc")),
            "R2_drag": _json_float(fit.get("R2")),
            "mu_app_cP": _json_float(
                (fit.get("viscosity_kcp") or 0) * 1000.0 if fit.get("viscosity_kcp") else None
            ),
            "viscosity_kcp": _json_float(fit.get("viscosity_kcp")),
            "n_points_used": int(fit.get("n_points_used") or 0),
            "fit_curve_z": fit.get("fit_curve_z") or [],
            "fit_curve_drag": fit.get("fit_curve_drag") or [],
            "pretrim_z": pretrim_z,
            "pretrim_drag": pretrim_drag,
        }

    def _successful_fits(self) -> Dict[float, Dict[str, Any]]:
        return {
            rpm: f
            for rpm, f in self._rpm_fits.items()
            if f.get("success") and _json_float(f.get("A")) is not None
        }

    def _build_stress_rows(self, fits: Dict[float, Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for rpm, fit in fits.items():
            a_val = float(fit["A"])
            g = float(shear_rate(rpm))
            mu_cp = float(amplitude_to_viscosity([a_val])[0])
            tau = mu_cp * CP_TO_PAS * g
            rows.append(
                {
                    "RPM": float(rpm),
                    "gamma_dot_1_s": g,
                    "mu_app_cP": mu_cp,
                    "tau_Pa": tau,
                    "R2_drag": _json_float(fit.get("R2")) or 0.0,
                    "A": a_val,
                }
            )
        return rows

    def _compute_summary(
        self,
        *,
        provisional: bool,
        is_partial: bool = False,
    ) -> Dict[str, Any]:
        fits = self._successful_fits()
        base: Dict[str, Any] = {
            "cell_id": self.cell_id,
            "success": False,
            "error": None,
            "provisional": provisional,
            "is_partial": is_partial,
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

        if not fits:
            base["error"] = "No valid RPM sweeps passed quality gate"
            return base

        rpms = sorted(fits.keys())
        as_arr = np.array([float(fits[r]["A"]) for r in rpms])
        g_arr = shear_rate(np.array(rpms))

        if len(rpms) == 1:
            rpm0 = rpms[0]
            mu_cp = float(amplitude_to_viscosity([as_arr[0]])[0])
            base.update(
                {
                    "success": True,
                    "mode": "newtonian",
                    "regime": "Newtonian",
                    "n_idx": 1.0,
                    "n": 1.0,
                    "K_Pas_n": mu_cp * CP_TO_PAS,
                    "viscosity_kcp": mu_cp / 1000.0,
                    "mu_app_cP": mu_cp,
                    "A_per_rpm": [[rpm0, float(as_arr[0])]],
                }
            )
            stress_rows = self._build_stress_rows(fits)
            if stress_rows:
                pl = fit_stress_powerlaw(
                    [stress_rows[0]["gamma_dot_1_s"]],
                    [stress_rows[0]["tau_Pa"]],
                )
                base["K_stress"] = _json_float(pl.get("K_stress"))
                base["n_stress"] = _json_float(pl.get("n_stress"))
                base["R2_stress"] = _json_float(pl.get("R2_stress"))
            return base

        pl_amp = fit_powerlaw(g_arr, as_arr)
        n_idx = pl_amp["n"]
        mu0 = float(amplitude_to_viscosity([as_arr[np.argmin(g_arr)]])[0])
        g0 = float(g_arr.min())
        k_cp = mu0 * (g0 ** (1.0 - n_idx))
        k_pas = k_cp * CP_TO_PAS

        if n_idx > THICKENING_THRESHOLD:
            regime = "shear-thickening"
        elif n_idx < THINNING_THRESHOLD:
            regime = "shear-thinning"
        else:
            regime = "Newtonian"

        base.update(
            {
                "success": True,
                "mode": "powerlaw",
                "regime": regime,
                "n_idx": _json_float(n_idx),
                "n": _json_float(n_idx),
                "K_Pas_n": _json_float(k_pas),
                "R2_amplitude": _json_float(pl_amp.get("R2")),
                "R2_powerlaw": _json_float(pl_amp.get("R2")),
                "viscosity_kcp": mu0 / 1000.0,
                "mu_app_cP": mu0,
                "A_per_rpm": [[float(r), float(fits[r]["A"])] for r in rpms],
            }
        )

        stress_rows = self._build_stress_rows(fits)
        staged = stage_powerlaw_points(stress_rows)
        if len(staged) >= 2:
            g_st = [r["gamma_dot_1_s"] for r in staged]
            tau_st = [r["tau_Pa"] for r in staged]
            pl_st = fit_stress_powerlaw(g_st, tau_st)
            base["K_stress"] = _json_float(pl_st.get("K_stress"))
            base["n_stress"] = _json_float(pl_st.get("n_stress"))
            base["R2_stress"] = _json_float(pl_st.get("R2_stress"))

        return base

    def _maybe_emit_summary(self, *, provisional: bool) -> Optional[Dict[str, Any]]:
        fits = self._successful_fits()
        if len(fits) < 2:
            return None
        return self._compute_and_emit_summary(provisional=provisional)

    def _compute_and_emit_summary(
        self,
        *,
        provisional: bool,
        is_partial: bool = False,
    ) -> Optional[Dict[str, Any]]:
        summary = self._compute_summary(provisional=provisional, is_partial=is_partial)
        self._summary = summary
        if not summary.get("success") and summary.get("error"):
            return {
                "type": "summary",
                "cell_id": self.cell_id,
                **summary,
            }
        if summary.get("success") or not provisional:
            return {
                "type": "summary",
                "cell_id": self.cell_id,
                **summary,
            }
        return None

    def snapshot(self) -> Dict[str, Any]:
        """JSON-safe full cell state for REST / reconnect."""
        out: Dict[str, Any] = {}
        for rpm, fit in self._rpm_fits.items():
            out[str(float(rpm))] = {
                k: v
                for k, v in fit.items()
                if k not in ("tau", "mu_app")
            }
        if self._summary:
            out[SUMMARY_KEY] = dict(self._summary)
        return out


@dataclass
class CharacterizationManager:
    """Registry of live cell sessions (controller thread only)."""

    torque_floor_pct: float = 0.0
    _sessions: Dict[int, LiveCellSession] = field(default_factory=dict)

    def reset_all(self) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        for session in self._sessions.values():
            events.extend(session.reset())
        self._sessions.clear()
        return events

    def start_cell(self, cell_id: int, rpms: Sequence[float]) -> List[Dict[str, Any]]:
        cid = int(cell_id)
        if cid in self._sessions:
            self._sessions[cid].reset()
        session = LiveCellSession(
            cid,
            rpms,
            torque_floor_pct=self.torque_floor_pct,
        )
        self._sessions[cid] = session
        return [{"type": "reset", "cell_id": cid}]

    def ingest_point(
        self,
        cell_id: int,
        h_mm: float,
        rpm: float,
        torque_pct: float,
        *,
        timestamp: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        session = self._sessions.get(int(cell_id))
        if session is None:
            return []
        return session.add_point(h_mm, rpm, torque_pct, timestamp=timestamp)

    def on_z_slice_complete(self, cell_id: int, z_mm: float) -> List[Dict[str, Any]]:
        session = self._sessions.get(int(cell_id))
        if session is None:
            return []
        return session.on_z_slice_complete(z_mm)

    def set_hit_point_z(self, cell_id: int, z: Optional[float]) -> List[Dict[str, Any]]:
        session = self._sessions.get(int(cell_id))
        if session is None:
            return []
        return session.set_hit_point_z(z)

    def finalize_cell(self, cell_id: int, *, is_partial: bool = False) -> List[Dict[str, Any]]:
        session = self._sessions.get(int(cell_id))
        if session is None:
            return []
        return session.finalize_cell(is_partial=is_partial)

    def get_session(self, cell_id: int) -> Optional[LiveCellSession]:
        return self._sessions.get(int(cell_id))

    def snapshot_all(self) -> Dict[str, Any]:
        return {str(cid): sess.snapshot() for cid, sess in self._sessions.items()}

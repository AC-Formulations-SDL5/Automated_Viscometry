"""
Incremental streaming rheology characterization engine.

Controller thread is the sole writer. Reuses live_adapter and prediction math
so batch and live analyses cannot drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from viscometry.rheology.characterization import compute_cell_characterization
from viscometry.rheology.live_adapter import SUMMARY_KEY, fit_sweep_drag, prepare_sweep_arrays

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
            "torque_pct_hit": _json_float(fit.get("torque_pct_hit")),
            "tau_Pa_hit": _json_float(fit.get("tau_Pa_hit")),
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

    def _compute_summary(
        self,
        *,
        provisional: bool,
        is_partial: bool = False,
    ) -> Dict[str, Any]:
        fits = self._successful_fits()
        summary = compute_cell_characterization(
            fits,
            cell_id=self.cell_id,
            provisional=provisional,
            is_partial=is_partial,
        )
        for rpm, fit in fits.items():
            self._rpm_fits[rpm] = fit
        return summary

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

"""Shared types for Discovery Mode RPM selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Protocol, Tuple, TypedDict

DiscoveryStatus = Literal[
    "probing",
    "converged",
    "converged_by_stability",
    "over_range",
    "under_range",
    "max_iter_reached",
    "probe_failed",
    "uncalibrated_cell",
]


class DiscoveryProbeRecord(TypedDict):
    rpm: float
    torque: float
    eta_est: Optional[float]
    z_mm: float


class DiscoveryResult(TypedDict):
    rpm: Optional[float]
    eta_estimate: Optional[float]
    status: DiscoveryStatus
    iterations: int
    probes: List[DiscoveryProbeRecord]
    target_z_mm: Optional[float]
    material_label: Optional[str]
    from_cache: bool


@dataclass(frozen=True)
class DiscoveryConfig:
    k_bulk: float
    target_torque: float
    torque_window: Tuple[float, float]
    hit_point_offset_mm: float
    valid_rpms: Tuple[float, ...]
    max_iterations: int
    a_cal: float
    b_cal: float
    rpm_min: float = 0.1
    rpm_max: float = 200.0
    rpm_stability_rel_tol: float = 0.05
    over_range_torque_pct: float = 85.0
    under_range_torque_pct: float = 5.0
    cold_start_rpm: float = 5.0
    surface_torque_ref: float = 50.0
    a_cal_r_squared: float = 0.0
    rpm_selection_mode: str = "continuous"


class ViscosityTableRow(TypedDict):
    viscosity_cp: float
    rpm: float
    torque_pct: float


class ProbeExecutor(Protocol):
    """Hardware boundary: one probe at (cell_id, z_mm, rpm) -> mean torque % or None."""

    def __call__(self, cell_id: int, z_mm: float, rpm: float) -> Optional[float]: ...


class MaterialCacheEntry(TypedDict):
    eta_est: float
    rpm: float
    timestamp: str
    cell_id: int

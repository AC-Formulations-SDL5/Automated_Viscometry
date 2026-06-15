"""Shared types for Discovery Mode RPM selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Protocol, Tuple, TypedDict

DiscoveryStatus = Literal[
    "probing",
    "ladder_probing",
    "converged",
    "converged_by_stability",
    "over_range",
    "under_range",
    "max_iter_reached",
    "probe_failed",
    "uncalibrated_cell",
    "ladder_failed",
    "ladder_over_range",
    "ladder_under_range",
]

LadderStatus = Literal["complete", "partial", "failed"]
DiscoveryPath = Literal["newtonian", "non_newtonian"]
LandingStatus = Literal["ok", "high", "low", "na"]


class DiscoveryProbeRecord(TypedDict, total=False):
    rpm: float
    torque: float
    eta_est: Optional[float]
    z_mm: float
    ladder_target_pct: Optional[float]


class DiscoveryResult(TypedDict, total=False):
    rpm: Optional[float]
    eta_estimate: Optional[float]
    status: DiscoveryStatus
    iterations: int
    probes: List[DiscoveryProbeRecord]
    target_z_mm: Optional[float]
    material_label: Optional[str]
    from_cache: bool
    # Stage 2 — pre-descent
    n_probe: Optional[float]
    is_newtonian: Optional[bool]
    power_law_r2: Optional[float]
    discovery_path: Optional[DiscoveryPath]
    rpm_30: Optional[float]
    rpm_40: Optional[float]
    rpm_50: Optional[float]
    rpm_60: Optional[float]
    rpm_70: Optional[float]
    torque_30: Optional[float]
    torque_40: Optional[float]
    torque_50: Optional[float]
    torque_60: Optional[float]
    torque_70: Optional[float]
    T_top_target: Optional[float]
    T_top: Optional[float]
    ladder_status: Optional[LadderStatus]
    # Stage 2 — post-descent
    T_bottom: Optional[float]
    Z_bottom_mm: Optional[float]
    S: Optional[float]
    landing_ok: Optional[bool]
    landing_status: Optional[LandingStatus]


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
    # Stage 2
    discovery_stage2_enabled: bool = True
    ladder_targets: Tuple[float, ...] = (30.0, 40.0, 50.0, 60.0, 70.0)
    ladder_tolerance_pct: float = 2.5
    newtonian_n_threshold: float = 0.975
    squeeze_boundary_base: float = 0.6
    hello_probe_rpm: float = 5.0
    ladder_max_iterations_per_target: int = 3
    landing_torque_window: Tuple[float, float] = (45.0, 55.0)
    min_ladder_points_for_fit: int = 3
    min_power_law_r_squared: float = 0.85


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

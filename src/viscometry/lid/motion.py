"""Single-axis plans for the lid pickup tool.

Every segment changes exactly one of X, Y, or Z. Horizontal travel happens at
Z = 0. The engage sequence descends into the large hole, shifts in -Y, then
lifts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from viscometry.run.cells import global_cell_to_row_and_local
from viscometry.run.settings import ROWS, Y_OFFSET

CLEARANCE_Z = 0.0
POSE_MATCH_MM = 0.2
Z_CLEARANCE_TOL_MM = 0.05
POSITION_MATCH_MM = 0.3
TRAVEL_FEED_MM_PER_MIN = 1500
ENGAGE_FEED_MM_PER_MIN = 300

XY_JOG_STEPS_MM = (0.1, 1.0, 10.0)
Z_JOG_STEPS_MM = (0.1, 1.0, 10.0)


class LidMotionError(ValueError):
    """A lid plan or jog request violates the single-axis safety rules."""


@dataclass(frozen=True)
class Pose:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class Segment:
    axis: str
    target: float
    feed: int

    def apply(self, pose: Pose) -> Pose:
        if self.axis == "x":
            return Pose(self.target, pose.y, pose.z)
        if self.axis == "y":
            return Pose(pose.x, self.target, pose.z)
        if self.axis == "z":
            return Pose(pose.x, pose.y, self.target)
        raise LidMotionError(f"Unknown axis '{self.axis}'")


def pose_dict(pose: Optional[Pose]) -> Optional[dict]:
    if pose is None:
        return None
    return {"x": round(pose.x, 3), "y": round(pose.y, 3), "z": round(pose.z, 3)}


def pose_from(value) -> Optional[Pose]:
    if not isinstance(value, dict):
        return None
    try:
        return Pose(float(value["x"]), float(value["y"]), float(value["z"]))
    except (KeyError, TypeError, ValueError):
        return None


def _near(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def _matches_step(delta: float, steps: tuple[float, ...]) -> bool:
    magnitude = abs(delta)
    return any(math.isclose(magnitude, step, rel_tol=0.0, abs_tol=1e-6) for step in steps)


def cell_delta(global_cell: int) -> tuple[float, float]:
    """Return (dx, dy) from cell 1 to a global cell, using the sample grid."""
    row, local = global_cell_to_row_and_local(global_cell)
    base_x = {int(item["row_number"]): float(item["base_x"]) for item in ROWS}
    if row not in base_x or 1 not in base_x:
        raise LidMotionError(f"No X origin for row {row}")
    dx = base_x[row] - base_x[1]
    dy = float(local - 1) * float(Y_OFFSET)
    return dx, dy


def cell_poses(cell1_large: Pose, cell1_small: Pose, global_cell: int) -> tuple[Pose, Pose]:
    dx, dy = cell_delta(global_cell)
    large = Pose(cell1_large.x + dx, cell1_large.y + dy, cell1_large.z)
    small = Pose(cell1_small.x + dx, cell1_small.y + dy, cell1_small.z)
    return large, small


def validate_trapped_pose(large: Pose, trapped: Pose) -> None:
    """Require a pure -Y shift from the large hole into the small hole."""
    if not _near(large.x, trapped.x, POSE_MATCH_MM):
        raise LidMotionError("Trapped pose X must match the large-hole pose.")
    if not _near(large.z, trapped.z, POSE_MATCH_MM):
        raise LidMotionError("Trapped pose Z must match the large-hole pose.")
    if trapped.y >= large.y - POSE_MATCH_MM:
        raise LidMotionError("Trapped pose must shift in -Y from the large hole.")


def single_axis_segment(
    current: Pose,
    feed: int,
    x: Optional[float] = None,
    y: Optional[float] = None,
    z: Optional[float] = None,
) -> Segment:
    specified = [(name, value) for name, value in (("x", x), ("y", y), ("z", z)) if value is not None]
    if len(specified) != 1:
        raise LidMotionError("A lid move must change exactly one axis.")
    axis, target = specified[0]
    target_f = float(target)
    if _near(getattr(current, axis), target_f, 1e-6):
        raise LidMotionError("Segment does not move.")
    return Segment(axis, target_f, int(feed))


def assert_single_axis_plan(start: Pose, segments: list[Segment]) -> None:
    pose = start
    for seg in segments:
        end = seg.apply(pose)
        moved = [
            axis
            for axis, amount in (
                ("x", abs(end.x - pose.x)),
                ("y", abs(end.y - pose.y)),
                ("z", abs(end.z - pose.z)),
            )
            if amount > 1e-9
        ]
        if moved != [seg.axis]:
            raise LidMotionError("A lid move must change exactly one axis.")
        pose = end


def _feed_for(pose: Pose, axis: str) -> int:
    if axis == "z" or abs(pose.z) > Z_CLEARANCE_TOL_MM:
        return ENGAGE_FEED_MM_PER_MIN
    return TRAVEL_FEED_MM_PER_MIN


def _append(segments: list[Segment], pose: Pose, axis: str, target: float) -> Pose:
    if _near(getattr(pose, axis), target, 1e-6):
        return pose
    segment = single_axis_segment(pose, feed=_feed_for(pose, axis), **{axis: target})
    segments.append(segment)
    return segment.apply(pose)


def plan_pickup(current: Pose, large: Pose, small: Pose) -> list[Segment]:
    """Raise to Z = 0, move X then Y above the large hole, descend, shift -Y, lift."""
    validate_trapped_pose(large, small)
    segments: list[Segment] = []
    pose = current
    pose = _append(segments, pose, "z", CLEARANCE_Z)
    pose = _append(segments, pose, "x", large.x)
    pose = _append(segments, pose, "y", large.y)
    pose = _append(segments, pose, "z", large.z)
    pose = _append(segments, pose, "y", small.y)
    pose = _append(segments, pose, "z", CLEARANCE_Z)
    assert_single_axis_plan(current, segments)
    return segments


def plan_return(current: Pose, large: Pose, small: Pose) -> list[Segment]:
    """Lower at the trapped pose, shift back to the large hole, and lift the tool."""
    validate_trapped_pose(large, small)
    if abs(current.z) > Z_CLEARANCE_TOL_MM:
        raise LidMotionError("Return lid starts at Z = 0.")
    if abs(current.x - small.x) > POSITION_MATCH_MM or abs(current.y - small.y) > POSITION_MATCH_MM:
        raise LidMotionError("Return lid starts at the trapped position.")
    segments: list[Segment] = []
    pose = current
    pose = _append(segments, pose, "z", small.z)
    pose = _append(segments, pose, "y", large.y)
    pose = _append(segments, pose, "z", CLEARANCE_Z)
    assert_single_axis_plan(current, segments)
    return segments


def plan_move_to_parking_pose(current: Pose, parking: Pose) -> list[Segment]:
    """Move an empty tool to a taught parking pose: Z to 0, then X, then Y."""
    segments: list[Segment] = []
    pose = current
    pose = _append(segments, pose, "z", CLEARANCE_Z)
    pose = _append(segments, pose, "x", parking.x)
    pose = _append(segments, pose, "y", parking.y)
    assert_single_axis_plan(current, segments)
    return segments


def parking_pose_for_cell(cell: int, row1: Pose, row4: Pose) -> Pose:
    if cell < 1 or cell > 18:
        raise LidMotionError("Cell must be between 1 and 18.")
    if cell <= 12:
        return row1
    return row4


def dock_for_cell(cell: int) -> int:
    """Map a sample cell to dock 1, 2, or 3 by sample row."""
    if cell < 1 or cell > 18:
        raise LidMotionError("Cell must be between 1 and 18.")
    if cell <= 6:
        return 1
    if cell <= 12:
        return 2
    return 3


def plan_parking_route(current: Pose, cell: int, row1: Pose, row4: Pose) -> list[Segment]:
    """Highway route: X onto row 1 or row 4, then Y to the back of that column.

    Cells 1–12 use the row 1 pose. Cells 13–18 use the row 4 pose.
    """
    target = parking_pose_for_cell(cell, row1, row4)
    return plan_move_to_parking_pose(current, target)


def plan_park_lid(
    current: Pose,
    *,
    highway: Pose,
    dock_xy: Pose,
    dock_z: float,
    large: Pose,
    small: Pose,
) -> list[Segment]:
    """Carry a held lid to a dock via the highway, drop, release +Y, and lift.

    Approach dock XY with the tool still in the small/trapped hole, lower to
    dock_z, shift into the large hole, then raise to Z = 0.
    """
    validate_trapped_pose(large, small)
    if abs(current.z) > Z_CLEARANCE_TOL_MM:
        raise LidMotionError("Park lid starts at Z = 0.")
    if float(dock_z) >= -Z_CLEARANCE_TOL_MM:
        raise LidMotionError("Dock drop Z must be below Z = 0.")
    release_dy = large.y - small.y
    if release_dy <= POSE_MATCH_MM:
        raise LidMotionError("Release shift must be a positive +Y distance.")
    release_y = float(dock_xy.y) + release_dy

    segments: list[Segment] = []
    pose = current
    pose = _append(segments, pose, "z", CLEARANCE_Z)
    pose = _append(segments, pose, "x", highway.x)
    pose = _append(segments, pose, "y", highway.y)
    pose = _append(segments, pose, "x", dock_xy.x)
    pose = _append(segments, pose, "y", dock_xy.y)
    pose = _append(segments, pose, "z", float(dock_z))
    pose = _append(segments, pose, "y", release_y)
    pose = _append(segments, pose, "z", CLEARANCE_Z)
    assert_single_axis_plan(current, segments)
    return segments


def plan_home(current: Pose) -> list[Segment]:
    """Raise to Z = 0 if needed, then move X to 0, then Y to 0."""
    segments: list[Segment] = []
    pose = current
    pose = _append(segments, pose, "z", CLEARANCE_Z)
    pose = _append(segments, pose, "x", 0.0)
    pose = _append(segments, pose, "y", 0.0)
    assert_single_axis_plan(current, segments)
    return segments


def validate_jog(axis: str, delta: float, z: float, *, lid_held: bool, needs_retract: bool) -> None:
    if axis not in ("x", "y", "z"):
        raise LidMotionError("Jog axis must be x, y, or z.")
    if not math.isfinite(delta) or _near(delta, 0.0, 1e-9):
        raise LidMotionError("Jog step must be non-zero.")
    if needs_retract:
        if axis != "z" or delta <= 0:
            raise LidMotionError("Raise Z to 0 before any other move.")
        if not _matches_step(delta, Z_JOG_STEPS_MM):
            raise LidMotionError("Z jog step must be 0.1, 1, or 10 mm.")
        return
    if lid_held:
        raise LidMotionError("Jog is disabled while a lid is held. Use Return lid or Park lid.")
    # X/Y may be jogged below Z = 0 while teaching inside a lid.
    if axis in ("x", "y"):
        if not _matches_step(delta, XY_JOG_STEPS_MM):
            raise LidMotionError(f"{axis.upper()} jog step must be 0.1, 1, or 10 mm.")
        return
    if not _matches_step(delta, Z_JOG_STEPS_MM):
        raise LidMotionError("Z jog step must be 0.1, 1, or 10 mm.")


def jog_target(current: Pose, axis: str, delta: float) -> Pose:
    value = getattr(current, axis) + delta
    if axis == "z":
        value = min(CLEARANCE_Z, value)
        return Pose(current.x, current.y, value)
    if axis == "x":
        return Pose(value, current.y, current.z)
    if axis == "y":
        return Pose(current.x, value, current.z)
    raise LidMotionError(f"Unknown axis '{axis}'")


def jog_feed(axis: str, z: float) -> int:
    if axis == "z" or abs(z) > Z_CLEARANCE_TOL_MM:
        return ENGAGE_FEED_MM_PER_MIN
    return TRAVEL_FEED_MM_PER_MIN

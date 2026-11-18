"""Run-time lid pickup + park using the experiment CNC instance.

Testing-tab LidToolService is blocked while is_running. Experiment runs call
these helpers with the controller's shared CNC so serial ownership stays single.
"""

from __future__ import annotations

from typing import Callable, Optional, Sequence

from viscometry.hardware.cnc import CNCMotionAbort, CNCMotionError, CNC_Machine
from viscometry.lid.calibration import load_lid_calibration
from viscometry.lid.motion import (
    Z_CLEARANCE_TOL_MM,
    LidMotionError,
    Pose,
    assert_single_axis_plan,
    cell_poses,
    dock_for_cell,
    highway_id_for_cell,
    highway_key_for_cell,
    plan_park_lid,
    plan_pickup,
    pose_from,
    validate_trapped_pose,
)


class LidRunError(RuntimeError):
    """Lid pickup/park failed during an experiment run."""


def _calibration() -> dict:
    return load_lid_calibration()


def cell1_pair_ready(cal: Optional[dict] = None) -> bool:
    data = cal if cal is not None else _calibration()
    large = pose_from(data.get("cell1_large"))
    small = pose_from(data.get("cell1_small"))
    if large is None or small is None:
        return False
    try:
        validate_trapped_pose(large, small)
    except LidMotionError:
        return False
    return True


def park_ready_for_cell(cell: int, cal: Optional[dict] = None) -> bool:
    """True when pickup poses + that cell's highway + dock are taught."""
    try:
        cell_id = int(cell)
    except (TypeError, ValueError):
        return False
    if cell_id < 1 or cell_id > 18:
        return False
    data = cal if cal is not None else _calibration()
    if not cell1_pair_ready(data):
        return False
    highway = pose_from(data.get(highway_key_for_cell(cell_id)))
    if highway is None:
        return False
    dock_id = dock_for_cell(cell_id)
    dock_xy = pose_from(data.get(f"dock{dock_id}_xy"))
    if dock_xy is None:
        return False
    try:
        dock_z = float(data.get(f"dock{dock_id}_z"))
    except (TypeError, ValueError):
        return False
    return dock_z < -Z_CLEARANCE_TOL_MM


def readiness_for_cells(cells: Sequence[int]) -> dict:
    """Summarize lid readiness for the given cells."""
    cal = _calibration()
    pair_ok = cell1_pair_ready(cal)
    details = {}
    not_ready = []
    for raw in cells:
        try:
            cell_id = int(raw)
        except (TypeError, ValueError):
            continue
        ready = park_ready_for_cell(cell_id, cal)
        details[str(cell_id)] = {
            "ready": ready,
            "highway": highway_id_for_cell(cell_id) if 1 <= cell_id <= 18 else None,
            "dock": dock_for_cell(cell_id) if 1 <= cell_id <= 18 else None,
        }
        if not ready:
            not_ready.append(cell_id)
    return {
        "cell1_ready": pair_ok,
        "cells": details,
        "not_ready": not_ready,
        "all_ready": pair_ok and not not_ready,
    }


def _poses_for_cell(cell: int, cal: dict) -> tuple[Pose, Pose]:
    large = pose_from(cal.get("cell1_large"))
    small = pose_from(cal.get("cell1_small"))
    if large is None or small is None:
        raise LidRunError("Teach the large-hole and trapped poses on cell 1 first.")
    try:
        validate_trapped_pose(large, small)
    except LidMotionError as exc:
        raise LidRunError(str(exc)) from exc
    return cell_poses(large, small, cell)


def _highway_and_dock(cell: int, cal: dict) -> tuple[Pose, Pose, float]:
    highway_id = highway_id_for_cell(cell)
    highway = pose_from(cal.get(highway_key_for_cell(cell)))
    if highway is None:
        raise LidRunError(f"Highway {highway_id} is not saved yet.")
    dock_id = dock_for_cell(cell)
    dock_xy = pose_from(cal.get(f"dock{dock_id}_xy"))
    if dock_xy is None:
        raise LidRunError(f"Dock {dock_id} XY is not saved yet.")
    try:
        dock_z = float(cal.get(f"dock{dock_id}_z"))
    except (TypeError, ValueError) as exc:
        raise LidRunError(f"Dock {dock_id} drop Z is not saved yet.") from exc
    if dock_z >= -Z_CLEARANCE_TOL_MM:
        raise LidRunError(f"Dock {dock_id} drop Z must be below Z = 0.")
    return highway, dock_xy, dock_z


def _ensure_in_bounds(pose: Pose) -> None:
    if not (
        CNC_Machine.X_LOW_BOUND <= pose.x <= CNC_Machine.X_HIGH_BOUND
        and CNC_Machine.Y_LOW_BOUND <= pose.y <= CNC_Machine.Y_HIGH_BOUND
        and CNC_Machine.Z_LOW_BOUND <= pose.z <= CNC_Machine.Z_HIGH_BOUND
    ):
        raise LidRunError(
            f"Lid move would leave machine bounds "
            f"(X {pose.x:.3f}, Y {pose.y:.3f}, Z {pose.z:.3f})."
        )


def _ensure_plan(current: Pose, segments) -> None:
    try:
        assert_single_axis_plan(current, segments)
    except LidMotionError as exc:
        raise LidRunError(str(exc)) from exc
    pose = current
    for segment in segments:
        pose = segment.apply(pose)
        _ensure_in_bounds(pose)


def _read_pose(cnc: CNC_Machine) -> Pose:
    try:
        raw = cnc.read_position(allow_abort=True)
    except CNCMotionAbort as exc:
        raise LidRunError("Lid motion stopped before reading position.") from exc
    except CNCMotionError as exc:
        raise LidRunError(f"Unable to read CNC position: {exc}") from exc
    return Pose(float(raw[0]), float(raw[1]), float(raw[2]))


def pickup_and_park_lid(
    cnc: CNC_Machine,
    cell: int,
    *,
    on_status: Optional[Callable[[str], None]] = None,
    on_position: Optional[Callable[[float, float, float], None]] = None,
) -> None:
    """Pick up the lid on ``cell`` and park it on that cell's dock.

    Uses the caller's CNC. Abort is honored via ``cnc.should_abort``.
    """
    try:
        cell_id = int(cell)
    except (TypeError, ValueError) as exc:
        raise LidRunError("Cell must be between 1 and 18.") from exc
    if cell_id < 1 or cell_id > 18:
        raise LidRunError("Cell must be between 1 and 18.")
    if not park_ready_for_cell(cell_id):
        raise LidRunError(
            f"Cell {cell_id} is not ready for lid pickup and park "
            "(need cell-1 poses, highway, and dock)."
        )

    cal = _calibration()
    large, small = _poses_for_cell(cell_id, cal)
    highway, dock_xy, dock_z = _highway_and_dock(cell_id, cal)
    dock_id = dock_for_cell(cell_id)

    def status(message: str) -> None:
        if on_status is not None:
            on_status(message)

    def emit_pos(pos) -> None:
        if on_position is not None:
            on_position(float(pos[0]), float(pos[1]), float(pos[2]))

    status(f"Picking up lid from cell {cell_id}")
    current = _read_pose(cnc)
    emit_pos((current.x, current.y, current.z))
    try:
        pickup_segments = plan_pickup(current, large, small)
    except LidMotionError as exc:
        raise LidRunError(str(exc)) from exc
    _ensure_plan(current, pickup_segments)
    try:
        after_pickup = cnc.execute_segments(
            pickup_segments,
            on_segment=lambda pos, _seg: emit_pos(pos),
            allow_abort=True,
        )
    except CNCMotionAbort as exc:
        if exc.position is not None:
            emit_pos(exc.position)
        raise LidRunError(f"Lid pickup stopped for cell {cell_id}.") from exc
    except CNCMotionError as exc:
        raise LidRunError(f"Lid pickup failed for cell {cell_id}: {exc}") from exc

    held = Pose(float(after_pickup[0]), float(after_pickup[1]), float(after_pickup[2]))
    emit_pos(after_pickup)
    if abs(held.z) > Z_CLEARANCE_TOL_MM:
        raise LidRunError(f"Lid pickup for cell {cell_id} did not finish at Z = 0.")

    status(f"Parking lid from cell {cell_id} on dock {dock_id}")
    try:
        park_segments = plan_park_lid(
            held,
            highway=highway,
            dock_xy=dock_xy,
            dock_z=dock_z,
            large=large,
            small=small,
        )
    except LidMotionError as exc:
        raise LidRunError(str(exc)) from exc
    _ensure_plan(held, park_segments)
    try:
        after_park = cnc.execute_segments(
            park_segments,
            on_segment=lambda pos, _seg: emit_pos(pos),
            allow_abort=True,
        )
    except CNCMotionAbort as exc:
        if exc.position is not None:
            emit_pos(exc.position)
        raise LidRunError(
            f"Lid park stopped for cell {cell_id}; lid may still be on the tool."
        ) from exc
    except CNCMotionError as exc:
        raise LidRunError(f"Lid park failed for cell {cell_id}: {exc}") from exc

    parked = Pose(float(after_park[0]), float(after_park[1]), float(after_park[2]))
    emit_pos(after_park)
    if abs(parked.z) > Z_CLEARANCE_TOL_MM:
        raise LidRunError(f"Lid park for cell {cell_id} did not finish at Z = 0.")
    status(f"Parked lid from cell {cell_id} on dock {dock_id}")

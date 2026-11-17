"""Testing-tab session for teaching and rehearsing lid pickup."""

from __future__ import annotations

import os
import threading
from typing import Optional

from viscometry.hardware.cnc import CNCMotionAbort, CNCMotionError, CNC_Machine
from viscometry.lid.calibration import load_lid_calibration, save_lid_calibration
from viscometry.lid.motion import (
    CLEARANCE_Z,
    POSITION_MATCH_MM,
    Pose,
    Z_CLEARANCE_TOL_MM,
    assert_single_axis_plan,
    cell_poses,
    dock_for_cell,
    highway_id_for_cell,
    highway_key_for_cell,
    jog_feed,
    jog_target,
    plan_home,
    plan_move_to_parking_pose,
    plan_park_lid,
    plan_pickup,
    plan_return,
    pose_dict,
    pose_from,
    validate_jog,
    validate_trapped_pose,
    LidMotionError,
)

SAVE_POSES = (
    "cell1_large",
    "cell1_small",
    "parking_row1",
    "parking_row4",
    "parking_row8",
    "dock1_xy",
    "dock1_z",
    "dock2_xy",
    "dock2_z",
    "dock3_xy",
    "dock3_z",
)
_POSE_LABELS = {
    "cell1_large": "large-hole pose on cell 1",
    "cell1_small": "trapped pose on cell 1",
    "parking_row1": "highway 1",
    "parking_row4": "highway 4",
    "parking_row8": "highway 8",
    "dock1_xy": "dock 1 XY",
    "dock1_z": "dock 1 drop Z",
    "dock2_xy": "dock 2 XY",
    "dock2_z": "dock 2 drop Z",
    "dock3_xy": "dock 3 XY",
    "dock3_z": "dock 3 drop Z",
}
_HIGHWAY_POSES = ("parking_row1", "parking_row4", "parking_row8")
_HIGHWAY_ROW_TO_KEY = {
    1: "parking_row1",
    4: "parking_row4",
    8: "parking_row8",
}
_DOCK_XY_POSES = ("dock1_xy", "dock2_xy", "dock3_xy")
_DOCK_Z_POSES = ("dock1_z", "dock2_z", "dock3_z")


class LidToolError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class LidToolService:
    def __init__(self, web):
        self.web = web
        self.position: Optional[Pose] = None
        self.position_known = False
        self.lid_held_cell: Optional[int] = None
        self.needs_retract = False
        self.engaged_cell: Optional[int] = None
        self.shift_completed = False
        self.dock_release_completed = False
        self._park_release_y: Optional[float] = None
        self._park_dock_x: Optional[float] = None
        self.busy = False
        self.last_error: Optional[str] = None
        self._abort = False
        self._motion_lock = threading.Lock()

    def request_stop(self) -> None:
        self._abort = True
        if self.busy:
            self.last_error = "Stop requested"

    def status(self) -> dict:
        cal = load_lid_calibration()
        large = pose_from(cal.get("cell1_large"))
        small = pose_from(cal.get("cell1_small"))
        cells = {}
        pair_ok = False
        if large is not None and small is not None:
            try:
                validate_trapped_pose(large, small)
                pair_ok = True
            except LidMotionError:
                pair_ok = False
        if pair_ok:
            for cell_id in range(1, 19):
                cell_large, cell_small = cell_poses(large, small, cell_id)
                cells[str(cell_id)] = {
                    "large": pose_dict(cell_large),
                    "small": pose_dict(cell_small),
                    "dock": dock_for_cell(cell_id),
                    "highway": highway_id_for_cell(cell_id),
                }
        shift_y = None
        if pair_ok and large is not None and small is not None:
            shift_y = round(small.y - large.y, 3)
        docks = {}
        for dock_id in (1, 2, 3):
            xy = pose_from(cal.get(f"dock{dock_id}_xy"))
            z_raw = cal.get(f"dock{dock_id}_z")
            try:
                z_val = float(z_raw) if z_raw is not None else None
            except (TypeError, ValueError):
                z_val = None
            docks[str(dock_id)] = {
                "xy": pose_dict(xy) if xy else None,
                "z": z_val,
                "ready": xy is not None and z_val is not None and z_val < -Z_CLEARANCE_TOL_MM,
            }
        held_dock = dock_for_cell(self.lid_held_cell) if self.lid_held_cell else None
        held_highway = highway_id_for_cell(self.lid_held_cell) if self.lid_held_cell else None
        return {
            "enabled": not bool(self.web.is_running),
            "busy": self.busy,
            "position_known": self.position_known,
            "position": pose_dict(self.position) if self.position_known and self.position else None,
            "lid_held_cell": self.lid_held_cell,
            "lid_held_dock": held_dock,
            "lid_held_highway": held_highway,
            "needs_retract": self.needs_retract,
            "last_error": self.last_error,
            "calibration": {
                "cell1_large": pose_dict(large) if large else None,
                "cell1_small": pose_dict(small) if small else None,
                "parking_row1": cal.get("parking_row1"),
                "parking_row4": cal.get("parking_row4"),
                "parking_row8": cal.get("parking_row8"),
                "dock1_xy": cal.get("dock1_xy"),
                "dock1_z": cal.get("dock1_z"),
                "dock2_xy": cal.get("dock2_xy"),
                "dock2_z": cal.get("dock2_z"),
                "dock3_xy": cal.get("dock3_xy"),
                "dock3_z": cal.get("dock3_z"),
                "docks": docks,
                "clearance_z": CLEARANCE_Z,
                "updated_at": cal.get("updated_at"),
                "shift_y": shift_y,
                "cell1_ready": pair_ok,
            },
            "cells": cells,
        }

    def read_position(self) -> dict:
        self._acquire()
        try:
            cnc = self._machine()
            cnc.should_abort = self._should_abort
            try:
                raw = cnc.read_position(allow_abort=True)
            except CNCMotionAbort as exc:
                self._apply_abort_position(exc)
                self.last_error = "Lid motion stopped"
                raise LidToolError("Lid motion stopped", 409) from exc
            except CNCMotionError as exc:
                self.last_error = str(exc)
                raise LidToolError(str(exc), 503) from exc
            self._set_position(Pose(*raw))
            self.web.update_status("Testing: read lid tool position")
            return self._ok("Machine position updated")
        finally:
            self._release()

    def jog(self, axis: str, delta: float) -> dict:
        self._acquire()
        try:
            self._require_known()
            assert self.position is not None
            try:
                validate_jog(
                    axis,
                    delta,
                    self.position.z,
                    lid_held=self.lid_held_cell is not None,
                    needs_retract=self.needs_retract,
                )
            except LidMotionError as exc:
                raise LidToolError(str(exc)) from exc
            target = jog_target(self.position, axis, delta)
            if (
                abs(target.x - self.position.x) <= 1e-6
                and abs(target.y - self.position.y) <= 1e-6
                and abs(target.z - self.position.z) <= 1e-6
            ):
                raise LidToolError("Already at Z = 0.")
            self._ensure_in_bounds(target)
            feed = jog_feed(axis, self.position.z)
            segment = _segment(self.position, axis, getattr(target, axis), feed)
            self._run_segments([segment])
            self._clear_retract_if_clear()
            self.web.update_status(f"Testing: jog {axis.upper()} to {getattr(self.position, axis):.3f}")
            return self._ok(f"Jogged {axis.upper()} to {getattr(self.position, axis):.3f}")
        finally:
            self._release()

    def save_pose(self, name: str) -> dict:
        self._acquire()
        try:
            self._require_known()
            assert self.position is not None
            if name not in SAVE_POSES:
                raise LidToolError(f"Unknown pose '{name}'.")
            if self.lid_held_cell is not None:
                raise LidToolError("Return or park the lid before saving a pose.")
            if self.needs_retract:
                raise LidToolError("Raise Z to 0 before saving a pose.")
            data = load_lid_calibration()
            if name in _HIGHWAY_POSES or name in _DOCK_XY_POSES:
                if abs(self.position.z) > Z_CLEARANCE_TOL_MM:
                    raise LidToolError("That pose is saved at Z = 0.")
                data[name] = pose_dict(Pose(self.position.x, self.position.y, 0.0))
                save_lid_calibration(data)
                label = _POSE_LABELS[name]
                self.web.update_status(f"Testing: saved {label}")
                return self._ok(f"Saved {label}.")
            if name in _DOCK_Z_POSES:
                if abs(self.position.z) <= Z_CLEARANCE_TOL_MM:
                    raise LidToolError("Dock drop Z must be below Z = 0.")
                dock_id = int(name[4])
                xy = pose_from(data.get(f"dock{dock_id}_xy"))
                if xy is None:
                    raise LidToolError(f"Save dock {dock_id} XY at Z = 0 before the drop Z.")
                if (
                    abs(self.position.x - xy.x) > POSITION_MATCH_MM
                    or abs(self.position.y - xy.y) > POSITION_MATCH_MM
                ):
                    raise LidToolError(
                        f"Dock {dock_id} drop Z must be taught at the saved dock XY."
                    )
                data[name] = round(self.position.z, 3)
                save_lid_calibration(data)
                label = _POSE_LABELS[name]
                self.web.update_status(f"Testing: saved {label}")
                return self._ok(f"Saved {label}.")
            if name == "cell1_large":
                data["cell1_large"] = pose_dict(self.position)
                small = pose_from(data.get("cell1_small"))
                cleared = False
                if small is not None:
                    try:
                        validate_trapped_pose(self.position, small)
                    except LidMotionError:
                        data["cell1_small"] = None
                        cleared = True
                save_lid_calibration(data)
                message = "Saved the large-hole pose on cell 1."
                if cleared:
                    message += " The trapped pose was cleared because it no longer matches."
                self.web.update_status("Testing: saved large-hole pose")
                return self._ok(message)
            large = pose_from(data.get("cell1_large"))
            if large is None:
                raise LidToolError("Save the large-hole pose before the trapped pose.")
            try:
                validate_trapped_pose(large, self.position)
            except LidMotionError as exc:
                raise LidToolError(str(exc)) from exc
            data["cell1_small"] = pose_dict(self.position)
            save_lid_calibration(data)
            self.web.update_status("Testing: saved trapped pose")
            return self._ok("Saved the trapped pose on cell 1.")
        finally:
            self._release()

    def pickup(self, cell: int) -> dict:
        self._acquire()
        try:
            self._require_known()
            if self.needs_retract:
                raise LidToolError("Raise Z to 0 before picking up a lid.")
            if self.lid_held_cell is not None:
                raise LidToolError("A lid is already on the tool. Return or park it first.")
            large, small = self._poses_for_cell(cell)
            self.engaged_cell = cell
            self.shift_completed = False
            self.dock_release_completed = False
            self._clear_park_release_track()
            try:
                segments = plan_pickup(self.position, large, small)
            except LidMotionError as exc:
                raise LidToolError(str(exc)) from exc
            self._run_segments(segments, small=small)
            if self.position is None or abs(self.position.z) > Z_CLEARANCE_TOL_MM:
                self.needs_retract = True
                raise LidToolError("Pickup did not finish at Z = 0.", 409)
            self.lid_held_cell = cell
            self.needs_retract = False
            self.web.update_status(f"Testing: picked up lid from cell {cell}")
            return self._ok(f"Picked up the lid from cell {cell}.")
        finally:
            self._release()

    def return_lid(self) -> dict:
        self._acquire()
        try:
            self._require_known()
            if self.lid_held_cell is None:
                raise LidToolError("No lid is on the tool.")
            if self.needs_retract:
                raise LidToolError("Raise Z to 0 before returning the lid.")
            cell = int(self.lid_held_cell)
            large, small = self._poses_for_cell(cell)
            try:
                segments = plan_return(self.position, large, small)
            except LidMotionError as exc:
                raise LidToolError(str(exc)) from exc
            self.engaged_cell = cell
            self.dock_release_completed = False
            self._clear_park_release_track()
            self._run_segments(segments, small=small, large=large)
            self.lid_held_cell = None
            self.shift_completed = False
            self.engaged_cell = None
            self.needs_retract = False
            self.web.update_status(f"Testing: returned lid to cell {cell}")
            return self._ok(f"Returned the lid to cell {cell}.")
        finally:
            self._release()

    def park_lid(self) -> dict:
        self._acquire()
        try:
            self._require_known()
            if self.lid_held_cell is None:
                raise LidToolError("No lid is on the tool.")
            if self.needs_retract:
                raise LidToolError("Raise Z to 0 before parking the lid.")
            assert self.position is not None
            if abs(self.position.z) > Z_CLEARANCE_TOL_MM:
                raise LidToolError("Park lid starts at Z = 0.")
            cell = int(self.lid_held_cell)
            large, small = self._poses_for_cell(cell)
            highway, dock_xy, dock_z = self._highway_and_dock_for_cell(cell)
            release_y = dock_xy.y + (large.y - small.y)
            self.engaged_cell = cell
            self.shift_completed = True
            self.dock_release_completed = False
            self._park_release_y = release_y
            self._park_dock_x = dock_xy.x
            try:
                segments = plan_park_lid(
                    self.position,
                    highway=highway,
                    dock_xy=dock_xy,
                    dock_z=dock_z,
                    large=large,
                    small=small,
                )
            except LidMotionError as exc:
                raise LidToolError(str(exc)) from exc
            self._run_segments(segments, park_release=True)
            if self.position is None or abs(self.position.z) > Z_CLEARANCE_TOL_MM:
                self.needs_retract = True
                raise LidToolError("Park did not finish at Z = 0.", 409)
            self.lid_held_cell = None
            self.shift_completed = False
            self.engaged_cell = None
            self.dock_release_completed = False
            self._clear_park_release_track()
            self.needs_retract = False
            dock_id = dock_for_cell(cell)
            self.web.update_status(f"Testing: parked lid from cell {cell} on dock {dock_id}")
            return self._ok(f"Parked the lid from cell {cell} on dock {dock_id}.")
        finally:
            self._release()

    def move_to_parking(self, row: int) -> dict:
        self._acquire()
        try:
            self._require_known()
            if row not in _HIGHWAY_ROW_TO_KEY:
                raise LidToolError("Highway must be 1, 4, or 8.")
            if self.lid_held_cell is not None:
                raise LidToolError("Return or park the lid before moving to a highway.")
            if self.needs_retract:
                raise LidToolError("Raise Z to 0 before moving to a highway.")
            assert self.position is not None
            if abs(self.position.z) > Z_CLEARANCE_TOL_MM:
                raise LidToolError("Move to Z = 0 before going to a highway.")
            key = _HIGHWAY_ROW_TO_KEY[row]
            parking = pose_from(load_lid_calibration().get(key))
            if parking is None:
                raise LidToolError(f"Highway {row} is not saved yet.")
            self.shift_completed = False
            self.engaged_cell = None
            self.dock_release_completed = False
            self._clear_park_release_track()
            try:
                segments = plan_move_to_parking_pose(self.position, parking)
            except LidMotionError as exc:
                raise LidToolError(str(exc)) from exc
            self._run_segments(segments)
            self.web.update_status(f"Testing: moved to highway {row}")
            return self._ok(f"Moved to highway {row}.")
        finally:
            self._release()

    def move_to_dock(self, dock: int) -> dict:
        self._acquire()
        try:
            self._require_known()
            if dock not in (1, 2, 3):
                raise LidToolError("Dock must be 1, 2, or 3.")
            if self.lid_held_cell is not None:
                raise LidToolError("Return or park the lid before moving to a dock.")
            if self.needs_retract:
                raise LidToolError("Raise Z to 0 before moving to a dock.")
            assert self.position is not None
            if abs(self.position.z) > Z_CLEARANCE_TOL_MM:
                raise LidToolError("Move to Z = 0 before going to a dock.")
            dock_xy = pose_from(load_lid_calibration().get(f"dock{dock}_xy"))
            if dock_xy is None:
                raise LidToolError(f"Dock {dock} XY is not saved yet.")
            self.shift_completed = False
            self.engaged_cell = None
            self.dock_release_completed = False
            self._clear_park_release_track()
            try:
                segments = plan_move_to_parking_pose(self.position, dock_xy)
            except LidMotionError as exc:
                raise LidToolError(str(exc)) from exc
            self._run_segments(segments)
            self.web.update_status(f"Testing: moved to dock {dock}")
            return self._ok(f"Moved to dock {dock}.")
        finally:
            self._release()

    def home(self) -> dict:
        self._acquire()
        try:
            if self.lid_held_cell is not None:
                raise LidToolError("Return or park the lid before homing.")
            if self.needs_retract:
                raise LidToolError("Raise Z to 0 before homing.")
            if not self.position_known or self.position is None:
                cnc = self._machine()
                cnc.should_abort = self._should_abort
                try:
                    raw = cnc.read_position(allow_abort=True)
                except CNCMotionAbort as exc:
                    self._apply_abort_position(exc)
                    self.last_error = "Lid motion stopped"
                    raise LidToolError("Lid motion stopped", 409) from exc
                except CNCMotionError as exc:
                    self.last_error = str(exc)
                    raise LidToolError(str(exc), 503) from exc
                self._set_position(Pose(*raw))
            assert self.position is not None
            self.shift_completed = False
            self.engaged_cell = None
            self.dock_release_completed = False
            self._clear_park_release_track()
            try:
                segments = plan_home(self.position)
            except LidMotionError as exc:
                raise LidToolError(str(exc)) from exc
            self._run_segments(segments)
            self.web.update_status("Testing: gantry homed")
            return self._ok("Moved home (Z, then X, then Y to 0).")
        finally:
            self._release()

    def _acquire(self) -> None:
        if self.web.is_running:
            raise LidToolError("Testing is unavailable during an active viscometry run", 409)
        if not self._motion_lock.acquire(blocking=False):
            raise LidToolError("Lid tool is already moving", 409)
        self.busy = True
        self._abort = False
        with self.web.testing_control_lock:
            self.web.testing_request_in_progress = True

    def _release(self) -> None:
        self.busy = False
        with self.web.testing_control_lock:
            self.web.testing_request_in_progress = False
        self._motion_lock.release()

    def _should_abort(self) -> bool:
        return bool(self._abort or self.web.is_running)

    def _require_known(self) -> None:
        if not self.position_known or self.position is None:
            raise LidToolError("Read the machine position before moving the lid tool.")

    def _machine(self) -> CNC_Machine:
        virtual = os.getenv("VISCOMETRY_CNC_VIRTUAL", "0") == "1"
        try:
            cnc = CNC_Machine(virtual=virtual)
        except Exception as exc:
            self.last_error = str(exc)
            raise LidToolError(f"Unable to open the CNC: {exc}", 503) from exc
        if cnc.VIRTUAL and self.position is not None:
            cnc._virtual_pos = (self.position.x, self.position.y, self.position.z)
        return cnc

    def _set_position(self, pose: Pose) -> None:
        self.position = Pose(round(pose.x, 3), round(pose.y, 3), round(pose.z, 3))
        self.position_known = True
        self.web.update_position(self.position.x, self.position.y, self.position.z)

    def _ensure_in_bounds(self, pose: Pose) -> None:
        if not (
            CNC_Machine.X_LOW_BOUND <= pose.x <= CNC_Machine.X_HIGH_BOUND
            and CNC_Machine.Y_LOW_BOUND <= pose.y <= CNC_Machine.Y_HIGH_BOUND
            and CNC_Machine.Z_LOW_BOUND <= pose.z <= CNC_Machine.Z_HIGH_BOUND
        ):
            raise LidToolError(
                f"That move would leave the machine bounds "
                f"(X {pose.x:.3f}, Y {pose.y:.3f}, Z {pose.z:.3f})."
            )

    def _ensure_plan(self, segments) -> None:
        assert self.position is not None
        try:
            assert_single_axis_plan(self.position, segments)
        except LidMotionError as exc:
            raise LidToolError(str(exc)) from exc
        pose = self.position
        for segment in segments:
            pose = segment.apply(pose)
            self._ensure_in_bounds(pose)

    def _poses_for_cell(self, cell: int) -> tuple[Pose, Pose]:
        try:
            cell_id = int(cell)
        except (TypeError, ValueError) as exc:
            raise LidToolError("Cell must be between 1 and 18.") from exc
        if cell_id < 1 or cell_id > 18:
            raise LidToolError("Cell must be between 1 and 18.")
        cal = load_lid_calibration()
        large = pose_from(cal.get("cell1_large"))
        small = pose_from(cal.get("cell1_small"))
        if large is None or small is None:
            raise LidToolError("Teach the large-hole and trapped poses on cell 1 first.")
        try:
            validate_trapped_pose(large, small)
        except LidMotionError as exc:
            raise LidToolError(str(exc)) from exc
        return cell_poses(large, small, cell_id)

    def _highway_and_dock_for_cell(self, cell: int) -> tuple[Pose, Pose, float]:
        cal = load_lid_calibration()
        dock_id = dock_for_cell(cell)
        highway_id = highway_id_for_cell(cell)
        highway_key = highway_key_for_cell(cell)
        highway = pose_from(cal.get(highway_key))
        if highway is None:
            raise LidToolError(f"Highway {highway_id} is not saved yet.")
        dock_xy = pose_from(cal.get(f"dock{dock_id}_xy"))
        if dock_xy is None:
            raise LidToolError(f"Dock {dock_id} XY is not saved yet.")
        try:
            dock_z = float(cal.get(f"dock{dock_id}_z"))
        except (TypeError, ValueError) as exc:
            raise LidToolError(f"Dock {dock_id} drop Z is not saved yet.") from exc
        if dock_z >= -Z_CLEARANCE_TOL_MM:
            raise LidToolError(f"Dock {dock_id} drop Z must be below Z = 0.")
        return highway, dock_xy, dock_z

    def _clear_park_release_track(self) -> None:
        self._park_release_y = None
        self._park_dock_x = None

    def _run_segments(
        self,
        segments,
        small: Optional[Pose] = None,
        large: Optional[Pose] = None,
        park_release: bool = False,
    ) -> None:
        if not segments:
            return
        self._ensure_plan(segments)
        cnc = self._machine()
        cnc.should_abort = self._should_abort

        def on_segment(pos, segment) -> None:
            pose = Pose(*pos)
            self._set_position(pose)
            if segment is None:
                return
            if small is not None and getattr(segment, "axis", None) == "y":
                if abs(pose.x - small.x) <= POSITION_MATCH_MM and abs(pose.y - small.y) <= POSITION_MATCH_MM:
                    self.shift_completed = True
            if (
                large is not None
                and self.lid_held_cell is not None
                and getattr(segment, "axis", None) == "y"
                and abs(pose.x - large.x) <= POSITION_MATCH_MM
                and abs(pose.y - large.y) <= POSITION_MATCH_MM
            ):
                self.shift_completed = False
            if (
                park_release
                and self._park_release_y is not None
                and self._park_dock_x is not None
                and getattr(segment, "axis", None) == "y"
                and abs(pose.x - self._park_dock_x) <= POSITION_MATCH_MM
                and abs(pose.y - self._park_release_y) <= POSITION_MATCH_MM
            ):
                self.dock_release_completed = True
                self.lid_held_cell = None
                self.shift_completed = False

        try:
            final = cnc.execute_segments(segments, on_segment=on_segment, allow_abort=True)
        except CNCMotionAbort as exc:
            self._apply_abort_position(exc)
            self._mark_interrupted()
            raise LidToolError("Lid motion stopped", 409) from exc
        except CNCMotionError as exc:
            self.last_error = str(exc)
            self._mark_interrupted()
            raise LidToolError(str(exc), 503) from exc
        self._set_position(Pose(*final))

    def _apply_abort_position(self, exc: CNCMotionAbort) -> None:
        if exc.position is not None:
            self._set_position(Pose(*exc.position))

    def _mark_interrupted(self) -> None:
        self.last_error = "Lid motion stopped"
        if self.position is None:
            self.position_known = False
            self.needs_retract = True
            return
        if self.dock_release_completed:
            self.lid_held_cell = None
            self.shift_completed = False
        elif self._released_into_large_hole():
            self.lid_held_cell = None
            self.shift_completed = False
        if abs(self.position.z) > Z_CLEARANCE_TOL_MM:
            self.needs_retract = True
            return
        self.needs_retract = False
        if (
            self.shift_completed
            and not self.dock_release_completed
            and self.engaged_cell is not None
            and self.lid_held_cell is None
        ):
            self.lid_held_cell = self.engaged_cell

    def _released_into_large_hole(self) -> bool:
        if self.lid_held_cell is None or self.position is None:
            return False
        try:
            large, _small = self._poses_for_cell(self.lid_held_cell)
        except LidToolError:
            return False
        return (
            abs(self.position.x - large.x) <= POSITION_MATCH_MM
            and abs(self.position.y - large.y) <= POSITION_MATCH_MM
            and (
                abs(self.position.z - large.z) <= POSITION_MATCH_MM
                or abs(self.position.z) <= Z_CLEARANCE_TOL_MM
            )
        )

    def _clear_retract_if_clear(self) -> None:
        if not self.needs_retract or self.position is None:
            return
        if abs(self.position.z) > Z_CLEARANCE_TOL_MM:
            return
        self.needs_retract = False
        if self.dock_release_completed:
            self.lid_held_cell = None
            self.shift_completed = False
            return
        if self.shift_completed and self.engaged_cell is not None and self.lid_held_cell is None:
            self.lid_held_cell = self.engaged_cell

    def _ok(self, message: str) -> dict:
        """Build a success payload. Force busy=False so the UI unlocks after this request."""
        self.last_error = None
        status = self.status()
        status["busy"] = False
        return {
            "ok": True,
            "message": message,
            "lid": status,
            **status,
        }


def _segment(current: Pose, axis: str, target: float, feed: int):
    from viscometry.lid.motion import single_axis_segment

    try:
        return single_axis_segment(current, feed=feed, **{axis: target})
    except LidMotionError as exc:
        raise LidToolError(str(exc)) from exc

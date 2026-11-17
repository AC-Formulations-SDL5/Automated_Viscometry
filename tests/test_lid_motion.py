"""Lid tool motion plans stay on one axis, and taught poses copy across the cell grid."""

from __future__ import annotations

import pytest

from viscometry.hardware.cnc import CNCMotionAbort, CNC_Machine, format_single_axis_gcode, parse_grbl_wpos
from viscometry.lid.calibration import load_lid_calibration, save_lid_calibration
from viscometry.lid.motion import (
    ENGAGE_FEED_MM_PER_MIN,
    TRAVEL_FEED_MM_PER_MIN,
    LidMotionError,
    Pose,
    Segment,
    assert_single_axis_plan,
    cell_poses,
    dock_for_cell,
    plan_home,
    plan_park_lid,
    plan_parking_route,
    plan_pickup,
    plan_return,
    single_axis_segment,
    validate_jog,
    validate_trapped_pose,
)


LARGE = Pose(40.0, 80.0, -12.0)
SMALL = Pose(40.0, 70.0, -12.0)


def test_cell_offsets_follow_the_sample_grid():
    cell1_large, cell1_small = cell_poses(LARGE, SMALL, 1)
    assert cell1_large == LARGE
    assert cell1_small == SMALL

    cell7_large, cell7_small = cell_poses(LARGE, SMALL, 7)
    assert cell7_large == Pose(LARGE.x + 75.0, LARGE.y, LARGE.z)
    assert cell7_small == Pose(SMALL.x + 75.0, SMALL.y, SMALL.z)

    cell13_large, cell13_small = cell_poses(LARGE, SMALL, 13)
    assert cell13_large.x == pytest.approx(LARGE.x + (309 - 10))
    assert cell13_large.y == LARGE.y
    assert cell13_small.y == SMALL.y
    assert cell13_large.z == LARGE.z


def test_pickup_and_return_are_single_axis_in_order():
    current = Pose(0.0, 0.0, -2.0)
    pickup = plan_pickup(current, LARGE, SMALL)
    assert [(seg.axis, seg.target) for seg in pickup] == [
        ("z", 0.0),
        ("x", LARGE.x),
        ("y", LARGE.y),
        ("z", LARGE.z),
        ("y", SMALL.y),
        ("z", 0.0),
    ]
    assert pickup[0].feed == ENGAGE_FEED_MM_PER_MIN
    assert pickup[1].feed == TRAVEL_FEED_MM_PER_MIN
    assert pickup[4].feed == ENGAGE_FEED_MM_PER_MIN
    assert_single_axis_plan(current, pickup)

    held = Pose(SMALL.x, SMALL.y, 0.0)
    returning = plan_return(held, LARGE, SMALL)
    assert [(seg.axis, seg.target) for seg in returning] == [
        ("z", SMALL.z),
        ("y", LARGE.y),
        ("z", 0.0),
    ]
    assert_single_axis_plan(held, returning)


def test_multi_axis_segment_is_rejected():
    with pytest.raises(LidMotionError):
        single_axis_segment(Pose(0, 0, 0), feed=100, x=1, y=2)


def test_xy_jog_allowed_below_clearance_for_teaching():
    validate_jog("x", 1.0, z=-2.0, lid_held=False, needs_retract=False)
    validate_jog("y", -1.0, z=-2.0, lid_held=False, needs_retract=False)
    validate_jog("y", -10.0, z=-2.0, lid_held=False, needs_retract=False)
    validate_jog("x", 10.0, z=-2.0, lid_held=False, needs_retract=False)
    validate_jog("x", 10.0, z=0.0, lid_held=False, needs_retract=False)
    validate_jog("z", 10.0, z=0.0, lid_held=False, needs_retract=False)
    validate_jog("z", 1.0, z=-4.0, lid_held=False, needs_retract=True)


def test_dock_mapping_follows_sample_rows():
    assert dock_for_cell(1) == 1
    assert dock_for_cell(6) == 1
    assert dock_for_cell(7) == 2
    assert dock_for_cell(12) == 2
    assert dock_for_cell(13) == 3
    assert dock_for_cell(18) == 3
    with pytest.raises(LidMotionError):
        dock_for_cell(0)


def test_park_lid_uses_highway_then_dock_then_release():
    current = Pose(100.0, 50.0, 0.0)
    highway = Pose(12.0, 320.0, 0.0)
    dock_xy = Pose(40.0, 340.0, 0.0)
    dock_z = -8.0
    segments = plan_park_lid(
        current,
        highway=highway,
        dock_xy=dock_xy,
        dock_z=dock_z,
        large=LARGE,
        small=SMALL,
    )
    release_y = dock_xy.y + (LARGE.y - SMALL.y)
    assert [(seg.axis, seg.target) for seg in segments] == [
        ("x", highway.x),
        ("y", highway.y),
        ("x", dock_xy.x),
        ("y", dock_xy.y),
        ("z", dock_z),
        ("y", release_y),
        ("z", 0.0),
    ]
    assert_single_axis_plan(current, segments)
    assert release_y > dock_xy.y

    with pytest.raises(LidMotionError):
        plan_park_lid(
            current,
            highway=highway,
            dock_xy=dock_xy,
            dock_z=0.0,
            large=LARGE,
            small=SMALL,
        )
    with pytest.raises(LidMotionError):
        plan_park_lid(
            Pose(100.0, 50.0, -1.0),
            highway=highway,
            dock_xy=dock_xy,
            dock_z=dock_z,
            large=LARGE,
            small=SMALL,
        )


def test_home_plan_is_z_then_x_then_y():
    current = Pose(40.0, 80.0, -5.0)
    segments = plan_home(current)
    assert [(seg.axis, seg.target) for seg in segments] == [
        ("z", 0.0),
        ("x", 0.0),
        ("y", 0.0),
    ]
    assert_single_axis_plan(current, segments)
    already = plan_home(Pose(0.0, 0.0, 0.0))
    assert already == []


def test_held_lid_blocks_jog_and_retract_allows_only_positive_z():
    with pytest.raises(LidMotionError):
        validate_jog("y", -1.0, z=0.0, lid_held=True, needs_retract=False)
    with pytest.raises(LidMotionError):
        validate_jog("y", 1.0, z=-4.0, lid_held=False, needs_retract=True)
    with pytest.raises(LidMotionError):
        validate_jog("z", -0.1, z=-4.0, lid_held=True, needs_retract=True)
    validate_jog("z", 1.0, z=-4.0, lid_held=True, needs_retract=True)


def test_trapped_pose_must_be_a_pure_negative_y_shift():
    validate_trapped_pose(LARGE, SMALL)
    with pytest.raises(LidMotionError):
        validate_trapped_pose(LARGE, Pose(LARGE.x + 0.3, SMALL.y, LARGE.z))
    with pytest.raises(LidMotionError):
        validate_trapped_pose(LARGE, Pose(LARGE.x, SMALL.y, LARGE.z - 0.3))
    with pytest.raises(LidMotionError):
        validate_trapped_pose(LARGE, Pose(LARGE.x, LARGE.y + 1.0, LARGE.z))
    with pytest.raises(LidMotionError):
        validate_trapped_pose(LARGE, LARGE)


def test_parking_route_selects_row_then_moves_x_before_y():
    current = Pose(100.0, 50.0, -3.0)
    row1 = Pose(12.0, 320.0, 0.0)
    row4 = Pose(240.0, 330.0, 0.0)

    to_row1 = plan_parking_route(current, 12, row1, row4)
    assert [(seg.axis, seg.target) for seg in to_row1] == [
        ("z", 0.0),
        ("x", row1.x),
        ("y", row1.y),
    ]
    assert_single_axis_plan(current, to_row1)

    to_row4 = plan_parking_route(Pose(100.0, 50.0, 0.0), 13, row1, row4)
    assert [(seg.axis, seg.target) for seg in to_row4] == [
        ("x", row4.x),
        ("y", row4.y),
    ]
    assert plan_parking_route(current, 1, row1, row4)[1].target == row1.x
    assert plan_parking_route(current, 18, row1, row4)[1].target == row4.x


def test_calibration_roundtrip(tmp_path, monkeypatch):
    from viscometry.lid import calibration as calibration_module

    monkeypatch.setattr(calibration_module, "calibration_file", lambda name: tmp_path / name)
    monkeypatch.setattr(
        calibration_module,
        "ensure_calibration_dir",
        lambda: tmp_path.mkdir(parents=True, exist_ok=True) or tmp_path,
    )

    saved = save_lid_calibration({
        "cell1_large": {"x": 40, "y": 80, "z": -12},
        "cell1_small": {"x": 40, "y": 70, "z": -12},
        "parking_row1": {"x": 12, "y": 320, "z": 0},
        "parking_row4": {"x": 240, "y": 330, "z": 0},
        "dock1_xy": {"x": 10, "y": 350, "z": 0},
        "dock1_z": -9.5,
        "dock2_xy": {"x": 85, "y": 350, "z": 0},
        "dock2_z": -9.5,
        "dock3_xy": {"x": 309, "y": 350, "z": 0},
        "dock3_z": -9.25,
    })
    assert saved["clearance_z"] == 0.0
    loaded = load_lid_calibration()
    assert loaded["cell1_large"]["z"] == -12
    assert loaded["parking_row4"]["x"] == 240
    assert loaded["dock2_xy"]["x"] == 85
    assert loaded["dock3_z"] == pytest.approx(-9.25)
    assert (tmp_path / "lid_tool_calibration.json").is_file()

    (tmp_path / "lid_tool_calibration.json").write_text("{", encoding="utf-8")
    assert load_lid_calibration()["cell1_large"] is None
    assert load_lid_calibration()["dock1_xy"] is None


def test_virtual_session_reports_each_single_axis_move_and_stops_between_them():
    cnc = CNC_Machine(virtual=True)
    reported = []
    segments = plan_pickup(Pose(0.0, 0.0, 0.0), LARGE, SMALL)
    final = cnc.execute_segments(segments, on_segment=lambda pos, seg: reported.append((pos, seg.axis)))
    assert [axis for _pos, axis in reported] == [seg.axis for seg in segments]
    assert final == (SMALL.x, SMALL.y, 0.0)
    assert cnc._virtual_pos == final

    cnc._virtual_pos = (0.0, 0.0, 0.0)
    cnc.should_abort = lambda: True
    with pytest.raises(CNCMotionAbort) as caught:
        cnc.execute_segments([Segment("x", 10.0, TRAVEL_FEED_MM_PER_MIN)])
    assert caught.value.position == (0.0, 0.0, 0.0)
    assert cnc._virtual_pos == (0.0, 0.0, 0.0)


def test_gcode_and_status_parse_one_axis():
    line = format_single_axis_gcode("y", 12.5, 300)
    assert line == "G1 Y12.500 F300\n"
    assert "X" not in line and "Z" not in line
    status = "<Idle|MPos:1,2,3|WPos:4.5,-6.25,0.000|FS:0,0>"
    assert parse_grbl_wpos(status) == (4.5, -6.25, 0.0)

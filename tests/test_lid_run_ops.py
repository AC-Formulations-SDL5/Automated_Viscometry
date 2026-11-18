"""Run-time lid pickup readiness and park planning helpers."""

from __future__ import annotations

import pytest

from viscometry.hardware.cnc import CNC_Machine
from viscometry.lid import calibration as calibration_module
from viscometry.lid.calibration import save_lid_calibration
from viscometry.lid.motion import Pose, plan_park_lid, plan_pickup
from viscometry.lid.run_ops import (
    LidRunError,
    cell1_pair_ready,
    park_ready_for_cell,
    pickup_and_park_lid,
    readiness_for_cells,
)


def _seed_full_lid_cal(tmp_path, monkeypatch):
    monkeypatch.setattr(calibration_module, "calibration_file", lambda name: tmp_path / name)
    monkeypatch.setattr(
        calibration_module,
        "ensure_calibration_dir",
        lambda: tmp_path.mkdir(parents=True, exist_ok=True) or tmp_path,
    )
    save_lid_calibration({
        "cell1_large": {"x": 40, "y": 80, "z": -12},
        "cell1_small": {"x": 40, "y": 70, "z": -12},
        "dock1_xy": {"x": 520, "y": 350, "z": 0},
        "dock1_z": -9.5,
        "dock2_xy": {"x": 540, "y": 350, "z": 0},
        "dock2_z": -9.5,
        "dock3_xy": {"x": 560, "y": 350, "z": 0},
        "dock3_z": -9.25,
    })


def test_park_ready_requires_dock_not_highway(tmp_path, monkeypatch):
    monkeypatch.setattr(calibration_module, "calibration_file", lambda name: tmp_path / name)
    monkeypatch.setattr(
        calibration_module,
        "ensure_calibration_dir",
        lambda: tmp_path.mkdir(parents=True, exist_ok=True) or tmp_path,
    )
    save_lid_calibration({
        "cell1_large": {"x": 40, "y": 80, "z": -12},
        "cell1_small": {"x": 40, "y": 70, "z": -12},
    })
    assert cell1_pair_ready()
    assert not park_ready_for_cell(1)
    report = readiness_for_cells([1, 7, 13])
    assert report["cell1_ready"] is True
    assert report["not_ready"] == [1, 7, 13]


def test_park_ready_for_all_docks(tmp_path, monkeypatch):
    _seed_full_lid_cal(tmp_path, monkeypatch)
    assert park_ready_for_cell(1)
    assert park_ready_for_cell(7)
    assert park_ready_for_cell(13)
    report = readiness_for_cells([1, 7, 13])
    assert report["all_ready"] is True
    assert report["cells"]["1"]["dock"] == 1
    assert report["cells"]["7"]["dock"] == 2
    assert report["cells"]["13"]["dock"] == 3
    assert "highway" not in report["cells"]["1"]


def test_virtual_pickup_and_park_clears_lid_path(tmp_path, monkeypatch):
    _seed_full_lid_cal(tmp_path, monkeypatch)
    cnc = CNC_Machine(virtual=True)
    cnc._virtual_pos = (0.0, 0.0, 0.0)
    statuses = []
    pickup_and_park_lid(
        cnc,
        1,
        on_status=statuses.append,
    )
    assert cnc._virtual_pos[2] == pytest.approx(0.0)
    assert any("Picking up lid" in msg for msg in statuses)
    assert any("Parked lid" in msg for msg in statuses)


def test_pickup_and_park_rejects_unready_cell(tmp_path, monkeypatch):
    monkeypatch.setattr(calibration_module, "calibration_file", lambda name: tmp_path / name)
    monkeypatch.setattr(
        calibration_module,
        "ensure_calibration_dir",
        lambda: tmp_path.mkdir(parents=True, exist_ok=True) or tmp_path,
    )
    save_lid_calibration({
        "cell1_large": {"x": 40, "y": 80, "z": -12},
        "cell1_small": {"x": 40, "y": 70, "z": -12},
    })
    cnc = CNC_Machine(virtual=True)
    with pytest.raises(LidRunError):
        pickup_and_park_lid(cnc, 1)


def test_plan_helpers_use_xy_for_approach_and_park():
    large = Pose(40.0, 80.0, -12.0)
    small = Pose(40.0, 70.0, -12.0)
    current = Pose(0.0, 0.0, 0.0)
    pickup = plan_pickup(current, large, small)
    held = Pose(small.x, small.y, 0.0)
    park = plan_park_lid(
        held,
        dock_xy=Pose(520.0, 350.0, 0.0),
        dock_z=-9.5,
        large=large,
        small=small,
    )
    assert any(seg.axis == "xy" for seg in pickup)
    assert park[0].axis == "xy"
    assert park[-1].axis == "z"
    assert park[-1].target == 0.0

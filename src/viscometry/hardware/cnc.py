import re
import serial
import time
import yaml
from typing import Callable, List, Optional, Tuple

from viscometry.paths import LOCATIONS_YAML

_WPOS_RE = re.compile(
    r"WPos:\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)"
)
_MPOS_RE = re.compile(
    r"MPos:\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)"
)


class CNCMotionError(Exception):
    """Raised when CNC motion fails (bounds, timeout, alarm, hold)."""


class CNCMotionAbort(CNCMotionError):
    """Raised when a lid move is stopped between segments."""

    def __init__(self, message: str, position: Optional[Tuple[float, float, float]] = None):
        super().__init__(message)
        self.position = position


def parse_grbl_wpos(line: str) -> Optional[Tuple[float, float, float]]:
    """Pull work position from a GRBL status line. Falls back to machine position."""
    if not line:
        return None
    match = _WPOS_RE.search(line) or _MPOS_RE.search(line)
    if not match:
        return None
    return float(match.group(1)), float(match.group(2)), float(match.group(3))


def format_single_axis_gcode(axis: str, target: float, feed: int) -> str:
    if axis not in ("x", "y", "z"):
        raise CNCMotionError(f"Lid segment axis must be x, y, or z, got {axis}")
    letter = axis.upper()
    return f"G1 {letter}{target:.3f} F{int(feed)}\n"


def format_xy_gcode(x: float, y: float, feed: int) -> str:
    return f"G1 X{float(x):.3f} Y{float(y):.3f} F{int(feed)}\n"


class CNC_Machine:
    BAUD_RATE = 115200
    SERIAL_PORT = "COM5"  # CNC / GRBL
    X_LOW_BOUND = 0;   X_HIGH_BOUND = 600
    Y_LOW_BOUND = 0;   Y_HIGH_BOUND = 400
    Z_LOW_BOUND = -75; Z_HIGH_BOUND = 0

    LOCATION_FILE = str(LOCATIONS_YAML)
    IDLE_TIMEOUT_S = 120.0
    STATUS_POLL_INTERVAL_S = 0.1

    def __init__(self, virtual: bool = False, idle_timeout_s: Optional[float] = None):
        self.VIRTUAL = virtual
        self.idle_timeout_s = idle_timeout_s if idle_timeout_s is not None else self.IDLE_TIMEOUT_S
        self.should_abort: Optional[Callable[[], bool]] = None
        self._virtual_pos: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        with open(self.LOCATION_FILE, "r") as f:
            self.LOCATIONS = yaml.safe_load(f) or {}
        print(f"Connected to CNC Machine! (virtual={self.VIRTUAL})")

    # serial helpers
    def _wake(self, ser):
        ser.write(str.encode("\r\n\r\n"))
        time.sleep(1)
        ser.reset_input_buffer()

    def _wait_idle(
        self,
        ser,
        should_abort: Optional[Callable[[], bool]] = None,
        allow_abort: bool = True,
    ):
        abort_fn = should_abort or self.should_abort
        time.sleep(0.25)
        deadline = time.time() + self.idle_timeout_s
        while True:
            if allow_abort and abort_fn and abort_fn():
                # #region agent log
                try:
                    import json as _json, time as _time, pathlib as _pathlib
                    payload = {
                        "sessionId": "80a163",
                        "id": f"log_{int(_time.time() * 1000)}_H4",
                        "timestamp": int(_time.time() * 1000),
                        "location": "cnc_controller.py:_wait_idle",
                        "message": "Abort requested during CNC wait",
                        "data": {},
                        "runId": "pre-fix-1",
                        "hypothesisId": "H4",
                    }
                    log_path = _pathlib.Path(__file__).resolve().parents[2] / ".cursor" / "debug-80a163.log"
                    log_path.parent.mkdir(parents=True, exist_ok=True)
                    with log_path.open("a", encoding="utf-8") as f:
                        f.write(_json.dumps(payload) + "\n")
                except Exception:
                    pass
                # #endregion agent log
                raise KeyboardInterrupt("Stop requested during CNC wait")
            if time.time() > deadline:
                raise CNCMotionError(
                    f"Timed out waiting for CNC idle after {self.idle_timeout_s:.0f}s"
                )
            ser.reset_input_buffer()
            ser.write(b"?\n")
            line = ser.readline().decode(errors="ignore").strip()
            if "Alarm" in line:
                raise CNCMotionError(f"GRBL alarm: {line}")
            if "Hold" in line:
                raise CNCMotionError(f"GRBL hold: {line}")
            if "Idle" in line:
                break
            time.sleep(self.STATUS_POLL_INTERVAL_S)

    def _check_bounds(self, x, y, z) -> None:
        if not self._within(x, y, z):
            raise CNCMotionError(f"Out of bounds: ({x},{y},{z})")

    # motion builders
    def _within(self, x, y, z) -> bool:
        xb = (x is None) or (self.X_LOW_BOUND <= x <= self.X_HIGH_BOUND)
        yb = (y is None) or (self.Y_LOW_BOUND <= y <= self.Y_HIGH_BOUND)
        zb = (z is None) or (self.Z_LOW_BOUND <= z <= self.Z_HIGH_BOUND)
        return xb and yb and zb

    def _gcode_to(self, x=None, y=None, z=None, speed=3000, gtype="G1"):
        s = gtype
        if x is not None: s += f" X{x}"
        if y is not None: s += f" Y{y}"
        if z is not None: s += f" Z{z}"
        if speed is not None: s += f" F{speed}"
        return s + "\n"

    # public ops
    def home(self, allow_abort: bool = True):
        self.move_to_point_safe(0, 0, 0, gtype="G0", allow_abort=allow_abort)

    def move_to_point(self, x=None, y=None, z=None, speed=3000, gtype="G1", allow_abort: bool = True):
        self._check_bounds(x, y, z)
        g = self._gcode_to(x, y, z, speed, gtype)
        self.follow_gcode_path(g, allow_abort=allow_abort)

    def move_to_point_safe(self, x, y, z, speed=3000, gtype="G1", allow_abort: bool = True):
        self._check_bounds(x, y, z)
        g = ""
        g += self._gcode_to(z=self.Z_HIGH_BOUND, speed=speed, gtype=gtype)
        g += self._gcode_to(x=x, y=y, z=self.Z_HIGH_BOUND, speed=speed, gtype=gtype)
        g += self._gcode_to(z=z, speed=speed, gtype=gtype)
        self.follow_gcode_path(g, allow_abort=allow_abort)

    def retract_z_at_cell(
        self,
        x,
        y,
        z_safe: float = 0,
        speed: int = 3000,
        gtype: str = "G1",
        allow_abort: bool = True,
    ) -> None:
        """Raise Z to safe height at fixed XY (no horizontal travel)."""
        self._check_bounds(x, y, z_safe)
        g = self._gcode_to(z=z_safe, speed=speed, gtype=gtype)
        self.follow_gcode_path(g, allow_abort=allow_abort)

    def get_location_position(self, name: str, idx: int):
        L = self.LOCATIONS[name]
        x = L["x_origin"]; y = L["y_origin"]; z = L["z_origin"]
        if idx > 0:
            num_x = L.get("num_x", 1); num_y = L.get("num_y", 1)
            x_off = L.get("x_offset", 0); y_off = L.get("y_offset", 0)
            x = x + (idx % num_x) * x_off
            y = y + (idx // num_x) * y_off
        return x, y, z

    def move_to_location(self, name: str, idx: int, safe: bool = True, speed: int = 3000):
        print(f"Moving to location: {name}[{idx}]")
        x, y, z = self.get_location_position(name, idx)
        if safe: self.move_to_point_safe(x, y, z, speed=speed)
        else:    self.move_to_point(x, y, z, speed=speed)

    def _abort_requested(self, allow_abort: bool) -> bool:
        return bool(allow_abort and self.should_abort and self.should_abort())

    def _query_wpos(self, ser) -> Tuple[float, float, float]:
        ser.reset_input_buffer()
        ser.write(b"?\n")
        for _ in range(5):
            line = ser.readline().decode(errors="ignore").strip()
            if not line:
                continue
            if "Alarm" in line:
                raise CNCMotionError(f"GRBL alarm: {line}")
            parsed = parse_grbl_wpos(line)
            if parsed is not None:
                return parsed
        raise CNCMotionError("GRBL did not report WPos")

    def _segment_command(self, segment):
        """Return (\"xy\", x, y, feed) or (axis, target, None, feed)."""
        axis = getattr(segment, "axis", None)
        target = getattr(segment, "target", None)
        feed = getattr(segment, "feed", None)
        x = getattr(segment, "x", None)
        y = getattr(segment, "y", None)
        if isinstance(segment, dict):
            axis = segment.get("axis", axis)
            target = segment.get("target", target)
            feed = segment.get("feed", feed)
            x = segment.get("x", x)
            y = segment.get("y", y)
        if feed is None:
            raise CNCMotionError("Lid segment is missing a feed")
        if axis == "xy":
            if x is None or y is None:
                raise CNCMotionError("XY lid segment is missing x or y")
            return "xy", float(x), float(y), int(feed)
        if axis not in ("x", "y", "z"):
            raise CNCMotionError(f"Lid segment axis must be x, y, z, or xy, got {axis}")
        if target is None:
            raise CNCMotionError("Lid segment is missing a target or feed")
        return str(axis), float(target), None, int(feed)

    def _position_after(
        self,
        pos: Tuple[float, float, float],
        axis: str,
        target: float,
        y_target: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        x, y, z = pos
        if axis == "xy":
            if y_target is None:
                raise CNCMotionError("XY move needs both X and Y targets")
            x = target
            y = y_target
        elif axis == "x":
            x = target
        elif axis == "y":
            y = target
        else:
            z = target
        self._check_bounds(x, y, z)
        return (float(x), float(y), float(z))

    def read_position(self, allow_abort: bool = True) -> Tuple[float, float, float]:
        """Read the current work position. Virtual mode returns the last commanded point."""
        if self.VIRTUAL:
            if self._abort_requested(allow_abort):
                raise CNCMotionAbort("Stop requested before position read", self._virtual_pos)
            return self._virtual_pos
        with serial.Serial(self.SERIAL_PORT, self.BAUD_RATE, timeout=2.0) as ser:
            self._wake(ser)
            if self._abort_requested(allow_abort):
                raise CNCMotionAbort("Stop requested before position read", None)
            return self._query_wpos(ser)

    def execute_segments(
        self,
        segments,
        on_segment: Optional[Callable[[Tuple[float, float, float], object], None]] = None,
        allow_abort: bool = True,
    ) -> Tuple[float, float, float]:
        """Send lid moves one segment at a time (single-axis or XY) and report position.

        Stop is honored before the next segment is sent. Virtual mode applies the
        commanded point without opening a serial port.
        """
        if self.VIRTUAL:
            pos = self._virtual_pos
            for segment in segments:
                if self._abort_requested(allow_abort):
                    raise CNCMotionAbort("Stop requested before the next lid move", pos)
                axis, a, b, _feed = self._segment_command(segment)
                pos = self._position_after(pos, axis, a, b)
                self._virtual_pos = pos
                if on_segment is not None:
                    on_segment(pos, segment)
            return pos

        with serial.Serial(self.SERIAL_PORT, self.BAUD_RATE, timeout=2.0) as ser:
            self._wake(ser)
            pos = self._query_wpos(ser)
            try:
                for segment in segments:
                    if self._abort_requested(allow_abort):
                        raise CNCMotionAbort("Stop requested before the next lid move", pos)
                    axis, a, b, feed = self._segment_command(segment)
                    self._position_after(pos, axis, a, b)
                    if axis == "xy":
                        line = format_xy_gcode(a, b, feed)
                    else:
                        line = format_single_axis_gcode(axis, a, feed)
                    ser.write(line.encode())
                    try:
                        self._wait_idle(ser, allow_abort=allow_abort)
                    except KeyboardInterrupt as exc:
                        try:
                            pos = self._query_wpos(ser)
                        except CNCMotionError:
                            pass
                        raise CNCMotionAbort("Stop requested during lid motion", pos) from exc
                    pos = self._query_wpos(ser)
                    if on_segment is not None:
                        on_segment(pos, segment)
            except CNCMotionAbort:
                raise
            except CNCMotionError:
                try:
                    pos = self._query_wpos(ser)
                    if on_segment is not None:
                        on_segment(pos, None)
                except CNCMotionError:
                    pass
                raise
            return pos

    def follow_gcode_path(self, gcode: str, buffer: int = 20, allow_abort: bool = True) -> List[str]:
        if self.VIRTUAL:
            print("VIRTUAL GCODE:\n" + gcode.strip())
            return ["ok"]
        outs = []
        with serial.Serial(self.SERIAL_PORT, self.BAUD_RATE, timeout=2.0) as ser:
            self._wake(ser)
            cmds = [c for c in gcode.splitlines() if c.strip()]
            for i in range(0, len(cmds), buffer):
                chunk = "\n".join(cmds[i:i+buffer]) + "\n"
                ser.write(chunk.encode())
                self._wait_idle(ser, allow_abort=allow_abort)
                out = ser.readline().decode(errors="ignore").strip()
                outs.append(out)
                print(f"Movement commands rendered: {min(i+buffer, len(cmds))}")
        return outs

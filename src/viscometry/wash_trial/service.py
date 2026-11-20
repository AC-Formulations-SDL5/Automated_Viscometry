"""Testing-tab session for dirty-then-wash solvent trials."""

from __future__ import annotations

import os
import threading
from typing import Any, Dict, Optional

from viscometry.calibration.store import get_calibration_summary, load_calibration
from viscometry.hardware.cnc import CNCMotionError, CNC_Machine
from viscometry.run import settings as run_settings


class WashTrialError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class WashTrialService:
    """Owns CNC+pump wash-trial motion with mutual exclusion against Lid Tool / runs."""

    def __init__(self, web):
        self.web = web
        self.busy = False
        self.phase = "idle"
        self.last_error: Optional[str] = None
        self.last_result: Optional[Dict[str, Any]] = None
        self._abort = False
        self._owned_stop_event = False
        self._motion_lock = threading.Lock()
        self._cnc: Optional[CNC_Machine] = None

    def request_stop(self) -> None:
        self._abort = True
        if self.busy:
            self.last_error = "Stop requested"
            self.phase = "stopping"
            # Reuse the run stop event so controller sleep/raise_if_stop abort promptly.
            self.web.stop_requested_event.set()
            self._owned_stop_event = True
            if self._cnc is not None:
                self._cnc.should_abort = self._should_abort

    def status(self) -> dict:
        cal = get_calibration_summary()
        cells = cal.get("cells") or {}
        calibrated_cells = sorted(int(k) for k in cells.keys() if str(k).isdigit())
        return {
            "busy": self.busy,
            "phase": self.phase,
            "last_error": self.last_error,
            "last_result": self.last_result,
            "calibrated_cells": calibrated_cells,
            "dip_offset_mm": float(run_settings.WASH_TRIAL_DIP_OFFSET_MM),
            "dip_dwell_s": float(run_settings.WASH_TRIAL_DIP_DWELL_S),
            "scrub": {
                "feed": int(run_settings.WASH_SCRUB_FEED),
                "feed_fast": int(run_settings.WASH_SCRUB_FEED_FAST),
                "count": int(run_settings.WASH_SCRUB_COUNT),
                "dwell_s": float(run_settings.WASH_SCRUB_DWELL_S),
                "dwell_s_fast": float(run_settings.WASH_SCRUB_DWELL_S_FAST),
            },
        }

    def run(self, cell: int, *, fast_scrub: bool = False) -> dict:
        self._acquire()
        try:
            self.phase = "preparing"
            self.last_error = None
            self.last_result = None
            self.web.stop_requested_event.clear()
            self._owned_stop_event = False
            self._abort = False

            try:
                cell_id = int(cell)
            except (TypeError, ValueError) as exc:
                raise WashTrialError("Cell must be between 1 and 18.") from exc
            if cell_id < 1 or cell_id > 18:
                raise WashTrialError("Cell must be between 1 and 18.")

            cal = load_calibration()
            cells = cal.get("cells", {}) if isinstance(cal, dict) else {}
            if str(cell_id) not in cells:
                raise WashTrialError(
                    f"Cell {cell_id} is not calibrated — select a calibrated cell.",
                    400,
                )

            if not self.web._ensure_testing_session_connected():
                raise WashTrialError(
                    "Unable to initialize pump controller for wash trial",
                    503,
                )
            pump = self.web.pump_controller
            if pump is None:
                raise WashTrialError("Pump controller is not connected", 503)

            cnc = self._machine()
            self._cnc = cnc
            cnc.should_abort = self._should_abort

            # Lazy import avoids circular import with run.controller → web.app.
            from viscometry.run.controller import run_wash_trial_dirty_and_wash

            self.phase = "dipping"
            self.web.update_status(f"Wash trial: starting Cell {cell_id}")
            try:
                result = run_wash_trial_dirty_and_wash(
                    cnc,
                    pump,
                    cell_id,
                    fast_scrub=bool(fast_scrub),
                )
            except KeyboardInterrupt as exc:
                self.last_error = "Wash trial stopped"
                self.phase = "stopped"
                self._emergency_cleanup(cnc, pump)
                raise WashTrialError("Wash trial stopped", 409) from exc
            except CNCMotionError as exc:
                self.last_error = str(exc)
                self.phase = "error"
                self._emergency_cleanup(cnc, pump)
                raise WashTrialError(str(exc), 503) from exc
            except ValueError as exc:
                self.last_error = str(exc)
                self.phase = "error"
                raise WashTrialError(str(exc), 400) from exc
            except Exception as exc:
                self.last_error = str(exc)
                self.phase = "error"
                self._emergency_cleanup(cnc, pump)
                raise WashTrialError(str(exc), 500) from exc

            self.last_result = result
            self.phase = "idle"
            self.web.update_status(
                f"Wash trial complete for Cell {cell_id}"
                + (" (fast scrub)" if fast_scrub else "")
            )
            return self._ok(
                f"Wash trial complete for Cell {cell_id}.",
                result=result,
            )
        finally:
            self._cnc = None
            if self._owned_stop_event or self.web.stop_requested_event.is_set():
                # Clear stop latch so a later viscometry run is not immediately aborted.
                if not self.web.is_running:
                    self.web.stop_requested_event.clear()
                self._owned_stop_event = False
            self._release()

    def _acquire(self) -> None:
        if self.web.is_running:
            raise WashTrialError(
                "Wash trial is unavailable during an active viscometry run",
                409,
            )
        lid = getattr(self.web, "lid_tool", None)
        if lid is not None and getattr(lid, "busy", False):
            raise WashTrialError("Lid tool is busy — wait until it finishes.", 409)
        if not self._motion_lock.acquire(blocking=False):
            raise WashTrialError("Wash trial is already running", 409)
        self.busy = True
        self._abort = False
        self.phase = "preparing"
        with self.web.testing_control_lock:
            self.web.testing_request_in_progress = True

    def _release(self) -> None:
        if self.phase not in ("error", "stopped"):
            self.phase = "idle"
        self.busy = False
        with self.web.testing_control_lock:
            self.web.testing_request_in_progress = False
        try:
            self._motion_lock.release()
        except RuntimeError:
            pass

    def _should_abort(self) -> bool:
        return bool(self._abort or self.web.is_running or self.web.should_stop())

    def _machine(self) -> CNC_Machine:
        virtual = os.getenv("VISCOMETRY_CNC_VIRTUAL", "0") == "1"
        try:
            return CNC_Machine(virtual=virtual)
        except Exception as exc:
            self.last_error = str(exc)
            raise WashTrialError(f"Unable to open the CNC: {exc}", 503) from exc

    def _emergency_cleanup(self, cnc: Optional[CNC_Machine], pump) -> None:
        try:
            if pump is not None:
                if hasattr(pump, "send_tag"):
                    pump.send_tag(b"0")
        except Exception:
            pass
        try:
            if cnc is not None:
                cnc.move_to_point(z=0, speed=500, allow_abort=False)
        except Exception:
            pass

    def _ok(self, message: str, *, result: Optional[Dict[str, Any]] = None) -> dict:
        status = self.status()
        status["busy"] = False
        payload = {
            "ok": True,
            "message": message,
            "wash_trial": status,
        }
        if result is not None:
            payload["result"] = result
        return payload

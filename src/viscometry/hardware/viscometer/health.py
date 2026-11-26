"""On-demand viscometer COM/health probe for the Testing tab."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

from viscometry.hardware.viscometer.client import ViscometerClient
from viscometry.paths import WORKER32_DIR
from viscometry.run import settings as run_settings


def _resolve_python32() -> str:
    env = os.getenv("VISCOMETRY_PYTHON32") or os.getenv("PYTHON32")
    if env:
        return str(env)
    return str(getattr(run_settings, "PYTHON32", ".\\.venv32\\Scripts\\python.exe"))


def _resolve_port() -> str:
    return str(
        os.getenv("VISCOMETRY_VISCO_PORT")
        or os.getenv("VISCO_PORT")
        or getattr(run_settings, "VISCO_PORT", "COM6")
    )


def _resolve_baud() -> int:
    raw = os.getenv("VISCOMETRY_VISCO_BAUD") or os.getenv("VISCO_BAUD")
    if raw:
        return int(raw)
    return int(getattr(run_settings, "VISCO_BAUD", 115200))


def _resolve_timeout() -> float:
    raw = os.getenv("VISCOMETRY_VISCO_TIMEOUT") or os.getenv("VISCO_TOUT")
    if raw:
        return float(raw)
    return float(getattr(run_settings, "VISCO_TOUT", 1.0))


def _resolve_spindle_k() -> float:
    raw = os.getenv("VISCOMETRY_SPINDLE_K")
    if raw:
        return float(raw)
    return float(getattr(run_settings, "SPINDLE_K", 992.47))


def probe_viscometer(*, reidentify: bool = True) -> Dict[str, Any]:
    """
    Open a short-lived 32-bit worker, init the COM port, optionally re-identify,
    then always close. Does not leave the port held.

    Returns a JSON-serialisable result dict with ok/state/message fields.
    """
    port = _resolve_port()
    baud = _resolve_baud()
    timeout = _resolve_timeout()
    spindle_k = _resolve_spindle_k()
    py32 = _resolve_python32()
    worker_path = WORKER32_DIR / "worker32.py"

    started = time.time()
    client: Optional[ViscometerClient] = None
    try:
        if not worker_path.is_file():
            return {
                "ok": False,
                "state": "error",
                "message": f"Viscometer worker not found: {worker_path}",
                "port": port,
                "baud": baud,
                "elapsed_s": round(time.time() - started, 3),
            }

        client = ViscometerClient(py32, worker_path)
        init_data = client.init(
            port=port,
            baud=baud,
            timeout=timeout,
            spindle_k=spindle_k,
        )
        identify_raw = None
        if reidentify:
            try:
                id_data = client.identify()
                identify_raw = (id_data or {}).get("cleaned") or (id_data or {}).get("raw")
            except Exception as id_exc:
                # init already talked to the device; treat re-identify failure as soft warn
                identify_raw = f"re-identify failed: {id_exc}"

        # Exercise reconnect path used after lid/idle so Testing matches run behavior.
        reconnect_ok = False
        try:
            client.reconnect(reason="health check")
            client.ping()
            reconnect_ok = True
        except Exception as reconnect_exc:
            return {
                "ok": False,
                "state": "error",
                "message": "Viscometer opened but reconnect/ping failed",
                "error": str(reconnect_exc),
                "port": port,
                "baud": baud,
                "elapsed_s": round(time.time() - started, 3),
                "identify": identify_raw,
            }

        elapsed = round(time.time() - started, 3)
        return {
            "ok": True,
            "state": "ok",
            "message": f"Connected on {port} @ {baud} (reconnect OK)",
            "port": port,
            "baud": baud,
            "elapsed_s": elapsed,
            "identify_raw": init_data.get("identify_raw") if isinstance(init_data, dict) else None,
            "identify": identify_raw,
            "proto": init_data.get("proto") if isinstance(init_data, dict) else None,
            "reconnect_ok": reconnect_ok,
        }
    except Exception as exc:
        return {
            "ok": False,
            "state": "error",
            "message": "Viscometer health check failed",
            "error": str(exc),
            "port": port,
            "baud": baud,
            "elapsed_s": round(time.time() - started, 3),
        }
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass

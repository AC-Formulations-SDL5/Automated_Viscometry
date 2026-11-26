# 64-bit client for the 32-bit worker (JSON-lines over subprocess)
from __future__ import annotations

import json
import pathlib
import queue
import subprocess
import threading
import time
import uuid
from typing import Any, Dict, Optional


def _looks_like_serial_fault(exc: BaseException) -> bool:
    """True for USB/COM write failures that usually need a fresh serial open."""
    text = str(exc).lower()
    needles = (
        "writefile",
        "permissionerror",
        "serialexception",
        "device does not recognize",
        "access is denied",
        "clearcommerror",
        "the device does not recognize the command",
        "port is closed",
        "device not initialized",
        "working",
        "i/o error",
        "errno 5",
        "errno 13",
    )
    return any(n in text for n in needles)


class ViscometerClient:
    """Long-lived bridge to the 32-bit viscometer worker with reconnect support."""

    def __init__(self, py32_path: str, worker_path: pathlib.Path):
        self.proc = subprocess.Popen(
            [py32_path, str(worker_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=str(worker_path.parent),
        )
        self.q: queue.Queue = queue.Queue()
        self._conn: Optional[Dict[str, Any]] = None
        self._last_ok_ts: float = 0.0
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        for line in self.proc.stdout:
            self.q.put(line)

    def req(self, cmd: str, timeout_s: float = 60, **kwargs) -> Dict[str, Any]:
        rid = str(uuid.uuid4())
        payload = {"id": rid, "cmd": cmd, **kwargs}
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            try:
                resp = json.loads(self.q.get(timeout=0.25))
            except queue.Empty:
                continue
            if resp.get("id") == rid:
                if not resp.get("ok"):
                    raise RuntimeError(f"{cmd} failed: {resp.get('error')}")
                self._last_ok_ts = time.time()
                return resp["data"]
        raise TimeoutError(f"{cmd} timed out after {timeout_s}s")

    # Convenience wrappers
    def init(self, *, port: str, baud: int, timeout: float = 1.0, spindle_k: float = 992.47):
        self._conn = {
            "port": str(port),
            "baud": int(baud),
            "timeout": float(timeout),
            "spindle_k": float(spindle_k),
        }
        return self.req(
            "init",
            timeout_s=10,
            port=self._conn["port"],
            baud=self._conn["baud"],
            timeout=self._conn["timeout"],
            spindle_k=self._conn["spindle_k"],
        )

    def status(self):
        return self.req("status", timeout_s=5)

    def identify(self):
        return self.req("identify", timeout_s=5)

    def zero(self):
        return self.req("zero", timeout_s=5)

    def set_speed(self, rpm: float):
        return self.req("set_speed", timeout_s=5, rpm=rpm)

    def read_single(self, timeout: float = 1.0):
        return self.req("read_single", timeout_s=5, timeout=timeout)

    def stop(self):
        return self.req("stop", timeout_s=5)

    def reconnect(self, *, reason: str = "") -> Dict[str, Any]:
        """Close and reopen the COM session using the last init parameters."""
        if not self._conn:
            raise RuntimeError("viscometer not initialized; call init() before reconnect()")
        label = f" ({reason})" if reason else ""
        print(f"  Viscometer: reconnecting COM session{label}...")
        # Prefer worker reconnect (keeps process); fall back to init which also reopens.
        try:
            data = self.req("reconnect", timeout_s=15, **self._conn)
        except Exception:
            data = self.init(**self._conn)
        print(
            f"  Viscometer: reconnect OK on {self._conn.get('port')} "
            f"@ {self._conn.get('baud')}"
        )
        return data

    def ping(self) -> Dict[str, Any]:
        """Lightweight serial round-trip (identify). Status alone does not touch COM."""
        return self.identify()

    def ensure_alive(
        self,
        *,
        reason: str = "",
        max_attempts: int = 2,
        idle_reconnect_s: Optional[float] = 45.0,
    ) -> Dict[str, Any]:
        """
        Ensure the COM link still answers. Proactively reconnect after long idle
        (e.g. lid pickup), and retry reconnect on serial faults.
        """
        if not self._conn:
            raise RuntimeError("viscometer not initialized; call init() first")

        if self._last_ok_ts and self._last_ok_ts > 0:
            idle_s: Optional[float] = time.time() - self._last_ok_ts
        else:
            # No successful COM traffic yet, or clock unset — treat as stale.
            idle_s = float("inf")
        should_preempt = (
            idle_reconnect_s is not None
            and idle_s >= float(idle_reconnect_s)
        )
        if should_preempt:
            idle_label = f"{idle_s:.0f}s idle"
            why = f"{reason}; {idle_label}" if reason else idle_label
            try:
                self.reconnect(reason=why)
            except Exception as exc:
                print(f"  Viscometer: proactive reconnect failed: {exc}")

        last_exc: Optional[BaseException] = None
        attempts = max(1, int(max_attempts))
        for attempt in range(1, attempts + 1):
            try:
                data = self.ping()
                if reason:
                    print(f"  Viscometer: link OK ({reason})")
                return data
            except Exception as exc:
                last_exc = exc
                print(
                    f"  Viscometer: ping failed "
                    f"(attempt {attempt}/{attempts}): {exc}"
                )
                if attempt >= attempts:
                    break
                if not _looks_like_serial_fault(exc) and attempt == 1:
                    # Still try one reconnect — mid-run faults are usually serial.
                    pass
                try:
                    self.reconnect(reason=f"after ping failure; {reason}" if reason else "after ping failure")
                except Exception as reconnect_exc:
                    last_exc = reconnect_exc
                    print(f"  Viscometer: reconnect failed: {reconnect_exc}")
        assert last_exc is not None
        raise RuntimeError(
            f"viscometer link unrecoverable"
            + (f" ({reason})" if reason else "")
            + f": {last_exc}"
        ) from last_exc

    def safe_zero(self, *, reason: str = "", soft: bool = True) -> Optional[Dict[str, Any]]:
        """Zero with one reconnect retry. soft=True logs and returns None instead of raising."""
        try:
            return self.zero()
        except Exception as first:
            print(f"  Viscometer: zero failed{(' — ' + reason) if reason else ''}: {first}")
            if not _looks_like_serial_fault(first):
                if soft:
                    return None
                raise
            try:
                self.reconnect(reason=f"before zero retry; {reason}" if reason else "before zero retry")
                return self.zero()
            except Exception as second:
                print(f"  Viscometer: zero retry failed: {second}")
                if soft:
                    return None
                raise

    def safe_stop(self, *, reason: str = "", soft: bool = True) -> Optional[Dict[str, Any]]:
        """Stop spindle with one reconnect retry. soft=True never raises."""
        try:
            return self.stop()
        except Exception as first:
            print(f"  Viscometer: stop failed{(' — ' + reason) if reason else ''}: {first}")
            try:
                self.reconnect(reason=f"before stop retry; {reason}" if reason else "before stop retry")
                return self.stop()
            except Exception as second:
                print(f"  Viscometer: stop retry failed: {second}")
                if soft:
                    return None
                raise

    def close(self):
        try:
            self.req("quit", timeout_s=5)
        except Exception:
            pass
        try:
            self.proc.terminate()
        except Exception:
            pass

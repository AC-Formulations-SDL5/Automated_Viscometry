# 64-bit client for the 32-bit worker (JSON-lines over subprocess)
import json, subprocess, threading, queue, time, uuid, pathlib
from typing import Any, Dict, Optional

class ViscometerClient:
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
        self.q = queue.Queue()
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
                return resp["data"]
        raise TimeoutError(f"{cmd} timed out after {timeout_s}s")

    # Convenience wrappers
    def init(self, *, port: str, baud: int, timeout: float = 1.0, spindle_k: float = 992.47):
        return self.req("init", timeout_s=10, port=port, baud=baud, timeout=timeout, spindle_k=spindle_k)

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

    def close(self):
        try:
            self.req("quit", timeout_s=5)
        except Exception:
            pass
        self.proc.terminate()

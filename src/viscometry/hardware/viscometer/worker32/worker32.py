# JSON-lines worker for the 32-bit viscometer side
import sys, json, traceback, time
from typing import Optional, Dict, Any

try:
    from viscometer_protocol import ViscometerProtocol
except Exception as e:
    # Return a clear error if import fails (wrong venv bitness)
    sys.stdout.write(json.dumps({"id": None, "ok": False, "error": f"import error: {e}"}) + "\n")
    sys.stdout.flush()
    sys.exit(1)

PROTO_VERSION = "1.0"

class DeviceState:
    def __init__(self):
        self.dev: Optional[ViscometerProtocol] = None
        self.opened: bool = False
        self.current_rpm: float = 0.0
        self.port: str = "COM6"
        self.baud: int = 115200
        self.timeout: float = 1.0
        self.spindle_k: float = 992.47

STATE = DeviceState()

def ok(i, data=None, **extra):
    resp = {"id": i, "ok": True, "data": data or {}}
    if extra:
        resp.update(extra)
    return resp

def err(i, message):
    return {"id": i, "ok": False, "error": message}

def ensure_open():
    if not (STATE.dev and STATE.opened):
        raise RuntimeError("device not initialized; call 'init' first")

def _close_device():
    if STATE.dev:
        try:
            STATE.dev.close()
        except Exception:
            pass
    STATE.dev = None
    STATE.opened = False

def _open_device(port: str, baud: int, timeout: float, spindle_k: float):
    _close_device()
    STATE.port = str(port)
    STATE.baud = int(baud)
    STATE.timeout = float(timeout)
    STATE.spindle_k = float(spindle_k)
    STATE.dev = ViscometerProtocol(
        port=STATE.port,
        baud=STATE.baud,
        spindle_k=STATE.spindle_k,
        timeout_s=STATE.timeout,
    )
    STATE.dev.connect()
    STATE.opened = True
    STATE.current_rpm = 0.0

# Command handlers
def cmd_init(i, msg):
    port = msg.get("port", STATE.port or "COM6")
    baud = int(msg.get("baud", STATE.baud or 115200))
    timeout = float(msg.get("timeout", STATE.timeout or 1.0))
    spindle_k = float(msg.get("spindle_k", STATE.spindle_k or 992.47))

    _open_device(port, baud, timeout, spindle_k)

    raw, cleaned = STATE.dev.send_command("I", wait_first_line=True)
    try:
        STATE.dev.stop_spindle()
    except Exception:
        pass
    return ok(i, data={
        "proto": PROTO_VERSION,
        "identify_raw": cleaned or raw,
        "port": STATE.port,
        "baud": STATE.baud,
        "reconnected": False,
    })

def cmd_reconnect(i, msg):
    """Close and reopen the COM port without killing the worker process."""
    port = msg.get("port", STATE.port or "COM6")
    baud = int(msg.get("baud", STATE.baud or 115200))
    timeout = float(msg.get("timeout", STATE.timeout or 1.0))
    spindle_k = float(msg.get("spindle_k", STATE.spindle_k or 992.47))

    # Brief pause so Windows can release a stale USB handle after lid/idle faults.
    time.sleep(0.35)
    _open_device(port, baud, timeout, spindle_k)

    raw, cleaned = STATE.dev.send_command("I", wait_first_line=True)
    try:
        STATE.dev.stop_spindle()
    except Exception:
        pass
    return ok(i, data={
        "proto": PROTO_VERSION,
        "identify_raw": cleaned or raw,
        "port": STATE.port,
        "baud": STATE.baud,
        "reconnected": True,
    })

def cmd_status(i, _msg):
    return ok(i, data={
        "opened": STATE.opened,
        "port": STATE.dev.port if STATE.dev else None,
        "baud": STATE.dev.baud if STATE.dev else None,
        "rpm": STATE.current_rpm
    })

def cmd_identify(i, _msg):
    ensure_open()
    raw, cleaned = STATE.dev.send_command("I", wait_first_line=True)
    return ok(i, data={"raw": raw, "cleaned": cleaned})

def cmd_zero(i, _msg):
    ensure_open()
    raw, cleaned = STATE.dev.send_command("Z", wait_first_line=True)
    return ok(i, data={"raw": raw, "cleaned": cleaned})

def cmd_set_speed(i, msg):
    ensure_open()
    rpm = float(msg["rpm"])
    raw, cleaned = STATE.dev.set_speed(rpm)
    STATE.current_rpm = rpm
    return ok(i, data={"raw": raw, "cleaned": cleaned, "rpm": rpm})

def cmd_read_single(i, msg):
    ensure_open()
    timeout = float(msg.get("timeout", 1.0))
    pkt = STATE.dev.read_single_point(timeout_s=timeout)
    if not pkt:
        return err(i, "no valid packet")
    return ok(i, data=pkt)

def cmd_stop(i, _msg):
    ensure_open()
    raw, cleaned = STATE.dev.stop_spindle()
    STATE.current_rpm = 0.0
    return ok(i, data={"raw": raw, "cleaned": cleaned})

def cmd_quit(i, _msg):
    try:
        if STATE.dev:
            try:
                STATE.dev.stop_streaming()
            except Exception:
                pass
            try:
                STATE.dev.stop_spindle()
            except Exception:
                pass
            try:
                STATE.dev.close()
            except Exception:
                pass
    finally:
        STATE.opened = False
        STATE.dev = None
    return ok(i)

HANDLERS = {
    "init": cmd_init,
    "reconnect": cmd_reconnect,
    "status": cmd_status,
    "identify": cmd_identify,
    "zero": cmd_zero,
    "set_speed": cmd_set_speed,
    "read_single": cmd_read_single,
    "stop": cmd_stop,
    "quit": cmd_quit,
}

def handle(msg: Dict[str, Any]):
    i = msg.get("id")
    cmd = msg.get("cmd")
    if not cmd:
        return err(i, "missing 'cmd'")
    fn = HANDLERS.get(cmd)
    if not fn:
        return err(i, f"unknown cmd '{cmd}'")
    try:
        return fn(i, msg)
    except Exception as e:
        tb = traceback.format_exc(limit=2)
        return err(i, f"{e} | {tb}")

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception as e:
            sys.stdout.write(json.dumps(err(None, f"bad json: {e}")) + "\n"); sys.stdout.flush()
            continue
        resp = handle(msg)
        sys.stdout.write(json.dumps(resp) + "\n"); sys.stdout.flush()
        if msg.get("cmd") == "quit":
            break

if __name__ == "__main__":
    main()

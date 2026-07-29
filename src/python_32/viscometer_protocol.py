# viscometer_protocol.py
import ctypes
from ctypes import c_wchar_p
import serial
import time
import os
import threading
from typing import Callable, Optional, Tuple, Dict, Any

COM_PORT   = "COM6"
BAUD_RATE  = 115200
SPINDLE_K  = 992.47   # spindle constant for viscosity calculation 

class ViscometerProtocol:
    _INVALID_16 = {0xFFFF, 0xFFFE, 0xFFFD}  # Sentinels & simple sanity for torque/temp fields

    def __init__(
        self,
        port: str = COM_PORT,
        baud: int = BAUD_RATE,
        spindle_k: float = SPINDLE_K,
        dll_path: Optional[str] = None,
        timeout_s: float = 1.0
    ):
        self.port = port
        self.baud = baud
        self.spindle_k = spindle_k
        self.timeout_s = timeout_s
        self._ser: Optional[serial.Serial] = None
        self._lock = threading.Lock()
        self._streaming = False
        self._stream_thread: Optional[threading.Thread] = None
        self._current_rpm: float = 0.0

        # Load DLL (defaults to DVT_COM.dll)
        if dll_path is None:
            dll_path = os.path.join(os.path.dirname(__file__), "DVT_COM.dll")
        self._dll = ctypes.WinDLL(dll_path)
        self._dll.AddCRCToString.argtypes = [c_wchar_p, c_wchar_p]
        self._dll.AddCRCToString.restype = None
        self._dll.CheckCRCAndRemove.argtypes = [c_wchar_p, c_wchar_p]
        self._dll.CheckCRCAndRemove.restype = None

    # Connection
    def connect(self):
        if self._ser is None or not self._ser.is_open:
            self._ser = serial.Serial(self.port, baudrate=self.baud, timeout=self.timeout_s)

    def close(self):
        self.stop_streaming()
        if self._ser and self._ser.is_open:
            self._ser.close()
        self._ser = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    # CRC wrappers
    def _add_crc(self, command: str) -> str:
        buf = ctypes.create_unicode_buffer(80)
        src = ctypes.create_unicode_buffer(command)
        self._dll.AddCRCToString(buf, src)
        return buf.value.strip()

    def _remove_crc(self, response: str) -> str:
        buf = ctypes.create_unicode_buffer(80)
        src = ctypes.create_unicode_buffer(response)
        self._dll.CheckCRCAndRemove(buf, src)
        return buf.value.strip()

    # Serial helpers 
    def _reset_input_buffer(self):
        with self._lock:
            if self._ser:
                self._ser.reset_input_buffer()

    def _write(self, text: str):
        with self._lock:
            if self._ser:
                self._ser.write(text.encode("ascii"))

    def _readline(self, timeout_s: Optional[float] = None) -> str:
        end = time.time() + (timeout_s if timeout_s is not None else self.timeout_s)
        line = b""
        while time.time() < end and not line:
            with self._lock:
                if self._ser:
                    line = self._ser.read_until(b"\r")
            if line:
                break
            time.sleep(0.01)
        try:
            return line.decode("ascii", errors="ignore").strip()
        except Exception:
            return ""

    # Protocol utilities 
    @staticmethod
    def rpm_to_vcmd(rpm: float) -> str:
        if not (0.0 <= rpm <= 200.0):
            raise ValueError("RPM must be between 0.0 and 200.0")
        v = int(round(rpm * 100.0))
        if v > 0xFFFF:
            v = 0xFFFF
        return f"V{v:04X}"

    def send_command(
        self,
        cmd: str,
        *,
        expect_stream: bool = False,
        wait_first_line: bool = True,
        first_line_timeout_s: float = 0.8
    ) -> Tuple[str, str]:

        wrapped = self._add_crc(cmd) + "\r"
        if not expect_stream:
            self._reset_input_buffer()
        self._write(wrapped)
        if wait_first_line:
            raw = self._readline(timeout_s=first_line_timeout_s)
            cleaned = self._remove_crc(raw) if raw else ""
            return raw, cleaned
        return "", ""

    # Field sanitizers 
    @classmethod
    def _sanitize_percent_from_q(cls, q_raw: int):
        # Returns (value_percent_or_None, is_valid, capped_value)
        if q_raw in cls._INVALID_16:
            return None, False, None
        val = q_raw / 100.0
        if not (0.0 <= val <= 100.0):
            return val, False, min(max(val, 0.0), 100.0)
        return val, True, val

    @classmethod
    def _sanitize_temp_from_T(cls, T_raw: int):
        # Returns (temp_c_or_None, is_valid)
        if T_raw in cls._INVALID_16:
            return None, False
        val = (T_raw / 100.0) - 100.0
        if val < -50.0 or val > 200.0:
            return val, False
        return val, True

    # Parsers 
    @classmethod
    def parse_data_response(cls, cleaned: str) -> Optional[Dict[str, Any]]:
        # Parse R<tttt><qqqq><TTTT><ss>.
        if not cleaned.startswith("R") or len(cleaned) < 15:
            return None
        try:
            s = cleaned[1:]
            record_number = int(s[0:4], 16)
            q_raw = int(s[4:8], 16)
            T_raw = int(s[8:12], 16)
            status = int(s[12:14], 16)

            tq_pct, tq_ok, tq_capped = cls._sanitize_percent_from_q(q_raw)
            temp_c, T_ok = cls._sanitize_temp_from_T(T_raw)

            return {
                "record_number": record_number,
                "torque_raw": q_raw,
                "temp_raw": T_raw,
                "status": status,
                "status_binary": format(status, "08b"),
                "torque_percent": tq_pct,            # None if invalid/sentinel
                "torque_valid": tq_ok,
                "torque_percent_capped": tq_capped,  # capped (0–100) or None
                "temperature_c": temp_c,             # None if invalid/sentinel
                "temp_valid": T_ok,
            }
        except Exception:
            return None

    @staticmethod
    def interpret_status(status_byte: int):
        msgs = []
        if status_byte & 0x01: msgs.append("Checksum Failure")
        if status_byte & 0x02: msgs.append("Exiting External Mode")
        # bit 2 unused
        if status_byte & 0x08: msgs.append("Temperature Probe Failure")
        if status_byte & 0x10: msgs.append("Temperature Probe Unplugged")
        if status_byte & 0x20: msgs.append("Sent Speed is Out of Range")
        if status_byte & 0x40: msgs.append("INI Write Error")
        if status_byte & 0x80: msgs.append("Audit Trail Write Error")
        return msgs if msgs else ["OK"]

    @staticmethod
    def parse_identify(cleaned: str):
        # I<dddd><mm><xxxxxx><ss>
        if not cleaned.startswith("I") or len(cleaned) < 1 + 4 + 2 + 6 + 2:
            return None
        s = cleaned[1:]
        series = s[0:4]
        model = s[4:6]
        fw_hex = s[6:12]
        status = int(s[12:14], 16)
        fwv = f"{int(fw_hex[0:2]):02d}.{int(fw_hex[2:4]):02d}.{int(fw_hex[4:6]):02d}"
        return {"series": series, "model": model, "fw_version": fwv, "status": status}

    @staticmethod
    def parse_zero(cleaned: str):
        # Z<ss>
        if not cleaned.startswith("Z") or len(cleaned) < 3:
            return None
        return {"status": int(cleaned[1:3], 16)}

    # High-level actions 
    def set_speed(self, rpm: float) -> Tuple[str, str]:
        vcmd = self.rpm_to_vcmd(rpm)
        self._current_rpm = float(rpm)
        return self.send_command(vcmd, wait_first_line=True, first_line_timeout_s=1.0)

    def stop_spindle(self) -> Tuple[str, str]:
        self._current_rpm = 0.0
        return self.send_command("V0000", wait_first_line=True)

    def read_single_point(self, timeout_s: float = 1.0) -> Optional[Dict[str, Any]]:
        raw, cleaned = self.send_command("R", wait_first_line=True, first_line_timeout_s=timeout_s)
        if not cleaned:
            return None
        pkt = self.parse_data_response(cleaned)
        if not pkt:
            return None

        # Compute viscosity only if torque is valid and RPM > 0
        if pkt.get("torque_valid") and pkt.get("torque_percent") is not None and self._current_rpm > 0:
            viscosity = (pkt["torque_percent"] * self.spindle_k) / self._current_rpm
            pkt["viscosity_cp"] = viscosity
        else:
            pkt["viscosity_cp"] = None
        return pkt

    # Streaming (optional; no prints) 
    def start_streaming(self, callback: Optional[Callable[[str, str], None]] = None):
        # Send D1 and read lines in a background thread. If callback is provided, it's called as callback(cleaned, raw) for each line.
        if self._streaming:
            return
        self.send_command("D1", expect_stream=True, wait_first_line=False)
        self._streaming = True

        def _reader():
            while self._streaming:
                raw = ""
                with self._lock:
                    if self._ser:
                        raw_bytes = self._ser.read_until(b"\r")
                        raw = raw_bytes.decode("ascii", errors="ignore").strip() if raw_bytes else ""
                if not raw:
                    continue
                cleaned = self._remove_crc(raw)
                if callback:
                    try:
                        callback(cleaned, raw)
                    except Exception:
                        pass

        self._stream_thread = threading.Thread(target=_reader, daemon=True)
        self._stream_thread.start()

    def stop_streaming(self, join_timeout_s: float = 1.0) -> Tuple[str, str]:
        if not self._streaming:
            return "", ""
        self._streaming = False
        if self._stream_thread:
            self._stream_thread.join(timeout=join_timeout_s)
        self._stream_thread = None
        return self.send_command("D0", wait_first_line=True)

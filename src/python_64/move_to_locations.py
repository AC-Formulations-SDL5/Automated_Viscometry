import time, serial
from serial import SerialException
from cnc_controller import CNC_Machine

MEASUREMENT_WAIT = 0
WASH1_WAIT = 60 # 30.0
WASH2_WAIT = 30
WASH3_WAIT = 30
ESP32_BOOT_DELAY_S = 1.5

class PumpESP32:
    def __init__(self, port: str, baud: int = 9600, virtual: bool = False):
        self.port = port
        self.baud = baud
        self.virtual = virtual
        self.ser: serial.Serial | None = None

    def open(self):
        if self.virtual:
            print(f"[PUMP VIRTUAL] open {self.port} @ {self.baud}")
            return
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            time.sleep(ESP32_BOOT_DELAY_S)
        except SerialException as e:
            print(f"[PUMP WARN] could not open {self.port}: {e}. Falling back to virtual.")
            self.virtual = True

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def send_tag(self, tag: bytes):
        if self.virtual:
            print(f"[PUMP VIRTUAL] tag -> {tag!r}")
            return
        self.ser.write(tag)

# helpers
def go_to_sample(cnc, rack: str, idx: int, safe: bool = True, wait_s=0):
    print(f"[SAMPLE] Moving to {rack}[{idx}]")
    cnc.move_to_location(rack, idx, safe=safe)
    if wait_s > 0:
        print(f"[SAMPLE] Waiting {wait_s}s for measurement...")
        time.sleep(wait_s)

def go_to_wash_station(cnc, station_idx: int, safe: bool = True):
    cnc.move_to_location("washing_station", station_idx, safe=safe)

def wash1(cnc, pump: PumpESP32):
    go_to_wash_station(cnc, 0, safe=True)
    print("[WASH1] start")
    pump.send_tag(b"1")
    time.sleep(WASH1_WAIT)

def wash2(cnc, pump: PumpESP32):
    go_to_wash_station(cnc, 1, safe=True)
    print("[WASH2] start")
    pump.send_tag(b"2")
    time.sleep(WASH2_WAIT)

def wash3(cnc, pump: PumpESP32):
    go_to_wash_station(cnc, 2, safe=True)
    print("[WASH3] start")
    pump.send_tag(b"3")
    time.sleep(WASH3_WAIT)

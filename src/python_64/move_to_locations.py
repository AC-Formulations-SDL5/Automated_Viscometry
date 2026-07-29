import time, serial
from typing import Callable, Optional
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
            # Clear any existing data in buffers
            if self.ser.is_open:
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
            print(f"[PUMP] Successfully opened {self.port} @ {self.baud}")
        except SerialException as e:
            print(f"[PUMP WARN] could not open {self.port}: {e}. Falling back to virtual.")
            self.virtual = True

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def send_tag(self, tag: bytes):
        """Send command without acknowledgment (legacy mode)"""
        if self.virtual:
            print(f"[PUMP VIRTUAL] tag -> {tag!r}")
            return
        if self.ser and self.ser.is_open:
            self.ser.write(tag)
        else:
            print(f"[PUMP ERROR] Serial port not open, cannot send {tag!r}")

    def send_command_with_ack(
        self,
        command: bytes,
        timeout: float = 2.0,
        max_retries: int = 3,
        should_abort: Optional[Callable[[], bool]] = None,
    ) -> bool:
        """
        Send command and wait for acknowledgment with retry mechanism.
        Returns True if successful, False if failed after retries.
        """
        if self.virtual:
            print(f"[PUMP VIRTUAL] command_with_ack -> {command!r}")
            return True
            
        if not self.ser or not self.ser.is_open:
            print(f"[PUMP ERROR] Serial port not open, cannot send {command!r}")
            return False
        
        command_str = command.decode('ascii')
        expected_ack = f"ACK:{command_str}"
        
        for attempt in range(max_retries):
            if should_abort and should_abort():
                print(f"[PUMP] ABORTED: Command {command_str} cancelled before attempt {attempt + 1}")
                return False
            try:
                # Clear input buffer before sending command
                self.ser.reset_input_buffer()
                
                # Send command
                print(f"[PUMP] Sending command: {command_str} (attempt {attempt + 1})")
                self.ser.write(command + b'\n')  # Add newline for better parsing
                
                # Wait for acknowledgment
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if should_abort and should_abort():
                        print(f"[PUMP] ABORTED: Command {command_str} cancelled while waiting for ACK")
                        return False
                    if self.ser.in_waiting > 0:
                        try:
                            response = self.ser.readline().decode('ascii').strip()
                            print(f"[PUMP] Received: '{response}'")
                            
                            if expected_ack in response:
                                print(f"[PUMP] SUCCESS: Command {command_str} acknowledged")
                                return True
                            elif "ERROR" in response or "CONFLICT" in response:
                                print(f"[PUMP] ERROR: Command {command_str} failed: {response}")
                                return False
                        except UnicodeDecodeError:
                            continue  # Skip malformed responses
                    time.sleep(0.05)  # Small delay to prevent excessive polling
                
                print(f"[PUMP] TIMEOUT: No acknowledgment for {command_str} (attempt {attempt + 1})")
                if should_abort and should_abort():
                    print(f"[PUMP] ABORTED: Command {command_str} will not be retried after timeout")
                    return False
                time.sleep(0.1)  # Brief delay before retry
                
            except Exception as e:
                print(f"[PUMP] Exception during command {command_str} (attempt {attempt + 1}): {e}")
                
        print(f"[PUMP] FAILED: Command {command_str} failed after {max_retries} attempts")
        return False

    def get_status(self) -> dict:
        """Get current ESP32 component status"""
        if self.virtual:
            # Return mock status for virtual mode
            return {
                "pump1": False, "pump3": False, "pump5": False,
                "motor1": False, "motor2": False, "motor3": False,
                "reverse1": False, "reverse2": False
            }
        
        if not self.ser or not self.ser.is_open:
            return {}
            
        try:
            # Clear input buffer
            self.ser.reset_input_buffer()
            
            # Send status request
            self.ser.write(b'ST\n')
            time.sleep(0.5)  # Allow time for response
            
            # Read response lines
            status_lines = []
            start_time = time.time()
            while time.time() - start_time < 2.0:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('ascii').strip()
                    if line:
                        status_lines.append(line)
                        if "================================" in line:
                            break
                time.sleep(0.05)
            
            # Parse status (simplified - you could make this more robust)
            status = {}
            for line in status_lines:
                if "Pump 1:" in line:
                    status["pump1"] = "RUNNING" in line
                elif "Pump 3:" in line:
                    status["pump3"] = "RUNNING" in line
                elif "Motor 1:" in line:
                    status["motor1"] = "RUNNING" in line
                elif "Motor 2:" in line:
                    status["motor2"] = "RUNNING" in line
                elif "Reverse 1:" in line:
                    status["reverse1"] = "RUNNING" in line
                elif "Reverse 2:" in line:
                    status["reverse2"] = "RUNNING" in line
                    
            return status
            
        except Exception as e:
            print(f"[PUMP] Error getting status: {e}")
            return {}

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

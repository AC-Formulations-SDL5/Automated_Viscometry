import time
import pathlib
import csv
import json
import glob
import os
import datetime
import traceback
import threading
import statistics
from typing import Dict, List, Optional, Tuple
from cnc_controller import CNC_Machine
from viscometer_client import ViscometerClient
from move_to_locations import PumpESP32
from feedback_helper_function import RotationalDragFeedbackController
from web_interface import web_interface

Z_STEP_SIZE = -0.02       #-0.100
Z_FEED_RATE = 500
TORQUE_BREAK_THRESHOLD = 100.0     #100.0

# ========== FEEDBACK CONTROLLER CONFIGURATION ==========
# Rotational drag feedback controller parameters
FEEDBACK_CONTROL_ENABLED = True             # Enable/disable feedback controller
MIN_DATA_POINTS_FOR_TREND = 8              # Minimum z-levels needed for trend analysis
R2_DRAG_MIN = 0.975
R2_CV_MIN = 0.975
R2_SLOPE_MIN = 0.975
HIT_POINT_CONFIDENCE_THRESHOLD = 0.8
WEIGHT_2ND_DERIV_DRAG = 0.2
WEIGHT_2ND_DERIV_CV = 0.2
WEIGHT_2ND_DERIV_SLOPE = 0.2
WEIGHT_R2_DRAG = 0.2
WEIGHT_R2_CV = 0.2
WEIGHT_R2_SLOPE = 0.2
BASELINE_N_CALIBRATION = 10
BASELINE_Z_THRESHOLD = 5.0

# ===============================================
SETTLE_TIME = 1.0                   # Time to wait after moving before taking measurements
TORQUE_READ_TIMEOUT = 2.0
SPINDLE_SETTLE_TIME = 1.0           # Time to wait after setting spindle speed before taking measurements
NUM_CELLS = 6
BASE_Y = 62
Y_OFFSET = 67                  
PYTHON32 = ".\\.venv32\\Scripts\\python.exe"
VISCO_PORT = "COM6"
VISCO_BAUD = 115200
VISCO_TOUT = 1.0
SPINDLE_K = 992.47
# ESP32 Pump Configuration
ESP32_PORT = "COM11"                # "COM8"
ESP32_BAUD = 115200 #9600
PUMP_VIRTUAL = False

# Wash station 1 coordinates
WASH_STATION1_X = 383    #387
WASH_STATION1_Y = 68
WASH_STATION1_Z = -67    # -67 is the contact point, so -10 is safely above that for washing position

# Wash station 2 coordinates
WASH_STATION2_X = 383    #387
WASH_STATION2_Y = 147
WASH_STATION2_Z = -67    # -67 is the contact point, so -10 is safely above that for washing position

# Row configurations: each row has different Z-parameters and BASE_X position
ROWS = [
    {'row_number': 1, 'base_x': 10, 'safe_z': -65.5, 'max_z_travel': -66.500},
    {'row_number': 2, 'base_x': 85, 'safe_z': -65.5, 'max_z_travel': -66.500},
    {'row_number': 3, 'base_x': 309, 'safe_z': -64.5, 'max_z_travel': -65.500}
]

# Array of RPMs to test at each Z-position (similar to analysis_methods.py)
TEST_RPMS = [0.8] #, 0.5, 1.0, 5.0, 10.0, 20.0, 50.0]
# Per-cell RPM overrides for custom mode: {cell_id: [rpm, ...]}
# Falls back to TEST_RPMS when a cell has no entry here.
CELL_RPM_MAP: Dict[int, List[float]] = {}
CELL_CONTENT_MAP: Dict[int, str] = {}
EXPERIMENT_NAME = ""
DWELL_SECONDS = 2.0
INTER_RPM_PAUSE = 2.0
MEASUREMENT_DURATION = 40.0
SAMPLE_INTERVAL = 5.0
SMART_EARLY_EXIT_ENABLED = False
SMART_CV_THRESHOLD = 0.005
SMART_WINDOW_SIZE = 3

# ========== TESTING MODE CONFIGURATION ==========
# Set the testing mode and parameters here (no runtime input required)

# MODE OPTIONS:
# "full"   - Test all 18 cells
# "row"    - Test specific rows 
# "custom" - Test specific cells by number
TESTING_MODE = "custom"  # Change this to "full", "row", or "custom"

# FOR ROW MODE: Specify which rows to test (1, 2, 3)
# Example: [1, 3] tests rows 1 and 3 (cells 1-6 and 13-18)
SELECTED_ROWS = [2]
# FOR CUSTOM MODE: Specify which cells to test (1-18)
# Example: [2, 5, 8, 11, 16] tests only those specific cells
SELECTED_CELLS = [1]  # Only used when TESTING_MODE = "custom"


def _sanitize_experiment_slug(name: str) -> str:
    """Create a filename-safe slug for experiment output files."""
    cleaned = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in (name or '').strip())
    cleaned = '_'.join(part for part in cleaned.split('_') if part)
    return cleaned[:80] if cleaned else "experiment"


def apply_runtime_settings_from_web():
    """Synchronize module-level run settings from the web interface."""
    global TESTING_MODE, SELECTED_ROWS, SELECTED_CELLS, TEST_RPMS, CELL_RPM_MAP, CELL_CONTENT_MAP
    global EXPERIMENT_NAME
    global Z_STEP_SIZE, DWELL_SECONDS, INTER_RPM_PAUSE, MEASUREMENT_DURATION, SAMPLE_INTERVAL
    global SMART_EARLY_EXIT_ENABLED, SMART_CV_THRESHOLD, SMART_WINDOW_SIZE
    global FEEDBACK_CONTROL_ENABLED, MIN_DATA_POINTS_FOR_TREND, HIT_POINT_CONFIDENCE_THRESHOLD, TORQUE_BREAK_THRESHOLD
    global R2_DRAG_MIN, R2_CV_MIN, R2_SLOPE_MIN
    global WEIGHT_2ND_DERIV_DRAG, WEIGHT_2ND_DERIV_CV, WEIGHT_2ND_DERIV_SLOPE
    global WEIGHT_R2_DRAG, WEIGHT_R2_CV, WEIGHT_R2_SLOPE
    global BASELINE_N_CALIBRATION, BASELINE_Z_THRESHOLD

    settings = web_interface.get_runtime_settings()

    EXPERIMENT_NAME = str(settings.get('experiment_name', EXPERIMENT_NAME) or '').strip()
    TESTING_MODE = settings.get('testing_mode', TESTING_MODE)
    SELECTED_ROWS = settings.get('selected_rows', SELECTED_ROWS)
    SELECTED_CELLS = settings.get('selected_cells', SELECTED_CELLS)
    TEST_RPMS = settings.get('test_rpms', TEST_RPMS)
    raw_map = settings.get('cell_rpm_map', {})
    CELL_RPM_MAP = {int(k): v for k, v in raw_map.items() if v}
    raw_content_map = settings.get('cell_content_map', {})
    CELL_CONTENT_MAP = {
        int(k): str(v).strip()
        for k, v in raw_content_map.items()
        if str(v).strip()
    }
    Z_STEP_SIZE = float(settings.get('z_step_size', Z_STEP_SIZE))
    DWELL_SECONDS = float(settings.get('dwell_seconds', DWELL_SECONDS))
    INTER_RPM_PAUSE = float(settings.get('inter_rpm_pause', INTER_RPM_PAUSE))
    MEASUREMENT_DURATION = float(settings.get('measurement_duration', MEASUREMENT_DURATION))
    SAMPLE_INTERVAL = float(settings.get('sample_interval', SAMPLE_INTERVAL))
    SMART_EARLY_EXIT_ENABLED = bool(settings.get('smart_early_exit_enabled', SMART_EARLY_EXIT_ENABLED))
    SMART_CV_THRESHOLD = float(settings.get('smart_cv_threshold', SMART_CV_THRESHOLD))
    SMART_WINDOW_SIZE = max(2, int(settings.get('smart_window_size', SMART_WINDOW_SIZE)))
    FEEDBACK_CONTROL_ENABLED = bool(settings.get('feedback_control_enabled', FEEDBACK_CONTROL_ENABLED))
    MIN_DATA_POINTS_FOR_TREND = int(settings.get('min_data_points_for_trend', MIN_DATA_POINTS_FOR_TREND))
    R2_DRAG_MIN = float(settings.get('r2_drag_min', R2_DRAG_MIN))
    R2_CV_MIN = float(settings.get('r2_cv_min', R2_CV_MIN))
    R2_SLOPE_MIN = float(settings.get('r2_slope_min', R2_SLOPE_MIN))
    HIT_POINT_CONFIDENCE_THRESHOLD = float(settings.get('hit_point_confidence_threshold', HIT_POINT_CONFIDENCE_THRESHOLD))
    TORQUE_BREAK_THRESHOLD = float(settings.get('torque_break_threshold', TORQUE_BREAK_THRESHOLD))
    WEIGHT_2ND_DERIV_DRAG = float(settings.get('weight_2nd_deriv_drag', WEIGHT_2ND_DERIV_DRAG))
    WEIGHT_2ND_DERIV_CV = float(settings.get('weight_2nd_deriv_cv', WEIGHT_2ND_DERIV_CV))
    WEIGHT_2ND_DERIV_SLOPE = float(settings.get('weight_2nd_deriv_slope', WEIGHT_2ND_DERIV_SLOPE))
    WEIGHT_R2_DRAG = float(settings.get('weight_r2_drag', WEIGHT_R2_DRAG))
    WEIGHT_R2_CV = float(settings.get('weight_r2_cv', WEIGHT_R2_CV))
    WEIGHT_R2_SLOPE = float(settings.get('weight_r2_slope', WEIGHT_R2_SLOPE))
    BASELINE_N_CALIBRATION = int(settings.get('baseline_n_calibration', BASELINE_N_CALIBRATION))
    BASELINE_Z_THRESHOLD = float(settings.get('baseline_z_threshold', BASELINE_Z_THRESHOLD))


def get_rpms_for_cell(global_cell: int) -> List[float]:
    """Return the RPM list for a specific cell.

    In custom mode, uses CELL_RPM_MAP if an entry exists for this cell,
    otherwise falls back to the global TEST_RPMS list.
    In full/row mode, always returns TEST_RPMS.
    """
    if TESTING_MODE == "custom" and global_cell in CELL_RPM_MAP:
        return CELL_RPM_MAP[global_cell]
    return TEST_RPMS


def sleep_with_stop(seconds: float, check_interval: float = 0.25):
    """Sleep in short intervals so a web stop request can interrupt the run."""
    deadline = time.time() + max(0.0, seconds)
    while time.time() < deadline:
        if web_interface.should_stop():
            raise KeyboardInterrupt("Stop requested from web interface")
        time.sleep(min(check_interval, max(0.0, deadline - time.time())))


def raise_if_stop_requested():
    """Raise KeyboardInterrupt if the web UI has requested a stop."""
    if web_interface.should_stop():
        raise KeyboardInterrupt("Stop requested from web interface")


def _run_in_thread(fn, *args, **kwargs) -> threading.Thread:
    """Launch fn(*args, **kwargs) in a daemon thread and return the thread object."""
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t


def _reliable_pump_command(pump: PumpESP32, command: bytes, description: str) -> bool:
    """Send pump command with acknowledgment and status verification (module-level)."""
    raise_if_stop_requested()
    print(f"  Executing: {description}")
    if hasattr(pump, 'send_command_with_ack'):
        success = pump.send_command_with_ack(
            command,
            timeout=3.0,
            max_retries=3,
            should_abort=web_interface.should_stop,
        )
        if success:
            print(f"  SUCCESS: {description}")
            return True
        else:
            print(f"  FAILED with ACK: {description}, trying legacy mode...")
            raise_if_stop_requested()
    pump.send_tag(command)
    sleep_with_stop(0.5)
    if hasattr(pump, 'get_status'):
        status = pump.get_status()
        if status and len(status) > 0:
            print(f"  Status after command: {status}")
    print(f"  LEGACY: {description} sent (no verification)")
    return True


def get_selected_cells():
    """Get the list of cells to test based on configuration parameters"""
    if TESTING_MODE == "full":
        return "full", list(range(1, 19))
    
    elif TESTING_MODE == "row":
        # Validate rows
        for row in SELECTED_ROWS:
            if row not in [1, 2, 3]:
                raise ValueError(f"Invalid row number in SELECTED_ROWS: {row}. Must be 1, 2, or 3.")
        
        # Convert rows to global cell numbers
        global_cells = []
        for row in SELECTED_ROWS:
            for local_cell in range(1, 7):
                global_cells.append(row_and_local_to_global_cell(row, local_cell))
        
        global_cells.sort()
        return "row", global_cells
    
    elif TESTING_MODE == "custom":
        # Validate cells
        for cell in SELECTED_CELLS:
            if cell < 1 or cell > 18:
                raise ValueError(f"Invalid cell number in SELECTED_CELLS: {cell}. Must be between 1 and 18.")
        
        custom_cells = sorted(SELECTED_CELLS)
        return "custom", custom_cells
    
    else:
        raise ValueError(f"Invalid TESTING_MODE: {TESTING_MODE}. Must be 'full', 'row', or 'custom'.")

def global_cell_to_row_and_local(global_cell: int) -> Tuple[int, int]:
    """Convert global cell number (1-18) to row number (1-3) and local cell number (1-6)"""
    if global_cell < 1 or global_cell > 18:
        raise ValueError(f"Global cell number must be between 1 and 18, got {global_cell}")
    
    row = ((global_cell - 1) // 6) + 1
    local_cell = ((global_cell - 1) % 6) + 1
    return row, local_cell

def row_and_local_to_global_cell(row: int, local_cell: int) -> int:
    """Convert row number (1-3) and local cell number (1-6) to global cell number (1-18)"""
    if row < 1 or row > 3:
        raise ValueError(f"Row number must be between 1 and 3, got {row}")
    if local_cell < 1 or local_cell > 6:
        raise ValueError(f"Local cell number must be between 1 and 6, got {local_cell}")
    
    return (row - 1) * 6 + local_cell

def perform_washing_sequence(
    cnc: CNC_Machine,
    pump: PumpESP32,
    global_cell: int,
    fill_thread: Optional[threading.Thread] = None,
):
    """
    Washing sequence with concurrent fill/drain overlap.

    PRE-CONDITION: _pump_fill_station1() and _motor1_start() are already running
    in background threads (started by test_cell_dynamic_z_series at end of last measurement).
    By the time this function is called and the CNC safe-moves to Station 1,
    the station should be filled and Motor M1 spinning.
    """
    print(f"\nStarting Washing Sequence for Cell {global_cell} (concurrent-overlap mode)")
    web_interface.update_status(f"Washing after Cell {global_cell}")
    drain_thread: Optional[threading.Thread] = None

    try:
        raise_if_stop_requested()

        print(f"Step W1: Moving CNC to above Wash Station 1 (X={WASH_STATION1_X}, Y={WASH_STATION1_Y}, Z=0)")
        web_interface.update_status("Wash Station 1: travelling (station pre-filling)")
        web_interface.update_position(WASH_STATION1_X, WASH_STATION1_Y, 0)
        cnc.move_to_point_safe(WASH_STATION1_X, WASH_STATION1_Y, 0, speed=3000)
        if fill_thread and fill_thread.is_alive():
            print("Waiting for concurrent Station 1 fill to complete (up to 30 s)...")
            fill_thread.join(timeout=30)
            if fill_thread.is_alive():
                print("WARNING: Fill thread still running after timeout — continuing with wash motion.")

        print("Step W2: Lowering CNC into Wash Station 1 (station pre-filled)...")
        web_interface.update_status("Wash Station 1: scrubbing")
        cnc.move_to_point(WASH_STATION1_X, WASH_STATION1_Y, WASH_STATION1_Z, speed=1000)

        print("Step W3: Performing 5 oscillating wash movements...")
        for i in range(5):
            raise_if_stop_requested()
            print(f"  Oscillation {i+1}/5: Moving to X=390")
            cnc.move_to_point(390, WASH_STATION1_Y, WASH_STATION1_Z, speed=1000)
            sleep_with_stop(1)
            print(f"  Oscillation {i+1}/5: Moving back to X={WASH_STATION1_X}")
            cnc.move_to_point(WASH_STATION1_X, WASH_STATION1_Y, WASH_STATION1_Z, speed=1000)
            sleep_with_stop(1)

        print("Step W4: Raising CNC from Station 1 and starting concurrent drain...")
        web_interface.update_status("Wash Station 1: draining (concurrent)")
        cnc.move_to_point(WASH_STATION1_X, WASH_STATION1_Y, 0, speed=500)
        drain_thread = _run_in_thread(_drain_station1, pump)
        _reliable_pump_command(pump, b"SM1", "Stop Motor 1 (post-scrub)")

        print(f"Step W5: Moving CNC to Wash Station 2 (X={WASH_STATION2_X}, Y={WASH_STATION2_Y}, Z=0)")
        web_interface.update_status("Wash Station 2: travelling | Drying Station: travelling")
        cnc.move_to_point_safe(WASH_STATION2_X, WASH_STATION2_Y, 0, speed=3000)

        print("Step W6: Starting Motor M2 and lowering into Wash Station 2...")
        _reliable_pump_command(pump, b"M2", "Start Motor 2")
        web_interface.update_status("Wash Station 2: scrubbing | Drying Station: scrubbing")
        cnc.move_to_point(WASH_STATION2_X, WASH_STATION2_Y, WASH_STATION2_Z, speed=1000)

        print("Step W7: Performing 5 oscillating dry-scrub movements...")
        for i in range(5):
            raise_if_stop_requested()
            print(f"  Oscillation {i+1}/5: Moving to X=390")
            cnc.move_to_point(390, WASH_STATION2_Y, WASH_STATION2_Z, speed=1000)
            sleep_with_stop(1)
            print(f"  Oscillation {i+1}/5: Moving back to X={WASH_STATION2_X}")
            cnc.move_to_point(WASH_STATION2_X, WASH_STATION2_Y, WASH_STATION2_Z, speed=1000)
            sleep_with_stop(1)

        print("Step W8: Raising CNC from Station 2 and stopping Motor M2...")
        cnc.move_to_point(WASH_STATION2_X, WASH_STATION2_Y, 0, speed=500)
        _reliable_pump_command(pump, b"SM2", "Stop Motor 2")

        if drain_thread and drain_thread.is_alive():
            print("Step W9: Waiting for Station 1 drain to complete (up to 30 s)...")
            drain_thread.join(timeout=30)
            if drain_thread.is_alive():
                print("WARNING: Drain thread did not finish within timeout — continuing.")

        print(f"Washing Sequence completed for Cell {global_cell}")

        if hasattr(pump, 'get_status'):
            final_status = pump.get_status()
            if final_status and any(final_status.values()):
                print(f"WARNING: Components still active after wash: {final_status}")
                pump.send_tag(b"0")
                sleep_with_stop(1)

    except Exception as e:
        print(f"Error during washing sequence for Cell {global_cell}: {e}")
        try:
            print("Executing emergency stop...")
            pump.send_tag(b"0")
            sleep_with_stop(2)
            cnc.move_to_point(WASH_STATION1_X, WASH_STATION1_Y, 0, speed=500)
        except Exception as cleanup_error:
            print(f"Error during cleanup: {cleanup_error}")
        raise

def move_to_cell_position(cnc: CNC_Machine, row_number: int, local_cell_number: int, z_height: float) -> Tuple[float, float, float]:
    """Move to specific cell position in a specific row (local cell numbering 1-6)"""
    # Find the BASE_X for this row
    base_x = None
    for row in ROWS:
        if row['row_number'] == row_number:
            base_x = row['base_x']
            break
    
    if base_x is None:
        raise ValueError(f"Invalid row number: {row_number}")
    
    x_pos = base_x
    y_pos = BASE_Y + (local_cell_number - 1) * Y_OFFSET
    global_cell = row_and_local_to_global_cell(row_number, local_cell_number)
    print(f"Moving to Cell {global_cell} (Row {row_number}, Local Cell {local_cell_number}): X={x_pos}, Y={y_pos}, Z={z_height:.3f}")
    
    # Update web interface with current cell and position
    web_interface.set_current_cell(global_cell)
    web_interface.update_status(f"Moving to Cell {global_cell}")
    web_interface.update_position(x_pos, y_pos, z_height)
    
    raise_if_stop_requested()
    cnc.move_to_point_safe(x_pos, y_pos, z_height, speed=3000)
    sleep_with_stop(SETTLE_TIME)
    return x_pos, y_pos, z_height


def _pump_fill_station1(pump: PumpESP32):
    """Fill wash station 1 (runs concurrently with CNC travel). Duration: 15 s."""
    try:
        raise_if_stop_requested()
        print("[CONCURRENT] Starting Pump P1 to fill Station 1...")
        _reliable_pump_command(pump, b"P1", "Start Pump 1 (concurrent fill)")
        sleep_with_stop(15)
        _reliable_pump_command(pump, b"SP1", "Stop Pump 1 (concurrent fill complete)")
        print("[CONCURRENT] Station 1 fill complete.")
    except KeyboardInterrupt:
        print("[CONCURRENT] Station 1 fill cancelled due to stop request.")


def _motor1_start(pump: PumpESP32):
    """Start Motor M1 (runs concurrently with CNC travel)."""
    try:
        raise_if_stop_requested()
        print("[CONCURRENT] Starting Motor M1...")
        _reliable_pump_command(pump, b"M1", "Start Motor 1 (concurrent)")
        print("[CONCURRENT] Motor M1 started.")
    except KeyboardInterrupt:
        print("[CONCURRENT] Motor M1 start cancelled due to stop request.")


def _drain_station1(pump: PumpESP32):
    """Drain wash station 1 via reverse rinse R1 (runs concurrently with CNC travel to Station 2). Duration: 20 s."""
    try:
        raise_if_stop_requested()
        print("[CONCURRENT] Starting reverse rinse R1 to drain Station 1...")
        _reliable_pump_command(pump, b"R1", "Start Reverse Rinse 1 (concurrent drain)")
        sleep_with_stop(20)
        _reliable_pump_command(pump, b"SR1", "Stop Reverse Rinse 1 (concurrent drain complete)")
        print("[CONCURRENT] Station 1 drain complete.")
    except KeyboardInterrupt:
        print("[CONCURRENT] Station 1 drain cancelled due to stop request.")

def measure_torque_at_rpm(client: ViscometerClient, rpm: float, z_height: float) -> Optional[List[Dict]]:
    """Measure torque at a specific RPM, returning all individual measurements with timestamps"""
    try:
        # Set spindle speed
        client.set_speed(rpm)
        web_interface.set_current_rpm(rpm)
        web_interface.update_status(f"Measuring at {rpm} RPM")
        sleep_with_stop(DWELL_SECONDS)  # Allow spindle to settle at new RPM
        
        # Collect torque measurements over duration
        measurements = []
        recent_torques = []
        start_time = time.time()
        measurement_start_time = time.time()
        next_sample_time = start_time + SAMPLE_INTERVAL
        
        while time.time() - start_time < MEASUREMENT_DURATION:
            raise_if_stop_requested()
            current_time = time.time()
            
            if current_time >= next_sample_time:
                try:
                    data = client.read_single(timeout=TORQUE_READ_TIMEOUT)
                    if data and data.get("torque_valid") and data.get("torque_percent") is not None:
                        measurement = {
                            "timestamp": current_time,
                            "elapsed_time": current_time - measurement_start_time,
                            "torque_percent": data["torque_percent"],
                            "rpm": rpm
                        }
                        measurements.append(measurement)
                        recent_torques.append(data["torque_percent"])
                        recent_torques = recent_torques[-SMART_WINDOW_SIZE:]
                        web_interface.update_live_torque(
                            torque_percent=data["torque_percent"],
                            rpm=rpm,
                            elapsed=current_time - measurement_start_time,
                        )
                        web_interface.add_measurement_point(
                            height=z_height,
                            rotational_drag=abs(data["torque_percent"]) / rpm if rpm > 0 else 0.0,
                            rpm=rpm,
                            cell_id=web_interface.current_cell,
                        )
                        if SMART_EARLY_EXIT_ENABLED and len(recent_torques) == SMART_WINDOW_SIZE:
                            recent_mean = statistics.mean(recent_torques)
                            if recent_mean > 0:
                                cv = statistics.pstdev(recent_torques) / recent_mean
                                if cv < SMART_CV_THRESHOLD:
                                    print(f"      [SMART EXIT] Torque stabilized at CV < {SMART_CV_THRESHOLD}")
                                    break
                    next_sample_time += SAMPLE_INTERVAL
                except Exception as e:
                    print(f"      Measurement error at RPM {rpm}: {e}")
            
            sleep_with_stop(0.1)
        
        # Stop spindle after measurement
        client.stop()
        web_interface.set_current_rpm(0)
        sleep_with_stop(INTER_RPM_PAUSE)
        
        # Report measurement summary
        if measurements:
            torque_values = [m["torque_percent"] for m in measurements]
            avg_torque = sum(torque_values) / len(torque_values)
            min_torque = min(torque_values)
            max_torque = max(torque_values)
            print(f"      RPM {rpm}: {len(measurements)} samples, Avg: {avg_torque:.2f}%, Range: {min_torque:.2f}% to {max_torque:.2f}%")
            return measurements
        else:
            print(f"      RPM {rpm}: No valid measurements collected")
            return None
            
    except Exception as e:
        print(f"      Error measuring torque at RPM {rpm}: {e}")
        try:
            client.stop()
            web_interface.set_current_rpm(0)
        except:
            pass
        return None

def test_dynamic_analysis_at_z(
    client: ViscometerClient,
    z_height: float,
    cell_rpms: List[float]
) -> Tuple[Dict[float, Optional[List[Dict]]], bool]:
    """Test all RPMs at a specific Z-height and return torque data and first_rpm_exceeded flag"""
    print(f"    Testing {len(cell_rpms)} RPMs at Z={z_height:.3f}")
    rpm_torque_data = {}
    first_rpm_exceeded_threshold = False
    
    for i, rpm in enumerate(cell_rpms):
        measurements = measure_torque_at_rpm(client, rpm, z_height)
        rpm_torque_data[rpm] = measurements
        
        # Check if measurements are invalid (high resistance condition) or exceed threshold
        if measurements is None:
            if i == 0:  # First RPM failed - critical condition
                print(f"      CRITICAL: First RPM {rpm} returned invalid torque (high resistance) - will break entire cell")
                first_rpm_exceeded_threshold = True
                # Fill remaining RPMs with None
                for remaining_rpm in cell_rpms[cell_rpms.index(rpm) + 1:]:
                    rpm_torque_data[remaining_rpm] = None
                break
            else:  # Later RPM failed - high resistance at this Z-level
                print(f"      RESISTANCE: RPM {rpm} returned invalid torque (high resistance) - stopping RPM sweep at this Z-level")
                # Fill remaining RPMs with None
                for remaining_rpm in cell_rpms[cell_rpms.index(rpm) + 1:]:
                    rpm_torque_data[remaining_rpm] = None
                break
        else:
            # Check if any torque measurement exceeds threshold
            max_torque = max(abs(m["torque_percent"]) for m in measurements)
            if max_torque >= TORQUE_BREAK_THRESHOLD:
                if i == 0:  # First RPM exceeded threshold
                    print(f"      CRITICAL: First RPM {rpm} exceeded threshold with max {max_torque:.2f}% - will break entire cell")
                    first_rpm_exceeded_threshold = True
                    # Fill remaining RPMs with None
                    for remaining_rpm in cell_rpms[cell_rpms.index(rpm) + 1:]:
                        rpm_torque_data[remaining_rpm] = None
                    break
                else:  # Later RPM exceeded threshold
                    print(f"      SAFETY: RPM {rpm} exceeded threshold with max {max_torque:.2f}% - stopping RPM sweep at this Z-level")
                    # Fill remaining RPMs with None
                    for remaining_rpm in cell_rpms[cell_rpms.index(rpm) + 1:]:
                        rpm_torque_data[remaining_rpm] = None
                    break
    
    return rpm_torque_data, first_rpm_exceeded_threshold

def test_cell_dynamic_z_series(
    cnc: CNC_Machine,
    client: ViscometerClient,
    global_cell: int,
    safe_z: float,
    max_z_travel: float,
    cell_rpms: List[float],
    pump: Optional[PumpESP32] = None,
) -> Tuple[Dict[float, Dict[float, Optional[List[Dict]]]], Optional[threading.Thread]]:
    """Test dynamic analysis (multiple RPMs) across Z-gap range for one cell using global cell numbering with rotational drag feedback control"""
    row_number, local_cell = global_cell_to_row_and_local(global_cell)
    print(f"\n{'='*60}")
    print(f"DYNAMIC ANALYSIS - CELL {global_cell} (Row {row_number}, Local Cell {local_cell})")
    print(f"Testing RPMs {cell_rpms} across Z-gap range")
    print(f"Safe Z: {safe_z:.3f}, Max Z Travel: {max_z_travel:.3f}")
    print(f"Feedback Control: {'ENABLED' if FEEDBACK_CONTROL_ENABLED else 'DISABLED'}")
    print(f"{'='*60}")
    
    # Initialize feedback controller with configuration
    feedback_controller = RotationalDragFeedbackController(
        feedback_enabled=FEEDBACK_CONTROL_ENABLED,
        min_data_points=MIN_DATA_POINTS_FOR_TREND,
        r2_drag_min=R2_DRAG_MIN,
        r2_cv_min=R2_CV_MIN,
        r2_slope_min=R2_SLOPE_MIN,
        hit_point_confidence_threshold=HIT_POINT_CONFIDENCE_THRESHOLD,
        weight_2nd_deriv_drag=WEIGHT_2ND_DERIV_DRAG,
        weight_2nd_deriv_cv=WEIGHT_2ND_DERIV_CV,
        weight_2nd_deriv_slope=WEIGHT_2ND_DERIV_SLOPE,
        weight_r2_drag=WEIGHT_R2_DRAG,
        weight_r2_cv=WEIGHT_R2_CV,
        weight_r2_slope=WEIGHT_R2_SLOPE,
        baseline_n_calibration=BASELINE_N_CALIBRATION,
        baseline_z_threshold=BASELINE_Z_THRESHOLD,
    )
    
    cell_z_rpm_data = {}
    current_z = safe_z
    print(f"Starting from Z-safe: {current_z:.3f}")

    # Require persistent confidence trigger before terminating the Z-series.
    hit_confidence_threshold = 0.80
    required_consecutive_hit_steps = 3
    consecutive_high_confidence_steps = 0
    _fill_thread: Optional[threading.Thread] = None
    
    step_count = 0
    try:
        while current_z >= max_z_travel:
            raise_if_stop_requested()
            step_count += 1
            z_rounded = round(current_z, 3)
            web_interface.set_current_z(z_rounded)
            
            print(f"\nCell {global_cell} - Z-Step {step_count}: Z={z_rounded:.3f}")
            
            try:
                # Move to position
                if step_count == 1:
                    move_to_cell_position(cnc, row_number, local_cell, current_z)
                else:
                    # Direct Z movement to next increment (no Z=0 retraction)
                    base_x = None
                    for row in ROWS:
                        if row['row_number'] == row_number:
                            base_x = row['base_x']
                            break
                    
                    x_pos = base_x
                    y_pos = BASE_Y + (local_cell - 1) * Y_OFFSET
                    print(f"  Moving directly to Z={current_z:.3f} (no retraction)")
                    raise_if_stop_requested()
                    cnc.move_to_point(x_pos, y_pos, current_z, speed=Z_FEED_RATE)
                    web_interface.update_position(x_pos, y_pos, current_z)
                    web_interface.update_status(
                        f"Cell {global_cell} | Z-step {step_count} | Z={z_rounded:.3f} mm"
                    )
                    sleep_with_stop(SETTLE_TIME)
                
                # Test all RPMs at this Z-height
                rpm_data, first_rpm_exceeded = test_dynamic_analysis_at_z(client, z_rounded, cell_rpms)
                cell_z_rpm_data[z_rounded] = rpm_data
                
                # Check if first RPM exceeded threshold - if so, break entire cell
                if first_rpm_exceeded:
                    print(f"  CELL TERMINATION: First RPM exceeded threshold at Z={z_rounded:.3f}")
                    print(f"  Stopping Cell {global_cell} Z-series testing")
                    break
                
                # Add measurements to feedback controller for rotational drag analysis
                # Always calculate and store metrics for consistent CSV output
                metrics_data = {}
                
                if FEEDBACK_CONTROL_ENABLED and rpm_data:
                    print(f"  Rotational Drag Analysis:")
                    feedback_controller.add_measurements_at_z(z_rounded, rpm_data)
                    
                    # Extract and store metrics for each RPM at this Z-level
                    for rpm in cell_rpms:
                        if rpm in rpm_data and rpm_data[rpm] is not None:
                            trend_analysis = feedback_controller.analyze_trend_for_rpm(rpm)
                            if trend_analysis['valid']:
                                web_interface.emit_feedback_metrics(
                                    rpm=rpm,
                                    second_derivative_drag=trend_analysis.get('second_derivative_drag'),
                                    second_derivative_cv=trend_analysis.get('second_derivative_cv'),
                                    second_derivative_slope=trend_analysis.get('second_derivative_slope'),
                                    trend_r_squared=trend_analysis.get('trend_r_squared'),
                                    moving_r2_cv=trend_analysis.get('moving_r2_cv'),
                                    moving_r2_slope=trend_analysis.get('moving_r2_slope'),
                                    hit_confidence=trend_analysis.get('hit_confidence'),
                                    hit_detected=trend_analysis.get('hit_detected', False),
                                    drag_sd2_calibrated=trend_analysis.get('drag_sd2_calibrated', False),
                                    cv_sd2_calibrated=trend_analysis.get('cv_sd2_calibrated', False),
                                    slope_sd2_calibrated=trend_analysis.get('slope_sd2_calibrated', False),
                                )
                                metrics_data[rpm] = {
                                    'CV': trend_analysis.get('moving_r2_cv', 0.0) if trend_analysis.get('moving_r2_cv') is not None else 0.0,
                                    'R2': trend_analysis.get('trend_r_squared', 0.0),
                                    'Trend_Slope': trend_analysis.get('trend_slope', 0.0),
                                    'Second_derivative': trend_analysis.get('second_derivative_drag', 0.0) if trend_analysis.get('second_derivative_drag') is not None else 0.0,
                                    'Hit_Point_Confidence': trend_analysis.get('hit_confidence', 0.0),
                                    'Hit_Detected': bool(trend_analysis.get('hit_detected', False)),
                                    'Hit_Reasons': '; '.join(trend_analysis.get('hit_reasons', []))
                                }
                            else:
                                web_interface.emit_feedback_metrics(
                                    rpm=rpm,
                                    second_derivative_drag=None,
                                    second_derivative_cv=None,
                                    second_derivative_slope=None,
                                    trend_r_squared=None,
                                    moving_r2_cv=None,
                                    moving_r2_slope=None,
                                    hit_confidence=0.0,
                                    hit_detected=False,
                                    drag_sd2_calibrated=False,
                                    cv_sd2_calibrated=False,
                                    slope_sd2_calibrated=False,
                                )
                                # Default values for invalid trend analysis
                                metrics_data[rpm] = {
                                    'CV': 0.0,
                                    'R2': 0.0,
                                    'Second_derivative': 0.0,
                                    'Trend_Slope': 0.0,
                                    'Hit_Point_Confidence': 0.0,
                                    'Hit_Detected': False,
                                    'Hit_Reasons': trend_analysis.get('reason', 'invalid_trend')
                                }
                        else:
                            # Default values when no measurements available
                            web_interface.emit_feedback_metrics(
                                rpm=rpm,
                                second_derivative_drag=None,
                                second_derivative_cv=None,
                                second_derivative_slope=None,
                                trend_r_squared=None,
                                moving_r2_cv=None,
                                moving_r2_slope=None,
                                hit_confidence=0.0,
                                hit_detected=False,
                                drag_sd2_calibrated=False,
                                cv_sd2_calibrated=False,
                                slope_sd2_calibrated=False,
                            )
                            metrics_data[rpm] = {
                                'CV': 0.0,
                                'R2': 0.0,
                                'Second_derivative': 0.0,
                                'Trend_Slope': 0.0,
                                'Hit_Point_Confidence': 0.0,
                                'Hit_Detected': False,
                                'Hit_Reasons': 'no_measurements'
                            }
                            
                    feedback_controller.evaluate_hit_point_detection(cell_rpms)

                    # Persistent trigger: require confidence >= 0.80 for 3 consecutive Z-steps.
                    z_level_max_confidence = max(
                        (rpm_metrics.get('Hit_Point_Confidence', 0.0) for rpm_metrics in metrics_data.values()),
                        default=0.0,
                    )

                    if z_level_max_confidence >= hit_confidence_threshold:
                        consecutive_high_confidence_steps += 1
                        print(
                            f"  High-confidence streak: {consecutive_high_confidence_steps}/{required_consecutive_hit_steps} "
                            f"(max confidence={z_level_max_confidence:.2f})"
                        )
                    else:
                        if consecutive_high_confidence_steps > 0:
                            print(
                                f"  High-confidence streak reset at Z={z_rounded:.3f} "
                                f"(max confidence={z_level_max_confidence:.2f})"
                            )
                        consecutive_high_confidence_steps = 0

                    if consecutive_high_confidence_steps >= required_consecutive_hit_steps:
                        print(f"  *** FEEDBACK CONTROLLER: PERSISTENT HIT TRIGGER DETECTED ***")
                        summary = feedback_controller.get_summary()
                        if summary.get('hit_point_z') is not None:
                            print(f"  Estimated hit Z: {summary['hit_point_z']:.3f}")
                        print(f"  Detection confidence: {summary.get('hit_point_confidence', z_level_max_confidence):.2f}")
                        print(
                            f"  Terminating Cell {global_cell} after "
                            f"{required_consecutive_hit_steps} consecutive high-confidence Z-steps"
                        )
                        # Send status update to web interface
                        hit_z_msg = f" at Z={summary['hit_point_z']:.3f}" if summary.get('hit_point_z') is not None else ""
                        web_interface.update_status(f"Cell {global_cell} terminated early - hit-point detected{hit_z_msg}")
                        # Store metrics before breaking
                        cell_z_rpm_data[z_rounded]['_metrics'] = metrics_data
                        break
                else:
                    # Feedback control disabled or no data - store default metrics
                    consecutive_high_confidence_steps = 0
                    for rpm in cell_rpms:
                        metrics_data[rpm] = {
                            'CV': 0.0,
                            'R2': 0.0,
                            'Second_derivative': 0.0,
                            'Trend_Slope': 0.0,
                            'Hit_Point_Confidence': 0.0,
                            'Hit_Detected': False,
                            'Hit_Reasons': 'feedback_disabled'
                        }
                
                # Always store metrics alongside RPM data for consistent CSV structure
                cell_z_rpm_data[z_rounded]['_metrics'] = metrics_data
                    
                print(f"  Completed Z={z_rounded:.3f}: {len([t for t in rpm_data.values() if t is not None])}/{len(cell_rpms)} successful RPM tests")
                
            except Exception as e:
                print(f"  Error testing Cell {global_cell} at Z={z_rounded:.3f}: {e}")
                # Fill with None values for all RPMs at this Z-height and add default metrics
                cell_z_rpm_data[z_rounded] = {rpm: None for rpm in cell_rpms}
                # Add default metrics for consistent CSV structure
                error_metrics_data = {}
                for rpm in cell_rpms:
                    error_metrics_data[rpm] = {
                        'CV': 0.0,
                        'R2': 0.0,
                        'Second_derivative': 0.0,
                        'Trend_Slope': 0.0,
                        'Hit_Point_Confidence': 0.0,
                        'Hit_Detected': False,
                        'Hit_Reasons': 'error'
                    }
                cell_z_rpm_data[z_rounded]['_metrics'] = error_metrics_data
            
            # Move to next Z position
            current_z += Z_STEP_SIZE
    finally:
        if pump is not None:
            web_interface.update_status(f"Cell {global_cell}: last measurement done — pre-filling wash station")
            print("[CONCURRENT] Firing pump fill + motor start as CNC begins rising...")
            _fill_thread = _run_in_thread(_pump_fill_station1, pump)
            _run_in_thread(_motor1_start, pump)
        
    # Move Z back to safe position
    try:
        base_x = None
        for row in ROWS:
            if row['row_number'] == row_number:
                base_x = row['base_x']
                break
        
        x_pos = base_x
        y_pos = BASE_Y + (local_cell - 1) * Y_OFFSET
        cnc.move_to_point(x_pos, y_pos, z=0, speed=Z_FEED_RATE)
        sleep_with_stop(1)
        # Stop viscometer once at safe position
        client.stop()
        print(f"Cell {global_cell} returned to safe Z position")
    except Exception as e:
        print(f"  Warning: Error moving to safe Z: {e}")
        # Ensure viscometer is stopped even if movement fails
        try:
            client.stop()
        except:
            pass
    
    # Print feedback controller summary
    if FEEDBACK_CONTROL_ENABLED:
        summary = feedback_controller.get_summary()
        print(f"\n  Feedback Controller Summary:")
        print(f"    Hit point detected: {summary['hit_point_detected']}")
        if summary['hit_point_detected']:
            print(f"    Hit Z-level: {summary['hit_point_z']:.3f}")
            print(f"    Detection confidence: {summary['hit_point_confidence']:.2f}")
        print(f"    Total Z-levels analyzed: {summary['total_z_levels']}")
        print(f"    RPMs tested: {len(cell_rpms)}")
    
    print(f"Cell {global_cell} dynamic analysis completed: {len(cell_z_rpm_data)} Z-positions tested")
    return cell_z_rpm_data, _fill_thread

def save_partial_data(all_data: Dict[int, Dict[float, Dict[float, Optional[List[Dict]]]]],
                     timestamp: str, mode: str, completed_cells: List[int], experiment_name: str) -> str:
    """Save partial results when experiment is terminated early"""
    if not all_data:
        print("No data collected to save.")
        return ""
    
    print(f"\nSAVING PARTIAL RESULTS...")
    print(f"Completed cells: {completed_cells}")
    
    # Create partial CSV filename with timestamp
    csv_filename = f"dynamic_analysis_{_sanitize_experiment_slug(experiment_name)}_{mode}_PARTIAL_{timestamp}.csv"
    
    with open(csv_filename, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        
        # Write metadata header
        csv_writer.writerow([f"# Dynamic Analysis - Mode: {mode.upper()} (PARTIAL RESULTS)"])
        csv_writer.writerow([f"# Experiment Name: {experiment_name}"])
        csv_writer.writerow([f"# Test RPMs (global fallback): {TEST_RPMS}"])
        if TESTING_MODE == "custom" and CELL_RPM_MAP:
            csv_writer.writerow([f"# Per-cell RPM overrides: {CELL_RPM_MAP}"])
        if CELL_CONTENT_MAP:
            csv_writer.writerow([f"# Per-cell sample labels: {CELL_CONTENT_MAP}"])
        csv_writer.writerow([f"# Timestamp: {timestamp}"])
        csv_writer.writerow([f"# Cell numbering: Row 1 = cells 1-6, Row 2 = cells 7-12, Row 3 = cells 13-18"])
        csv_writer.writerow([f"# Completed cells: {completed_cells}"])
        csv_writer.writerow([f"# Feedback Control: {'ENABLED' if FEEDBACK_CONTROL_ENABLED else 'DISABLED'}"])
        if FEEDBACK_CONTROL_ENABLED:
            csv_writer.writerow([f"# Feedback R2 Thresholds: Drag = {R2_DRAG_MIN}, CV = {R2_CV_MIN}, Slope = {R2_SLOPE_MIN}, Confidence = {HIT_POINT_CONFIDENCE_THRESHOLD}"])
            csv_writer.writerow([f"# Confidence Weights: 2nd-Deriv(Drag/CV/Slope) = {WEIGHT_2ND_DERIV_DRAG}/{WEIGHT_2ND_DERIV_CV}/{WEIGHT_2ND_DERIV_SLOPE}, R2(Drag/CV/Slope) = {WEIGHT_R2_DRAG}/{WEIGHT_R2_CV}/{WEIGHT_R2_SLOPE}"])
        csv_writer.writerow([f"# WARNING: Experiment was terminated early - these are partial results"])
        csv_writer.writerow([])
        
        # Write column headers with Rotational_Drag and metrics columns
        headers = [
            "row", "cell", "Cell_Label", "Z_Height_mm", "RPM", "Elapsed_Time_s", "Torque_%", "Rotational_Drag",
            "CV", "R2", "Trend_Slope", "Second_derivative", "Hit_Point_Confidence", "Hit_Detected", "Hit_Reasons"
        ]
        csv_writer.writerow(headers)
        
        # Write all individual measurements for completed cells with calculated rotational drag
        for global_cell in sorted(all_data.keys()):
            row_number, local_cell = global_cell_to_row_and_local(global_cell)
            cell_data = all_data[global_cell]
            
            # Sort Z heights from highest to lowest
            z_heights = sorted(cell_data.keys(), reverse=True)
            
            for z_height in z_heights:
                if z_height in cell_data:
                    rpm_data = cell_data[z_height]
                    metrics_data = cell_data[z_height].get('_metrics', {})
                    for rpm in sorted(k for k in rpm_data.keys() if k != '_metrics'):
                        measurements = rpm_data.get(rpm)
                        if measurements is not None:
                            # Get metrics for this RPM at this Z-height
                            rpm_metrics = metrics_data.get(rpm, {
                                'CV': 0.0,
                                'R2': 0.0,
                                'Trend_Slope': 0.0,
                                'Second_derivative': 0.0,
                                'Hit_Point_Confidence': 0.0,
                                'Hit_Detected': False,
                                'Hit_Reasons': ''
                            })
                            
                            for measurement in measurements:
                                # Calculate rotational drag for this measurement
                                torque_percent = measurement['torque_percent']
                                rotational_drag = abs(torque_percent) / rpm if rpm > 0 else float('inf')
                                
                                data_row = [
                                    str(row_number),                              # row
                                    str(global_cell),                            # cell (global numbering)
                                    CELL_CONTENT_MAP.get(global_cell, ''),       # Cell_Label
                                    f"{z_height:.3f}",                          # Z_Height_mm
                                    f"{rpm:.1f}",                               # RPM
                                    f"{measurement['elapsed_time']:.2f}",        # Elapsed_Time_s
                                    f"{measurement['torque_percent']:.3f}",      # Torque_%
                                    f"{rotational_drag:.6f}",                   # Rotational_Drag
                                    f"{rpm_metrics['CV']:.6f}",                 # CV
                                    f"{rpm_metrics['R2']:.6f}",                 # R2
                                    f"{rpm_metrics['Trend_Slope']:.6f}",        # Trend_Slope
                                    f"{rpm_metrics['Second_derivative']:.6f}",   # Second_derivative
                                    f"{rpm_metrics['Hit_Point_Confidence']:.6f}", # Hit_Point_Confidence
                                    str(bool(rpm_metrics['Hit_Detected'])),       # Hit_Detected
                                    str(rpm_metrics['Hit_Reasons'])               # Hit_Reasons
                                ]
                                csv_writer.writerow(data_row)
    
    print(f"Partial results saved to: {csv_filename}")
    return csv_filename

def save_dynamic_analysis_data(all_data: Dict[int, Dict[float, Dict[float, Optional[List[Dict]]]]],
                              timestamp: str, mode: str, experiment_name: str) -> str:
    """Save dynamic analysis data - single CSV file for entire run with columns including metrics"""
    
    # Create single CSV filename
    csv_filename = f"dynamic_analysis_{_sanitize_experiment_slug(experiment_name)}_{mode}_{timestamp}.csv"
    
    with open(csv_filename, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        
        # Write metadata header
        csv_writer.writerow([f"# Dynamic Analysis - Mode: {mode.upper()}"])
        csv_writer.writerow([f"# Experiment Name: {experiment_name}"])
        csv_writer.writerow([f"# Test RPMs (global fallback): {TEST_RPMS}"])
        if TESTING_MODE == "custom" and CELL_RPM_MAP:
            csv_writer.writerow([f"# Per-cell RPM overrides: {CELL_RPM_MAP}"])
        if CELL_CONTENT_MAP:
            csv_writer.writerow([f"# Per-cell sample labels: {CELL_CONTENT_MAP}"])
        csv_writer.writerow([f"# Timestamp: {timestamp}"])
        csv_writer.writerow([f"# Cell numbering: Row 1 = cells 1-6, Row 2 = cells 7-12, Row 3 = cells 13-18"])
        csv_writer.writerow([f"# Feedback Control: {'ENABLED' if FEEDBACK_CONTROL_ENABLED else 'DISABLED'}"])
        if FEEDBACK_CONTROL_ENABLED:
            csv_writer.writerow([f"# Feedback R2 Thresholds: Drag = {R2_DRAG_MIN}, CV = {R2_CV_MIN}, Slope = {R2_SLOPE_MIN}, Confidence = {HIT_POINT_CONFIDENCE_THRESHOLD}"])
            csv_writer.writerow([f"# Confidence Weights: 2nd-Deriv(Drag/CV/Slope) = {WEIGHT_2ND_DERIV_DRAG}/{WEIGHT_2ND_DERIV_CV}/{WEIGHT_2ND_DERIV_SLOPE}, R2(Drag/CV/Slope) = {WEIGHT_R2_DRAG}/{WEIGHT_R2_CV}/{WEIGHT_R2_SLOPE}"])
        csv_writer.writerow([])
        
        # Write column headers with Rotational_Drag and metrics columns
        headers = [
            "row", "cell", "Cell_Label", "Z_Height_mm", "RPM", "Elapsed_Time_s", "Torque_%", "Rotational_Drag",
            "CV", "R2", "Trend_Slope", "Second_derivative", "Hit_Point_Confidence", "Hit_Detected", "Hit_Reasons"
        ]
        csv_writer.writerow(headers)
        
        # Write all individual measurements with calculated rotational drag and metrics (LATEST ONLY)
        for global_cell in sorted(all_data.keys()):
            row_number, local_cell = global_cell_to_row_and_local(global_cell)
            cell_data = all_data[global_cell]
            
            # Sort Z heights from highest to lowest
            z_heights = sorted(cell_data.keys(), reverse=True)
            
            for z_height in z_heights:
                if z_height in cell_data:
                    rpm_data = cell_data[z_height]
                    metrics_data = cell_data[z_height].get('_metrics', {})
                    for rpm in sorted(k for k in rpm_data.keys() if k != '_metrics'):
                        measurements = rpm_data.get(rpm)
                        if measurements is not None:
                            # Get metrics for this RPM at this Z-height
                            rpm_metrics = metrics_data.get(rpm, {
                                'CV': 0.0,
                                'R2': 0.0,
                                'Trend_Slope': 0.0,
                                'Second_derivative': 0.0,
                                'Hit_Point_Confidence': 0.0,
                                'Hit_Detected': False,
                                'Hit_Reasons': ''
                            })
                            
                            # Use LATEST measurement only (as requested by user)
                            latest_measurement = measurements[-1]  # Take the last measurement
                            torque_percent = latest_measurement['torque_percent']
                            rotational_drag = abs(torque_percent) / rpm if rpm > 0 else float('inf')
                            
                            # Add measurement to web interface
                            web_interface.add_measurement_point(
                                height=z_height,
                                rotational_drag=rotational_drag,
                                rpm=rpm,
                                cell_id=global_cell
                                ,
                                hit_detected=bool(rpm_metrics.get('Hit_Detected', False))
                            )
                            
                            data_row = [
                                str(row_number),                              # row
                                str(global_cell),                            # cell (global numbering)
                                CELL_CONTENT_MAP.get(global_cell, ''),       # Cell_Label
                                f"{z_height:.3f}",                          # Z_Height_mm
                                f"{rpm:.1f}",                               # RPM
                                f"{latest_measurement['elapsed_time']:.2f}", # Elapsed_Time_s
                                f"{latest_measurement['torque_percent']:.3f}", # Torque_%
                                f"{rotational_drag:.6f}",                   # Rotational_Drag
                                f"{rpm_metrics['CV']:.6f}",                 # CV
                                f"{rpm_metrics['R2']:.6f}",                 # R2
                                f"{rpm_metrics['Trend_Slope']:.6f}",        # Trend_Slope
                                f"{rpm_metrics['Second_derivative']:.6f}",   # Second_derivative
                                f"{rpm_metrics['Hit_Point_Confidence']:.6f}", # Hit_Point_Confidence
                                str(bool(rpm_metrics['Hit_Detected'])),       # Hit_Detected
                                str(rpm_metrics['Hit_Reasons'])               # Hit_Reasons
                            ]
                            csv_writer.writerow(data_row)
    
    print(f"All data saved to: {csv_filename}")
    return csv_filename

def main():
    print("="*80)
    print("MULTI-ROW DYNAMIC ANALYSIS - Z-GAP vs TORQUE at MULTIPLE RPMs")
    print("WITH ROTATIONAL DRAG FEEDBACK CONTROLLER")
    print(f"Testing RPMs: {TEST_RPMS}")
    print(f"Total available: {len(ROWS)} rows x {NUM_CELLS} cells = {len(ROWS) * NUM_CELLS} cells")
    
    # Start web interface in background thread
    print("\nStarting web interface...")
    try:
        web_interface.start_in_thread(debug=False)
        print(f"Web interface started at http://localhost:{web_interface.port}")
        web_interface.update_status("Configure the run in the web interface, then press Start")
        web_interface.set_running_state(False)
    except Exception as e:
        print(f"Warning: Could not start web interface: {e}")
        return
    
    # Main loop to keep the web interface running and accept multiple runs
    while True:
        web_interface.consume_start_command()
        print("Waiting for Start Run command from the web interface...")
        try:
            started = web_interface.wait_for_start_command()
        except KeyboardInterrupt:
            print("Shutdown requested by user")
            break
        if not started:
            web_interface.clear_stop_request()
            web_interface.update_status("Start cancelled before run")
            print("Start cancelled before run")
            continue  # Continue waiting for next start command
        
        web_interface.clear_run_data()
        apply_runtime_settings_from_web()
        web_interface.consume_start_command()
        web_interface.update_status("Initializing hardware...")
        web_interface.set_running_state(True)
        
        # Display feedback control configuration
        print(f"\nFEEDBACK CONTROL CONFIGURATION:")
        print(f"  Enabled: {'YES' if FEEDBACK_CONTROL_ENABLED else 'NO'}")
        if FEEDBACK_CONTROL_ENABLED:
            print(f"  Min data points for trend: {MIN_DATA_POINTS_FOR_TREND}")
            print(f"  R² drag min: {R2_DRAG_MIN}")
            print(f"  R² CV min: {R2_CV_MIN}")
            print(f"  R² slope min: {R2_SLOPE_MIN}")
            print(f"  Hit point confidence threshold: {HIT_POINT_CONFIDENCE_THRESHOLD}")
        
        for row in ROWS:
            start_cell = row_and_local_to_global_cell(row['row_number'], 1)
            end_cell = row_and_local_to_global_cell(row['row_number'], 6)
            print(f"  Row {row['row_number']}: cells {start_cell}-{end_cell}, BASE_X = {row['base_x']}, Safe Z = {row['safe_z']:.3f}, Max Z = {row['max_z_travel']:.3f}")
        print("="*80)
        
        # Get selected cells based on configuration parameters
        try:
            mode, selected_cells = get_selected_cells()
            print(f"\nConfigured mode: {mode.upper()}")
            if mode == "row":
                print(f"Selected rows: {SELECTED_ROWS}")
            elif mode == "custom":
                print(f"Selected cells: {SELECTED_CELLS}")
            print(f"Testing {len(selected_cells)} cells: {selected_cells}")
        except ValueError as e:
            print(f"\nCONFIGURATION ERROR: {e}")
            print("Please check TESTING_MODE, SELECTED_ROWS, and SELECTED_CELLS parameters at the top of the file.")
            continue
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_experiment_name = EXPERIMENT_NAME if EXPERIMENT_NAME else f"{mode}_{timestamp}"
        
        # Initialize hardware with proper error handling
        cnc = None
        client = None
        pump = None
        
        try:
            print("Initializing CNC machine...")
            cnc = CNC_Machine(virtual=False)
            cnc.home()
            sleep_with_stop(1.0)
            print("CNC machine initialized and homed")
            web_interface.set_instrument_status(cnc=True)
        except Exception as e:
            print(f"ERROR initializing CNC machine: {e}")
            continue
    
        # Initialize ESP32 pump controller
        try:
            print("Initializing ESP32 pump controller...")
            pump = PumpESP32(port=ESP32_PORT, baud=ESP32_BAUD, virtual=PUMP_VIRTUAL)
            pump.open()
            
            # Test ESP32 communication
            print("Testing ESP32 communication...")
            if hasattr(pump, 'send_command_with_ack'):
                # Test new acknowledgment system
                test_success = pump.send_command_with_ack(b"ST", timeout=5.0, max_retries=3)
                if test_success:
                    print("✓ ESP32 communication test successful (with acknowledgment)")
                else:
                    print("⚠ ESP32 acknowledgment test failed, falling back to legacy mode")
                    # Test basic communication
                    pump.send_tag(b"ST")
                    sleep_with_stop(1)
                    print("ESP32 communication initialized (legacy mode)")
            else:
                # Legacy test
                pump.send_tag(b"ST")
                sleep_with_stop(1)
                print("ESP32 communication initialized (legacy mode)")
                
            print("ESP32 pump controller initialized successfully")
            web_interface.set_instrument_status(pump=True)
            
        except Exception as e:
            print(f"ERROR initializing ESP32 pump controller: {e}")
            try:
                if cnc:
                    cnc.home()
            except:
                pass
            continue
    
        # Initialize viscometer
        try:
            print("Initializing viscometer...")
            worker_path = pathlib.Path(__file__).resolve().parents[0] / ".." / "python_32" / "worker32.py"
            client = ViscometerClient(PYTHON32, worker_path)
            client.init(port=VISCO_PORT, baud=VISCO_BAUD, timeout=VISCO_TOUT, spindle_k=SPINDLE_K)
            print("Viscometer initialized successfully")
            
            # Test viscometer communication
            test_data = client.read_single(timeout=5.0)
            if test_data and test_data.get("torque_valid"):
                print(f"Viscometer test successful: Torque = {test_data.get('torque_percent', 0):.1f}%")
            else:
                print("WARNING: Viscometer test failed ")
            web_interface.set_instrument_status(viscometer=True)
            
        except Exception as e:
            print(f"ERROR initializing viscometer: {e}")
            try:
                if cnc:
                    cnc.home()
            except:
                pass
            continue
    
        # Data structure: all_data[global_cell] = cell_z_rpm_data
        all_data = {}
        completed_cells = []  # Track completed cells for partial saving
        active_threads: List[threading.Thread] = []
        
        try:
            print(f"\nStarting dynamic analysis...")
            print(f"Experiment name: {run_experiment_name}")
            print(f"Testing {len(selected_cells)} cells with {len(TEST_RPMS)} RPMs per Z-position")
        
            # Go through each selected cell
            for i, global_cell in enumerate(selected_cells):
                raise_if_stop_requested()
                _fill_thread: Optional[threading.Thread] = None
                row_number, local_cell = global_cell_to_row_and_local(global_cell)
                
                # Find row configuration
                row_config = None
                for row in ROWS:
                    if row['row_number'] == row_number:
                        row_config = row
                        break
                
                if row_config is None:
                    print(f"Error: Could not find configuration for row {row_number}")
                    continue
                    
                print(f"\n{'='*60}")
                print(f"TESTING CELL {global_cell} ({i+1}/{len(selected_cells)})")
                print(f"Row {row_number}, Local Cell {local_cell}, BASE_X = {row_config['base_x']}")
                print(f"{'='*60}")
                    
                # Auto-zero the viscometer sensor before testing each cell
                try:
                    print(f"Auto-zeroing viscometer for Cell {global_cell}...")
                    client.zero()
                    print("Viscometer auto-zero completed")
                except Exception as e:
                    print(f"Warning: Failed to auto-zero viscometer: {e}")

                sleep_with_stop(5)
                # Stop viscometer once at safe position
                client.stop()
                
                try:
                    # Resolve per-cell RPMs before the cell test
                    cell_rpms = get_rpms_for_cell(global_cell)
                    print(f"  RPMs for Cell {global_cell}: {cell_rpms}")
                    web_interface.update_status(f"Testing Cell {global_cell} at RPMs {cell_rpms}")
                    result = test_cell_dynamic_z_series(
                        cnc,
                        client,
                        global_cell,
                        row_config['safe_z'],
                        row_config['max_z_travel'],
                        cell_rpms,
                        pump=pump,
                    )
                    try:
                        cell_data, _fill_thread = result
                    except ValueError:
                        cell_data = result
                        _fill_thread = None
                    if _fill_thread is not None:
                        active_threads.append(_fill_thread)
                    all_data[global_cell] = cell_data
                    completed_cells.append(global_cell)
                    print(f"Cell {global_cell} testing completed")
                    
                    # Perform washing sequence after each cell completion
                    if pump:
                        perform_washing_sequence(cnc, pump, global_cell, fill_thread=_fill_thread)
                        web_interface.add_completed_cell(global_cell)
                    else:
                        print(f"Warning: Pump not available, skipping washing for Cell {global_cell}")
                        
                    print(f"Cell {global_cell} fully completed (including wash)")
                    
                except Exception as e:
                    print(f"Error during testing of Cell {global_cell}: {e}")
                    print(f"Saving partial results and terminating...")
                    traceback.print_exc()
                    # Save partial data before exiting
                    if all_data:
                        save_partial_data(all_data, timestamp, mode, completed_cells, run_experiment_name)
                    raise  # Re-raise to trigger cleanup
        
            # All testing completed successfully
            print(f"\nAll dynamic analysis completed successfully!")
            print(f"Tested {len(completed_cells)} cells: {completed_cells}")
            print(f"Saving final results...")
            
            web_interface.update_status("Saving final results...")
            
            csv_filename = save_dynamic_analysis_data(all_data, timestamp, mode, run_experiment_name)
            print(f"\nFINAL RESULTS SAVED TO: {csv_filename}")
            print(f"\nDynamic analysis experiment completed successfully at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            web_interface.update_status("Experiment completed successfully")
            
        except KeyboardInterrupt:
            print(f"\nExperiment interrupted by user")
            web_interface.update_status("Experiment interrupted by user")
            if all_data:
                print("Saving partial results...")
                save_partial_data(all_data, timestamp, mode, completed_cells, run_experiment_name)
        except Exception as e:
            print(f"Critical error during experiment: {e}")
            traceback.print_exc()
            web_interface.update_status(f"Error: {str(e)}")
            if all_data:
                print("Saving partial results...")
                save_partial_data(all_data, timestamp, mode, completed_cells, run_experiment_name)
        finally:
            # Cleanup hardware
            print("Cleaning up hardware...")
            web_interface.update_status("Cleaning up hardware...")
            web_interface.set_running_state(False)
            web_interface.set_instrument_status(cnc=False, viscometer=False, pump=False)
            try:
                if client:
                    client.stop()
                    client.close()
            except:
                pass
            try:
                if pump:
                    # Emergency stop all pumps and motors
                    pump.send_tag(b"0")
                    sleep_with_stop(1)
                    for _t in active_threads:
                        if _t and _t.is_alive():
                            print("Cleanup: waiting for fill/drain thread to finish...")
                            _t.join(timeout=10)
                    pump.close()
            except:
                pass
            try:
                if cnc:
                    cnc.home()
                    web_interface.update_position(0, 0, 0)
            except:
                pass
        print("Hardware cleanup completed")
        web_interface.update_status("Ready - Configure next run and press Start")
        # Continue the loop to wait for next start command

if __name__ == "__main__":
    main()
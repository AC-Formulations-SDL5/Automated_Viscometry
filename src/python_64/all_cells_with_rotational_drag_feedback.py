import time
import pathlib
import csv
import json
import glob
import os
import sys
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
from predicted_viscosity import predict_viscosity
from calibration_store import (
    is_calibrated, load_calibration, save_calibration,
    update_calibration_for_cells, get_safe_z_for_cell, get_calibration_summary, clear_calibration
)

# Ensure progress prints appear in real time even when launched in buffered contexts.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, write_through=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True, write_through=True)

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
# Wash / pump timing (seconds)
# Fill/drain durations (seconds)
STATION1_FILL_DURATION = 22  # reduced by 3s from previous 25s
STATION1_DRAIN_DURATION = 25  # increased by 5s from previous 20s

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
SMART_EARLY_EXIT_ENABLED = True
SMART_CV_THRESHOLD = 0.005
SMART_WINDOW_SIZE = 3
FAIL_SAFE_ENABLED = True
FAIL_SAFE_CONSECUTIVE_STEPS = 5

# Skip Z-levels until post-interval torque ≥ threshold (first sample at elapsed ≥ SAMPLE_INTERVAL;
# regular runs only; see web toggle).
LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED = True
LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT = 25.0
PREDICTED_VISCOSITY_ENABLED = False
CELL_VISCOSITY_RESULTS: Dict[int, Dict[float, dict]] = {}

# ========== CALIBRATION MODE CONFIGURATION ==========
CALIBRATION_MODE = False          # Set to True when a calibration run is requested
RECALIBRATE_INDIVIDUAL_CELLS = False  # Set to True for individual cell recalibration mode
RECALIBRATION_CELLS = {}  # Dict[cell_id, optional_starting_z] for individual recalibration
CALIBRATION_OFFSET = 0.4         # mm above rough hitpoint to use as safe_z

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
    global SMART_EARLY_EXIT_ENABLED, SMART_CV_THRESHOLD, SMART_WINDOW_SIZE, FAIL_SAFE_ENABLED
    global FEEDBACK_CONTROL_ENABLED, MIN_DATA_POINTS_FOR_TREND, HIT_POINT_CONFIDENCE_THRESHOLD, TORQUE_BREAK_THRESHOLD
    global R2_DRAG_MIN, R2_CV_MIN, R2_SLOPE_MIN
    global WEIGHT_2ND_DERIV_DRAG, WEIGHT_2ND_DERIV_CV, WEIGHT_2ND_DERIV_SLOPE
    global WEIGHT_R2_DRAG, WEIGHT_R2_CV, WEIGHT_R2_SLOPE
    global BASELINE_N_CALIBRATION, BASELINE_Z_THRESHOLD
    global CALIBRATION_MODE, RECALIBRATE_INDIVIDUAL_CELLS, RECALIBRATION_CELLS
    global LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED, LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT
    global PREDICTED_VISCOSITY_ENABLED

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
    FAIL_SAFE_ENABLED = bool(settings.get('fail_safe_enabled', FAIL_SAFE_ENABLED))
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
    CALIBRATION_MODE = bool(settings.get('calibration_mode', False))
    RECALIBRATE_INDIVIDUAL_CELLS = bool(settings.get('recalibrate_individual_cells', False))
    LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED = bool(
        settings.get('low_torque_liquid_contact_skip_enabled', LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED)
    )
    LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT = float(
        settings.get('low_torque_liquid_contact_threshold_pct', LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT)
    )
    PREDICTED_VISCOSITY_ENABLED = bool(
        settings.get('predicted_viscosity_enabled', PREDICTED_VISCOSITY_ENABLED)
    )
    # Parse recalibration cells: expect dict {cell_id: optional_starting_z}
    # JSON object keys arrive as strings; normalize to int keys for runtime lookup.
    raw_recalibration_cells = settings.get('recalibration_cells', {})
    normalized_recalibration_cells: Dict[int, Optional[float]] = {}
    if isinstance(raw_recalibration_cells, dict):
        for cell_id, maybe_z in raw_recalibration_cells.items():
            try:
                normalized_cell_id = int(cell_id)
            except (TypeError, ValueError):
                continue
            if maybe_z in (None, ''):
                normalized_recalibration_cells[normalized_cell_id] = None
            else:
                try:
                    normalized_recalibration_cells[normalized_cell_id] = float(maybe_z)
                except (TypeError, ValueError):
                    normalized_recalibration_cells[normalized_cell_id] = None
    RECALIBRATION_CELLS = normalized_recalibration_cells


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


def _liquid_skip_csv_row(row_number: int, global_cell: int, z_height: float, rpm: float, torque_label: str) -> List[str]:
    """One CSV row for a Z-level skipped due to low torque (no liquid contact)."""
    sk = "SKIPPED"
    return [
        str(row_number),
        str(global_cell),
        CELL_CONTENT_MAP.get(global_cell, ""),
        f"{z_height:.3f}",
        f"{rpm:.1f}",
        sk,
        torque_label,
        sk,
    ] + [sk] * 10 + [sk] * 6 + [sk, sk, sk, sk]


def _liquid_skip_torque_label(th: float) -> str:
    if abs(th - round(th)) < 1e-9:
        return f"<{int(round(th))}%"
    return f"<{th:.1f}%"


def _run_in_thread(fn, *args, **kwargs) -> threading.Thread:
    """Launch fn(*args, **kwargs) in a daemon thread and return the thread object."""
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t


_PUMP_IO_LOCK = threading.Lock()


def _safe_pump_send_tag(pump: PumpESP32, command: bytes):
    """Serialize raw pump serial writes to avoid concurrent access collisions."""
    with _PUMP_IO_LOCK:
        pump.send_tag(command)


def _reliable_pump_command(pump: PumpESP32, command: bytes, description: str) -> bool:
    """Send pump command with acknowledgment and status verification (module-level)."""
    raise_if_stop_requested()
    print(f"  Executing: {description}")
    with _PUMP_IO_LOCK:
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
    if RECALIBRATE_INDIVIDUAL_CELLS:
        # Individual cell recalibration mode: only recalibrate specified cells
        selected = list(RECALIBRATION_CELLS.keys()) if RECALIBRATION_CELLS else []
        selected.sort()
        return "recalibration", selected
    if CALIBRATION_MODE:
        # Calibration always runs all 18 cells
        return "calibration", list(range(1, 19))
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
            wait_timeout = STATION1_FILL_DURATION + 10
            print(f"Waiting for concurrent Station 1 fill to complete (up to {wait_timeout} s)...")
            fill_thread.join(timeout=wait_timeout)
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
            wait_timeout = STATION1_DRAIN_DURATION + 10
            print(f"Step W9: Waiting for Station 1 drain to complete (up to {wait_timeout} s)...")
            drain_thread.join(timeout=wait_timeout)
            if drain_thread.is_alive():
                print("WARNING: Drain thread did not finish within timeout — continuing.")

        print(f"Washing Sequence completed for Cell {global_cell}")

        if hasattr(pump, 'get_status'):
            final_status = pump.get_status()
            if final_status and any(final_status.values()):
                print(f"WARNING: Components still active after wash: {final_status}")
                _safe_pump_send_tag(pump, b"0")
                sleep_with_stop(1)

    except Exception as e:
        print(f"Error during washing sequence for Cell {global_cell}: {e}")
        try:
            print("Executing emergency stop...")
            _safe_pump_send_tag(pump, b"0")
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
    """Fill wash station 1 (runs concurrently with CNC travel).

    Uses STATION1_FILL_DURATION for the fill time.
    """
    try:
        raise_if_stop_requested()
        print("[CONCURRENT] Starting Pump P1 to fill Station 1...")
        _reliable_pump_command(pump, b"P1", "Start Pump 1 (concurrent fill)")
        sleep_with_stop(STATION1_FILL_DURATION)
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
    """Drain wash station 1 via reverse rinse R1 (runs concurrently with CNC travel to Station 2).

    Uses STATION1_DRAIN_DURATION for the drain time.
    """
    try:
        raise_if_stop_requested()
        print("[CONCURRENT] Starting reverse rinse R1 to drain Station 1...")
        _reliable_pump_command(pump, b"R1", "Start Reverse Rinse 1 (concurrent drain)")
        sleep_with_stop(STATION1_DRAIN_DURATION)
        _reliable_pump_command(pump, b"SR1", "Stop Reverse Rinse 1 (concurrent drain complete)")
        print("[CONCURRENT] Station 1 drain complete.")
    except KeyboardInterrupt:
        print("[CONCURRENT] Station 1 drain cancelled due to stop request.")

def measure_torque_at_rpm(
    client: ViscometerClient,
    rpm: float,
    z_height: float,
    hunting_first_contact_min_pct: Optional[float] = None,
) -> Optional[List[Dict]]:
    """Measure torque at a specific RPM, returning all individual measurements with timestamps.

    Recorded samples (and live web points) occur only on a fixed grid every ``SAMPLE_INTERVAL``
    seconds from the start of the measurement window (after dwell)—no off-grid immediate read.

    If ``hunting_first_contact_min_pct`` is set (liquid-contact hunt at first Z after spindle starts):
    on the **first** recorded sample, if torque is **strictly less than** that threshold, sampling
    stops immediately. Otherwise the full ``MEASUREMENT_DURATION`` collection proceeds.
    Smart early exit is disabled until this gate is resolved.
    """
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
        # Recorded samples and live plots: fixed grid at SAMPLE_INTERVAL (first slot = 1 * interval).
        sample_index = 1
        next_sample_time = measurement_start_time + sample_index * SAMPLE_INTERVAL
        hunt_contact_confirmed = False

        while time.time() - start_time < MEASUREMENT_DURATION:
            raise_if_stop_requested()
            current_time = time.time()
            
            if current_time >= next_sample_time:
                try:
                    data = client.read_single(timeout=TORQUE_READ_TIMEOUT)
                    if data and data.get("torque_valid") and data.get("torque_percent") is not None:
                        tp = float(data["torque_percent"])
                        elapsed_since_start = current_time - measurement_start_time
                        liquid_hunt_stop = False
                        if (
                            hunting_first_contact_min_pct is not None
                            and not hunt_contact_confirmed
                        ):
                            if tp < hunting_first_contact_min_pct:
                                liquid_hunt_stop = True
                            else:
                                hunt_contact_confirmed = True
                        measurement = {
                            "timestamp": current_time,
                            "elapsed_time": elapsed_since_start,
                            "torque_percent": tp,
                            "rpm": rpm
                        }
                        measurements.append(measurement)
                        recent_torques.append(tp)
                        recent_torques = recent_torques[-SMART_WINDOW_SIZE:]
                        web_interface.update_live_torque(
                            torque_percent=tp,
                            rpm=rpm,
                            elapsed=elapsed_since_start,
                        )
                        web_interface.add_measurement_point(
                            height=z_height,
                            rotational_drag=abs(tp) / rpm if rpm > 0 else 0.0,
                            rpm=rpm,
                            cell_id=web_interface.current_cell,
                        )
                        if liquid_hunt_stop:
                            print(
                                f"      [LIQUID CONTACT] Sample at {elapsed_since_start:.2f}s "
                                f"{tp:.2f}% < {hunting_first_contact_min_pct:.2f}% — "
                                "stopping this Z-level sample early"
                            )
                            break
                        hunting_unresolved = (
                            hunting_first_contact_min_pct is not None and not hunt_contact_confirmed
                        )
                        if (
                            SMART_EARLY_EXIT_ENABLED
                            and not hunting_unresolved
                            and len(recent_torques) == SMART_WINDOW_SIZE
                        ):
                            recent_mean = statistics.mean(recent_torques)
                            if recent_mean > 0:
                                cv = statistics.pstdev(recent_torques) / recent_mean
                                if cv < SMART_CV_THRESHOLD:
                                    print(f"      [SMART EXIT] Torque stabilized at CV < {SMART_CV_THRESHOLD}")
                                    break
                    sample_index += 1
                    next_sample_time = measurement_start_time + sample_index * SAMPLE_INTERVAL
                except Exception as e:
                    print(f"      Measurement error at RPM {rpm}: {e}")
                    sample_index += 1
                    next_sample_time = measurement_start_time + sample_index * SAMPLE_INTERVAL
            
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
    cell_rpms: List[float],
    *,
    liquid_skip_enabled: bool = False,
    liquid_threshold_pct: float = 20.0,
    liquid_contact_established_box: Optional[List[bool]] = None,
) -> Tuple[Dict[float, Optional[List[Dict]]], bool, bool]:
    """Test all RPMs at a specific Z-height.

    Returns ``(rpm_torque_data, first_rpm_exceeded_threshold, z_skipped_due_to_liquid)``.
    When ``z_skipped_due_to_liquid`` is True, ``rpm_torque_data`` maps every RPM to ``None`` and no
    further RPMs were measured at this Z-level.
    """
    print(f"    Testing {len(cell_rpms)} RPMs at Z={z_height:.3f}")
    rpm_torque_data: Dict[float, Optional[List[Dict]]] = {}
    first_rpm_exceeded_threshold = False
    start_i = 0
    box = liquid_contact_established_box

    if liquid_skip_enabled and box is not None and (not box[0]) and len(cell_rpms) > 0:
        first_rpm = cell_rpms[0]
        measurements = measure_torque_at_rpm(
            client,
            first_rpm,
            z_height,
            hunting_first_contact_min_pct=liquid_threshold_pct,
        )
        if measurements is None or len(measurements) == 0:
            print(f"      [LIQUID CONTACT] No valid torque samples at Z={z_height:.3f} — skipping Z-level")
            for r in cell_rpms:
                rpm_torque_data[r] = None
            return rpm_torque_data, False, True
        post_interval = next(
            (m for m in measurements if float(m.get("elapsed_time", 0)) >= SAMPLE_INTERVAL),
            None,
        )
        if post_interval is not None:
            t_gate = float(post_interval["torque_percent"])
            if t_gate < liquid_threshold_pct:
                print(
                    f"      [LIQUID CONTACT] Post-interval torque {t_gate:.2f}% (first sample at "
                    f"elapsed ≥ {SAMPLE_INTERVAL:.1f}s) < {liquid_threshold_pct:.2f}% — "
                    "skipping Z-level (no hit-point inputs, no further RPMs)"
                )
                for r in cell_rpms:
                    rpm_torque_data[r] = None
                return rpm_torque_data, False, True
        else:
            print(
                f"      [LIQUID CONTACT] No sample with elapsed ≥ {SAMPLE_INTERVAL:.1f}s — "
                "cannot evaluate air gap; treating as liquid contact at this Z"
            )
        box[0] = True
        rpm_torque_data[first_rpm] = measurements
        start_i = 1
        max_torque = max(abs(m["torque_percent"]) for m in measurements)
        if max_torque >= TORQUE_BREAK_THRESHOLD:
            print(
                f"      CRITICAL: First RPM {first_rpm} exceeded safety threshold with max {max_torque:.2f}% "
                f"- will break entire cell"
            )
            first_rpm_exceeded_threshold = True
            for remaining_rpm in cell_rpms[1:]:
                rpm_torque_data[remaining_rpm] = None
            return rpm_torque_data, first_rpm_exceeded_threshold, False

    for i in range(start_i, len(cell_rpms)):
        rpm = cell_rpms[i]
        measurements = measure_torque_at_rpm(client, rpm, z_height)
        rpm_torque_data[rpm] = measurements
        is_first_rpm_in_profile = rpm == cell_rpms[0]

        # Check if measurements are invalid (high resistance condition) or exceed threshold
        if measurements is None:
            if is_first_rpm_in_profile:  # First RPM failed - critical condition
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
                if is_first_rpm_in_profile:  # First RPM exceeded threshold
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

    return rpm_torque_data, first_rpm_exceeded_threshold, False

def test_cell_dynamic_z_series(
    cnc: CNC_Machine,
    client: ViscometerClient,
    global_cell: int,
    safe_z: float,
    max_z_travel: float,
    cell_rpms: List[float],
    pump: Optional[PumpESP32] = None,
    custom_starting_z: Optional[float] = None,
) -> Tuple[Dict[float, Dict[float, Optional[List[Dict]]]], Optional[threading.Thread]]:
    """Test dynamic analysis (multiple RPMs) across Z-gap range for one cell using global cell numbering with rotational drag feedback control
    
    Args:
        custom_starting_z: Optional custom starting Z-height for recalibration mode. If provided, overrides safe_z.
    """
    row_number, local_cell = global_cell_to_row_and_local(global_cell)
    print(f"\n{'='*60}")
    print(f"DYNAMIC ANALYSIS - CELL {global_cell} (Row {row_number}, Local Cell {local_cell})")
    print(f"Testing RPMs {cell_rpms} across Z-gap range")
    print(f"Safe Z: {safe_z:.3f}, Max Z Travel: {max_z_travel:.3f}")
    if custom_starting_z is not None:
        print(f"Custom Starting Z: {custom_starting_z:.3f}")
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
    use_liquid_z_skip = (
        LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED
        and (not CALIBRATION_MODE)
        and (not RECALIBRATE_INDIVIDUAL_CELLS)
    )
    liquid_contact_established_box: Optional[List[bool]] = [False] if use_liquid_z_skip else None
    if use_liquid_z_skip:
        print(
            f"  Liquid-contact hunt enabled (regular run): skip Z-rows when first torque sample at "
            f"elapsed ≥ {SAMPLE_INTERVAL:.1f}s is < "
            f"{LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT:.2f}% (otherwise continue); skipped rows use torque "
            f"{_liquid_skip_torque_label(LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT)} and SKIPPED metrics"
        )
    
    # Determine starting Z: custom_starting_z > RECALIBRATE_INDIVIDUAL_CELLS > CALIBRATION_MODE > normal
    if custom_starting_z is not None:
        current_z = custom_starting_z
    elif not (CALIBRATION_MODE or RECALIBRATE_INDIVIDUAL_CELLS):
        safe_z = get_safe_z_for_cell(global_cell, safe_z, offset=CALIBRATION_OFFSET)
        current_z = safe_z
    else:
        # In calibration or recalibration mode, use the provided safe_z
        current_z = safe_z
    print(f"Starting from Z-safe: {current_z:.3f}")

    # Require persistent confidence trigger before terminating the Z-series.
    hit_confidence_threshold = 0.80
    required_consecutive_hit_steps = 3
    consecutive_high_confidence_steps = 0
    consecutive_fail_safe_steps = 0
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
                rpm_data, first_rpm_exceeded, z_liquid_skipped = test_dynamic_analysis_at_z(
                    client,
                    z_rounded,
                    cell_rpms,
                    liquid_skip_enabled=use_liquid_z_skip,
                    liquid_threshold_pct=LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT,
                    liquid_contact_established_box=liquid_contact_established_box,
                )
                cell_z_rpm_data[z_rounded] = rpm_data

                if z_liquid_skipped:
                    tlab = _liquid_skip_torque_label(LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT)
                    rpm_data["_liquid_skipped_z"] = True
                    rpm_data["_liquid_skip_torque_label"] = tlab
                    rpm_data["_metrics"] = {}
                    print(
                        f"  Z={z_rounded:.3f}: no liquid contact (post-interval sample below "
                        f"{LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT:.2f}%) — hit-point logic skipped for this Z"
                    )
                    current_z += Z_STEP_SIZE
                    continue

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
                                hit_reasons = trend_analysis.get('hit_reasons', [])
                                hit_reason_set = set(hit_reasons)
                                metrics_data[rpm] = {
                                    'CV': trend_analysis.get('moving_r2_cv', 0.0) if trend_analysis.get('moving_r2_cv') is not None else 0.0,
                                    'R2': trend_analysis.get('trend_r_squared', 0.0),
                                    'Trend_Slope': trend_analysis.get('trend_slope', 0.0),
                                    'Second_derivative': trend_analysis.get('second_derivative_drag', 0.0) if trend_analysis.get('second_derivative_drag') is not None else 0.0,
                                    'Second_derivative_drag': trend_analysis.get('second_derivative_drag', 0.0) if trend_analysis.get('second_derivative_drag') is not None else 0.0,
                                    'Second_derivative_cv': trend_analysis.get('second_derivative_cv', 0.0) if trend_analysis.get('second_derivative_cv') is not None else 0.0,
                                    'Second_derivative_slope': trend_analysis.get('second_derivative_slope', 0.0) if trend_analysis.get('second_derivative_slope') is not None else 0.0,
                                    'R2_drag': trend_analysis.get('trend_r_squared', 0.0),
                                    'R2_cv': trend_analysis.get('moving_r2_cv', 0.0) if trend_analysis.get('moving_r2_cv') is not None else 0.0,
                                    'R2_slope': trend_analysis.get('moving_r2_slope', 0.0) if trend_analysis.get('moving_r2_slope') is not None else 0.0,
                                    'Hit_2nd_Deriv_Drag': any(reason.startswith('hit_2nd_deriv_drag') for reason in hit_reason_set),
                                    'Hit_2nd_Deriv_CV': any(reason.startswith('hit_2nd_deriv_cv') for reason in hit_reason_set),
                                    'Hit_2nd_Deriv_Slope': any(reason.startswith('hit_2nd_deriv_slope') for reason in hit_reason_set),
                                    'Hit_R2_Drag': any(reason.startswith('hit_r2_drag') for reason in hit_reason_set),
                                    'Hit_R2_CV': any(reason.startswith('hit_r2_cv') for reason in hit_reason_set),
                                    'Hit_R2_Slope': any(reason.startswith('hit_r2_slope') for reason in hit_reason_set),
                                    'Hit_Point_Confidence': trend_analysis.get('hit_confidence', 0.0),
                                    'Hit_Detected': bool(trend_analysis.get('hit_detected', False)),
                                    'Hit_Reasons': '; '.join(hit_reasons)
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
                                    'Second_derivative_drag': 0.0,
                                    'Second_derivative_cv': 0.0,
                                    'Second_derivative_slope': 0.0,
                                    'R2_drag': 0.0,
                                    'R2_cv': 0.0,
                                    'R2_slope': 0.0,
                                    'Hit_2nd_Deriv_Drag': False,
                                    'Hit_2nd_Deriv_CV': False,
                                    'Hit_2nd_Deriv_Slope': False,
                                    'Hit_R2_Drag': False,
                                    'Hit_R2_CV': False,
                                    'Hit_R2_Slope': False,
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
                                'Second_derivative_drag': 0.0,
                                'Second_derivative_cv': 0.0,
                                'Second_derivative_slope': 0.0,
                                'R2_drag': 0.0,
                                'R2_cv': 0.0,
                                'R2_slope': 0.0,
                                'Hit_2nd_Deriv_Drag': False,
                                'Hit_2nd_Deriv_CV': False,
                                'Hit_2nd_Deriv_Slope': False,
                                'Hit_R2_Drag': False,
                                'Hit_R2_CV': False,
                                'Hit_R2_Slope': False,
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

                    # Fail-safe: sub-threshold confidence streak (requires feedback metrics above).
                    if FAIL_SAFE_ENABLED:
                        fail_safe_threshold = HIT_POINT_CONFIDENCE_THRESHOLD * 0.75
                        if z_level_max_confidence >= fail_safe_threshold:
                            consecutive_fail_safe_steps += 1
                            print(
                                f"  Fail-safe streak: {consecutive_fail_safe_steps}/{FAIL_SAFE_CONSECUTIVE_STEPS} "
                                f"(max confidence={z_level_max_confidence:.2f}, threshold={fail_safe_threshold:.2f})"
                            )
                        else:
                            if consecutive_fail_safe_steps > 0:
                                print(
                                    f"  Fail-safe streak reset at Z={z_rounded:.3f} "
                                    f"(max confidence={z_level_max_confidence:.2f})"
                                )
                            consecutive_fail_safe_steps = 0

                        if consecutive_fail_safe_steps >= FAIL_SAFE_CONSECUTIVE_STEPS:
                            for rpm in metrics_data:
                                metrics_data[rpm]['Hit_Detected'] = False
                                metrics_data[rpm]['Hit_Reasons'] = 'fail safe, experiment terminated'
                            cell_z_rpm_data[z_rounded]['_metrics'] = metrics_data
                            web_interface.update_status(
                                f"Cell {global_cell}: fail-safe activated after "
                                f"{FAIL_SAFE_CONSECUTIVE_STEPS} consecutive sub-threshold confidence readings"
                            )
                            print(
                                f"  *** FAIL-SAFE: terminating Cell {global_cell} after "
                                f"{FAIL_SAFE_CONSECUTIVE_STEPS} consecutive sub-threshold Z-steps ***"
                            )
                            break
                else:
                    # Feedback control disabled or no data - store default metrics.
                    # Fail-safe never fires here (Hit_Point_Confidence is 0.0).
                    consecutive_high_confidence_steps = 0
                    consecutive_fail_safe_steps = 0
                    for rpm in cell_rpms:
                        metrics_data[rpm] = {
                            'CV': 0.0,
                            'R2': 0.0,
                            'Second_derivative': 0.0,
                            'Trend_Slope': 0.0,
                            'Second_derivative_drag': 0.0,
                            'Second_derivative_cv': 0.0,
                            'Second_derivative_slope': 0.0,
                            'R2_drag': 0.0,
                            'R2_cv': 0.0,
                            'R2_slope': 0.0,
                            'Hit_2nd_Deriv_Drag': False,
                            'Hit_2nd_Deriv_CV': False,
                            'Hit_2nd_Deriv_Slope': False,
                            'Hit_R2_Drag': False,
                            'Hit_R2_CV': False,
                            'Hit_R2_Slope': False,
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
                        'Second_derivative_drag': 0.0,
                        'Second_derivative_cv': 0.0,
                        'Second_derivative_slope': 0.0,
                        'R2_drag': 0.0,
                        'R2_cv': 0.0,
                        'R2_slope': 0.0,
                        'Hit_2nd_Deriv_Drag': False,
                        'Hit_2nd_Deriv_CV': False,
                        'Hit_2nd_Deriv_Slope': False,
                        'Hit_R2_Drag': False,
                        'Hit_R2_CV': False,
                        'Hit_R2_Slope': False,
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
    if FEEDBACK_CONTROL_ENABLED:
        feedback_summary = feedback_controller.get_summary()
    else:
        feedback_summary = {
            'hit_point_detected': False,
            'hit_point_z': None,
            'hit_point_confidence': None,
            'total_z_levels': len(cell_z_rpm_data),
            'feedback_enabled': False,
        }
    return cell_z_rpm_data, _fill_thread, feedback_summary


def run_predicted_viscosity_for_cell(
    cell_id: int,
    rpms: List[float],
    feedback_summary: Dict,
) -> None:
    """Fit hyperbolic viscosity per RPM after a cell completes; emit to dashboard."""
    global CELL_VISCOSITY_RESULTS

    hit_z = feedback_summary.get('hit_point_z')
    if hit_z is not None:
        try:
            hit_z = float(hit_z)
        except (TypeError, ValueError):
            hit_z = None

    if cell_id not in CELL_VISCOSITY_RESULTS:
        CELL_VISCOSITY_RESULTS[cell_id] = {}

    for rpm in rpms:
        try:
            result = predict_viscosity(
                cell_id,
                float(rpm),
                web_interface.measurement_data,
                torque_floor_pct=LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT,
                hit_point_z=hit_z,
            )
            CELL_VISCOSITY_RESULTS[cell_id][float(rpm)] = result
            web_interface.emit_predicted_viscosity(cell_id, float(rpm), result)
            if result.get('success'):
                print(
                    f"  Predicted viscosity Cell {cell_id} @ {rpm} RPM: "
                    f"{result.get('viscosity_kcp'):.3f} kCp (n={result.get('n_points_used')})"
                )
            else:
                print(
                    f"  Predicted viscosity Cell {cell_id} @ {rpm} RPM: failed — "
                    f"{result.get('error')}"
                )
        except Exception as e:
            print(f"  Warning: predicted viscosity failed for Cell {cell_id} RPM {rpm}: {e}")


def extract_rough_hitpoint(cell_z_rpm_data: dict) -> Optional[float]:
    """
    Extract the rough hitpoint Z from a completed cell's measurement data.

    The rough hitpoint is defined as the LAST z-level (in descent order)
    where Hit_Detected == False, provided that it is immediately followed by
    at least 3 consecutive z-levels where Hit_Detected == True.

    Returns the Z-height (float) or None if no reliable hitpoint was found.
    """
    # Sort from highest (start of descent) to lowest (end of descent)
    # safe_z is least negative, max_z_travel is most negative
    # Sorted descending by value: -65.5, -65.52, -65.54, ... -66.5
    z_levels = sorted(
        [k for k in cell_z_rpm_data.keys() if k != '_metrics'],
        reverse=True
    )

    # Build a list of (z, any_hit_detected) tuples in descent order
    hit_sequence = []
    for z in z_levels:
        rpm_data = cell_z_rpm_data[z]
        metrics = rpm_data.get('_metrics', {})
        any_hit = any(
            bool(metrics.get(rpm, {}).get('Hit_Detected', False))
            for rpm in metrics
        )
        hit_sequence.append((z, any_hit))

    # Find last z where hit==False AND at least 3 subsequent z-levels are all True
    rough_hitpoint = None
    n = len(hit_sequence)
    for i in range(n - 3):
        z_val, is_hit = hit_sequence[i]
        if not is_hit:
            # Check next 3 are all True
            next_three_true = all(
                hit_sequence[j][1] for j in range(i + 1, min(i + 4, n))
            )
            if next_three_true:
                rough_hitpoint = z_val  # Keep updating — we want the LAST such point

    return rough_hitpoint

def _append_predicted_viscosity_csv_metadata(csv_writer) -> None:
    """Write predicted viscosity summary rows into CSV metadata comments."""
    if not PREDICTED_VISCOSITY_ENABLED or not CELL_VISCOSITY_RESULTS:
        return
    csv_writer.writerow(["# Predicted Viscosity Results"])
    csv_writer.writerow([
        "# Cell,Cell_Label,RPM,Viscosity_kCp,a,b,n_points_used,fit_success"
    ])
    for global_cell in sorted(CELL_VISCOSITY_RESULTS.keys()):
        rpm_map = CELL_VISCOSITY_RESULTS[global_cell]
        label = CELL_CONTENT_MAP.get(global_cell, "")
        for rpm in sorted(rpm_map.keys()):
            result = rpm_map[rpm]
            if not isinstance(result, dict):
                continue
            visc = result.get("viscosity_kcp")
            a_val = result.get("a")
            b_val = result.get("b")
            csv_writer.writerow([
                f"# {global_cell},{label},{rpm},"
                f"{'' if visc is None else visc},"
                f"{'' if a_val is None else a_val},"
                f"{'' if b_val is None else b_val},"
                f"{result.get('n_points_used', 0)},"
                f"{bool(result.get('success'))}",
            ])
    csv_writer.writerow([])


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
        if LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED:
            csv_writer.writerow([
                f"# Low-torque liquid-contact hunt: skip Z-rows when first sample at elapsed >= "
                f"{SAMPLE_INTERVAL:.1f}s is < {LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT:.2f}% (regular runs only); "
                f"skipped rows use {_liquid_skip_torque_label(LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT)} and SKIPPED metrics"
            ])
        csv_writer.writerow([f"# WARNING: Experiment was terminated early - these are partial results"])
        _append_predicted_viscosity_csv_metadata(csv_writer)
        
        # Write column headers with Rotational_Drag and metrics columns
        headers = [
            "row", "cell", "Cell_Label", "Z_Height_mm", "RPM", "Elapsed_Time_s", "Torque_%", "Rotational_Drag",
            "CV", "R_2", "Trend_Slope", "Second_derivative",
            "Second_derivative_drag", "Second_derivative_cv", "Second_derivative_slope",
            "R_2_drag", "R_2_cv", "R_2_slope",
            "Hit_2nd_Deriv_Drag", "Hit_2nd_Deriv_CV", "Hit_2nd_Deriv_Slope",
            "Hit_R_2_Drag", "Hit_R_2_CV", "Hit_R_2_Slope",
            "Samples_Collected_At_Z",
            "Hit_Point_Confidence", "Hit_Detected", "Hit_Reasons"
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
                    _md_keys = {"_metrics", "_liquid_skipped_z", "_liquid_skip_torque_label"}
                    if rpm_data.get("_liquid_skipped_z"):
                        tlab = rpm_data.get(
                            "_liquid_skip_torque_label",
                            _liquid_skip_torque_label(LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT),
                        )
                        for rpm in sorted(k for k in rpm_data.keys() if k not in _md_keys):
                            csv_writer.writerow(_liquid_skip_csv_row(row_number, global_cell, z_height, rpm, tlab))
                        continue
                    metrics_data = cell_data[z_height].get("_metrics", {})
                    for rpm in sorted(k for k in rpm_data.keys() if k not in _md_keys):
                        measurements = rpm_data.get(rpm)
                        if measurements is not None:
                            # Get metrics for this RPM at this Z-height
                            rpm_metrics = metrics_data.get(rpm, {
                                'CV': 0.0,
                                'R2': 0.0,
                                'Trend_Slope': 0.0,
                                'Second_derivative': 0.0,
                                'Second_derivative_drag': 0.0,
                                'Second_derivative_cv': 0.0,
                                'Second_derivative_slope': 0.0,
                                'R2_drag': 0.0,
                                'R2_cv': 0.0,
                                'R2_slope': 0.0,
                                'Hit_2nd_Deriv_Drag': False,
                                'Hit_2nd_Deriv_CV': False,
                                'Hit_2nd_Deriv_Slope': False,
                                'Hit_R2_Drag': False,
                                'Hit_R2_CV': False,
                                'Hit_R2_Slope': False,
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
                                    f"{rpm_metrics.get('Second_derivative_drag', 0.0):.6f}",
                                    f"{rpm_metrics.get('Second_derivative_cv', 0.0):.6f}",
                                    f"{rpm_metrics.get('Second_derivative_slope', 0.0):.6f}",
                                    f"{rpm_metrics.get('R2_drag', 0.0):.6f}",
                                    f"{rpm_metrics.get('R2_cv', 0.0):.6f}",
                                    f"{rpm_metrics.get('R2_slope', 0.0):.6f}",
                                    str(bool(rpm_metrics.get('Hit_2nd_Deriv_Drag', False))),
                                    str(bool(rpm_metrics.get('Hit_2nd_Deriv_CV', False))),
                                    str(bool(rpm_metrics.get('Hit_2nd_Deriv_Slope', False))),
                                    str(bool(rpm_metrics.get('Hit_R2_Drag', False))),
                                    str(bool(rpm_metrics.get('Hit_R2_CV', False))),
                                    str(bool(rpm_metrics.get('Hit_R2_Slope', False))),
                                    str(len(measurements)),
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
        if LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED:
            csv_writer.writerow([
                f"# Low-torque liquid-contact hunt: skip Z-rows when first sample at elapsed >= "
                f"{SAMPLE_INTERVAL:.1f}s is < {LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT:.2f}% (regular runs only); "
                f"skipped rows use {_liquid_skip_torque_label(LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT)} and SKIPPED metrics"
            ])
        _append_predicted_viscosity_csv_metadata(csv_writer)
        
        # Write column headers with Rotational_Drag and metrics columns
        headers = [
            "row", "cell", "Cell_Label", "Z_Height_mm", "RPM", "Elapsed_Time_s", "Torque_%", "Rotational_Drag",
            "CV", "R_2", "Trend_Slope", "Second_derivative",
            "Second_derivative_drag", "Second_derivative_cv", "Second_derivative_slope",
            "R_2_drag", "R_2_cv", "R_2_slope",
            "Hit_2nd_Deriv_Drag", "Hit_2nd_Deriv_CV", "Hit_2nd_Deriv_Slope",
            "Hit_R_2_Drag", "Hit_R_2_CV", "Hit_R_2_Slope",
            "Samples_Collected_At_Z",
            "Hit_Point_Confidence", "Hit_Detected", "Hit_Reasons"
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
                    _md_keys = {"_metrics", "_liquid_skipped_z", "_liquid_skip_torque_label"}
                    if rpm_data.get("_liquid_skipped_z"):
                        tlab = rpm_data.get(
                            "_liquid_skip_torque_label",
                            _liquid_skip_torque_label(LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT),
                        )
                        for rpm in sorted(k for k in rpm_data.keys() if k not in _md_keys):
                            csv_writer.writerow(_liquid_skip_csv_row(row_number, global_cell, z_height, rpm, tlab))
                        continue
                    metrics_data = cell_data[z_height].get("_metrics", {})
                    for rpm in sorted(k for k in rpm_data.keys() if k not in _md_keys):
                        measurements = rpm_data.get(rpm)
                        if measurements is not None:
                            # Get metrics for this RPM at this Z-height
                            rpm_metrics = metrics_data.get(rpm, {
                                'CV': 0.0,
                                'R2': 0.0,
                                'Trend_Slope': 0.0,
                                'Second_derivative': 0.0,
                                'Second_derivative_drag': 0.0,
                                'Second_derivative_cv': 0.0,
                                'Second_derivative_slope': 0.0,
                                'R2_drag': 0.0,
                                'R2_cv': 0.0,
                                'R2_slope': 0.0,
                                'Hit_2nd_Deriv_Drag': False,
                                'Hit_2nd_Deriv_CV': False,
                                'Hit_2nd_Deriv_Slope': False,
                                'Hit_R2_Drag': False,
                                'Hit_R2_CV': False,
                                'Hit_R2_Slope': False,
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
                                cell_id=global_cell,
                                hit_detected=bool(rpm_metrics.get('Hit_Detected', False)),
                                sample_count=len(measurements),
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
                                f"{rpm_metrics.get('Second_derivative_drag', 0.0):.6f}",
                                f"{rpm_metrics.get('Second_derivative_cv', 0.0):.6f}",
                                f"{rpm_metrics.get('Second_derivative_slope', 0.0):.6f}",
                                f"{rpm_metrics.get('R2_drag', 0.0):.6f}",
                                f"{rpm_metrics.get('R2_cv', 0.0):.6f}",
                                f"{rpm_metrics.get('R2_slope', 0.0):.6f}",
                                str(bool(rpm_metrics.get('Hit_2nd_Deriv_Drag', False))),
                                str(bool(rpm_metrics.get('Hit_2nd_Deriv_CV', False))),
                                str(bool(rpm_metrics.get('Hit_2nd_Deriv_Slope', False))),
                                str(bool(rpm_metrics.get('Hit_R2_Drag', False))),
                                str(bool(rpm_metrics.get('Hit_R2_CV', False))),
                                str(bool(rpm_metrics.get('Hit_R2_Slope', False))),
                                str(len(measurements)),
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
                    _safe_pump_send_tag(pump, b"ST")
                    sleep_with_stop(1)
                    print("ESP32 communication initialized (legacy mode)")
            else:
                # Legacy test
                _safe_pump_send_tag(pump, b"ST")
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
        global CELL_VISCOSITY_RESULTS
        CELL_VISCOSITY_RESULTS = {}
        
        try:
            print(f"\nStarting dynamic analysis...")
            print(f"Experiment name: {run_experiment_name}")
            print(f"Testing {len(selected_cells)} cells with {len(TEST_RPMS)} RPMs per Z-position")
        
            # Go through each selected cell
            calibration_cells: dict[int, float] = {}  # Populated during calibration runs
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
                    # Use resolved run mode (set once at run start) to avoid accidental drift in per-cell flags.
                    is_calibration_like_run = mode in ("calibration", "recalibration")
                    
                    # Determine status message and custom starting Z for recalibration
                    custom_z = None
                    if RECALIBRATE_INDIVIDUAL_CELLS:
                        # Check if a custom starting Z is provided for this cell
                        custom_z = RECALIBRATION_CELLS.get(global_cell, None)
                        if custom_z is not None:
                            web_interface.update_status(f"Recalibrating cell {i+1}/{len(selected_cells)} (Cell {global_cell}, starting at Z={custom_z:.3f})")
                        else:
                            web_interface.update_status(f"Recalibrating cell {i+1}/{len(selected_cells)} (Cell {global_cell})")
                    elif CALIBRATION_MODE:
                        web_interface.update_status(f"Calibrating cell {i+1}/{len(selected_cells)} (Cell {global_cell})")
                    else:
                        web_interface.update_status(f"Testing Cell {global_cell} at RPMs {cell_rpms}")

                    result = test_cell_dynamic_z_series(
                        cnc,
                        client,
                        global_cell,
                        row_config['safe_z'],        # Always pass the ROW default; calibration handled inside
                        row_config['max_z_travel'],
                        cell_rpms,
                        pump=None if is_calibration_like_run else pump,   # No pump in calibration/recalibration mode
                        custom_starting_z=custom_z,  # Pass custom starting Z if in recalibration mode
                    )
                    feedback_summary = {}
                    if isinstance(result, tuple):
                        if len(result) >= 3:
                            cell_data, _fill_thread, feedback_summary = result[0], result[1], result[2]
                        elif len(result) >= 2:
                            cell_data, _fill_thread = result[0], result[1]
                        else:
                            cell_data = result[0]
                            _fill_thread = None
                    else:
                        cell_data = result
                        _fill_thread = None
                    if _fill_thread is not None:
                        active_threads.append(_fill_thread)
                    all_data[global_cell] = cell_data
                    completed_cells.append(global_cell)
                    print(f"Cell {global_cell} testing completed")

                    if is_calibration_like_run:
                        # Extract and save rough hitpoint for this cell
                        rough_z = extract_rough_hitpoint(cell_data)
                        if rough_z is not None:
                            print(f"  Calibration: Cell {global_cell} rough hitpoint = {rough_z:.3f}")
                            calibration_cells[global_cell] = rough_z
                        else:
                            print(f"  Calibration: Cell {global_cell} — no reliable hitpoint found, skipping")
                        # Track calibration/recalibration progress for live cross-device UI sync.
                        web_interface.add_completed_cell(global_cell)
                        if CALIBRATION_MODE:
                            web_interface.update_status(f"Calibrated cell {i+1}/{len(selected_cells)} (Cell {global_cell})")
                        else:
                            web_interface.update_status(f"Recalibrated cell {i+1}/{len(selected_cells)} (Cell {global_cell})")
                        # NO washing in calibration/recalibration mode — move directly to next cell
                    else:
                        if PREDICTED_VISCOSITY_ENABLED:
                            run_predicted_viscosity_for_cell(
                                global_cell, cell_rpms, feedback_summary
                            )
                        # Normal run: perform washing as before
                        if pump:
                            perform_washing_sequence(cnc, pump, global_cell, fill_thread=_fill_thread)
                            web_interface.add_completed_cell(global_cell)
                        else:
                            print(f"Warning: Pump not available, skipping washing for Cell {global_cell}")

                    print(f"Cell {global_cell} fully completed")

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
            
            # If this was a calibration or recalibration run, save per-cell rough hitpoints
            if (CALIBRATION_MODE or RECALIBRATE_INDIVIDUAL_CELLS) and calibration_cells:
                try:
                    calibrated_at_local = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
                    if RECALIBRATE_INDIVIDUAL_CELLS:
                        # For individual cell recalibration, use update_calibration_for_cells to merge with existing data
                        update_calibration_for_cells(calibration_cells, calibrated_at=calibrated_at_local)
                        print(f"Updated calibration data for {len(calibration_cells)} cells (other cells preserved).")
                        web_interface.update_status("Individual cell recalibration complete — Z-height data updated")
                    else:
                        # For full calibration, replace all calibration data
                        save_calibration(calibration_cells, calibrated_at=calibrated_at_local)
                        print(f"Calibration data saved for {len(calibration_cells)} cells.")
                        web_interface.update_status("Calibration complete — Z-height data saved")
                    try:
                        web_interface.emit_calibration_complete(get_calibration_summary())
                    except Exception:
                        pass
                except Exception as e:
                    print(f"Error saving calibration data: {e}")

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
                    _safe_pump_send_tag(pump, b"0")
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
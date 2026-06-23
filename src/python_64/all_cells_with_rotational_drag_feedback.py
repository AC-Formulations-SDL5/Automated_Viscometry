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
from typing import Dict, List, Optional, Set, Tuple
from cnc_controller import CNC_Machine, CNCMotionError
from viscometer_client import ViscometerClient
from move_to_locations import PumpESP32
from feedback_helper_function import RotationalDragFeedbackController
from web_interface import web_interface
from predicted_viscosity import normalize_viscosity_prediction_mode, predict_viscosity
from rheology_live_adapter import SUMMARY_KEY
from hitpoint import extract_hitpoint, extract_rough_hitpoint
from calibration_store import (
    is_calibrated, load_calibration, get_safe_z_for_cell, get_calibration_summary, clear_calibration
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
CALIBRATION_READ_RETRIES_PER_SLOT = 3
CALIBRATION_READ_RETRY_DELAY_S = 0.5
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
    {'row_number': 1, 'base_x': 10, 'safe_z': -65.5, 'max_z_travel': -67.00},
    {'row_number': 2, 'base_x': 85, 'safe_z': -65.5, 'max_z_travel': -67.00},
    {'row_number': 3, 'base_x': 309, 'safe_z': -64.5, 'max_z_travel': -67.00}
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
VISCOSITY_PREDICTION_MODE = "off"
CELL_VISCOSITY_RESULTS: Dict[int, Dict] = {}
SAVE_ALL_SAMPLE_DATA = False
Z_START_OFFSET_MM = 0.4

# ========== CALIBRATION MODE CONFIGURATION ==========
CALIBRATION_MODE = False          # Set to True when a calibration run is requested
RECALIBRATE_INDIVIDUAL_CELLS = False  # Set to True for individual cell recalibration mode
RECALIBRATION_CELLS = {}  # Dict[cell_id, optional_starting_z] for individual recalibration
RECALIBRATION_IGNORE_MAX_Z_TRAVEL = False  # Recalibration only: use global floor instead of row max_z_travel
RECALIBRATION_ABSOLUTE_MAX_Z_TRAVEL = -66.800  # Global Z floor when override is enabled (mm)
CALIBRATION_OFFSET = 0.4         # mm above rough hitpoint to use as safe_z

# ========== DISCOVERY MODE CONFIGURATION ==========
DISCOVERY_MODE_ENABLED = False
DISCOVERY_ETA_GUESS_MAP: Dict[int, Optional[float]] = {}
DISCOVERY_PROBE_DURATION_S = 60.0
DISCOVERY_DUCK_TORQUE_PCT = 80.0
DISCOVERY_HANDOFF_PAUSE_S = 10.0


def _is_calibration_like_run() -> bool:
    """True during full calibration or individual-cell recalibration runs."""
    return bool(CALIBRATION_MODE or RECALIBRATE_INDIVIDUAL_CELLS)


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


# #region agent log helper
def _agent_debug_log(hypothesis_id: str, location: str, message: str, data: dict, run_id: str = "pre-fix-1") -> None:
    """Append a single NDJSON debug log line for this debug session."""
    try:
        import json as _json
        import time as _time

        payload = {
            "sessionId": "80a163",
            "id": f"log_{int(_time.time() * 1000)}_{hypothesis_id}",
            "timestamp": int(_time.time() * 1000),
            "location": location,
            "message": message,
            "data": data or {},
            "runId": run_id,
            "hypothesisId": hypothesis_id,
        }
        log_path = pathlib.Path(__file__).resolve().parents[2] / ".cursor" / "debug-80a163.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(_json.dumps(payload) + "\n")
    except Exception:
        # Logging must never interfere with runtime behavior.
        pass
# #endregion agent log helper


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
    global RECALIBRATION_IGNORE_MAX_Z_TRAVEL
    global LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED, LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT
    global VISCOSITY_PREDICTION_MODE
    global SAVE_ALL_SAMPLE_DATA, Z_START_OFFSET_MM
    global DISCOVERY_MODE_ENABLED, DISCOVERY_ETA_GUESS_MAP, DISCOVERY_PROBE_DURATION_S
    global DISCOVERY_DUCK_TORQUE_PCT, DISCOVERY_HANDOFF_PAUSE_S

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
    RECALIBRATION_IGNORE_MAX_Z_TRAVEL = bool(
        settings.get('recalibration_ignore_max_z_travel', RECALIBRATION_IGNORE_MAX_Z_TRAVEL)
    )
    LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED = bool(
        settings.get('low_torque_liquid_contact_skip_enabled', LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED)
    )
    LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT = float(
        settings.get('low_torque_liquid_contact_threshold_pct', LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT)
    )
    VISCOSITY_PREDICTION_MODE = normalize_viscosity_prediction_mode(
        settings.get('viscosity_prediction_mode'),
        legacy_enabled=settings.get('predicted_viscosity_enabled'),
    )
    SAVE_ALL_SAMPLE_DATA = bool(settings.get('save_all_sample_data', SAVE_ALL_SAMPLE_DATA))
    try:
        z_offset = float(settings.get('z_start_offset_mm', Z_START_OFFSET_MM))
        if not (-1.0 <= z_offset <= 3.0):
            z_offset = 0.4
        Z_START_OFFSET_MM = z_offset
    except (TypeError, ValueError):
        Z_START_OFFSET_MM = 0.4
    DISCOVERY_MODE_ENABLED = bool(settings.get('discovery_mode_enabled', False))
    DISCOVERY_PROBE_DURATION_S = float(settings.get('discovery_probe_duration_s', DISCOVERY_PROBE_DURATION_S))
    try:
        duck_pct = float(settings.get('discovery_duck_torque_pct', DISCOVERY_DUCK_TORQUE_PCT))
        DISCOVERY_DUCK_TORQUE_PCT = max(1.0, min(100.0, duck_pct))
    except (TypeError, ValueError):
        DISCOVERY_DUCK_TORQUE_PCT = 80.0
    try:
        pause_s = float(settings.get('discovery_handoff_pause_s', DISCOVERY_HANDOFF_PAUSE_S))
        DISCOVERY_HANDOFF_PAUSE_S = max(0.0, pause_s)
    except (TypeError, ValueError):
        DISCOVERY_HANDOFF_PAUSE_S = 10.0
    raw_eta_map = settings.get('discovery_eta_guess_map', {})
    DISCOVERY_ETA_GUESS_MAP = {}
    if isinstance(raw_eta_map, dict):
        for cell_key, eta_val in raw_eta_map.items():
            try:
                cell_id = int(cell_key)
            except (TypeError, ValueError):
                continue
            if eta_val in (None, ''):
                DISCOVERY_ETA_GUESS_MAP[cell_id] = None
            else:
                try:
                    DISCOVERY_ETA_GUESS_MAP[cell_id] = float(eta_val)
                except (TypeError, ValueError):
                    continue
    if DISCOVERY_MODE_ENABLED:
        LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED = False
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


SUMMARY_CSV_HEADERS = [
    "row", "cell", "Cell_Label", "Z_Height_mm", "RPM",
    "Elapsed_Time_s", "Torque_%", "Rotational_Drag", "Hit_Detected",
]

TIMESERIES_CSV_HEADERS = [
    "row", "cell", "Cell_Label", "Z_Height_mm", "RPM",
    "Elapsed_Time_s", "Torque_%", "Rotational_Drag",
]


def _append_cell_termination_metadata(
    csv_writer,
    all_data: Dict[int, object],
    termination_by_cell: Optional[Dict[int, str]] = None,
) -> None:
    """Write per-cell termination methods into CSV metadata comments."""
    if not all_data:
        return
    term = termination_by_cell or {}
    cell_map = {cell: term.get(cell, "normal") for cell in sorted(all_data.keys())}
    csv_writer.writerow([f"# Cell termination methods: {cell_map}"])


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
        "False",
    ]


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

    PRE-CONDITION: CNC has retracted to safe Z at the cell XY (_finish_cell_measurement).
    _pump_fill_station1() and _motor1_start() may already be running in background threads
    started only after successful retract.
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

def _cell_xy_for_global(global_cell: int) -> Tuple[int, float, float]:
    """Return (row_number, x_pos, y_pos) for a global cell id."""
    row_number, local_cell = global_cell_to_row_and_local(global_cell)
    base_x = None
    for row in ROWS:
        if row['row_number'] == row_number:
            base_x = row['base_x']
            break
    if base_x is None:
        raise ValueError(f"Invalid row for cell {global_cell}")
    x_pos = base_x
    y_pos = BASE_Y + (local_cell - 1) * Y_OFFSET
    # #region agent log
    _agent_debug_log(
        hypothesis_id="H1",
        location="all_cells_with_rotational_drag_feedback.py:_cell_xy_for_global",
        message="Computed XY for global cell",
        data={
            "global_cell": global_cell,
            "row_number": row_number,
            "local_cell": local_cell,
            "x_pos": x_pos,
            "y_pos": y_pos,
        },
    )
    # #endregion agent log
    return row_number, x_pos, y_pos


def _finish_cell_measurement(
    cnc: CNC_Machine,
    client: ViscometerClient,
    pump: Optional[PumpESP32],
    global_cell: int,
    exit_reason: str,
    start_wash_prefill: bool,
) -> Tuple[Optional[threading.Thread], bool, str]:
    """
    Retract CNC to safe Z, stop viscometer, optionally start wash prefill threads.

    Returns (fill_thread, cnc_retracted_ok, exit_reason).
    """
    fill_thread: Optional[threading.Thread] = None
    cnc_retracted_ok = False
    _, x_pos, y_pos = _cell_xy_for_global(global_cell)

    try:
        raise_if_stop_requested()
    except KeyboardInterrupt:
        exit_reason = "user_stop"

    print(
        f"Cell {global_cell}: CNC retract to safe Z at X={x_pos}, Y={y_pos}, Z=0 "
        f"(exit_reason={exit_reason})"
    )
    # #region agent log
    _agent_debug_log(
        hypothesis_id="H2",
        location="all_cells_with_rotational_drag_feedback.py:_finish_cell_measurement",
        message="Begin retract to safe Z",
        data={
            "global_cell": global_cell,
            "x_pos": x_pos,
            "y_pos": y_pos,
            "exit_reason": exit_reason,
        },
    )
    # #endregion agent log
    web_interface.update_status(f"Cell {global_cell}: retracting to safe Z")

    try:
        retract_allow_abort = exit_reason != "user_stop"
        cnc.retract_z_at_cell(
            x_pos,
            y_pos,
            z_safe=0,
            speed=Z_FEED_RATE,
            allow_abort=retract_allow_abort,
        )
        sleep_with_stop(1)
        cnc_retracted_ok = True
        print(f"Cell {global_cell} returned to safe Z position (CNC retract OK)")
        web_interface.update_position(x_pos, y_pos, 0)
    except KeyboardInterrupt:
        exit_reason = "user_stop"
        print(f"Cell {global_cell}: CNC retract cancelled (stop requested)")
    except CNCMotionError as e:
        print(f"Cell {global_cell}: CNC retract failed: {e}")
        web_interface.update_status(f"Cell {global_cell}: CNC retract failed — wash skipped")
    # #region agent log
    _agent_debug_log(
        hypothesis_id="H2",
        location="all_cells_with_rotational_drag_feedback.py:_finish_cell_measurement",
        message="Retract to safe Z result",
        data={
            "global_cell": global_cell,
            "x_pos": x_pos,
            "y_pos": y_pos,
            "exit_reason": exit_reason,
            "cnc_retracted_ok": cnc_retracted_ok,
        },
    )
    # #endregion agent log

    try:
        client.stop()
    except Exception:
        pass

    if (
        start_wash_prefill
        and pump is not None
        and cnc_retracted_ok
        and exit_reason != "user_stop"
    ):
        web_interface.update_status(
            f"Cell {global_cell}: last measurement done — pre-filling wash station"
        )
        print("[CONCURRENT] CNC retract OK — starting pump fill + motor start...")
        fill_thread = _run_in_thread(_pump_fill_station1, pump)
        _run_in_thread(_motor1_start, pump)
    elif pump is not None and not cnc_retracted_ok:
        try:
            print(f"Cell {global_cell}: emergency pump stop (retract failed, no wash prefill)")
            _safe_pump_send_tag(pump, b"0")
        except Exception:
            pass

    return fill_thread, cnc_retracted_ok, exit_reason


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
    # #region agent log
    _agent_debug_log(
        hypothesis_id="H1",
        location="all_cells_with_rotational_drag_feedback.py:move_to_cell_position",
        message="Move to cell position",
        data={
            "row_number": row_number,
            "local_cell": local_cell_number,
            "global_cell": global_cell,
            "x_pos": x_pos,
            "y_pos": y_pos,
            "z_height": z_height,
        },
    )
    # #endregion agent log
    
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


def _read_valid_torque_packet(
    client: ViscometerClient,
    *,
    max_attempts: int = 1,
    retry_delay_s: float = CALIBRATION_READ_RETRY_DELAY_S,
) -> Optional[Dict]:
    """Read viscometer data; retry within a single sample slot when max_attempts > 1."""
    attempts = max(1, int(max_attempts))
    for attempt in range(1, attempts + 1):
        raise_if_stop_requested()
        try:
            data = client.read_single(timeout=TORQUE_READ_TIMEOUT)
            if data and data.get("torque_valid") and data.get("torque_percent") is not None:
                return data
            if attempt == 1:
                torque_valid = data.get("torque_valid") if data else None
                torque_percent = data.get("torque_percent") if data else None
                print(
                    f"      Invalid torque read: valid={torque_valid}, "
                    f"value={torque_percent}"
                )
        except Exception as e:
            if attempt == 1:
                print(f"      Torque read error: {e}")
        if attempt < attempts:
            sleep_with_stop(retry_delay_s)
    return None


def _publish_torque_sample_to_web(
    z_height: float,
    rpm: float,
    torque_percent: float,
    elapsed_since_start: float,
    *,
    emit_measurement_point: bool,
    sample_count: int = 1,
) -> None:
    """Broadcast live torque and a measurement point to the web UI (Z vs drag live chart)."""
    web_interface.update_live_torque(
        torque_percent=torque_percent,
        rpm=rpm,
        elapsed=elapsed_since_start,
    )
    if not emit_measurement_point:
        return
    rotational_drag = abs(torque_percent) / rpm if rpm > 0 else 0.0
    web_interface.add_measurement_point(
        height=z_height,
        rotational_drag=rotational_drag,
        rpm=rpm,
        cell_id=web_interface.current_cell,
        elapsed_time=elapsed_since_start,
        sample_count=sample_count,
    )


def measure_torque_at_rpm(
    client: ViscometerClient,
    rpm: float,
    z_height: float,
    hunting_first_contact_min_pct: Optional[float] = None,
    read_retries_per_slot: int = 1,
    duck_above_pct_on_first_sample: Optional[float] = None,
) -> Optional[List[Dict]]:
    """Measure torque at a specific RPM, returning all individual measurements with timestamps.

    Recorded samples (and live web points) occur only on a fixed grid every ``SAMPLE_INTERVAL``
    seconds from the start of the measurement window (after dwell)—no off-grid immediate read.

    ``read_retries_per_slot``: viscometer read attempts per scheduled sample slot (calibration
    runs typically pass 3; regular runs use the default of 1).

    If ``hunting_first_contact_min_pct`` is set (liquid-contact hunt at first Z after spindle starts):
    on the **first** recorded sample, if torque is **strictly less than** that threshold, sampling
    stops immediately. Otherwise the full ``MEASUREMENT_DURATION`` collection proceeds.
    Smart early exit is disabled until this gate is resolved.

    If ``duck_above_pct_on_first_sample`` is set (Discovery probe ceiling), on the **first**
    recorded sample, if torque is **greater than or equal to** that threshold, sampling stops
    immediately after recording that point.
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
                    data = _read_valid_torque_packet(
                        client,
                        max_attempts=read_retries_per_slot,
                        retry_delay_s=CALIBRATION_READ_RETRY_DELAY_S,
                    )
                    if data:
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
                        if liquid_hunt_stop:
                            print(
                                f"      [LIQUID CONTACT] Sample at {elapsed_since_start:.2f}s "
                                f"{tp:.2f}% < {hunting_first_contact_min_pct:.2f}% — "
                                "skipping this RPM at this Z (try next RPM)"
                            )
                            _publish_torque_sample_to_web(
                                z_height,
                                rpm,
                                tp,
                                elapsed_since_start,
                                emit_measurement_point=True,
                                sample_count=1,
                            )
                            break
                        if (
                            duck_above_pct_on_first_sample is not None
                            and sample_index == 1
                            and tp >= duck_above_pct_on_first_sample
                        ):
                            measurement = {
                                "timestamp": current_time,
                                "elapsed_time": elapsed_since_start,
                                "torque_percent": tp,
                                "rpm": rpm,
                            }
                            measurements.append(measurement)
                            _publish_torque_sample_to_web(
                                z_height,
                                rpm,
                                tp,
                                elapsed_since_start,
                                emit_measurement_point=True,
                                sample_count=1,
                            )
                            print(
                                f"      [DISCOVERY DUCK] Sample at {elapsed_since_start:.2f}s "
                                f"{tp:.2f}% >= {duck_above_pct_on_first_sample:.2f}% — "
                                "stopping probe"
                            )
                            break
                        measurement = {
                            "timestamp": current_time,
                            "elapsed_time": elapsed_since_start,
                            "torque_percent": tp,
                            "rpm": rpm
                        }
                        measurements.append(measurement)
                        recent_torques.append(tp)
                        recent_torques = recent_torques[-SMART_WINDOW_SIZE:]
                        _publish_torque_sample_to_web(
                            z_height,
                            rpm,
                            tp,
                            elapsed_since_start,
                            emit_measurement_point=True,
                            sample_count=1,
                        )
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

def _torque_should_drop_rpm(measurements: Optional[List[Dict]]) -> Tuple[bool, str]:
    """Return whether an RPM should be dropped from future Z-heights after this measurement."""
    if measurements is None:
        return True, "invalid torque (high resistance)"
    if not measurements:
        return True, "no valid measurements"
    max_torque = max(abs(m["torque_percent"]) for m in measurements)
    if max_torque >= TORQUE_BREAK_THRESHOLD:
        return (
            True,
            f"max torque {max_torque:.2f}% >= threshold {TORQUE_BREAK_THRESHOLD:.2f}%",
        )
    return False, ""


def _rpm_liquid_contact_established(
    measurements: Optional[List[Dict]],
    threshold_pct: float,
) -> bool:
    """True if a sample at elapsed >= SAMPLE_INTERVAL met the torque floor."""
    if not measurements:
        return False
    for row in measurements:
        try:
            elapsed = float(row.get("elapsed_time", 0))
            torque = float(row.get("torque_percent", 0))
        except (TypeError, ValueError):
            continue
        if elapsed >= SAMPLE_INTERVAL and torque >= threshold_pct:
            return True
    return False


_RPM_DATA_META_KEYS = frozenset({
    "_metrics",
    "_liquid_skipped_z",
    "_liquid_skip_torque_label",
    "_liquid_skip_probe_at_z",
})


def _mark_rpm_torque_dropped(
    rpm: float,
    dropped_torque_rpms: Set[float],
    cell_rpms: List[float],
    global_cell: int,
    reason: str,
) -> None:
    if rpm in dropped_torque_rpms:
        return
    dropped_torque_rpms.add(rpm)
    print(f"      [RPM DROPPED] RPM {rpm}: {reason} — excluded from future Z-heights")
    web_interface.emit_rpm_torque_status(global_cell, cell_rpms, dropped_torque_rpms)


def test_dynamic_analysis_at_z(
    client: ViscometerClient,
    z_height: float,
    cell_rpms: List[float],
    *,
    global_cell: int,
    dropped_torque_rpms: Optional[Set[float]] = None,
    liquid_skip_enabled: bool = False,
    liquid_threshold_pct: float = 20.0,
) -> Tuple[Dict[float, Optional[List[Dict]]], bool, bool]:
    """Test active RPMs at a specific Z-height.

    Returns ``(rpm_torque_data, first_rpm_exceeded_threshold, z_skipped_due_to_liquid)``.
    The second value is retained for API compatibility and is always ``False`` (cells no longer
    terminate on first-RPM torque limit). Dropped RPMs are recorded in ``dropped_torque_rpms``
    for regular runs only (not calibration or recalibration).

    When liquid_skip_enabled, each RPM is probed at this Z: if the first sample at
    SAMPLE_INTERVAL is below the floor, that RPM is skipped and the next RPM is tried.
    """
    read_retries_per_slot = (
        CALIBRATION_READ_RETRIES_PER_SLOT if _is_calibration_like_run() else 1
    )
    dropped: Set[float] = dropped_torque_rpms if dropped_torque_rpms is not None else set()
    rpm_torque_data: Dict[float, Optional[List[Dict]]] = {}
    for r in cell_rpms:
        if r in dropped:
            rpm_torque_data[r] = None

    active_rpms = [r for r in cell_rpms if r not in dropped]
    if not active_rpms:
        print(f"    No active RPMs at Z={z_height:.3f} (all dropped)")
        return rpm_torque_data, False, False

    print(
        f"    Testing {len(active_rpms)} active RPM(s) at Z={z_height:.3f} "
        f"({len(dropped)} dropped)"
    )
    if liquid_skip_enabled:
        rpm_torque_data["_liquid_skip_probe_at_z"] = True

    for rpm in active_rpms:
        if liquid_skip_enabled:
            measurements = measure_torque_at_rpm(
                client,
                rpm,
                z_height,
                hunting_first_contact_min_pct=liquid_threshold_pct,
                read_retries_per_slot=read_retries_per_slot,
            )
            if not _rpm_liquid_contact_established(measurements, liquid_threshold_pct):
                print(
                    f"      [LIQUID CONTACT] RPM {rpm}: below floor after first interval "
                    f"(≥ {SAMPLE_INTERVAL:.1f}s) at Z={z_height:.3f} — skip RPM, try next"
                )
                rpm_torque_data[rpm] = None
                continue
        else:
            measurements = measure_torque_at_rpm(
                client,
                rpm,
                z_height,
                read_retries_per_slot=read_retries_per_slot,
            )

        rpm_torque_data[rpm] = measurements
        should_drop, reason = _torque_should_drop_rpm(measurements)
        if should_drop and not _is_calibration_like_run():
            _mark_rpm_torque_dropped(rpm, dropped, cell_rpms, global_cell, reason)
        elif should_drop:
            print(
                f"      [CAL] RPM {rpm}: would drop ({reason}) — continuing for calibration"
            )

    z_liquid_skipped = False
    if liquid_skip_enabled and active_rpms:
        if all(rpm_torque_data.get(r) is None for r in active_rpms):
            z_liquid_skipped = True
            tlab = _liquid_skip_torque_label(liquid_threshold_pct)
            rpm_torque_data["_liquid_skipped_z"] = True
            rpm_torque_data["_liquid_skip_torque_label"] = tlab
            print(
                f"  Z={z_height:.3f}: no RPM met liquid-contact floor "
                f"({liquid_threshold_pct:.2f}%) — hit-point logic skipped for this Z"
            )

    return rpm_torque_data, False, z_liquid_skipped

def test_cell_dynamic_z_series(
    cnc: CNC_Machine,
    client: ViscometerClient,
    global_cell: int,
    safe_z: float,
    max_z_travel: float,
    cell_rpms: List[float],
    pump: Optional[PumpESP32] = None,
    custom_starting_z: Optional[float] = None,
    skip_initial_safe_move: bool = False,
) -> Tuple[Dict[float, Dict[float, Optional[List[Dict]]]], Optional[threading.Thread]]:
    """Test dynamic analysis (multiple RPMs) across Z-gap range for one cell using global cell numbering with rotational drag feedback control
    
    Args:
        custom_starting_z: Optional custom starting Z-height for recalibration mode. If provided, overrides safe_z.
        skip_initial_safe_move: When True, first Z-step uses direct in-sample move (no retract to Z=0).
    """
    row_number, local_cell = global_cell_to_row_and_local(global_cell)
    print(f"\n{'='*60}")
    print(f"DYNAMIC ANALYSIS - CELL {global_cell} (Row {row_number}, Local Cell {local_cell})")
    print(f"Testing RPMs {cell_rpms} across Z-gap range")
    use_row_z_limit = not (
        RECALIBRATE_INDIVIDUAL_CELLS and RECALIBRATION_IGNORE_MAX_Z_TRAVEL
    )
    effective_max_z = max_z_travel if use_row_z_limit else RECALIBRATION_ABSOLUTE_MAX_Z_TRAVEL
    z_limit_mode = "row limit" if use_row_z_limit else "global override (recalibration)"
    print(f"Safe Z: {safe_z:.3f}, Row max Z travel: {max_z_travel:.3f}")
    print(f"Effective max Z: {effective_max_z:.3f} ({z_limit_mode})")
    if custom_starting_z is not None:
        print(f"Custom Starting Z: {custom_starting_z:.3f}")
    if skip_initial_safe_move:
        print("Discovery handoff: in-sample Z-scan (no safe retract on first step)")
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
    if use_liquid_z_skip:
        print(
            f"  Liquid-contact hunt enabled (regular run): per RPM at each Z, skip RPM when first "
            f"sample at elapsed ≥ {SAMPLE_INTERVAL:.1f}s is < "
            f"{LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT:.2f}% and try next RPM; SKIPPED rows use "
            f"{_liquid_skip_torque_label(LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT)}"
        )
    
    # Determine starting Z: custom_starting_z > RECALIBRATE_INDIVIDUAL_CELLS > CALIBRATION_MODE > normal
    if custom_starting_z is not None:
        current_z = custom_starting_z
    elif not (CALIBRATION_MODE or RECALIBRATE_INDIVIDUAL_CELLS):
        from calibration_store import load_calibration
        cal_cells = load_calibration().get("cells", {})
        cal_key = str(int(global_cell))
        if cal_key in cal_cells:
            rough_z = float(cal_cells[cal_key])
            current_z = rough_z + Z_START_OFFSET_MM
            print(
                f"  Calibrated Z-start: rough {rough_z:.3f} + {Z_START_OFFSET_MM:.3f} "
                f"= {current_z:.3f} mm"
            )
        else:
            current_z = get_safe_z_for_cell(global_cell, safe_z, offset=Z_START_OFFSET_MM)
    else:
        # In calibration or recalibration mode, use the provided safe_z
        current_z = safe_z
    print(f"Starting from Z-safe: {current_z:.3f}")
    if not use_row_z_limit:
        web_interface.update_status(
            f"Cell {global_cell}: recalibration ignoring row max-Z; floor Z={effective_max_z:.3f} mm"
        )

    # Require persistent confidence trigger before terminating the Z-series.
    hit_confidence_threshold = 0.80
    required_consecutive_hit_steps = 3
    consecutive_high_confidence_steps = 0
    consecutive_fail_safe_steps = 0
    _fill_thread: Optional[threading.Thread] = None
    cell_exit_reason = "normal"
    start_wash_prefill = pump is not None

    dropped_torque_rpms: Set[float] = set()
    web_interface.emit_rpm_torque_status(global_cell, cell_rpms, dropped_torque_rpms)

    step_count = 0
    try:
        while current_z >= effective_max_z:
            raise_if_stop_requested()
            step_count += 1
            z_rounded = round(current_z, 3)
            web_interface.set_current_z(z_rounded)
            
            print(f"\nCell {global_cell} - Z-Step {step_count}: Z={z_rounded:.3f}")
            
            try:
                # Move to position
                if step_count == 1 and not skip_initial_safe_move:
                    move_to_cell_position(cnc, row_number, local_cell, current_z)
                else:
                    # Direct Z movement (no Z=0 retraction)
                    base_x = None
                    for row in ROWS:
                        if row['row_number'] == row_number:
                            base_x = row['base_x']
                            break
                    
                    x_pos = base_x
                    y_pos = BASE_Y + (local_cell - 1) * Y_OFFSET
                    if step_count == 1 and skip_initial_safe_move:
                        web_interface.set_current_cell(global_cell)
                        print(
                            f"  Discovery handoff: direct move to Z={current_z:.3f} mm "
                            f"(no retract to safe Z)"
                        )
                        web_interface.update_status(
                            f"Cell {global_cell}: in-sample Z-scan from Z={z_rounded:.3f} mm"
                        )
                    else:
                        print(f"  Moving directly to Z={current_z:.3f} (no retraction)")
                        web_interface.update_status(
                            f"Cell {global_cell} | Z-step {step_count} | Z={z_rounded:.3f} mm"
                        )
                    raise_if_stop_requested()
                    cnc.move_to_point(x_pos, y_pos, current_z, speed=Z_FEED_RATE)
                    web_interface.update_position(x_pos, y_pos, current_z)
                    sleep_with_stop(SETTLE_TIME)
                
                if len(dropped_torque_rpms) >= len(cell_rpms):
                    print(
                        f"  All RPMs dropped at Z={z_rounded:.3f}; continuing Z-series "
                        "(hit-point / fail-safe only, no spindle tests)"
                    )
                    rpm_data = {r: None for r in cell_rpms}
                    rpm_data["_metrics"] = {}
                    cell_z_rpm_data[z_rounded] = rpm_data
                    current_z += Z_STEP_SIZE
                    continue

                # Test active RPMs at this Z-height
                rpm_data, _first_rpm_exceeded, z_liquid_skipped = test_dynamic_analysis_at_z(
                    client,
                    z_rounded,
                    cell_rpms,
                    global_cell=global_cell,
                    dropped_torque_rpms=dropped_torque_rpms,
                    liquid_skip_enabled=use_liquid_z_skip,
                    liquid_threshold_pct=LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT,
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

                # Add measurements to feedback controller for rotational drag analysis
                # Always calculate and store metrics for consistent CSV output
                metrics_data = {}
                
                if FEEDBACK_CONTROL_ENABLED and rpm_data:
                    print(f"  Rotational Drag Analysis:")
                    rpm_data_for_feedback = {
                        k: v for k, v in rpm_data.items() if k not in _RPM_DATA_META_KEYS
                    }
                    feedback_controller.add_measurements_at_z(z_rounded, rpm_data_for_feedback)
                    
                    fail_safe_floor = HIT_POINT_CONFIDENCE_THRESHOLD * 0.75

                    # Extract and store metrics for each RPM at this Z-level
                    for rpm in cell_rpms:
                        if rpm in rpm_data and rpm_data[rpm] is not None:
                            trend_analysis = feedback_controller.analyze_trend_for_rpm(rpm)
                            if trend_analysis['valid']:
                                rpm_confidence = float(trend_analysis.get('hit_confidence', 0.0) or 0.0)
                                rpm_fail_safe_active = rpm_confidence >= fail_safe_floor
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
                                    fail_safe_active=rpm_fail_safe_active,
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
                                    fail_safe_active=False,
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
                                fail_safe_active=False,
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

                    cell_z_rpm_data[z_rounded]['_metrics'] = metrics_data
                    hitpoint_z = extract_hitpoint(cell_z_rpm_data)
                    if hitpoint_z is not None:
                        feedback_controller.hit_point_z = hitpoint_z

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
                        cell_exit_reason = "hit_detected"
                        break

                    # Fail-safe: sustained confidence above 75% of hit threshold (requires feedback metrics above).
                    if FAIL_SAFE_ENABLED:
                        fail_safe_floor = HIT_POINT_CONFIDENCE_THRESHOLD * 0.75
                        has_valid_fail_safe_metrics = (
                            bool(metrics_data)
                            and len(feedback_controller.z_rpm_drag_data) >= MIN_DATA_POINTS_FOR_TREND
                        )
                        if has_valid_fail_safe_metrics:
                            above_fail_safe_floor = z_level_max_confidence >= fail_safe_floor
                            if above_fail_safe_floor:
                                consecutive_fail_safe_steps += 1
                                print(
                                    f"  Fail-safe streak: {consecutive_fail_safe_steps}/{FAIL_SAFE_CONSECUTIVE_STEPS} "
                                    f"(max confidence={z_level_max_confidence:.2f} >= floor={fail_safe_floor:.2f})"
                                )
                            else:
                                if consecutive_fail_safe_steps > 0:
                                    print(
                                        f"  Fail-safe streak reset at Z={z_rounded:.3f} "
                                        f"(max confidence={z_level_max_confidence:.2f} < floor={fail_safe_floor:.2f})"
                                    )
                                consecutive_fail_safe_steps = 0

                            if consecutive_fail_safe_steps >= FAIL_SAFE_CONSECUTIVE_STEPS:
                                for rpm in metrics_data:
                                    metrics_data[rpm]['Hit_Detected'] = False
                                    metrics_data[rpm]['Hit_Reasons'] = 'fail safe, experiment terminated'
                                cell_z_rpm_data[z_rounded]['_metrics'] = metrics_data
                                web_interface.update_status(
                                    f"Cell {global_cell}: fail-safe activated after "
                                    f"{FAIL_SAFE_CONSECUTIVE_STEPS} consecutive confidence readings "
                                    f">= {fail_safe_floor:.2f} (75% of hit threshold)"
                                )
                                print(
                                    f"  *** FAIL-SAFE: terminating Cell {global_cell} after "
                                    f"{FAIL_SAFE_CONSECUTIVE_STEPS} consecutive Z-steps above 75% confidence floor ***"
                                )
                                cell_exit_reason = "fail_safe"
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
                if web_interface.should_terminate_current_cell():
                    web_interface.clear_terminate_current_cell_request()
                    cell_exit_reason = "manual_terminate"
                    web_interface.update_status(
                        f"Cell {global_cell}: manual termination queued; ending after current measurement cycle"
                    )
                    print(
                        f"  *** MANUAL TERMINATION: ending Cell {global_cell} after current measurement cycle at Z={z_rounded:.3f} ***"
                    )
                    break
                    
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
    except KeyboardInterrupt:
        cell_exit_reason = "user_stop"
        _fill_thread, cnc_retracted_ok, cell_exit_reason = _finish_cell_measurement(
            cnc,
            client,
            pump,
            global_cell,
            cell_exit_reason,
            start_wash_prefill=False,
        )
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
        feedback_summary['exit_reason'] = cell_exit_reason
        feedback_summary['cnc_retracted_ok'] = cnc_retracted_ok
        print(
            f"Cell {global_cell} stopped early: "
            f"{len(cell_z_rpm_data)} Z-positions collected"
        )
        return cell_z_rpm_data, _fill_thread, feedback_summary

    _fill_thread, cnc_retracted_ok, cell_exit_reason = _finish_cell_measurement(
        cnc,
        client,
        pump,
        global_cell,
        cell_exit_reason,
        start_wash_prefill=start_wash_prefill,
    )

    # Print feedback controller summary
    if FEEDBACK_CONTROL_ENABLED:
        summary = feedback_controller.get_summary()
        print(f"\n  Feedback Controller Summary:")
        print(f"    Hit point detected: {summary['hit_point_detected']}")
        if summary['hit_point_detected']:
            print(f"    Hit Z-level: {_format_hit_point_z(summary.get('hit_point_z'))}")
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
    feedback_summary['exit_reason'] = cell_exit_reason
    feedback_summary['cnc_retracted_ok'] = cnc_retracted_ok
    return cell_z_rpm_data, _fill_thread, feedback_summary


def run_predicted_viscosity_for_cell(
    cell_id: int,
    rpms: List[float],
    cell_z_rpm_data: dict,
    feedback_summary: Dict,
) -> None:
    """Fit unified rheology per RPM and cell summary after a cell completes."""
    global CELL_VISCOSITY_RESULTS

    if normalize_viscosity_prediction_mode(VISCOSITY_PREDICTION_MODE) == "off":
        return

    hit_z = extract_hitpoint(cell_z_rpm_data)
    if hit_z is not None:
        print(f"  Viscosity trim hitpoint Z: {hit_z:.3f}")

    if cell_id not in CELL_VISCOSITY_RESULTS:
        CELL_VISCOSITY_RESULTS[cell_id] = {}

    rpm_list = [float(r) for r in rpms]
    for rpm in rpm_list:
        try:
            result = predict_viscosity(
                cell_id,
                rpm,
                web_interface.measurement_data,
                torque_floor_pct=LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT,
                hit_point_z=hit_z,
                viscosity_prediction_mode=VISCOSITY_PREDICTION_MODE,
            )
            CELL_VISCOSITY_RESULTS[cell_id][rpm] = result
            web_interface.emit_predicted_viscosity(cell_id, rpm, result)
            if result.get('success'):
                print(
                    f"  Predicted viscosity Cell {cell_id} @ {rpm} RPM: "
                    f"{result.get('viscosity_kcp'):.3f} kCp "
                    f"(R²={result.get('R2')}, pts={result.get('n_points_used')})"
                )
            else:
                print(
                    f"  Predicted viscosity Cell {cell_id} @ {rpm} RPM: failed — "
                    f"{result.get('error')}"
                )
        except Exception as e:
            print(f"  Warning: predicted viscosity failed for Cell {cell_id} RPM {rpm}: {e}")

    try:
        from predicted_viscosity import predict_cell_viscosity

        cell_results = predict_cell_viscosity(
            cell_id,
            rpm_list,
            web_interface.measurement_data,
            torque_floor_pct=LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT,
            hit_point_z=hit_z,
            viscosity_prediction_mode=VISCOSITY_PREDICTION_MODE,
        )
        summary = cell_results.get(SUMMARY_KEY) or {}
        CELL_VISCOSITY_RESULTS[cell_id][SUMMARY_KEY] = summary
        web_interface.emit_predicted_viscosity_summary(cell_id, summary)
        if summary.get('success'):
            print(
                f"  Cell {cell_id} rheology summary: {summary.get('regime')} "
                f"n={summary.get('n')} η={summary.get('viscosity_kcp')} kCp"
            )
        elif summary.get('error'):
            print(f"  Cell {cell_id} rheology summary failed: {summary.get('error')}")
    except Exception as e:
        print(f"  Warning: cell rheology summary failed for Cell {cell_id}: {e}")


def _append_discovery_csv_metadata(csv_writer) -> None:
    """Write Discovery Mode RPM probe summary into CSV metadata comments."""
    if not DISCOVERY_MODE_ENABLED:
        return
    try:
        from web_interface import web_interface

        results = dict(web_interface.discovery_results_by_cell or {})
    except Exception:
        results = {}
    if not results:
        return

    csv_writer.writerow(["# Discovery Mode Results"])
    csv_writer.writerow([
        "# Cell,Cell_Label,n_probe,is_newtonian,T_top,T_top_target,T_bottom,Z_bottom_mm,S,"
        "landing_ok,landing_status,rpm_30,rpm_40,rpm_50,rpm_60,rpm_70,power_law_r2,"
        "discovery_path,status,Discovered_RPM,eta_est_cP,Target_Z_mm"
    ])
    for cell_key in sorted(results.keys(), key=lambda k: int(k)):
        entry = results.get(cell_key) or {}
        try:
            cell_id = int(cell_key)
        except (TypeError, ValueError):
            continue
        label = CELL_CONTENT_MAP.get(cell_id, "")
        csv_writer.writerow([
            f"# {cell_id},{label},"
            f"{entry.get('n_probe', '')},"
            f"{entry.get('is_newtonian', '')},"
            f"{entry.get('T_top', '')},"
            f"{entry.get('T_top_target', '')},"
            f"{entry.get('T_bottom', '')},"
            f"{entry.get('Z_bottom_mm', '')},"
            f"{entry.get('S', '')},"
            f"{entry.get('landing_ok', '')},"
            f"{entry.get('landing_status', '')},"
            f"{entry.get('rpm_30', '')},"
            f"{entry.get('rpm_40', '')},"
            f"{entry.get('rpm_50', '')},"
            f"{entry.get('rpm_60', '')},"
            f"{entry.get('rpm_70', '')},"
            f"{entry.get('power_law_r2', '')},"
            f"{entry.get('discovery_path', '')},"
            f"{entry.get('status', '')},"
            f"{entry.get('rpm', '')},"
            f"{entry.get('eta_estimate', '')},"
            f"{entry.get('target_z_mm', '')}",
        ])
    csv_writer.writerow([
        "# Probe detail: Cell,Cell_Label,Probe#,Probe_RPM,Probe_Torque_%,"
        "Probe_eta_cP,Ladder_Target_%"
    ])
    for cell_key in sorted(results.keys(), key=lambda k: int(k)):
        entry = results.get(cell_key) or {}
        try:
            cell_id = int(cell_key)
        except (TypeError, ValueError):
            continue
        label = CELL_CONTENT_MAP.get(cell_id, "")
        probes = entry.get("probes") or []
        for idx, probe in enumerate(probes, 1):
            p_rpm = probe.get("rpm", "")
            p_torque = probe.get("torque", "")
            p_eta = probe.get("eta_est", "")
            ladder_tgt = probe.get("ladder_target_pct", "")
            csv_writer.writerow([
                f"# {cell_id},{label},{idx},"
                f"{'' if p_rpm is None else p_rpm},"
                f"{'' if p_torque is None else p_torque},"
                f"{'' if p_eta is None else p_eta},"
                f"{'' if ladder_tgt is None else ladder_tgt}",
            ])
    csv_writer.writerow([])


def _merge_discovery_landing_after_descent(
    cell_id: int,
    cell_data: Dict[float, Dict[float, Optional[List[Dict]]]],
    discovery_rpm: float,
    termination_reason: str,
) -> None:
    """Enrich discovery_results_by_cell with post-descent T_bottom, S, landing flag."""
    try:
        from discovery_landing import merge_landing_into_discovery_result
        from discovery_mode import load_discovery_config
        from discovery_runner import discovery_result_to_web_payload
        from web_interface import web_interface

        cfg = load_discovery_config()
        key = str(int(cell_id))
        existing = dict(web_interface.discovery_results_by_cell.get(key) or {})
        if not existing:
            return
        merged = merge_landing_into_discovery_result(
            existing,
            cell_data,
            float(discovery_rpm),
            termination_reason,
            landing_window=cfg.landing_torque_window,
        )
        payload = discovery_result_to_web_payload(cell_id, merged)
        web_interface.record_discovery_result(cell_id, payload)
    except Exception as exc:
        print(f"  Warning: discovery landing metrics failed for Cell {cell_id}: {exc}")


def _format_hit_point_z(hit_point_z: Optional[float]) -> str:
    """Format a hit-point Z value for logs without raising on missing data."""
    if hit_point_z is None:
        return "n/a"
    try:
        return f"{float(hit_point_z):.3f}"
    except (TypeError, ValueError):
        return "n/a"


def _append_predicted_viscosity_csv_metadata(csv_writer) -> None:
    """Write predicted viscosity summary rows into CSV metadata comments."""
    csv_writer.writerow([f"# Viscosity prediction mode: {VISCOSITY_PREDICTION_MODE}"])
    if VISCOSITY_PREDICTION_MODE == "off" or not CELL_VISCOSITY_RESULTS:
        csv_writer.writerow([])
        return
    csv_writer.writerow(["# Predicted Viscosity Results"])
    csv_writer.writerow([
        "# Cell,Cell_Label,RPM,Viscosity_kCp,A,B,R2,regime,n,n_points_used,fit_success"
    ])
    for global_cell in sorted(CELL_VISCOSITY_RESULTS.keys()):
        rpm_map = CELL_VISCOSITY_RESULTS[global_cell]
        label = CELL_CONTENT_MAP.get(global_cell, "")
        summary = rpm_map.get(SUMMARY_KEY) if isinstance(rpm_map, dict) else {}
        cell_regime = summary.get("regime") if isinstance(summary, dict) else ""
        cell_n = summary.get("n") if isinstance(summary, dict) else ""
        for rpm in sorted(k for k in rpm_map.keys() if k != SUMMARY_KEY):
            result = rpm_map[rpm]
            if not isinstance(result, dict):
                continue
            visc = result.get("viscosity_kcp")
            a_val = result.get("A")
            b_val = result.get("B")
            r2_val = result.get("R2")
            csv_writer.writerow([
                f"# {global_cell},{label},{rpm},"
                f"{'' if visc is None else visc},"
                f"{'' if a_val is None else a_val},"
                f"{'' if b_val is None else b_val},"
                f"{'' if r2_val is None else r2_val},"
                f"{cell_regime},"
                f"{'' if cell_n is None else cell_n},"
                f"{result.get('n_points_used', 0)},"
                f"{bool(result.get('success'))}",
            ])
    csv_writer.writerow([])


PARTIAL_TERMINATION_REASONS = frozenset({"user_stop", "manual_terminate"})


def is_partial_termination(reason: str) -> bool:
    """True when a cell ended before completing its full Z sweep."""
    return str(reason or "").strip().lower() in PARTIAL_TERMINATION_REASONS


def _z_keys_from_cell_data(cell_data: dict) -> List[float]:
    """Numeric Z-height keys from a cell's all_data entry (excludes metadata)."""
    out: List[float] = []
    for key in cell_data.keys():
        if isinstance(key, str):
            continue
        try:
            out.append(float(key))
        except (TypeError, ValueError):
            continue
    return out


def count_z_levels(all_data: Dict, cell_id: int) -> int:
    """Count Z levels with structured data for a cell in all_data."""
    cell_data = all_data.get(cell_id)
    if cell_data is None:
        try:
            cell_data = all_data.get(int(cell_id))
        except (TypeError, ValueError):
            cell_data = None
    if not isinstance(cell_data, dict):
        return 0
    return len(_z_keys_from_cell_data(cell_data))


def extract_latest_points_from_all_data(
    all_data: Dict,
    cell_ids: List[int],
    run_start_ts: Optional[float] = None,
) -> List[Dict]:
    """
    Extract the latest measurement per Z×RPM from all_data for experiment history.
    """
    points: List[Dict] = []
    for cell_id in cell_ids:
        cell_data = all_data.get(cell_id)
        if cell_data is None:
            try:
                cell_data = all_data.get(int(cell_id))
            except (TypeError, ValueError):
                cell_data = None
        if not isinstance(cell_data, dict):
            continue
        for z_height in sorted(_z_keys_from_cell_data(cell_data), reverse=True):
            rpm_data = cell_data.get(z_height)
            if not isinstance(rpm_data, dict):
                continue
            for rpm in sorted(k for k in rpm_data.keys() if k not in _RPM_DATA_META_KEYS):
                measurements = rpm_data.get(rpm)
                if not measurements:
                    continue
                latest = measurements[-1]
                torque_percent = float(latest.get("torque_percent") or 0)
                rpm_f = float(rpm)
                rotational_drag = abs(torque_percent) / rpm_f if rpm_f > 0 else 0.0
                ts = latest.get("timestamp")
                if ts is None:
                    elapsed = latest.get("elapsed_time")
                    if run_start_ts is not None and elapsed is not None:
                        try:
                            ts = float(run_start_ts) + float(elapsed)
                        except (TypeError, ValueError):
                            ts = time.time()
                    else:
                        ts = time.time()
                else:
                    try:
                        ts = float(ts)
                    except (TypeError, ValueError):
                        ts = time.time()
                points.append({
                    "timestamp": ts,
                    "cell_id": int(cell_id),
                    "height": float(z_height),
                    "torque_percent": torque_percent,
                    "rotational_drag": rotational_drag,
                    "rpm": rpm_f,
                    "is_final_save": True,
                })
    return points


def _finalize_regular_experiment_run(
    all_data: Dict,
    timestamp: str,
    mode: str,
    run_experiment_name: str,
    termination_by_cell: Dict[int, str],
    completed_cells: List[int],
    selected_cells: List[int],
    run_ended_early: bool = False,
    default_termination: str = "normal",
) -> Optional[str]:
    """Sync review state, open review modal, or auto-save when review is not needed."""
    partial_by_cell = {
        str(int(k)): is_partial_termination(v)
        for k, v in termination_by_cell.items()
    }
    if not run_ended_early:
        run_ended_early = any(partial_by_cell.values()) or len(completed_cells) < len(selected_cells)

    web_interface.sync_experiment_review_cells_from_run(
        all_data,
        termination_by_cell,
        default_termination=default_termination,
    )
    web_interface.set_experiment_review_run_context(
        all_data,
        timestamp,
        mode,
        run_experiment_name,
        termination_by_cell=termination_by_cell,
        completed_cells=completed_cells,
        partial_by_cell=partial_by_cell,
        run_ended_early=run_ended_early,
        selected_cell_count=len(selected_cells),
    )
    if web_interface.open_experiment_review_if_needed():
        if run_ended_early:
            web_interface.update_status(
                "Run ended early — review experiment data (Save or Discard each cell)"
            )
        else:
            web_interface.update_status(
                "Run finished — review experiment data (Save or Discard each cell)"
            )
        return None

    web_interface.update_status("Saving final results...")
    csv_filename = save_dynamic_analysis_data(
        all_data,
        timestamp,
        mode,
        run_experiment_name,
        termination_by_cell=termination_by_cell,
        partial=run_ended_early,
        completed_cells=completed_cells,
    )
    maybe_save_timeseries_data(
        all_data,
        timestamp,
        mode,
        run_experiment_name,
        termination_by_cell=termination_by_cell,
        partial=run_ended_early,
        completed_cells=completed_cells,
    )
    print(f"\nFINAL RESULTS SAVED TO: {csv_filename}")
    web_interface.update_status("Experiment completed successfully")
    return csv_filename


def save_partial_data(all_data: Dict[int, Dict[float, Dict[float, Optional[List[Dict]]]]],
                     timestamp: str, mode: str, completed_cells: List[int], experiment_name: str,
                     termination_by_cell: Optional[Dict[int, str]] = None) -> str:
    """Deprecated wrapper — use save_dynamic_analysis_data(..., partial=True)."""
    csv_path = save_dynamic_analysis_data(
        all_data,
        timestamp,
        mode,
        experiment_name,
        termination_by_cell=termination_by_cell,
        partial=True,
        completed_cells=completed_cells,
    )
    maybe_save_timeseries_data(
        all_data,
        timestamp,
        mode,
        experiment_name,
        termination_by_cell=termination_by_cell,
        partial=True,
        completed_cells=completed_cells,
    )
    return csv_path


def save_dynamic_analysis_data(all_data: Dict[int, Dict[float, Dict[float, Optional[List[Dict]]]]],
                              timestamp: str, mode: str, experiment_name: str,
                              termination_by_cell: Optional[Dict[int, str]] = None,
                              partial: bool = False,
                              completed_cells: Optional[List[int]] = None) -> str:
    """Save dynamic analysis data — latest measurement per Z×RPM."""
    if not all_data:
        print("No data collected to save.")
        return ""

    slug = _sanitize_experiment_slug(experiment_name)
    if partial:
        print(f"\nSAVING PARTIAL RESULTS...")
        if completed_cells is not None:
            print(f"Completed cells: {completed_cells}")
        csv_filename = f"dynamic_analysis_{slug}_{mode}_PARTIAL_{timestamp}.csv"
    else:
        csv_filename = f"dynamic_analysis_{slug}_{mode}_{timestamp}.csv"

    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)

        # Write metadata header
        if partial:
            csv_writer.writerow([f"# Dynamic Analysis - Mode: {mode.upper()} (PARTIAL RESULTS)"])
        else:
            csv_writer.writerow([f"# Dynamic Analysis - Mode: {mode.upper()}"])
        csv_writer.writerow([f"# Experiment Name: {experiment_name}"])
        csv_writer.writerow([f"# Test RPMs (global fallback): {TEST_RPMS}"])
        if TESTING_MODE == "custom" and CELL_RPM_MAP:
            csv_writer.writerow([f"# Per-cell RPM overrides: {CELL_RPM_MAP}"])
        if CELL_CONTENT_MAP:
            csv_writer.writerow([f"# Per-cell sample labels: {CELL_CONTENT_MAP}"])
        csv_writer.writerow([f"# Timestamp: {timestamp}"])
        csv_writer.writerow([f"# Cell numbering: Row 1 = cells 1-6, Row 2 = cells 7-12, Row 3 = cells 13-18"])
        if partial and completed_cells is not None:
            csv_writer.writerow([f"# Completed cells: {completed_cells}"])
        csv_writer.writerow([f"# Feedback Control: {'ENABLED' if FEEDBACK_CONTROL_ENABLED else 'DISABLED'}"])
        if FEEDBACK_CONTROL_ENABLED:
            csv_writer.writerow([f"# Feedback R2 Thresholds: Drag = {R2_DRAG_MIN}, CV = {R2_CV_MIN}, Slope = {R2_SLOPE_MIN}, Confidence = {HIT_POINT_CONFIDENCE_THRESHOLD}"])
            csv_writer.writerow([f"# Confidence Weights: 2nd-Deriv(Drag/CV/Slope) = {WEIGHT_2ND_DERIV_DRAG}/{WEIGHT_2ND_DERIV_CV}/{WEIGHT_2ND_DERIV_SLOPE}, R2(Drag/CV/Slope) = {WEIGHT_R2_DRAG}/{WEIGHT_R2_CV}/{WEIGHT_R2_SLOPE}"])
        if LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED:
            csv_writer.writerow([
                f"# Low-torque liquid-contact hunt: per RPM at each Z, skip RPM when first sample at "
                f"elapsed >= {SAMPLE_INTERVAL:.1f}s is < "
                f"{LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT:.2f}% (regular runs only); "
                f"skipped RPM rows use {_liquid_skip_torque_label(LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT)} "
                "and SKIPPED metrics"
            ])
        if partial:
            csv_writer.writerow([
                "# WARNING: Experiment was terminated early - these are partial results"
            ])
        _append_discovery_csv_metadata(csv_writer)
        _append_predicted_viscosity_csv_metadata(csv_writer)
        _append_cell_termination_metadata(csv_writer, all_data, termination_by_cell)

        csv_writer.writerow(SUMMARY_CSV_HEADERS)

        for global_cell in sorted(all_data.keys()):
            row_number, local_cell = global_cell_to_row_and_local(global_cell)
            cell_data = all_data[global_cell]
            z_heights = sorted(_z_keys_from_cell_data(cell_data), reverse=True)
            
            for z_height in z_heights:
                if z_height in cell_data:
                    rpm_data = cell_data[z_height]
                    liquid_probe = bool(rpm_data.get("_liquid_skip_probe_at_z"))
                    tlab = rpm_data.get(
                        "_liquid_skip_torque_label",
                        _liquid_skip_torque_label(LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT),
                    )
                    metrics_data = cell_data[z_height].get("_metrics", {})
                    for rpm in sorted(k for k in rpm_data.keys() if k not in _RPM_DATA_META_KEYS):
                        measurements = rpm_data.get(rpm)
                        if measurements is None:
                            if liquid_probe:
                                csv_writer.writerow(
                                    _liquid_skip_csv_row(
                                        row_number, global_cell, z_height, rpm, tlab
                                    )
                                )
                            continue
                        if measurements is not None:
                            rpm_metrics = metrics_data.get(rpm, {})
                            hit_detected = bool(rpm_metrics.get('Hit_Detected', False))

                            # Use LATEST measurement only (as requested by user)
                            latest_measurement = measurements[-1]
                            torque_percent = latest_measurement['torque_percent']
                            rotational_drag = abs(torque_percent) / rpm if rpm > 0 else float('inf')

                            csv_writer.writerow([
                                str(row_number),
                                str(global_cell),
                                CELL_CONTENT_MAP.get(global_cell, ''),
                                f"{z_height:.3f}",
                                f"{rpm:.1f}",
                                f"{latest_measurement['elapsed_time']:.2f}",
                                f"{latest_measurement['torque_percent']:.3f}",
                                f"{rotational_drag:.6f}",
                                str(hit_detected),
                            ])

    if partial:
        print(f"Partial results saved to: {csv_filename}")
    else:
        print(f"All data saved to: {csv_filename}")
    return csv_filename


def save_timeseries_data(
    all_data: Dict[int, Dict[float, Dict[float, Optional[List[Dict]]]]],
    timestamp: str,
    mode: str,
    experiment_name: str,
    termination_by_cell: Optional[Dict[int, str]] = None,
    partial: bool = False,
    completed_cells: Optional[List[int]] = None,
) -> str:
    """Save every collected sample (one row per dwell reading) to a separate CSV."""
    if not all_data:
        return ""

    slug = _sanitize_experiment_slug(experiment_name)
    if partial:
        csv_filename = f"dynamic_analysis_{slug}_{mode}_PARTIAL_{timestamp}_timeseries.csv"
    else:
        csv_filename = f"dynamic_analysis_{slug}_{mode}_{timestamp}_timeseries.csv"

    with open(csv_filename, "w", newline="", encoding="utf-8") as csvfile:
        csv_writer = csv.writer(csvfile)
        if partial:
            csv_writer.writerow([f"# Timeseries - Mode: {mode.upper()} (PARTIAL RESULTS)"])
        else:
            csv_writer.writerow([f"# Timeseries - Mode: {mode.upper()}"])
        csv_writer.writerow([f"# Experiment Name: {experiment_name}"])
        csv_writer.writerow([f"# Timestamp: {timestamp}"])
        csv_writer.writerow(["# Save all sample data: ENABLED"])
        csv_writer.writerow([f"# Sample interval (s): {SAMPLE_INTERVAL:.3f}"])
        csv_writer.writerow([f"# Measurement duration (s): {MEASUREMENT_DURATION:.3f}"])
        if partial and completed_cells is not None:
            csv_writer.writerow([f"# Completed cells: {completed_cells}"])
        if partial:
            csv_writer.writerow([
                "# WARNING: Experiment was terminated early - these are partial results"
            ])
        _append_cell_termination_metadata(csv_writer, all_data, termination_by_cell)

        csv_writer.writerow(TIMESERIES_CSV_HEADERS)

        for global_cell in sorted(all_data.keys()):
            row_number, _local_cell = global_cell_to_row_and_local(global_cell)
            cell_data = all_data[global_cell]
            z_heights = sorted(_z_keys_from_cell_data(cell_data), reverse=True)
            for z_height in z_heights:
                rpm_data = cell_data.get(z_height)
                if not isinstance(rpm_data, dict):
                    continue
                for rpm in sorted(k for k in rpm_data.keys() if k not in _RPM_DATA_META_KEYS):
                    measurements = rpm_data.get(rpm)
                    if not measurements:
                        continue
                    for sample in measurements:
                        try:
                            torque_percent = float(sample.get("torque_percent", 0))
                            elapsed = float(sample.get("elapsed_time", 0))
                        except (TypeError, ValueError):
                            continue
                        rpm_f = float(rpm)
                        rotational_drag = abs(torque_percent) / rpm_f if rpm_f > 0 else 0.0
                        csv_writer.writerow([
                            str(row_number),
                            str(global_cell),
                            CELL_CONTENT_MAP.get(global_cell, ""),
                            f"{float(z_height):.3f}",
                            f"{rpm_f:.1f}",
                            f"{elapsed:.2f}",
                            f"{torque_percent:.3f}",
                            f"{rotational_drag:.6f}",
                        ])

    print(f"Timeseries data saved to: {csv_filename}")
    return csv_filename


def maybe_save_timeseries_data(
    all_data: Dict,
    timestamp: str,
    mode: str,
    experiment_name: str,
    termination_by_cell: Optional[Dict[int, str]] = None,
    partial: bool = False,
    completed_cells: Optional[List[int]] = None,
    save_all: Optional[bool] = None,
) -> str:
    """Write timeseries CSV when save-all mode is enabled; never raises."""
    enabled = SAVE_ALL_SAMPLE_DATA if save_all is None else bool(save_all)
    if not enabled or not all_data:
        return ""
    try:
        return save_timeseries_data(
            all_data,
            timestamp,
            mode,
            experiment_name,
            termination_by_cell=termination_by_cell,
            partial=partial,
            completed_cells=completed_cells,
        )
    except Exception as e:
        print(f"Warning: Failed to save timeseries CSV: {e}")
        return ""


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
        web_interface.configure_pump_connection(ESP32_PORT, ESP32_BAUD, PUMP_VIRTUAL)
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
            cnc.should_abort = web_interface.should_stop
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
        termination_by_cell: Dict[int, str] = {}
        active_threads: List[threading.Thread] = []
        global CELL_VISCOSITY_RESULTS
        CELL_VISCOSITY_RESULTS = {}
        
        try:
            print(f"\nStarting dynamic analysis...")
            print(f"Experiment name: {run_experiment_name}")
            print(f"Testing {len(selected_cells)} cells with {len(TEST_RPMS)} RPMs per Z-position")
        
            # Go through each selected cell
            calibration_cells: dict[int, float] = {}  # Populated during calibration runs
            run_ended_early = False
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
                    # Use resolved run mode (set once at run start) to avoid accidental drift in per-cell flags.
                    is_calibration_like_run = mode in ("calibration", "recalibration")
                    discovery_handoff_z: Optional[float] = None
                    skip_initial_safe_move = False
                    discovery_rpm_for_landing: Optional[float] = None

                    if DISCOVERY_MODE_ENABLED and not is_calibration_like_run:
                        try:
                            from discovery_runner import run_discovery_for_cell

                            eta_guess = DISCOVERY_ETA_GUESS_MAP.get(global_cell)
                            if eta_guess is not None and eta_guess <= 0:
                                eta_guess = None
                            web_interface.update_status(
                                f"Discovery: selecting RPM for Cell {global_cell}"
                            )
                            discovery_result, discovered_rpms = run_discovery_for_cell(
                                global_cell,
                                cnc,
                                client,
                                eta_guess=eta_guess,
                                material_label=CELL_CONTENT_MAP.get(global_cell),
                                move_fn=move_to_cell_position,
                                measure_fn=measure_torque_at_rpm,
                                row_resolver=global_cell_to_row_and_local,
                                measure_module=sys.modules[__name__],
                                probe_duration_s=DISCOVERY_PROBE_DURATION_S,
                                duck_torque_pct=DISCOVERY_DUCK_TORQUE_PCT,
                                web_emit=True,
                            )
                            if not discovered_rpms:
                                status = discovery_result.get("status", "unknown")
                                print(
                                    f"  Discovery failed for Cell {global_cell}: {status} "
                                    f"— skipping cell"
                                )
                                web_interface.update_status(
                                    f"Cell {global_cell}: discovery failed ({status}) — skipped"
                                )
                                termination_by_cell[global_cell] = f"discovery_{status}"
                                continue
                            try:
                                from discovery_runner import discovery_result_to_web_payload

                                web_interface.record_discovery_result(
                                    global_cell,
                                    discovery_result_to_web_payload(global_cell, discovery_result),
                                )
                            except Exception:
                                pass
                            cell_rpms = discovered_rpms
                            discovery_rpm_for_landing = float(cell_rpms[0])
                            discovery_handoff_z = discovery_result.get("target_z_mm")
                            skip_initial_safe_move = True
                            print(
                                f"  Discovery converged for Cell {global_cell}: "
                                f"RPM={cell_rpms[0]:.2f}, "
                                f"status={discovery_result.get('status')}"
                            )
                            if discovery_handoff_z is not None:
                                print(
                                    f"  Discovery handoff: in-sample Z-scan from "
                                    f"Z={float(discovery_handoff_z):.3f}, "
                                    f"RPM={cell_rpms[0]:.2f}, no safe retract"
                                )
                            if DISCOVERY_HANDOFF_PAUSE_S > 0:
                                web_interface.update_status(
                                    f"Discovery complete — pausing {DISCOVERY_HANDOFF_PAUSE_S:.0f}s "
                                    f"before Z-scan for Cell {global_cell}"
                                )
                                sleep_with_stop(DISCOVERY_HANDOFF_PAUSE_S)
                        except Exception as discovery_exc:
                            print(
                                f"  Discovery error for Cell {global_cell}: {discovery_exc}"
                            )
                            traceback.print_exc()
                            web_interface.update_status(
                                f"Cell {global_cell}: discovery error — skipped"
                            )
                            termination_by_cell[global_cell] = "discovery_error"
                            continue

                    print(f"  RPMs for Cell {global_cell}: {cell_rpms}")
                    
                    # Determine status message and custom starting Z for recalibration / discovery handoff
                    custom_z = None
                    if RECALIBRATE_INDIVIDUAL_CELLS:
                        # Check if a custom starting Z is provided for this cell
                        custom_z = RECALIBRATION_CELLS.get(global_cell, None)
                        if custom_z is not None:
                            web_interface.update_status(f"Recalibrating cell {i+1}/{len(selected_cells)} (Cell {global_cell}, starting at Z={custom_z:.3f})")
                        else:
                            web_interface.update_status(f"Recalibrating cell {i+1}/{len(selected_cells)} (Cell {global_cell})")
                    elif skip_initial_safe_move and discovery_handoff_z is not None:
                        custom_z = float(discovery_handoff_z)
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
                        custom_starting_z=custom_z,  # Pass custom starting Z if in recalibration or discovery handoff
                        skip_initial_safe_move=skip_initial_safe_move,
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
                    termination_by_cell[global_cell] = str(feedback_summary.get("exit_reason", "normal"))
                    print(f"Cell {global_cell} testing completed")

                    if (
                        DISCOVERY_MODE_ENABLED
                        and discovery_rpm_for_landing is not None
                        and not is_calibration_like_run
                    ):
                        _merge_discovery_landing_after_descent(
                            global_cell,
                            cell_data,
                            discovery_rpm_for_landing,
                            termination_by_cell[global_cell],
                        )

                    if is_calibration_like_run:
                        # Extract rough hitpoint for post-run review (not auto-saved to disk)
                        rough_z = extract_rough_hitpoint(cell_data)
                        if rough_z is not None:
                            print(f"  Calibration: Cell {global_cell} rough hitpoint = {rough_z:.3f}")
                            calibration_cells[global_cell] = rough_z
                            snapshot = [
                                m for m in web_interface.measurement_data
                                if isinstance(m, dict) and int(m.get("cell_id", -1)) == int(global_cell)
                            ]
                            web_interface.add_calibration_review_cell(
                                global_cell,
                                rough_z,
                                snapshot,
                                calibration_offset=CALIBRATION_OFFSET,
                            )
                        else:
                            print(f"  Calibration: Cell {global_cell} — no reliable hitpoint found, skipping")
                        # Track calibration/recalibration progress for live cross-device UI sync.
                        web_interface.add_completed_cell(global_cell, termination_reason=termination_by_cell.get(global_cell, "normal"))
                        if CALIBRATION_MODE:
                            web_interface.update_status(f"Calibrated cell {i+1}/{len(selected_cells)} (Cell {global_cell})")
                        else:
                            web_interface.update_status(f"Recalibrated cell {i+1}/{len(selected_cells)} (Cell {global_cell})")
                        # NO washing in calibration/recalibration mode — move directly to next cell
                    else:
                        cell_term = termination_by_cell.get(global_cell, "normal")
                        snapshot = [
                            m for m in web_interface.measurement_data
                            if isinstance(m, dict) and int(m.get("cell_id", -1)) == int(global_cell)
                        ]
                        web_interface.add_experiment_review_cell(
                            global_cell,
                            snapshot,
                            termination_reason=cell_term,
                            is_partial=is_partial_termination(cell_term),
                            z_level_count=count_z_levels(all_data, global_cell),
                        )
                        web_interface.add_completed_cell(
                            global_cell,
                            termination_reason=cell_term,
                        )
                        if normalize_viscosity_prediction_mode(VISCOSITY_PREDICTION_MODE) != "off":
                            run_predicted_viscosity_for_cell(
                                global_cell, cell_rpms, cell_data, feedback_summary
                            )
                        if cell_term == "user_stop":
                            run_ended_early = True
                            print(
                                f"Experiment stop requested during Cell {global_cell} — "
                                "ending run after saving cell data"
                            )
                            break
                        # Normal run: perform washing only after successful CNC retract
                        if pump and feedback_summary.get("cnc_retracted_ok"):
                            perform_washing_sequence(cnc, pump, global_cell, fill_thread=_fill_thread)
                        elif pump:
                            print(
                                f"Wash skipped for Cell {global_cell}: CNC safe retract failed "
                                f"(exit_reason={feedback_summary.get('exit_reason')})"
                            )
                            web_interface.update_status(
                                f"Cell {global_cell}: wash skipped — CNC retract failed"
                            )
                        else:
                            print(f"Warning: Pump not available, skipping washing for Cell {global_cell}")

                    print(f"Cell {global_cell} fully completed")

                except Exception as e:
                    print(f"Error during testing of Cell {global_cell}: {e}")
                    traceback.print_exc()
                    if CALIBRATION_MODE or RECALIBRATE_INDIVIDUAL_CELLS:
                        print("Saving partial results and terminating...")
                        if all_data:
                            save_partial_data(
                                all_data,
                                timestamp,
                                mode,
                                completed_cells,
                                run_experiment_name,
                                termination_by_cell=termination_by_cell,
                            )
                    raise  # Re-raise to trigger cleanup
        
            # All testing completed successfully
            print(f"\nAll dynamic analysis completed successfully!")
            print(f"Tested {len(completed_cells)} cells: {completed_cells}")
            print(f"Saving final results...")
            
            if CALIBRATION_MODE or RECALIBRATE_INDIVIDUAL_CELLS:
                web_interface.update_status("Saving final results...")
                csv_filename = save_dynamic_analysis_data(
                    all_data,
                    timestamp,
                    mode,
                    run_experiment_name,
                    termination_by_cell=termination_by_cell,
                )
                print(f"\nFINAL RESULTS SAVED TO: {csv_filename}")
                print(f"\nDynamic analysis experiment completed successfully at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                review_type = "recalibration" if RECALIBRATE_INDIVIDUAL_CELLS else "calibration"
                if web_interface.open_calibration_review_if_needed(
                    review_type, calibration_offset=CALIBRATION_OFFSET
                ):
                    web_interface.update_status(
                        "Run finished — review calibration data (Save or Discard each cell)"
                    )
                else:
                    web_interface.update_status("Experiment completed successfully")
            else:
                _finalize_regular_experiment_run(
                    all_data,
                    timestamp,
                    mode,
                    run_experiment_name,
                    termination_by_cell,
                    completed_cells,
                    selected_cells,
                    run_ended_early=run_ended_early,
                )
                print(f"\nDynamic analysis experiment completed successfully at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        except KeyboardInterrupt:
            print(f"\nExperiment interrupted by user")
            web_interface.update_status("Experiment interrupted by user")
            if CALIBRATION_MODE or RECALIBRATE_INDIVIDUAL_CELLS:
                if all_data:
                    print("Saving partial results...")
                    save_partial_data(
                        all_data,
                        timestamp,
                        mode,
                        completed_cells,
                        run_experiment_name,
                        termination_by_cell=termination_by_cell,
                    )
                review_type = "recalibration" if RECALIBRATE_INDIVIDUAL_CELLS else "calibration"
                web_interface.open_calibration_review_if_needed(
                    review_type, calibration_offset=CALIBRATION_OFFSET
                )
            else:
                _finalize_regular_experiment_run(
                    all_data,
                    timestamp,
                    mode,
                    run_experiment_name,
                    termination_by_cell,
                    completed_cells,
                    selected_cells,
                    run_ended_early=True,
                    default_termination="user_stop",
                )
        except Exception as e:
            print(f"Critical error during experiment: {e}")
            traceback.print_exc()
            web_interface.update_status(f"Error: {str(e)}")
            if CALIBRATION_MODE or RECALIBRATE_INDIVIDUAL_CELLS:
                if all_data:
                    print("Saving partial results...")
                    save_partial_data(
                        all_data,
                        timestamp,
                        mode,
                        completed_cells,
                        run_experiment_name,
                        termination_by_cell=termination_by_cell,
                    )
                review_type = "recalibration" if RECALIBRATE_INDIVIDUAL_CELLS else "calibration"
                web_interface.open_calibration_review_if_needed(
                    review_type, calibration_offset=CALIBRATION_OFFSET
                )
            else:
                _finalize_regular_experiment_run(
                    all_data,
                    timestamp,
                    mode,
                    run_experiment_name,
                    termination_by_cell,
                    completed_cells,
                    selected_cells,
                    run_ended_early=True,
                    default_termination="error",
                )
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
                    stop_requested = web_interface.should_stop()
                    # #region agent log
                    _agent_debug_log(
                        hypothesis_id="H3",
                        location="all_cells_with_rotational_drag_feedback.py:cleanup",
                        message="Cleanup CNC decision",
                        data={"stop_requested": stop_requested},
                    )
                    # #endregion agent log
                    if stop_requested:
                        web_interface.update_status("Stop requested — retracting to safe Z then homing")
                        web_interface.clear_stop_request()
                    web_interface.update_status("Cleanup: homing CNC")
                    try:
                        cnc.move_to_point_safe(0, 0, 0, speed=3000, allow_abort=False)
                        web_interface.update_position(0, 0, 0)
                        print("Cleanup: CNC move_to_point_safe(0,0,0) complete.")
                    except CNCMotionError as e:
                        print(f"Cleanup: safe move to origin failed ({e}), trying home()...")
                        try:
                            cnc.home(allow_abort=False)
                            web_interface.update_position(0, 0, 0)
                        except CNCMotionError as home_error:
                            print(f"Cleanup: CNC home fallback failed ({home_error})")
                    web_interface.update_status("Cleanup: CNC homed")
            except Exception as e:
                print(f"Cleanup: CNC shutdown error: {e}")
        print("Hardware cleanup completed")
        web_interface.update_status("Ready - Configure next run and press Start")
        # Continue the loop to wait for next start command

if __name__ == "__main__":
    main()
"""Runtime configuration for viscometry experiment runs."""

from typing import Dict, List, Optional

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

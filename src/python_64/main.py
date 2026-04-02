# src/python_64/main.py
import pathlib
import time
from cnc_controller import CNC_Machine
from move_to_locations import PumpESP32, go_to_sample, wash1, wash2, wash3
from viscometer_client import ViscometerClient
from analysis_methods import run_single_rpm, run_dynamic_analysis, run_bisection
from z_calibration import get_latest_z_contact_values

# Paths & device settings 
PYTHON32    = ".\\.venv32\\Scripts\\python.exe"  
VISCO_PORT  = "COM6"
VISCO_BAUD  = 115200
VISCO_TOUT  = 1.0
SPINDLE_K   = 992.47
ANALYSIS_MODE = "single"  # "single" | "dynamic" | "bisection"
SAMPLE_RACK  = "main_rack_A"
SAMPLE_RANGE = range(0, 1)     # 6 cells: 0, 1, 2, 3, 4, 5
Z_OFFSET_MM = 0.090            # 90μm offset above contact point
USE_CALIBRATED_Z = True        # Use calibrated Z values from z_calibration.py     
# Wash / Pump settings # ENABLE_WASH  = False # ESP32_PORT = "COM4"  #ESP32_BAUD = 9600#PUMP_VIRTUAL = True             
PAUSE_AFTER_HOME = 0.2
PAUSE_AFTER_MOVE = 0.1

def _root_dir() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]

def _worker_path() -> pathlib.Path:
    return _root_dir() / "src" / "python_32" / "worker32.py"

def _results_dir() -> pathlib.Path:
    d = _root_dir() / "results"
    d.mkdir(parents=True, exist_ok=True)
    return d


def main():
    root = _root_dir()
    results_root = _results_dir()
    worker = _worker_path()
    
    cnc = CNC_Machine(virtual=False)
    cnc.home()
    time.sleep(PAUSE_AFTER_HOME)
    
    # Load calibrated Z values if enabled
    z_contact_array = None
    if USE_CALIBRATED_Z:
        try:
            z_contact_array, _, _ = get_latest_z_contact_values()
            print(f"Loaded calibrated Z-values: {z_contact_array}")
        except Exception as e:
            print(f"Warning: Could not load calibrated Z-values: {e}")
            print("Falling back to YAML Z-values")
            z_contact_array = None
    
    #pump = None
    #if ENABLE_WASH:
     #   pump = PumpESP32(port=ESP32_PORT, baud=ESP32_BAUD, virtual=PUMP_VIRTUAL)
      #  pump.open()

    client = ViscometerClient(PYTHON32, worker)
    try:
        client.init(port=VISCO_PORT, baud=VISCO_BAUD, timeout=VISCO_TOUT, spindle_k=SPINDLE_K)

        for i in SAMPLE_RANGE:
            sample_dir = results_root / f"sample_{i:03d}"
            sample_dir.mkdir(parents=True, exist_ok=True)
            
            # Move to sample using calibrated Z if available
            if z_contact_array and i < len(z_contact_array):
                # Use calibrated Z position with offset
                x, y, _ = cnc.get_location_position(SAMPLE_RACK, i)  # Get X,Y from YAML, ignore Z
                z_calibrated = z_contact_array[i] + Z_OFFSET_MM
                print(f"[sample {i}] Moving to calibrated position: X={x}, Y={y}, Z={z_calibrated:.3f}")
                cnc.move_to_point_safe(x, y, z_calibrated, speed=3000)
            else:
                # Fallback to YAML positions
                print(f"[sample {i}] Using YAML position (fallback)")
                go_to_sample(cnc, rack=SAMPLE_RACK, idx=i, safe=True, wait_s=0)
            
            time.sleep(PAUSE_AFTER_MOVE)

            # Run the chosen viscometer analysis 
            if ANALYSIS_MODE == "single":
                csv_path = run_single_rpm(sample_dir, client)
            elif ANALYSIS_MODE == "dynamic":
                csv_path = run_dynamic_analysis(sample_dir, client)
            elif ANALYSIS_MODE == "bisection":
                csv_path = run_bisection(sample_dir, client)
            else:
                raise ValueError(f"Unknown ANALYSIS_MODE: {ANALYSIS_MODE}")
            print(f"[sample {i}] results -> {csv_path}")

            #wash sequence between samples 
           # if ENABLE_WASH and pump is not None:
            #  wash1(cnc, pump)# wash2(cnc, pump) # wash3(cnc, pump)
        cnc.home()

    finally:
        try:
            client.stop()
        except Exception:
            pass
        client.close()
        # Close pump if used
       # if pump is not None:
       #     try:
       #         pump.close()
        #    except Exception:
       #         pass

if __name__ == "__main__":
    main()

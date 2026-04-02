# z_calibration.py - Z-axis calibration for viscometer spindle contact detection
import time
import pathlib
import csv
import json
import glob
import os
import datetime
from cnc_controller import CNC_Machine
from viscometer_client import ViscometerClient

SAFE_Z = -64.400                # Safe Z height above the sample (mm)
Z_STEP_SIZE = -0.10            # Step size for Z descent (mm, negative = downward)
Z_FEED_RATE = 500               # Feed rate for Z descent (mm/min)
TORQUE_THRESHOLD = 0.5          # Torque threshold to detect contact (abs %)
MAX_Z_TRAVEL = -66.500          # Maximum Z travel from SAFE_Z (safety limit)
SETTLE_TIME = 0.5               # Time to wait after each Z move (seconds)
TORQUE_READ_TIMEOUT = 2.0       # Timeout for torque readings (seconds)
SPINDLE_SETTLE_TIME = 0.5       # Time after setting spindle speed to zero (seconds)
NUM_CELLS = 6                   # Number of cells to calibrate
#BASE_X = 10                      # X position for all cells (mm)
#BASE_X = 85                    # Row 1 = 10, ROW 2 = 85, Row 3 = 309
BASE_X = 309                     # ROW 3 = 309
BASE_Y = 62                     # Y position for first cell (mm)
Y_OFFSET = 67                   # Y offset between cells (mm)
PYTHON32 = ".\\.venv32\\Scripts\\python.exe"
VISCO_PORT = "COM6"
VISCO_BAUD = 115200
VISCO_TOUT = 1.0
SPINDLE_K = 992.47

# Move CNC to the specified (x, y) position and safe Z height
def move_to_cell(cnc: CNC_Machine, x: float, y: float, safe_z: float):
    print(f"Moving to cell position: X={x}, Y={y}, Z={safe_z}")
    cnc.move_to_point_safe(x, y, safe_z, speed=3000)
    time.sleep(1.0)

def find_hit_point_with_data_matrix(cnc: CNC_Machine, client: ViscometerClient, x: float, y: float, safe_z: float, cell_number: int, calibration_data: dict) -> float:
    current_z = safe_z
    total_z_movement = 0.0
    step_count = 0

    print(f"Starting Z calibration for Cell {cell_number} from Z={safe_z} with step size {Z_STEP_SIZE}mm...")
    
    # Set spindle speed to zero ONCE at the start of each cell calibration
    print("Setting spindle speed to zero...")
    try:
        client.set_speed(0)
        print("Spindle speed set to zero successfully")
    except Exception as e:
        print(f"ERROR setting spindle speed: {e}")
    time.sleep(SPINDLE_SETTLE_TIME)
    
    while current_z >= MAX_Z_TRAVEL: 
        # Move down one step
        current_z += Z_STEP_SIZE
        total_z_movement += Z_STEP_SIZE
        step_count += 1

        print(f"Cell {cell_number} - Step {step_count}: Moving to Z={current_z:.3f}")
        cnc.move_to_point(x, y, current_z, speed=Z_FEED_RATE)
        time.sleep(SETTLE_TIME)

        # Take torque reading with retry logic
        torque_reading_successful = False
        for attempt in range(1, 4):  # 3 attempts
            try:
                torque_data = client.read_single(timeout=TORQUE_READ_TIMEOUT)
                
                if torque_data:
                    torque_valid = torque_data.get("torque_valid", False)
                    torque_percent = torque_data.get("torque_percent")
                    
                    if torque_valid and torque_percent is not None:
                        abs_torque = abs(torque_percent)
                        print(f"Cell {cell_number} - Z={current_z:.3f}, Torque={torque_percent:.1f}%")
                        
                        # Record data to matrix
                        z_rounded = round(current_z, 3)
                        if z_rounded in calibration_data:
                            calibration_data[z_rounded][f"TC{cell_number}"] = round(torque_percent, 1)
                        
                        # Check if torque threshold is met
                        if abs_torque >= TORQUE_THRESHOLD:
                            print(f"Contact detected! Torque={torque_percent:.1f}% at Z={current_z:.3f}")
                            client.stop()
                            cnc.move_to_point(x, y, z=0, speed=3000)
                            time.sleep(1.0)
                            return current_z
                        
                        torque_reading_successful = True
                        break
                    else:
                        if attempt == 1:  # Only print details on first attempt
                            print(f"  Invalid torque: valid={torque_valid}, value={torque_percent:.1f}%")
                        
            except Exception as e:
                if attempt == 1:
                    print(f"  Torque read error: {e}")
            
            if attempt < 3:
                time.sleep(0.5)
        
        if not torque_reading_successful:
            print(f"  No valid torque at Z={current_z:.3f}")

    # If no contact detected within the limit
    print(f"Warning: No contact detected for Cell {cell_number} after {abs(MAX_Z_TRAVEL)}mm travel")
    
    # Move Z back up to Z=0 even if no contact detected
    print("Moving Z back up to Z=0...")
    cnc.move_to_point(x, y, z=0, speed=3000)
    time.sleep(1.0)
    
    return current_z

def calibrate_multiple_cells(cnc: CNC_Machine, client: ViscometerClient) -> tuple:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"z_calibration_data_{timestamp}.csv"
    
    # Pre-calculate all Z-heights based on parameters
    z_heights = []
    current_z = SAFE_Z
    while current_z >= MAX_Z_TRAVEL:
        z_heights.append(round(current_z, 3))
        current_z += Z_STEP_SIZE
    
    print(f"Pre-calculated {len(z_heights)} Z-height steps from {SAFE_Z} to {z_heights[-1]}")
    
    # Initialize data structure: {z_height: {cell1: torque, cell2: torque, ...}}
    calibration_data = {}
    for z in z_heights:
        calibration_data[z] = {f"TC{i}": "" for i in range(1, NUM_CELLS + 1)}
    
    # Initialize CSV with headers
    fieldnames = ["Z-Height"] + [f"TC{i}" for i in range(1, NUM_CELLS + 1)]
    
    calibrated_positions = {}
    
    print(f"Starting calibration for {NUM_CELLS} cells...")
    print(f"Data will be saved to: {csv_filename}")
    
    # Main calibration loop
    for cell in range(1, NUM_CELLS + 1):
        print(f"\n{'='*50}")
        print(f"CALIBRATING CELL {cell}")
        print(f"{'='*50}")
        
        # Calculate position for current cell
        y_position = BASE_Y + (cell - 1) * Y_OFFSET
        
        # Move to cell and perform calibration
        move_to_cell(cnc, BASE_X, y_position, SAFE_Z)
        calibrated_z = find_hit_point_with_data_matrix(cnc, client, BASE_X, y_position, SAFE_Z, cell, calibration_data)
        
        # Store the calibrated position
        calibrated_positions[f"Cell_{cell}"] = {
            "x": BASE_X,
            "y": y_position,
            "z_contact": calibrated_z
        }
        
        print(f"Cell {cell} completed - Contact Z: {calibrated_z:.3f}")
    
    # Write all data to CSV after collecting from all cells
    with open(csv_filename, 'w', newline='') as csvfile:
        csv_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        csv_writer.writeheader()
        
        # Write data in Z-height order
        for z in z_heights:
            row_data = {"Z-Height": f"{z:.3f}"}
            # Format torque values to 1 decimal place
            formatted_torque_data = {}
            for key, value in calibration_data[z].items():
                if value != "":  # Only format non-empty values
                    formatted_torque_data[key] = f"{value:.1f}"
                else:
                    formatted_torque_data[key] = value
            row_data.update(formatted_torque_data)
            csv_writer.writerow(row_data)
    
    # Extract Z-contact values as arrays for dynamic memory manipulation
    z_contact_values = []
    z_contact_dict = {}
    
    for cell_num in range(1, NUM_CELLS + 1):
        cell_key = f"Cell_{cell_num}"
        if cell_key in calibrated_positions:
            z_contact = calibrated_positions[cell_key]["z_contact"]
            z_contact_values.append(z_contact)
            z_contact_dict[f"cell_{cell_num}"] = z_contact
    
    # Save Z-contact values to multiple formats for easy access
    save_calibration_data(timestamp, z_contact_values, z_contact_dict, calibrated_positions)
    
    print(f"\nCalibration data saved to: {csv_filename}")
    print(f"\nZ-contact array: {z_contact_values}")
    
    return calibrated_positions, z_contact_values, z_contact_dict

def save_calibration_data(timestamp: str, z_contact_values: list, z_contact_dict: dict, calibrated_positions: dict):
    # Save as JSON file (human-readable, cross-platform, used by main.py)
    json_filename = f"z_contact_values_{timestamp}.json"
    with open(json_filename, 'w') as json_file:
        json.dump({
            "timestamp": timestamp,
            "num_cells": NUM_CELLS,
            "z_contact_array": z_contact_values,
            "z_contact_dict": z_contact_dict,
            "calibrated_positions": calibrated_positions
        }, json_file, indent=2)
    
    print(f"Z-contact values saved to: {json_filename}")

def load_z_contact_values(filename: str) -> tuple:
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Calibration file not found: {filename}")
    try:
        with open(filename, 'r') as f:
            data = json.load(f)   
        return (
            data["z_contact_array"],
            data["z_contact_dict"], 
            data["calibrated_positions"]
        )
        
    except Exception as e:
        raise ValueError(f"Error loading calibration file: {e}")

def get_latest_z_contact_values() -> tuple:
    # Find the most recent JSON file
    json_files = glob.glob("z_contact_values_*.json")
    if not json_files:
        raise FileNotFoundError("No calibration files found. Run z_calibration.py first.")
    
    # Get the most recent file
    latest_file = max(json_files, key=os.path.getctime)
    print(f"Loading latest calibration from: {latest_file}")
    
    return load_z_contact_values(latest_file)

def main():
    # Initialize hardware
    print("Initializing CNC machine...")
    cnc = CNC_Machine(virtual=False)
    cnc.home()

    # Create proper path to worker32.py
    worker_path = pathlib.Path(__file__).resolve().parents[0] / ".." / "python_32" / "worker32.py"
    print(f"Worker path: {worker_path}")
    client = ViscometerClient(PYTHON32, worker_path)
    print(f"Initializing viscometer on {VISCO_PORT} at {VISCO_BAUD} baud...")
    client.init(port=VISCO_PORT, baud=VISCO_BAUD, timeout=VISCO_TOUT, spindle_k=SPINDLE_K)
    print("Viscometer initialized successfully")
    
    # Give the viscometer extra time to initialize
    print("Waiting for viscometer to initialize...")
    time.sleep(3.0)
    
    # Test viscometer communication and check calibration
    print("Testing viscometer communication...")
    try:
        test_data = client.read_single(timeout=5.0)
        if test_data:
            torque_valid = test_data.get("torque_valid", False)
            torque_percent = test_data.get("torque_percent", 0)
            print(f"Viscometer test: valid={torque_valid}, torque={torque_percent:.1f}%")
            
            if not torque_valid:
                print("WARNING: Viscometer torque readings are invalid!")
                print("This usually means the viscometer needs to be calibrated/zeroed.")
                print("Please calibrate the viscometer before running this script.")
                print("Continuing anyway for testing...")
        else:
            print("WARNING: Viscometer test returned None")
    except Exception as e:
        print(f"WARNING: Viscometer test FAILED: {e}")
    print("Proceeding with calibration...")

    try:
        # Calibrate multiple cells and save data to CSV
        calibrated_positions, z_contact_array, z_contact_dict = calibrate_multiple_cells(cnc, client)

        print(f"\nAll calibrations complete!")
        print("Calibrated positions:")
        for cell_name, position in calibrated_positions.items():
            print(f"{cell_name}: X={position['x']}, Y={position['y']}, Z_contact={position['z_contact']:.3f}")
        
        # Return to home after calibration
        print("Returning to home position...")
        cnc.home()

    finally:
        client.stop()
        client.close()

if __name__ == "__main__":
    main()
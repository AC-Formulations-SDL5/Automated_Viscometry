import time
import pathlib
import csv
import json
import glob
import os
import datetime
import traceback
from typing import Dict, List, Optional, Tuple
from cnc_controller import CNC_Machine
from viscometer_client import ViscometerClient

SAFE_Z = -65.500    #-65.600                
Z_STEP_SIZE = -0.020        #-0.100            
Z_FEED_RATE = 500               
MAX_Z_TRAVEL = -66.800      #-66.700          
TORQUE_BREAK_THRESHOLD = 1000.0     #100.0   
SETTLE_TIME = 0.5               
TORQUE_READ_TIMEOUT = 2.0       
SPINDLE_SETTLE_TIME = 1.0      
NUM_CELLS = 1   #6                  
BASE_X = 85    #Row 2                  
BASE_Y = 62                    
Y_OFFSET = 67                  
PYTHON32 = ".\\.venv32\\Scripts\\python.exe"
VISCO_PORT = "COM6"
VISCO_BAUD = 115200
VISCO_TOUT = 1.0
SPINDLE_K = 992.47

# RPM Calibration Settings
TARGET_TORQUE_PERCENT = 50.0        # Target torque percentage
TORQUE_TOLERANCE = 5  #10.0             # ±20% tolerance around target
MIN_RPM = 0.1                       # Minimum RPM to test
MAX_RPM = 10.0 #100.0                     # Maximum RPM to test
RPM_SEARCH_STEP = 0.1 #0.5               # Initial RPM step size for search
RPM_PRECISION = 0.1 #0.1                 # Final RPM precision
MAX_SEARCH_ITERATIONS = 30 #50          # Maximum iterations to find target RPM

# Control Switches - Enable/Disable Safety Features
ENABLE_TORQUE_BREAK_THRESHOLD = True    # Enable/disable torque break threshold check
ENABLE_FIRST_RPM_CHECK = True           # Enable/disable first RPM critical check  
ENABLE_RESISTANCE_CHECK = True          # Enable/disable high resistance detection
ENABLE_MAX_RPM_LIMIT = True             # Enable/disable maximum RPM limit
ENABLE_Z_TRAVEL_LIMIT = True            # Enable/disable Z travel limit

DWELL_SECONDS = 2.0            
INTER_RPM_PAUSE = 1.0           

def move_to_cell_position(cnc: CNC_Machine, cell_number: int, z_height: float) -> Tuple[float, float, float]:
    x_pos = BASE_X
    y_pos = BASE_Y + (cell_number - 1) * Y_OFFSET
    print(f"Moving to Cell {cell_number}: X={x_pos}, Y={y_pos}, Z={z_height:.3f}")
    cnc.move_to_point_safe(x_pos, y_pos, z_height, speed=3000)
    time.sleep(SETTLE_TIME)
    return x_pos, y_pos, z_height

def measure_torque_at_rpm(client: ViscometerClient, rpm: float) -> Optional[float]:
    """Measure average torque at a specific RPM"""
    MEASUREMENT_DURATION = 5.0      # Increased for more accurate RPM searching
    SAMPLE_INTERVAL = 1.0           # Reduced sample interval

    try:
        # Set spindle speed
        client.set_speed(rpm)
        time.sleep(DWELL_SECONDS)  # Allow spindle to settle at new RPM
        
        # Collect torque measurements over duration
        measurements = []
        start_time = time.time()
        next_sample_time = start_time + SAMPLE_INTERVAL
        
        while time.time() - start_time < MEASUREMENT_DURATION:
            current_time = time.time()
            
            if current_time >= next_sample_time:
                try:
                    data = client.read_single(timeout=TORQUE_READ_TIMEOUT)
                    if data and data.get("torque_valid") and data.get("torque_percent") is not None:
                        measurements.append(data["torque_percent"])
                    next_sample_time += SAMPLE_INTERVAL
                except Exception as e:
                    print(f"      Measurement error at RPM {rpm}: {e}")
            
            time.sleep(0.1)
        
        # Stop spindle after measurement
        client.stop()
        time.sleep(INTER_RPM_PAUSE)
        
        # Calculate average torque
        if measurements:
            avg_torque = sum(measurements) / len(measurements)
            print(f"      RPM {rpm:.2f}: {len(measurements)} samples, Avg torque: {avg_torque:.2f}%")
            return round(avg_torque, 2)
        else:
            print(f"      RPM {rpm:.2f}: No valid measurements collected")
            return None
            
    except Exception as e:
        print(f"      Error measuring torque at RPM {rpm:.2f}: {e}")
        try:
            client.stop()
        except:
            pass
        return None

def find_target_rpm_at_z(client: ViscometerClient, z_height: float) -> Tuple[Optional[float], Optional[float], bool]:
    """Find RPM that produces target torque (50% ± 20%) at specific Z-height using binary search approach"""
    print(f"    Finding RPM for {TARGET_TORQUE_PERCENT}%±{TORQUE_TOLERANCE}% torque at Z={z_height:.3f}")
    
    target_min = TARGET_TORQUE_PERCENT - TORQUE_TOLERANCE
    target_max = TARGET_TORQUE_PERCENT + TORQUE_TOLERANCE
    
    # Check safety thresholds if enabled
    should_break_cell = False
    
    # First, test at minimum RPM to check if it's even feasible
    print(f"      Testing minimum RPM {MIN_RPM:.2f} for feasibility...")
    min_torque = measure_torque_at_rpm(client, MIN_RPM)
    
    if min_torque is None:
        if ENABLE_RESISTANCE_CHECK:
            print(f"      RESISTANCE: Min RPM {MIN_RPM:.2f} returned invalid torque (high resistance)")
            return None, None, False
        else:
            print(f"      WARNING: Min RPM {MIN_RPM:.2f} returned invalid torque (resistance check disabled)")
    elif ENABLE_FIRST_RPM_CHECK and abs(min_torque) >= TORQUE_BREAK_THRESHOLD:
        print(f"      CRITICAL: Min RPM {MIN_RPM:.2f} exceeded threshold with {min_torque:.2f}% - breaking cell")
        return None, None, True
    elif min_torque is not None and min_torque > target_max:
        print(f"      INFO: Min RPM {MIN_RPM:.2f} already gives {min_torque:.2f}% (above target range)")
        # Target torque achieved at minimum RPM
        return MIN_RPM, min_torque, False
    
    # Binary search approach to find target RPM
    low_rpm = MIN_RPM
    high_rpm = MAX_RPM
    best_rpm = None
    best_torque = None
    best_error = float('inf')
    
    iteration = 0
    while iteration < MAX_SEARCH_ITERATIONS and (high_rpm - low_rpm) > RPM_PRECISION:
        iteration += 1
        mid_rpm = (low_rpm + high_rpm) / 2.0
        
        print(f"      Iteration {iteration}: Testing RPM {mid_rpm:.2f} (range: {low_rpm:.2f} - {high_rpm:.2f})")
        
        # Check maximum RPM limit if enabled
        if ENABLE_MAX_RPM_LIMIT and mid_rpm > MAX_RPM:
            print(f"      RPM limit reached: {mid_rpm:.2f} > {MAX_RPM:.2f}")
            break
        
        torque = measure_torque_at_rpm(client, mid_rpm)
        
        if torque is None:
            if ENABLE_RESISTANCE_CHECK:
                print(f"      RESISTANCE: RPM {mid_rpm:.2f} returned invalid torque")
                high_rpm = mid_rpm  # Reduce upper bound
                continue
            else:
                print(f"      WARNING: RPM {mid_rpm:.2f} returned invalid torque (resistance check disabled)")
                high_rpm = mid_rpm
                continue
                
        # Check torque break threshold if enabled
        if ENABLE_TORQUE_BREAK_THRESHOLD and abs(torque) >= TORQUE_BREAK_THRESHOLD:
            print(f"      SAFETY: RPM {mid_rpm:.2f} exceeded threshold with {torque:.2f}%")
            high_rpm = mid_rpm  # Reduce upper bound
            continue
        
        # Check if torque is in target range
        if target_min <= torque <= target_max:
            print(f"      TARGET FOUND: RPM {mid_rpm:.2f} gives {torque:.2f}% (within {TARGET_TORQUE_PERCENT}%±{TORQUE_TOLERANCE}%)")
            return round(mid_rpm, 2), round(torque, 2), False
        
        # Track best result so far
        error = abs(torque - TARGET_TORQUE_PERCENT)
        if error < best_error:
            best_error = error
            best_rpm = mid_rpm
            best_torque = torque
        
        # Adjust search range
        if torque < target_min:
            low_rpm = mid_rpm  # Need higher RPM
        else:  # torque > target_max
            high_rpm = mid_rpm  # Need lower RPM
    
    # If exact target not found, return best approximation
    if best_rpm is not None:
        print(f"      BEST APPROXIMATION: RPM {best_rpm:.2f} gives {best_torque:.2f}% (error: {best_error:.1f}%)")
        return round(best_rpm, 2), round(best_torque, 2), False
    else:
        print(f"      NO SOLUTION: Could not find suitable RPM within range {MIN_RPM:.2f} - {MAX_RPM:.2f}")
        return None, None, False

def test_cell_rpm_calibration_z_series(cnc: CNC_Machine, client: ViscometerClient, cell_number: int) -> Dict[float, Tuple[Optional[float], Optional[float]]]:
    """Test RPM calibration across Z-gap range for one cell"""
    print(f"\n{'='*60}")
    print(f"RPM CALIBRATION ANALYSIS - CELL {cell_number}")
    print(f"Finding RPM for {TARGET_TORQUE_PERCENT}%±{TORQUE_TOLERANCE}% torque across Z-gap range")
    print(f"Safety switches: Torque_Break={ENABLE_TORQUE_BREAK_THRESHOLD}, First_RPM={ENABLE_FIRST_RPM_CHECK}")
    print(f"                Resistance={ENABLE_RESISTANCE_CHECK}, Max_RPM={ENABLE_MAX_RPM_LIMIT}, Z_Limit={ENABLE_Z_TRAVEL_LIMIT}")
    print(f"{'='*60}")
    
    cell_z_data = {}  # {z_height: (rpm, torque)}
    current_z = SAFE_Z
    print(f"Starting from Z-safe: {current_z:.3f}")
    
    step_count = 0
    while current_z >= MAX_Z_TRAVEL or not ENABLE_Z_TRAVEL_LIMIT:
        step_count += 1
        z_rounded = round(current_z, 3)
        
        # Check Z travel limit if enabled
        if ENABLE_Z_TRAVEL_LIMIT and current_z < MAX_Z_TRAVEL:
            print(f"\nZ travel limit reached: {current_z:.3f} < {MAX_Z_TRAVEL:.3f}")
            break
        
        print(f"\nCell {cell_number} - Z-Step {step_count}: Z={z_rounded:.3f}")
        
        try:
            # Move to position
            if step_count == 1:
                move_to_cell_position(cnc, cell_number, current_z)
            else:
                # Direct Z movement to next increment (no Z=0 retraction)
                x_pos = BASE_X
                y_pos = BASE_Y + (cell_number - 1) * Y_OFFSET
                print(f"  Moving directly to Z={current_z:.3f} (no retraction)")
                cnc.move_to_point(x_pos, y_pos, current_z, speed=Z_FEED_RATE)
                time.sleep(SETTLE_TIME)
            
            # Find target RPM at this Z-height
            found_rpm, found_torque, should_break_cell = find_target_rpm_at_z(client, z_rounded)
            cell_z_data[z_rounded] = (found_rpm, found_torque)
            
            # Check if cell should be terminated
            if should_break_cell:
                print(f"  CELL TERMINATION: Critical condition at Z={z_rounded:.3f}")
                print(f"  Stopping Cell {cell_number} Z-series testing")
                break
                
            if found_rpm is not None and found_torque is not None:
                print(f"  SUCCESS: Found RPM {found_rpm:.2f} giving {found_torque:.2f}% torque at Z={z_rounded:.3f}")
            else:
                print(f"  NO SOLUTION: Could not find suitable RPM at Z={z_rounded:.3f}")
            
        except Exception as e:
            print(f"  Error testing Cell {cell_number} at Z={z_rounded:.3f}: {e}")
            # Record failure
            cell_z_data[z_rounded] = (None, None)
        
        # Move to next Z position
        current_z += Z_STEP_SIZE
    
    # Move Z back to safe position
    try:
        x_pos = BASE_X
        y_pos = BASE_Y + (cell_number - 1) * Y_OFFSET
        cnc.move_to_point(x_pos, y_pos, z=0, speed=3000)
        time.sleep(0.5)
        print(f"Cell {cell_number} returned to safe Z position")
    except Exception as e:
        print(f"  Warning: Error moving to safe Z: {e}")
    
    print(f"Cell {cell_number} RPM calibration completed: {len(cell_z_data)} Z-positions tested")
    return cell_z_data

def save_rpm_calibration_data(all_cell_data: Dict[int, Dict[float, Tuple[Optional[float], Optional[float]]]], 
                             timestamp: str) -> List[str]:
    """Save RPM calibration data - one CSV file per cell with Z-heights vs found RPM and torque"""
    csv_filenames = []
    
    for cell_num in range(1, NUM_CELLS + 1):
        if cell_num not in all_cell_data:
            continue
            
        csv_filename = f"rpm_calibration_cell_{cell_num}_{timestamp}.csv"
        cell_data = all_cell_data[cell_num]
        
        # Get all Z-heights for this cell, sorted descending (safe to deep)
        z_heights = sorted(cell_data.keys(), reverse=True)
        
        # Create CSV headers
        headers = ["Z-Height", "Found_RPM", "Measured_Torque", "Target_Range"]
        
        # Write CSV file for this cell
        with open(csv_filename, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            
            # Write metadata header
            csv_writer.writerow([f"# RPM Calibration Analysis - Cell {cell_num}"])
            csv_writer.writerow([f"# Target Torque: {TARGET_TORQUE_PERCENT}% ± {TORQUE_TOLERANCE}%"])
            csv_writer.writerow([f"# RPM Range: {MIN_RPM} - {MAX_RPM}"])
            csv_writer.writerow([f"# Z-range: {max(z_heights):.3f} to {min(z_heights):.3f}"])
            csv_writer.writerow([f"# Timestamp: {timestamp}"])
            csv_writer.writerow([f"# Safety Settings: Break_Threshold={ENABLE_TORQUE_BREAK_THRESHOLD}, First_RPM_Check={ENABLE_FIRST_RPM_CHECK}"])
            csv_writer.writerow([f"#                  Resistance_Check={ENABLE_RESISTANCE_CHECK}, Max_RPM_Limit={ENABLE_MAX_RPM_LIMIT}"])
            csv_writer.writerow([])
            
            # Write column headers
            csv_writer.writerow(headers)
            
            # Write data rows
            for z_height in z_heights:
                if z_height in cell_data:
                    rpm, torque = cell_data[z_height]
                    target_range = f"{TARGET_TORQUE_PERCENT-TORQUE_TOLERANCE:.1f}-{TARGET_TORQUE_PERCENT+TORQUE_TOLERANCE:.1f}%"
                    
                    row = [
                        f"{z_height:.3f}",
                        f"{rpm:.2f}" if rpm is not None else "",
                        f"{torque:.2f}" if torque is not None else "",
                        target_range
                    ]
                else:
                    # Fill with empty strings if no data for this Z-height
                    row = [f"{z_height:.3f}", "", "", ""]
                
                csv_writer.writerow(row)
        
        csv_filenames.append(csv_filename)
        print(f"Cell {cell_num} RPM calibration data saved to: {csv_filename}")
    
    return csv_filenames

def main():
    print("="*80)
    print("RPM CALIBRATION ANALYSIS - FIND RPM FOR TARGET TORQUE AT EACH Z-LEVEL")
    print(f"Target Torque: {TARGET_TORQUE_PERCENT}% ± {TORQUE_TOLERANCE}%")
    print(f"RPM Search Range: {MIN_RPM} - {MAX_RPM}")
    print(f"Z-range: {SAFE_Z:.3f} to {MAX_Z_TRAVEL:.3f}")
    print(f"Safety Controls: Break_Threshold={ENABLE_TORQUE_BREAK_THRESHOLD}, First_RPM={ENABLE_FIRST_RPM_CHECK}")
    print(f"                Resistance={ENABLE_RESISTANCE_CHECK}, Max_RPM={ENABLE_MAX_RPM_LIMIT}, Z_Limit={ENABLE_Z_TRAVEL_LIMIT}")
    print("="*80)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Initialize hardware with proper error handling
    try:
        print("Initializing CNC machine...")
        cnc = CNC_Machine(virtual=False)
        cnc.home()
        time.sleep(1.0)
        print("CNC machine initialized and homed")
    except Exception as e:
        print(f"ERROR initializing CNC machine: {e}")
        return
    
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
        
    except Exception as e:
        print(f"ERROR initializing viscometer: {e}")
        try:
            cnc.home()
        except:
            pass
        return
    
    all_cell_data = {}
    
    try:
        print(f"\nStarting RPM calibration analysis for {NUM_CELLS} cells...")
        print(f"Each cell will find the RPM producing {TARGET_TORQUE_PERCENT}%±{TORQUE_TOLERANCE}% torque at each Z-position")
        
        # Go through each cell and perform RPM calibration across Z-gap range
        for cell_number in range(1, NUM_CELLS + 1):
            cell_data = test_cell_rpm_calibration_z_series(cnc, client, cell_number)
            all_cell_data[cell_number] = cell_data
            
            print(f"Cell {cell_number} RPM calibration completed")
        
        # Save all data to separate CSV files (one per cell)
        csv_filenames = save_rpm_calibration_data(all_cell_data, timestamp)
        
        print(f"\n{'='*80}")
        print("RPM CALIBRATION ANALYSIS COMPLETED SUCCESSFULLY!")
        print("Results saved to:")
        for filename in csv_filenames:
            print(f"  - {filename}")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"ERROR during RPM calibration analysis: {e}")
        traceback.print_exc()
    
    finally:
        # Safely home the CNC machine and close the viscometer connection
        try:
            print("\nCleaning up...")
            client.stop()
            client.close()
            print("Viscometer connection closed")
        except Exception as e:
            print(f"Warning: Error closing viscometer: {e}")
        
        try:
            cnc.home()
            print("CNC machine homed safely")
        except Exception as e:
            print(f"Warning: Error homing CNC: {e}")
        
        print("Cleanup completed")

if __name__ == "__main__":
    main()
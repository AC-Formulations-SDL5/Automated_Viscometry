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

SAFE_Z = -65.9 #-65.500                
Z_STEP_SIZE = -0.020        #-0.100            
Z_FEED_RATE = 500               
MAX_Z_TRAVEL = -66.5 #-66.800      #-66.700          
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

# Array of RPMs to test at each Z-position (similar to analysis_methods.py)
TEST_RPMS = [1.7] #, 0.5, 1.0, 5.0, 10.0, 20.0, 50.0]
DWELL_SECONDS = 2.0            
INTER_RPM_PAUSE = 2.0           

def move_to_cell_position(cnc: CNC_Machine, cell_number: int, z_height: float) -> Tuple[float, float, float]:
    x_pos = BASE_X
    y_pos = BASE_Y + (cell_number - 1) * Y_OFFSET
    print(f"Moving to Cell {cell_number}: X={x_pos}, Y={y_pos}, Z={z_height:.3f}")
    cnc.move_to_point_safe(x_pos, y_pos, z_height, speed=3000)
    time.sleep(SETTLE_TIME)
    return x_pos, y_pos, z_height

def measure_torque_at_rpm(client: ViscometerClient, rpm: float) -> Optional[float]:
    #Measure average torque at a specific RPM
    MEASUREMENT_DURATION = 40 #70 #5.0      #35.0
    SAMPLE_INTERVAL = 10.0       #2.0

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
            print(f"      RPM {rpm}: {len(measurements)} samples, Avg torque: {avg_torque:.2f}%")
            return round(avg_torque, 2)
        else:
            print(f"      RPM {rpm}: No valid measurements collected")
            return None
            
    except Exception as e:
        print(f"      Error measuring torque at RPM {rpm}: {e}")
        try:
            client.stop()
        except:
            pass
        return None

def test_dynamic_analysis_at_z(client: ViscometerClient, z_height: float) -> Tuple[Dict[float, Optional[float]], bool]:
    #Test all RPMs at a specific Z-height and return torque data and first_rpm_exceeded flag
    print(f"    Testing {len(TEST_RPMS)} RPMs at Z={z_height:.3f}")
    rpm_torque_data = {}
    first_rpm_exceeded_threshold = False
    
    for i, rpm in enumerate(TEST_RPMS):
        torque = measure_torque_at_rpm(client, rpm)
        rpm_torque_data[rpm] = torque
        
        # Check if torque is invalid (high resistance condition) or exceeds threshold
        if torque is None:
            if i == 0:  # First RPM failed - critical condition
                print(f"      CRITICAL: First RPM {rpm} returned invalid torque (high resistance) - will break entire cell")
                first_rpm_exceeded_threshold = True
                # Fill remaining RPMs with None
                for remaining_rpm in TEST_RPMS[TEST_RPMS.index(rpm) + 1:]:
                    rpm_torque_data[remaining_rpm] = None
                break
            else:  # Later RPM failed - high resistance at this Z-level
                print(f"      RESISTANCE: RPM {rpm} returned invalid torque (high resistance) - stopping RPM sweep at this Z-level")
                # Fill remaining RPMs with None
                for remaining_rpm in TEST_RPMS[TEST_RPMS.index(rpm) + 1:]:
                    rpm_torque_data[remaining_rpm] = None
                break
        elif abs(torque) >= TORQUE_BREAK_THRESHOLD:
            if i == 0:  # First RPM exceeded threshold
                print(f"      CRITICAL: First RPM {rpm} exceeded threshold with {torque:.2f}% - will break entire cell")
                first_rpm_exceeded_threshold = True
                # Fill remaining RPMs with None
                for remaining_rpm in TEST_RPMS[TEST_RPMS.index(rpm) + 1:]:
                    rpm_torque_data[remaining_rpm] = None
                break
            else:  # Later RPM exceeded threshold
                print(f"      SAFETY: RPM {rpm} exceeded threshold with {torque:.2f}% - stopping RPM sweep at this Z-level")
                # Fill remaining RPMs with None
                for remaining_rpm in TEST_RPMS[TEST_RPMS.index(rpm) + 1:]:
                    rpm_torque_data[remaining_rpm] = None
                break
    
    return rpm_torque_data, first_rpm_exceeded_threshold

def test_cell_dynamic_z_series(cnc: CNC_Machine, client: ViscometerClient, cell_number: int) -> Dict[float, Dict[float, Optional[float]]]:
    #Test dynamic analysis (multiple RPMs) across Z-gap range for one cell
    print(f"\n{'='*60}")
    print(f"DYNAMIC ANALYSIS - CELL {cell_number}")
    print(f"Testing RPMs {TEST_RPMS} across Z-gap range")
    print(f"{'='*60}")
    
    cell_z_rpm_data = {}
    current_z = SAFE_Z
    print(f"Starting from Z-safe: {current_z:.3f}")
    
    step_count = 0
    while current_z >= MAX_Z_TRAVEL:
        step_count += 1
        z_rounded = round(current_z, 3)
        
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
            
            # Test all RPMs at this Z-height
            rpm_data, first_rpm_exceeded = test_dynamic_analysis_at_z(client, z_rounded)
            cell_z_rpm_data[z_rounded] = rpm_data
            
            # Check if first RPM exceeded threshold - if so, break entire cell
            if first_rpm_exceeded:
                print(f"  CELL TERMINATION: First RPM exceeded threshold at Z={z_rounded:.3f}")
                print(f"  Stopping Cell {cell_number} Z-series testing")
                break
                
            print(f"  Completed Z={z_rounded:.3f}: {len([t for t in rpm_data.values() if t is not None])}/{len(TEST_RPMS)} successful measurements")
            
        except Exception as e:
            print(f"  Error testing Cell {cell_number} at Z={z_rounded:.3f}: {e}")
            # Fill with None values for all RPMs at this Z-height
            cell_z_rpm_data[z_rounded] = {rpm: None for rpm in TEST_RPMS}
        
        # Move to next Z position
        current_z += Z_STEP_SIZE
        
    # Move Z back to safe position
    try:
        x_pos = BASE_X
        y_pos = BASE_Y + (cell_number - 1) * Y_OFFSET
        # Start viscometer at low RPM while moving to safe position
        client.set_speed(0.5)
        cnc.move_to_point(x_pos, y_pos, z=0, speed=Z_FEED_RATE)
        time.sleep(0.5)
        # Stop viscometer once at safe position
        client.stop()
        print(f"Cell {cell_number} returned to safe Z position")
    except Exception as e:
        print(f"  Warning: Error moving to safe Z: {e}")
        # Ensure viscometer is stopped even if movement fails
        try:
            client.stop()
        except:
            pass
    
    print(f"Cell {cell_number} dynamic analysis completed: {len(cell_z_rpm_data)} Z-positions tested")
    return cell_z_rpm_data

def save_dynamic_analysis_data(all_cell_data: Dict[int, Dict[float, Dict[float, Optional[float]]]], 
                              timestamp: str) -> List[str]:
    """Save dynamic analysis data - one CSV file per cell with Z-heights vs RPMs matrix"""
    csv_filenames = []
    
    for cell_num in range(1, NUM_CELLS + 1):
        if cell_num not in all_cell_data:
            continue
            
        csv_filename = f"dynamic_analysis_cell_{cell_num}_{timestamp}.csv"
        cell_data = all_cell_data[cell_num]
        
        # Get all Z-heights for this cell, sorted descending (safe to deep)
        z_heights = sorted(cell_data.keys(), reverse=True)
        
        # Create CSV headers: Z-Height, then each RPM
        headers = ["Z-Height"] + [f"RPM_{rpm}" for rpm in TEST_RPMS]
        
        # Write CSV file for this cell
        with open(csv_filename, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            
            # Write metadata header
            csv_writer.writerow([f"# Dynamic Analysis - Cell {cell_num}"])
            csv_writer.writerow([f"# Test RPMs: {TEST_RPMS}"])
            csv_writer.writerow([f"# Z-range: {max(z_heights):.3f} to {min(z_heights):.3f}"])
            csv_writer.writerow([f"# Timestamp: {timestamp}"])
            csv_writer.writerow([])
            
            # Write column headers
            csv_writer.writerow(headers)
            
            # Write data rows
            for z_height in z_heights:
                row = [f"{z_height:.3f}"]
                
                if z_height in cell_data:
                    rpm_data = cell_data[z_height]
                    for rpm in TEST_RPMS:
                        torque_value = rpm_data.get(rpm)
                        row.append(f"{torque_value:.2f}" if torque_value is not None else "")
                else:
                    # Fill with empty strings if no data for this Z-height
                    row.extend([""] * len(TEST_RPMS))
                
                csv_writer.writerow(row)
        
        csv_filenames.append(csv_filename)
        print(f"Cell {cell_num} data saved to: {csv_filename}")
    
    return csv_filenames

def main():
    print("="*80)
    print("DYNAMIC ANALYSIS - Z-GAP vs TORQUE at MULTIPLE RPMs")
    print(f"Testing RPMs: {TEST_RPMS}")
    print(f"Z-range: {SAFE_Z:.3f} to {MAX_Z_TRAVEL:.3f}")
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
        print(f"\nStarting dynamic analysis for {NUM_CELLS} cells...")
        print(f"Each cell will test {len(TEST_RPMS)} RPMs at each Z-position")
        
        # Go through each cell and perform dynamic analysis across Z-gap range
        for cell_number in range(1, NUM_CELLS + 1):
            cell_data = test_cell_dynamic_z_series(cnc, client, cell_number)
            all_cell_data[cell_number] = cell_data
            
            print(f"Cell {cell_number} dynamic analysis completed")
        
        # Save all data to separate CSV files (one per cell)
        csv_filenames = save_dynamic_analysis_data(all_cell_data, timestamp)
        
        print(f"\n{'='*80}")
        print("DYNAMIC ANALYSIS COMPLETED SUCCESSFULLY!")
        print("Results saved to:")
        for filename in csv_filenames:
            print(f"  - {filename}")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"ERROR during dynamic analysis: {e}")
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

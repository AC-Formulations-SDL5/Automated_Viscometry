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
from analysis_methods import run_single_rpm

SAFE_Z = -65.300                
Z_STEP_SIZE = -0.030            
Z_FEED_RATE = 500               
MAX_Z_TRAVEL = -66.700          
TORQUE_BREAK_THRESHOLD = 55.0   
SETTLE_TIME = 0.5               
TORQUE_READ_TIMEOUT = 2.0       
SPINDLE_SETTLE_TIME = 1.0      
NUM_CELLS = 6                 
BASE_X = 85                     
BASE_Y = 62                    
Y_OFFSET = 67                  
PYTHON32 = ".\\.venv32\\Scripts\\python.exe"
VISCO_PORT = "COM6"
VISCO_BAUD = 115200
VISCO_TOUT = 1.0
SPINDLE_K = 992.47
TORQUE_READ_TIMEOUT = 2.0       

def move_to_cell_position(cnc: CNC_Machine, cell_number: int, z_height: float) -> Tuple[float, float, float]:
    x_pos = BASE_X
    y_pos = BASE_Y + (cell_number - 1) * Y_OFFSET
    print(f"Moving to Cell {cell_number}: X={x_pos}, Y={y_pos}, Z={z_height:.3f}")
    cnc.move_to_point_safe(x_pos, y_pos, z_height, speed=3000)
    time.sleep(SETTLE_TIME)
    return x_pos, y_pos, z_height

def measure_average_torque(client: ViscometerClient) -> Optional[float]:
    RPM = 4.5                   
    MEASUREMENT_DURATION = 30
    SAMPLE_INTERVAL = 3

    try:
        # Set spindle speed
        client.set_speed(RPM)
        time.sleep(SPINDLE_SETTLE_TIME)
        
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
                    print(f"    Measurement error: {e}")
            
            time.sleep(0.1)
        
        # Stop spindle
        client.stop()
        time.sleep(0.2)
        
        # Calculate average torque
        if measurements:
            avg_torque = sum(measurements) / len(measurements)
            print(f"    Collected {len(measurements)} samples, Average torque: {avg_torque:.2f}%")
            return round(avg_torque, 2)
        else:
            print("    No valid measurements collected")
            return None
            
    except Exception as e:
        print(f"    Error during torque measurement: {e}")
        try:
            client.stop()
        except:
            pass
        return None

def test_cell_z_gap_series(cnc: CNC_Machine, client: ViscometerClient, cell_number: int) -> Dict[float, Optional[float]]:
    print(f"\n{'='*50}")
    print(f"TESTING CELL {cell_number} - Z-GAP vs TORQUE")
    print(f"{'='*50}")
    cell_data = {}
    current_z = SAFE_Z
    print(f"Starting from Z-safe: {current_z:.3f}")
    
    step_count = 0
    while current_z >= MAX_Z_TRAVEL:
        step_count += 1
        z_rounded = round(current_z, 3)
        
        print(f"\nCell {cell_number} - Step {step_count}: Z={z_rounded:.3f}")
        
        try:
            # Move to position - for first step use safe move, for subsequent steps move directly
            if step_count == 1:
                move_to_cell_position(cnc, cell_number, current_z)
            else:
                # Direct Z movement to next increment (no Z=0 retraction)
                x_pos = BASE_X
                y_pos = BASE_Y + (cell_number - 1) * Y_OFFSET
                print(f"Moving directly to Z={current_z:.3f} (no retraction)")
                cnc.move_to_point(x_pos, y_pos, current_z, speed=Z_FEED_RATE)
                time.sleep(SETTLE_TIME)
            
            # Measure average torque
            avg_torque = measure_average_torque(client)
            
            if avg_torque is not None:
                cell_data[z_rounded] = avg_torque
                print(f"    Recorded: Z={z_rounded:.3f}, Torque={avg_torque:.2f}%")
                
                # Check if torque threshold reached
                if abs(avg_torque) >= TORQUE_BREAK_THRESHOLD:
                    print(f"    TORQUE THRESHOLD REACHED: {avg_torque:.2f}% >= {TORQUE_BREAK_THRESHOLD}%")
                    print(f"    Stopping Cell {cell_number} testing")
                    break
            else:
                cell_data[z_rounded] = None
                print(f"    Failed to measure torque at Z={z_rounded:.3f}")
            
        except Exception as e:
            print(f"    Error testing Cell {cell_number} at Z={z_rounded:.3f}: {e}")
            cell_data[z_rounded] = None
        
        # Move to next Z position
        current_z += Z_STEP_SIZE
    
    # Move Z back to safe position
    try:
        x_pos = BASE_X
        y_pos = BASE_Y + (cell_number - 1) * Y_OFFSET
        cnc.move_to_point(x_pos, y_pos, z=0, speed=3000)
        time.sleep(0.5)
    except Exception as e:
        print(f"    Warning: Error moving to safe Z: {e}")
    
    print(f"Cell {cell_number} completed: {len(cell_data)} Z-positions tested")
    return cell_data

def save_z_gap_torque_data(all_cell_data: Dict[int, Dict[float, Optional[float]]], 
                          timestamp: str) -> str:
    csv_filename = f"z_gap_vs_torque_{timestamp}.csv"

    # Collect all unique Z-heights from all cells
    all_z_heights = set()
    for cell_data in all_cell_data.values():
        all_z_heights.update(cell_data.keys())
    
    # Sort Z-heights in descending order (from safe to deep)
    sorted_z_heights = sorted(all_z_heights, reverse=True)
    
    # Create CSV headers
    headers = ["Z-Height"]
    for cell_num in range(1, NUM_CELLS + 1):
        headers.append(f"Cell_{cell_num}_Torque")
    
    # Write CSV file
    with open(csv_filename, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(headers)
        
        for z_height in sorted_z_heights:
            row = [f"{z_height:.3f}"]
            
            for cell_num in range(1, NUM_CELLS + 1):
                if cell_num in all_cell_data and z_height in all_cell_data[cell_num]:
                    torque_value = all_cell_data[cell_num][z_height]
                    row.append(f"{torque_value:.2f}" if torque_value is not None else "")
                else:
                    row.append("")
            
            csv_writer.writerow(row)
    
    print(f"\nData saved to: {csv_filename}")
    return csv_filename

def main():
    print("="*70)
    print("Z-GAP vs TORQUE MEASUREMENT SYSTEM")
    print("="*70)
    
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
    
    # Load calibration data
    print("using direct Z positions from SAFE_Z")
    
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
        print(f"\nStarting Z-gap vs torque measurements for {NUM_CELLS} cells...")
        
        # Go through each cell and test Z-gap vs torque
        for cell_number in range(1, NUM_CELLS + 1):
            # Test this cell across Z-gap range (no calibrated Z - start from SAFE_Z)
            cell_data = test_cell_z_gap_series(cnc, client, cell_number)
            all_cell_data[cell_number] = cell_data
            
            print(f"Cell {cell_number} testing completed")
        
        # Save all data to CSV
        csv_filename = save_z_gap_torque_data(all_cell_data, timestamp)
        
        print(f"\n{'='*70}")
        print("ALL TESTING COMPLETED SUCCESSFULLY!")
        print(f"Results saved to: {csv_filename}")
        print(f"{'='*70}")
        
    except Exception as e:
        print(f"ERROR during testing: {e}")
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
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

Z_STEP_SIZE = -0.100        #-0.100            
Z_FEED_RATE = 500               
TORQUE_BREAK_THRESHOLD = 1000.0     #100.0   
SETTLE_TIME = 0.5               
TORQUE_READ_TIMEOUT = 2.0       
SPINDLE_SETTLE_TIME = 1.0      
NUM_CELLS = 6                  
BASE_Y = 62                    
Y_OFFSET = 67                  
PYTHON32 = ".\\.venv32\\Scripts\\python.exe"
VISCO_PORT = "COM6"
VISCO_BAUD = 115200
VISCO_TOUT = 1.0
SPINDLE_K = 992.47

# Row configurations: each row has different Z-parameters and BASE_X position
ROWS = [
    {'row_number': 1, 'base_x': 10, 'safe_z': -65.5, 'max_z_travel': -66.500},
    {'row_number': 2, 'base_x': 85, 'safe_z': -65.5, 'max_z_travel': -66.500},
    {'row_number': 3, 'base_x': 309, 'safe_z': -64.5, 'max_z_travel': -65.500}
]

# Array of RPMs to test at each Z-position (similar to analysis_methods.py)
TEST_RPMS = [0.5, 2.0] #, 0.5, 1.0, 5.0, 10.0, 20.0, 50.0]
DWELL_SECONDS = 2.0            
INTER_RPM_PAUSE = 2.0           

def move_to_cell_position(cnc: CNC_Machine, row_number: int, cell_number: int, z_height: float) -> Tuple[float, float, float]:
    """Move to specific cell position in a specific row"""
    # Find the BASE_X for this row
    base_x = None
    for row in ROWS:
        if row['row_number'] == row_number:
            base_x = row['base_x']
            break
    
    if base_x is None:
        raise ValueError(f"Invalid row number: {row_number}")
    
    x_pos = base_x
    y_pos = BASE_Y + (cell_number - 1) * Y_OFFSET
    print(f"Moving to Row {row_number}, Cell {cell_number}: X={x_pos}, Y={y_pos}, Z={z_height:.3f}")
    cnc.move_to_point_safe(x_pos, y_pos, z_height, speed=3000)
    time.sleep(SETTLE_TIME)
    return x_pos, y_pos, z_height

def measure_torque_at_rpm(client: ViscometerClient, rpm: float) -> Optional[List[Dict]]:
    """Measure torque at a specific RPM, returning all individual measurements with timestamps"""
    MEASUREMENT_DURATION = 10.0      #35.0
    SAMPLE_INTERVAL = 5.0       #2.0

    try:
        # Set spindle speed
        client.set_speed(rpm)
        time.sleep(DWELL_SECONDS)  # Allow spindle to settle at new RPM
        
        # Collect torque measurements over duration
        measurements = []
        start_time = time.time()
        measurement_start_time = time.time()
        next_sample_time = start_time + SAMPLE_INTERVAL
        
        while time.time() - start_time < MEASUREMENT_DURATION:
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
                    next_sample_time += SAMPLE_INTERVAL
                except Exception as e:
                    print(f"      Measurement error at RPM {rpm}: {e}")
            
            time.sleep(0.1)
        
        # Stop spindle after measurement
        client.stop()
        time.sleep(INTER_RPM_PAUSE)
        
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
        except:
            pass
        return None

def test_dynamic_analysis_at_z(client: ViscometerClient, z_height: float) -> Tuple[Dict[float, Optional[List[Dict]]], bool]:
    """Test all RPMs at a specific Z-height and return torque data and first_rpm_exceeded flag"""
    print(f"    Testing {len(TEST_RPMS)} RPMs at Z={z_height:.3f}")
    rpm_torque_data = {}
    first_rpm_exceeded_threshold = False
    
    for i, rpm in enumerate(TEST_RPMS):
        measurements = measure_torque_at_rpm(client, rpm)
        rpm_torque_data[rpm] = measurements
        
        # Check if measurements are invalid (high resistance condition) or exceed threshold
        if measurements is None:
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
        else:
            # Check if any torque measurement exceeds threshold
            max_torque = max(abs(m["torque_percent"]) for m in measurements)
            if max_torque >= TORQUE_BREAK_THRESHOLD:
                if i == 0:  # First RPM exceeded threshold
                    print(f"      CRITICAL: First RPM {rpm} exceeded threshold with max {max_torque:.2f}% - will break entire cell")
                    first_rpm_exceeded_threshold = True
                    # Fill remaining RPMs with None
                    for remaining_rpm in TEST_RPMS[TEST_RPMS.index(rpm) + 1:]:
                        rpm_torque_data[remaining_rpm] = None
                    break
                else:  # Later RPM exceeded threshold
                    print(f"      SAFETY: RPM {rpm} exceeded threshold with max {max_torque:.2f}% - stopping RPM sweep at this Z-level")
                    # Fill remaining RPMs with None
                    for remaining_rpm in TEST_RPMS[TEST_RPMS.index(rpm) + 1:]:
                        rpm_torque_data[remaining_rpm] = None
                    break
    
    return rpm_torque_data, first_rpm_exceeded_threshold

def test_cell_dynamic_z_series(cnc: CNC_Machine, client: ViscometerClient, row_number: int, cell_number: int, safe_z: float, max_z_travel: float) -> Dict[float, Dict[float, Optional[List[Dict]]]]:
    """Test dynamic analysis (multiple RPMs) across Z-gap range for one cell in a specific row"""
    print(f"\n{'='*60}")
    print(f"DYNAMIC ANALYSIS - ROW {row_number}, CELL {cell_number}")
    print(f"Testing RPMs {TEST_RPMS} across Z-gap range")
    print(f"Safe Z: {safe_z:.3f}, Max Z Travel: {max_z_travel:.3f}")
    print(f"{'='*60}")
    
    cell_z_rpm_data = {}
    current_z = safe_z
    print(f"Starting from Z-safe: {current_z:.3f}")
    
    step_count = 0
    while current_z >= max_z_travel:
        step_count += 1
        z_rounded = round(current_z, 3)
        
        print(f"\nRow {row_number}, Cell {cell_number} - Z-Step {step_count}: Z={z_rounded:.3f}")
        
        try:
            # Move to position
            if step_count == 1:
                move_to_cell_position(cnc, row_number, cell_number, current_z)
            else:
                # Direct Z movement to next increment (no Z=0 retraction)
                base_x = None
                for row in ROWS:
                    if row['row_number'] == row_number:
                        base_x = row['base_x']
                        break
                
                x_pos = base_x
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
                print(f"  Stopping Row {row_number}, Cell {cell_number} Z-series testing")
                break
                
            print(f"  Completed Z={z_rounded:.3f}: {len([t for t in rpm_data.values() if t is not None])}/{len(TEST_RPMS)} successful RPM tests")
            
        except Exception as e:
            print(f"  Error testing Row {row_number}, Cell {cell_number} at Z={z_rounded:.3f}: {e}")
            # Fill with None values for all RPMs at this Z-height
            cell_z_rpm_data[z_rounded] = {rpm: None for rpm in TEST_RPMS}
        
        # Move to next Z position
        current_z += Z_STEP_SIZE
        
    # Move Z back to safe position
    try:
        base_x = None
        for row in ROWS:
            if row['row_number'] == row_number:
                base_x = row['base_x']
                break
        
        x_pos = base_x
        y_pos = BASE_Y + (cell_number - 1) * Y_OFFSET
        # Start viscometer at low RPM while moving to safe position
        client.set_speed(0.5)
        cnc.move_to_point(x_pos, y_pos, z=0, speed=Z_FEED_RATE)
        time.sleep(0.5)
        # Stop viscometer once at safe position
        client.stop()
        print(f"Row {row_number}, Cell {cell_number} returned to safe Z position")
    except Exception as e:
        print(f"  Warning: Error moving to safe Z: {e}")
        # Ensure viscometer is stopped even if movement fails
        try:
            client.stop()
        except:
            pass
    
    print(f"Row {row_number}, Cell {cell_number} dynamic analysis completed: {len(cell_z_rpm_data)} Z-positions tested")
    return cell_z_rpm_data

def save_dynamic_analysis_data(all_data: Dict[int, Dict[int, Dict[float, Dict[float, Optional[List[Dict]]]]]], 
                              timestamp: str) -> List[str]:
    """Save dynamic analysis data - separate detailed and summary CSV files per cell"""
    csv_filenames = []
    
    for row_num in all_data.keys():
        if row_num not in all_data:
            continue
            
        for cell_num in range(1, NUM_CELLS + 1):
            if cell_num not in all_data[row_num]:
                continue
                
            # Save detailed measurements (all individual data points)
            detailed_filename = f"dynamic_analysis_detailed_row_{row_num}_cell_{cell_num}_{timestamp}.csv"
            csv_filenames.append(detailed_filename)
            
            # Save summary data (averages for easy analysis)
            summary_filename = f"dynamic_analysis_summary_row_{row_num}_cell_{cell_num}_{timestamp}.csv"
            csv_filenames.append(summary_filename)
            
            cell_data = all_data[row_num][cell_num]
            z_heights = sorted(cell_data.keys(), reverse=True)
            
            # Write detailed CSV with all individual measurements
            with open(detailed_filename, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                
                # Write metadata header
                csv_writer.writerow([f"# Dynamic Analysis Detailed - Row {row_num}, Cell {cell_num}"])
                csv_writer.writerow([f"# Test RPMs: {TEST_RPMS}"])
                csv_writer.writerow([f"# Z-range: {max(z_heights):.3f} to {min(z_heights):.3f}"])
                csv_writer.writerow([f"# Timestamp: {timestamp}"])
                csv_writer.writerow([])
                
                # Write column headers for detailed data
                headers = ["Z-Height", "RPM", "Measurement_Index", "Elapsed_Time_s", "Torque_Percent", "Timestamp"]
                csv_writer.writerow(headers)
                
                # Write all individual measurements
                for z_height in z_heights:
                    if z_height in cell_data:
                        rpm_data = cell_data[z_height]
                        for rpm in TEST_RPMS:
                            measurements = rpm_data.get(rpm)
                            if measurements is not None:
                                for i, measurement in enumerate(measurements):
                                    row = [
                                        f"{z_height:.3f}",
                                        f"{rpm:.1f}",
                                        str(i + 1),
                                        f"{measurement['elapsed_time']:.2f}",
                                        f"{measurement['torque_percent']:.3f}",
                                        f"{measurement['timestamp']:.3f}"
                                    ]
                                    csv_writer.writerow(row)
            
            # Write summary CSV with averages (compatible with existing analysis)
            with open(summary_filename, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                
                # Write metadata header
                csv_writer.writerow([f"# Dynamic Analysis Summary - Row {row_num}, Cell {cell_num}"])
                csv_writer.writerow([f"# Test RPMs: {TEST_RPMS}"])
                csv_writer.writerow([f"# Z-range: {max(z_heights):.3f} to {min(z_heights):.3f}"])
                csv_writer.writerow([f"# Timestamp: {timestamp}"])
                csv_writer.writerow([])
                
                # Create CSV headers: Z-Height, then each RPM (avg, min, max, count)
                headers = ["Z-Height"]
                for rpm in TEST_RPMS:
                    headers.extend([f"RPM_{rpm}_Avg", f"RPM_{rpm}_Min", f"RPM_{rpm}_Max", f"RPM_{rpm}_Count"])
                csv_writer.writerow(headers)
                
                # Write summary data rows
                for z_height in z_heights:
                    row = [f"{z_height:.3f}"]
                    
                    if z_height in cell_data:
                        rpm_data = cell_data[z_height]
                        for rpm in TEST_RPMS:
                            measurements = rpm_data.get(rpm)
                            if measurements is not None and len(measurements) > 0:
                                torque_values = [m["torque_percent"] for m in measurements]
                                avg_torque = sum(torque_values) / len(torque_values)
                                min_torque = min(torque_values)
                                max_torque = max(torque_values)
                                count = len(torque_values)
                                row.extend([f"{avg_torque:.3f}", f"{min_torque:.3f}", f"{max_torque:.3f}", str(count)])
                            else:
                                row.extend(["", "", "", "0"])
                    else:
                        # Fill with empty strings if no data for this Z-height
                        row.extend([""] * (len(TEST_RPMS) * 4))
                    
                    csv_writer.writerow(row)
            
            print(f"Row {row_num}, Cell {cell_num} detailed data saved to: {detailed_filename}")
            print(f"Row {row_num}, Cell {cell_num} summary data saved to: {summary_filename}")
    
    return csv_filenames

def main():
    print("="*80)
    print("MULTI-ROW DYNAMIC ANALYSIS - Z-GAP vs TORQUE at MULTIPLE RPMs")
    print(f"Testing RPMs: {TEST_RPMS}")
    print(f"Rows: {len(ROWS)} rows x {NUM_CELLS} cells = {len(ROWS) * NUM_CELLS} total cells")
    for row in ROWS:
        print(f"  Row {row['row_number']}: BASE_X = {row['base_x']}, Safe Z = {row['safe_z']:.3f}, Max Z = {row['max_z_travel']:.3f}")
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
    
    # Data structure: all_data[row_number][cell_number] = cell_z_rpm_data
    all_data = {}
    
    try:
        print(f"\nStarting multi-row dynamic analysis...")
        print(f"Total tests: {len(ROWS)} rows x {NUM_CELLS} cells x {len(TEST_RPMS)} RPMs per Z-position")
        
        # Go through each row, then each cell in that row
        for row_config in ROWS:
            row_number = row_config['row_number']
            base_x = row_config['base_x']
            
            print(f"\n{'='*60}")
            print(f"STARTING ROW {row_number} (BASE_X = {base_x})")
            print(f"{'='*60}")
            
            all_data[row_number] = {}
            
            # Test each cell in this row
            for cell_number in range(1, NUM_CELLS + 1):
                print(f"\nStarting Row {row_number}, Cell {cell_number}...")
                
                # Auto-zero the viscometer sensor before testing each cell
                try:
                    print(f"Auto-zeroing viscometer for Row {row_number}, Cell {cell_number}...")
                    client.zero()
                    print("Viscometer auto-zero completed")
                except Exception as e:
                    print(f"Warning: Failed to auto-zero viscometer: {e}")
                
                cell_data = test_cell_dynamic_z_series(cnc, client, row_number, cell_number, row_config['safe_z'], row_config['max_z_travel'])
                all_data[row_number][cell_number] = cell_data
                print(f"Row {row_number}, Cell {cell_number} completed")
            
            print(f"\nROW {row_number} COMPLETED - All {NUM_CELLS} cells tested")
        
        # Save all data to separate CSV files (one per cell)
        csv_filenames = save_dynamic_analysis_data(all_data, timestamp)
        
        print(f"\n{'='*80}")
        print("MULTI-ROW DYNAMIC ANALYSIS COMPLETED SUCCESSFULLY!")
        print(f"Total cells tested: {len(ROWS)} rows x {NUM_CELLS} cells = {len(ROWS) * NUM_CELLS} cells")
        print("Results saved to:")
        for filename in csv_filenames:
            print(f"  - {filename}")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"ERROR during multi-row dynamic analysis: {e}")
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
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
from move_to_locations import PumpESP32

Z_STEP_SIZE = -0.02       #-0.100            
Z_FEED_RATE = 500               
TORQUE_BREAK_THRESHOLD = 100.0     #100.0   
SETTLE_TIME = 1               
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
DWELL_SECONDS = 2.0            
INTER_RPM_PAUSE = 2.0           

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
SELECTED_CELLS = [4, 7]  # Only used when TESTING_MODE = "custom"

# ===============================================

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

def perform_washing_sequence(cnc: CNC_Machine, pump: PumpESP32, global_cell: int):
    """Perform the washing sequence after completing a cell test with improved reliability"""
    print(f"\nStarting Step 2.5: Washing Station Sequence after Cell {global_cell}")
    
    def reliable_pump_command(command: bytes, description: str) -> bool:
        """Send pump command with acknowledgment and status verification"""
        print(f"  Executing: {description}")
        
        # Try with acknowledgment first (new method)
        if hasattr(pump, 'send_command_with_ack'):
            success = pump.send_command_with_ack(command, timeout=3.0, max_retries=3)
            if success:
                print(f"  SUCCESS: {description}")
                return True
            else:
                print(f"  FAILED with ACK: {description}, trying legacy mode...")
        
        # Fallback to legacy mode with verification
        pump.send_tag(command)
        time.sleep(0.5)  # Give ESP32 time to process
        
        # Verify status if possible
        if hasattr(pump, 'get_status'):
            status = pump.get_status()
            if status and len(status) > 0:
                print(f"  Status after command: {status}")
            
        print(f"  LEGACY: {description} sent (no verification)")
        return True
    
    try:
        # Step 2.5.1: Move CNC arm to washing station 1 location first
        print(f"Step 2.5.1: Moving CNC to wash station 1 (X={WASH_STATION1_X}, Y={WASH_STATION1_Y}, Z=0)")
        cnc.move_to_point_safe(WASH_STATION1_X, WASH_STATION1_Y, 0, speed=3000)
        
        # Step 2.5.2: Start pump and run for 15 seconds
        print("Step 2.5.2: Starting pump system for 15 seconds...")
        if not reliable_pump_command(b"P1", "Start Pump 1"):
            raise Exception("Failed to start Pump 1")
        
        time.sleep(15)  # Pump runs for 15 seconds
        
        if not reliable_pump_command(b"SP1", "Stop Pump 1"):
            print("Warning: Failed to confirm Pump 1 stop")
        
        # Step 2.5.3: Start 12V DC motor 1 and perform oscillating wash movements
        print("Step 2.5.3: Starting 12V DC motor 1 and performing oscillating wash movements...")
        if not reliable_pump_command(b"M1", "Start 12V DC Motor 1"):
            raise Exception("Failed to start Motor 1")
            
        # Lower viscometer into washing position
        cnc.move_to_point(WASH_STATION1_X, WASH_STATION1_Y, WASH_STATION1_Z, speed=1000)
        
        # Perform 5 oscillating movements from x=383 to x=390 and back
        print("  Performing 5 oscillating wash movements...")
        for i in range(5):
            print(f"  Oscillation {i+1}/5: Moving to X=390")
            cnc.move_to_point(390, WASH_STATION1_Y, WASH_STATION1_Z, speed=1000)
            time.sleep(1)  # Brief pause at extended position
            print(f"  Oscillation {i+1}/5: Moving back to X=383")
            cnc.move_to_point(WASH_STATION1_X, WASH_STATION1_Y, WASH_STATION1_Z, speed=1000)
            time.sleep(1)  # Brief pause at home position
        
        # Step 2.5.4: Raise CNC arm to safe position and start reverse rinse cycle
        print("Step 2.5.4: Raising to safe position and starting reverse rinse cycle...")
        cnc.move_to_point(WASH_STATION1_X, WASH_STATION1_Y, 0, speed=500)
        
        if not reliable_pump_command(b"R1", "Start Reverse Rinse 1"):
            print("Warning: Failed to start reverse rinse")
            
        time.sleep(20)  # Reverse rinse cycle
        
        if not reliable_pump_command(b"SR1", "Stop Reverse Rinse 1"):
            print("Warning: Failed to confirm reverse rinse stop")
        
        # Step 2.5.5: Stop motor 1
        print("Step 2.5.5: Stopping motor 1...")
        if not reliable_pump_command(b"SM1", "Stop Motor 1"):
            print("Warning: Failed to confirm Motor 1 stop")
        
        # Step 2.5.6: Move CNC to washing station 2 location
        print(f"Step 2.5.6: Moving CNC to wash station 2 (X={WASH_STATION2_X}, Y={WASH_STATION2_Y}, Z=0)")
        cnc.move_to_point_safe(WASH_STATION2_X, WASH_STATION2_Y, 0, speed=3000)
        
        # Step 2.5.7: Start pump 3 for 15 seconds
        print("Step 2.5.7: Starting pump 3 for 15 seconds...")
        if not reliable_pump_command(b"P3", "Start Pump 3"):
            raise Exception("Failed to start Pump 3")
            
        time.sleep(15)
        
        if not reliable_pump_command(b"SP3", "Stop Pump 3"):
            print("Warning: Failed to confirm Pump 3 stop")
        
        # Step 2.5.8: Start 12V DC motor 2 and perform oscillating wash movements
        print("Step 2.5.8: Starting 12V DC motor 2 and performing oscillating wash movements...")
        if not reliable_pump_command(b"M2", "Start 12V DC Motor 2"):
            raise Exception("Failed to start Motor 2")
            
        # Lower viscometer into washing position
        cnc.move_to_point(WASH_STATION2_X, WASH_STATION2_Y, WASH_STATION2_Z, speed=1000)
        
        # Perform 5 oscillating movements from x=383 to x=390 and back
        print("  Performing 5 oscillating wash movements...")
        for i in range(5):
            print(f"  Oscillation {i+1}/5: Moving to X=390")
            cnc.move_to_point(390, WASH_STATION2_Y, WASH_STATION2_Z, speed=1000)
            time.sleep(1)  # Brief pause at extended position
            print(f"  Oscillation {i+1}/5: Moving back to X=383")
            cnc.move_to_point(WASH_STATION2_X, WASH_STATION2_Y, WASH_STATION2_Z, speed=1000)
            time.sleep(1)  # Brief pause at home position
        
        # Step 2.5.9: Raise CNC arm to safe position and start reverse rinse cycle
        print("Step 2.5.9: Raising CNC arm to safe position and starting reverse rinse cycle...")
        cnc.move_to_point(WASH_STATION2_X, WASH_STATION2_Y, 0, speed=500)
        
        if not reliable_pump_command(b"R2", "Start Reverse Rinse 2"):
            print("Warning: Failed to start reverse rinse 2")
            
        time.sleep(20)
        
        if not reliable_pump_command(b"SR2", "Stop Reverse Rinse 2"):
            print("Warning: Failed to confirm reverse rinse 2 stop")
        
        # Step 2.5.10: Stop motor 2
        print("Step 2.5.10: Stopping motor 2...")
        if not reliable_pump_command(b"SM2", "Stop Motor 2"):
            print("Warning: Failed to confirm Motor 2 stop")
        
        print(f"Step 2.5: Washing Station Sequence completed for Cell {global_cell}")
        
        # Final status check
        if hasattr(pump, 'get_status'):
            final_status = pump.get_status()
            if final_status and any(final_status.values()):
                print(f"WARNING: Some components still running after wash: {final_status}")
                # Emergency stop if anything is still running
                pump.send_tag(b"0")
                time.sleep(1)
        
    except Exception as e:
        print(f"Error during washing sequence for Cell {global_cell}: {e}")
        try:
            # Emergency stop pumps and motors in case of error
            print("Executing emergency stop...")
            pump.send_tag(b"0")  # Emergency stop all
            time.sleep(2)  # Give time for stop command
            # Try to move CNC to safe position
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
    cnc.move_to_point_safe(x_pos, y_pos, z_height, speed=3000)
    time.sleep(SETTLE_TIME)
    return x_pos, y_pos, z_height

def measure_torque_at_rpm(client: ViscometerClient, rpm: float) -> Optional[List[Dict]]:
    """Measure torque at a specific RPM, returning all individual measurements with timestamps"""
    MEASUREMENT_DURATION = 40.0      #35.0
    SAMPLE_INTERVAL = 10.0       #2.0

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

def test_cell_dynamic_z_series(cnc: CNC_Machine, client: ViscometerClient, global_cell: int, safe_z: float, max_z_travel: float) -> Dict[float, Dict[float, Optional[List[Dict]]]]:
    """Test dynamic analysis (multiple RPMs) across Z-gap range for one cell using global cell numbering"""
    row_number, local_cell = global_cell_to_row_and_local(global_cell)
    print(f"\n{'='*60}")
    print(f"DYNAMIC ANALYSIS - CELL {global_cell} (Row {row_number}, Local Cell {local_cell})")
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
                cnc.move_to_point(x_pos, y_pos, current_z, speed=Z_FEED_RATE)
                time.sleep(SETTLE_TIME)
            
            # Test all RPMs at this Z-height
            rpm_data, first_rpm_exceeded = test_dynamic_analysis_at_z(client, z_rounded)
            cell_z_rpm_data[z_rounded] = rpm_data
            
            # Check if first RPM exceeded threshold - if so, break entire cell
            if first_rpm_exceeded:
                print(f"  CELL TERMINATION: First RPM exceeded threshold at Z={z_rounded:.3f}")
                print(f"  Stopping Cell {global_cell} Z-series testing")
                break
                
            print(f"  Completed Z={z_rounded:.3f}: {len([t for t in rpm_data.values() if t is not None])}/{len(TEST_RPMS)} successful RPM tests")
            
        except Exception as e:
            print(f"  Error testing Cell {global_cell} at Z={z_rounded:.3f}: {e}")
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
        y_pos = BASE_Y + (local_cell - 1) * Y_OFFSET
        # Start viscometer at low RPM while moving to safe position
        #client.set_speed(0.5)
        cnc.move_to_point(x_pos, y_pos, z=0, speed=Z_FEED_RATE)
        time.sleep(1)
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
    
    print(f"Cell {global_cell} dynamic analysis completed: {len(cell_z_rpm_data)} Z-positions tested")
    return cell_z_rpm_data

def save_partial_data(all_data: Dict[int, Dict[float, Dict[float, Optional[List[Dict]]]]], 
                     timestamp: str, mode: str, completed_cells: List[int]) -> str:
    """Save partial results when experiment is terminated early"""
    if not all_data:
        print("No data collected to save.")
        return ""
    
    print(f"\nSAVING PARTIAL RESULTS...")
    print(f"Completed cells: {completed_cells}")
    
    # Create partial CSV filename with timestamp
    csv_filename = f"dynamic_analysis_{mode}_PARTIAL_{timestamp}.csv"
    
    with open(csv_filename, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        
        # Write metadata header
        csv_writer.writerow([f"# Dynamic Analysis - Mode: {mode.upper()} (PARTIAL RESULTS)"])
        csv_writer.writerow([f"# Test RPMs: {TEST_RPMS}"])
        csv_writer.writerow([f"# Timestamp: {timestamp}"])
        csv_writer.writerow([f"# Cell numbering: Row 1 = cells 1-6, Row 2 = cells 7-12, Row 3 = cells 13-18"])
        csv_writer.writerow([f"# Completed cells: {completed_cells}"])
        csv_writer.writerow([f"# WARNING: Experiment was terminated early - these are partial results"])
        csv_writer.writerow([])
        
        # Write column headers
        headers = ["row", "cell", "Z_Height_mm", "RPM", "Elapsed_Time_s", "Torque_%"]
        csv_writer.writerow(headers)
        
        # Write all individual measurements for completed cells
        for global_cell in sorted(all_data.keys()):
            row_number, local_cell = global_cell_to_row_and_local(global_cell)
            cell_data = all_data[global_cell]
            
            # Sort Z heights from highest to lowest
            z_heights = sorted(cell_data.keys(), reverse=True)
            
            for z_height in z_heights:
                if z_height in cell_data:
                    rpm_data = cell_data[z_height]
                    for rpm in TEST_RPMS:
                        measurements = rpm_data.get(rpm)
                        if measurements is not None:
                            for measurement in measurements:
                                data_row = [
                                    str(row_number),                              # row
                                    str(global_cell),                            # cell (global numbering)
                                    f"{z_height:.3f}",                          # Z_Height_mm
                                    f"{rpm:.1f}",                               # RPM
                                    f"{measurement['elapsed_time']:.2f}",        # Elapsed_Time_s
                                    f"{measurement['torque_percent']:.3f}"       # Torque_%
                                ]
                                csv_writer.writerow(data_row)
    
    print(f"Partial results saved to: {csv_filename}")
    return csv_filename

def save_dynamic_analysis_data(all_data: Dict[int, Dict[float, Dict[float, Optional[List[Dict]]]]], 
                              timestamp: str, mode: str) -> str:
    """Save dynamic analysis data - single CSV file for entire run with columns: row, cell, Z_Height_mm, RPM, Elapsed_Time_s, Torque_%"""
    
    # Create single CSV filename
    csv_filename = f"dynamic_analysis_{mode}_{timestamp}.csv"
    
    with open(csv_filename, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        
        # Write metadata header
        csv_writer.writerow([f"# Dynamic Analysis - Mode: {mode.upper()}"])
        csv_writer.writerow([f"# Test RPMs: {TEST_RPMS}"])
        csv_writer.writerow([f"# Timestamp: {timestamp}"])
        csv_writer.writerow([f"# Cell numbering: Row 1 = cells 1-6, Row 2 = cells 7-12, Row 3 = cells 13-18"])
        csv_writer.writerow([])
        
        # Write column headers
        headers = ["row", "cell", "Z_Height_mm", "RPM", "Elapsed_Time_s", "Torque_%"]
        csv_writer.writerow(headers)
        
        # Write all individual measurements
        for global_cell in sorted(all_data.keys()):
            row_number, local_cell = global_cell_to_row_and_local(global_cell)
            cell_data = all_data[global_cell]
            
            # Sort Z heights from highest to lowest
            z_heights = sorted(cell_data.keys(), reverse=True)
            
            for z_height in z_heights:
                if z_height in cell_data:
                    rpm_data = cell_data[z_height]
                    for rpm in TEST_RPMS:
                        measurements = rpm_data.get(rpm)
                        if measurements is not None:
                            for measurement in measurements:
                                data_row = [
                                    str(row_number),                              # row
                                    str(global_cell),                            # cell (global numbering)
                                    f"{z_height:.3f}",                          # Z_Height_mm
                                    f"{rpm:.1f}",                               # RPM
                                    f"{measurement['elapsed_time']:.2f}",        # Elapsed_Time_s
                                    f"{measurement['torque_percent']:.3f}"       # Torque_%
                                ]
                                csv_writer.writerow(data_row)
    
    print(f"All data saved to: {csv_filename}")
    return csv_filename

def main():
    print("="*80)
    print("MULTI-ROW DYNAMIC ANALYSIS - Z-GAP vs TORQUE at MULTIPLE RPMs")
    print(f"Testing RPMs: {TEST_RPMS}")
    print(f"Total available: {len(ROWS)} rows x {NUM_CELLS} cells = {len(ROWS) * NUM_CELLS} cells")
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
        return
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Initialize hardware with proper error handling
    cnc = None
    client = None
    pump = None
    
    try:
        print("Initializing CNC machine...")
        cnc = CNC_Machine(virtual=False)
        cnc.home()
        time.sleep(1.0)
        print("CNC machine initialized and homed")
    except Exception as e:
        print(f"ERROR initializing CNC machine: {e}")
        return
    
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
                time.sleep(1)
                print("ESP32 communication initialized (legacy mode)")
        else:
            # Legacy test
            pump.send_tag(b"ST")
            time.sleep(1)
            print("ESP32 communication initialized (legacy mode)")
            
        print("ESP32 pump controller initialized successfully")
        
    except Exception as e:
        print(f"ERROR initializing ESP32 pump controller: {e}")
        try:
            if cnc:
                cnc.home()
        except:
            pass
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
            if cnc:
                cnc.home()
        except:
            pass
        return
    
    # Data structure: all_data[global_cell] = cell_z_rpm_data
    all_data = {}
    completed_cells = []  # Track completed cells for partial saving
    
    try:
        print(f"\nStarting dynamic analysis...")
        print(f"Testing {len(selected_cells)} cells with {len(TEST_RPMS)} RPMs per Z-position")
        
        # Go through each selected cell
        for i, global_cell in enumerate(selected_cells):
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

            time.sleep(5)
            # Stop viscometer once at safe position
            client.stop()
            
            try:
                cell_data = test_cell_dynamic_z_series(cnc, client, global_cell, row_config['safe_z'], row_config['max_z_travel'])
                all_data[global_cell] = cell_data
                completed_cells.append(global_cell)
                print(f"Cell {global_cell} testing completed")
                
                # Perform washing sequence after each cell completion
                if pump:
                    perform_washing_sequence(cnc, pump, global_cell)
                else:
                    print(f"Warning: Pump not available, skipping washing sequence for Cell {global_cell}")
                    
                print(f"Cell {global_cell} fully completed (including wash)")
                
            except Exception as e:
                print(f"Error during testing of Cell {global_cell}: {e}")
                print(f"Saving partial results and terminating...")
                traceback.print_exc()
                # Save partial data before exiting
                if all_data:
                    save_partial_data(all_data, timestamp, mode, completed_cells)
                raise  # Re-raise to trigger cleanup
        
        # Save all data to single CSV file
        csv_filename = save_dynamic_analysis_data(all_data, timestamp, mode)
        
        print(f"\n{'='*80}")
        print("DYNAMIC ANALYSIS COMPLETED SUCCESSFULLY!")
        print(f"Mode: {mode.upper()}")
        print(f"Total cells tested: {len(completed_cells)}")
        print(f"Tested cells: {completed_cells}")
        print(f"Results saved to: {csv_filename}")
        print(f"{'='*80}")
        
    except KeyboardInterrupt:
        print(f"\n\nEXPERIMENT INTERRUPTED BY USER (Ctrl+C)")
        print(f"Saving partial results...")
        if all_data:
            partial_filename = save_partial_data(all_data, timestamp, mode, completed_cells)
            print(f"Partial results saved to: {partial_filename}")
        else:
            print("No data collected to save.")
        
    except Exception as e:
        print(f"ERROR during dynamic analysis: {e}")
        print(f"Saving partial results...")
        traceback.print_exc()
        if all_data:
            partial_filename = save_partial_data(all_data, timestamp, mode, completed_cells)
            print(f"Partial results saved to: {partial_filename}")
        else:
            print("No data collected to save.")
    
    finally:
        # Safely home the CNC machine and close connections
        try:
            print("\nCleaning up...")
            if pump:
                try:
                    print("Stopping all ESP32 pumps and motors...")
                    if hasattr(pump, 'send_command_with_ack'):
                        # Try with acknowledgment
                        success = pump.send_command_with_ack(b"0", timeout=5.0, max_retries=2)
                        if success:
                            print("✓ ESP32 emergency stop confirmed")
                        else:
                            print("⚠ ESP32 emergency stop ACK failed, using legacy")
                            pump.send_tag(b"0")
                            time.sleep(2)
                    else:
                        pump.send_tag(b"0")  # Emergency stop all pumps
                        time.sleep(2)
                    
                    # Final status check
                    if hasattr(pump, 'get_status'):
                        final_status = pump.get_status()
                        if final_status and any(final_status.values()):
                            print(f"⚠ WARNING: Some components may still be running: {final_status}")
                        else:
                            print("✓ All ESP32 components confirmed stopped")
                    
                    pump.close()
                    print("ESP32 pump controller stopped and closed")
                except Exception as e:
                    print(f"Warning: Error stopping pump: {e}")
            
            if client:
                client.stop()
                client.close()
                print("Viscometer connection closed")
        except Exception as e:
            print(f"Warning: Error closing connections: {e}")
        
        try:
            if cnc:
                cnc.home()
                print("CNC machine homed safely")
        except Exception as e:
            print(f"Warning: Error homing CNC: {e}")
        
        print("Cleanup completed")

if __name__ == "__main__":
    main()
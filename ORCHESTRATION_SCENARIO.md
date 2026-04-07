# CNC-Viscometer-Washing Station Orchestration Scenario

## System Overview

This document provides a complete orchestration reference for the automated viscosity measurement system that coordinates:
- **CNC Machine**: 3-axis positioning system with viscometer mounted on arm
- **Viscometer**: Brookfield DV2T Pro viscometer for torque/viscosity measurements
- **ESP32 Washing Station**: Multi-pump cleaning system with 12V DC motor
- **Sample Layout**: 18 cells arranged in 3 rows (6 cells per row)

## Hardware Configuration

### Sample Cell Layout
```
Row 1 (Cells 1-6):   BASE_X = 10mm,  Z_safe = -65.5mm, Z_max = -66.5mm
Row 2 (Cells 7-12):  BASE_X = 85mm,  Z_safe = -65.5mm, Z_max = -66.5mm  
Row 3 (Cells 13-18): BASE_X = 309mm, Z_safe = -64.5mm, Z_max = -65.5mm

Y-positions: BASE_Y = 62mm, Y_OFFSET = 67mm per cell
```

### Washing Station Configuration
```
Wash Station 1: X = 383mm, Y = 68mm,  Z = -67mm (contact)
Wash Station 2: X = 383mm, Y = 147mm, Z = -66mm (contact) 
Wash Positions: Z = 0mm (safe position above contact)
```

### Communication Interfaces
- **CNC**: COM12 @ 115200 baud (GRBL protocol)
- **Viscometer**: COM6 @ 115200 baud (via 32-bit Python subprocess)
- **ESP32 Pumps**: COM11 @ 115200 baud (custom protocol)

## Complete Orchestration Workflow

### Phase 1: System Initialization

```python
# 1.1 Initialize all hardware connections
cnc = CNC_Machine(virtual=False)
pump = PumpESP32(port="COM11", baud=115200, virtual=False)
client = ViscometerClient(PYTHON32, worker_path)

# 1.2 Home CNC machine and settle
cnc.home()
time.sleep(1.0)

# 1.3 Open communication channels
pump.open()
client.init(port="COM6", baud=115200, timeout=1.0, spindle_k=992.47)

# 1.4 Configure test parameters  
TEST_RPMS = [3.4]  # Primary test RPM (expandable to [3.4, 0.5, 1.0, 5.0, 10.0, 20.0, 50.0])
Z_STEP_SIZE = -0.5mm  # Incremental Z movement (reduced from -1mm)
TORQUE_BREAK_THRESHOLD = 1000.0%  # Safety limit
SETTLEMENT_TIME = 1.0s  # Mechanical settling after movement
```

### Phase 2: Cell Processing Loop (Repeat for each selected cell)

For each cell in the test sequence:

#### Step 2.1: Cell Selection & Preparation
```python
# Get selected cells based on mode configuration
mode, selected_cells = get_selected_cells()  # Returns "custom", [1, 8] etc.

# Convert global cell to row coordinates
row_number, local_cell = global_cell_to_row_and_local(global_cell)

# Find row configuration with Z-parameters
row_config = ROWS[row_number-1]  # Contains base_x, safe_z, max_z_travel
safe_z = row_config['safe_z']
max_z_travel = row_config['max_z_travel']

# Auto-zero viscometer before each cell
client.zero()
time.sleep(5)
client.stop()
```

#### Step 2.2: Move to Cell Position
```python
# Calculate target coordinates
base_x = row_config['base_x']
target_x = base_x
target_y = BASE_Y + (local_cell - 1) * Y_OFFSET

# Safe movement with Z-retraction  
cnc.move_to_point_safe(target_x, target_y, safe_z, speed=3000)
time.sleep(SETTLE_TIME)
```

#### Step 2.3: Dynamic Z-Series Analysis
```python
current_z = safe_z
step_count = 0

while current_z >= max_z_travel:
    step_count += 1
    
    # 2.3.1 Position viscometer at current Z-height
    if step_count == 1:
        # First movement - use safe movement
        cnc.move_to_point_safe(target_x, target_y, current_z, speed=3000)
    else:
        # Subsequent movements - direct Z movement without retraction
        cnc.move_to_point(target_x, target_y, current_z, speed=Z_FEED_RATE)
    time.sleep(SETTLE_TIME)
    
    # 2.3.2 RPM Analysis at Current Z-Height
    for i, rpm in enumerate(TEST_RPMS):
        # Set spindle speed and settle  
        client.set_speed(rpm)
        time.sleep(DWELL_SECONDS)  # 2.0s spindle stabilization
        
        # Collect measurements over 40-second duration with 10s sampling
        measurements = []
        start_time = time.time()
        next_sample_time = start_time + SAMPLE_INTERVAL  # 10.0s intervals
        
        while time.time() - start_time < MEASUREMENT_DURATION:  # 40.0s total
            current_time = time.time()
            if current_time >= next_sample_time:
                try:
                    data = client.read_single(timeout=2.0)
                    if data and data.get("torque_valid") and data.get("torque_percent") is not None:
                        measurements.append({
                            "timestamp": current_time,
                            "elapsed_time": current_time - start_time,
                            "torque_percent": data["torque_percent"], 
                            "rpm": rpm
                        })
                    next_sample_time += SAMPLE_INTERVAL
                except Exception as e:
                    print(f"Measurement error at RPM {rpm}: {e}")
            time.sleep(0.1)
        
        # Safety check: abort if torque exceeds threshold
        if measurements:
            max_torque = max(abs(m["torque_percent"]) for m in measurements)
            if max_torque >= TORQUE_BREAK_THRESHOLD:
                if i == 0:  # First RPM failed - critical, break entire cell
                    print(f"CRITICAL: First RPM {rpm} exceeded threshold - terminating cell")
                    break
                else:  # Later RPM failed - stop RPM sweep at this Z-level
                    print(f"SAFETY: RPM {rpm} exceeded threshold - stopping Z-level RPM sweep")
                    break
        
        client.stop()
        time.sleep(INTER_RPM_PAUSE)  # 2.0s between RPMs
    
    # 2.3.3 Check for critical failure and increment Z position
    if first_rpm_exceeded_threshold:
        break  # Terminate entire cell if first RPM failed
    current_z += Z_STEP_SIZE  # Move deeper by 0.5mm
```

#### Step 2.4: Return to Safe Position
```python
# Move viscometer to safe height while stopped
cnc.move_to_point(target_x, target_y, z=0, speed=Z_FEED_RATE)
client.stop()
time.sleep(1)
```

#### Step 2.5: Enhanced Two-Station Washing Sequence
```python
# 2.5.1 Move to Washing Station 1
print("Moving CNC to wash station 1...")
cnc.move_to_point_safe(WASH_STATION1_X, WASH_STATION1_Y, 0, speed=3000)

# 2.5.2 Initial Pump Cycle (Station 1)  
print("Starting pump 1 for 10 seconds...")
pump.send_tag(b"P1")  # Start Pump 1
time.sleep(10)
pump.send_tag(b"SP1") # Stop Pump 1

# 2.5.3 Mechanical Wash Cycle (Station 1)
print("Starting motor 1 and lowering viscometer...")
pump.send_tag(b"M1")  # Start 12V DC Motor 1
cnc.move_to_point(WASH_STATION1_X, WASH_STATION1_Y, WASH_STATION1_Z, speed=1000)
time.sleep(60)  # 60-second wash cycle

# 2.5.4 Raise and Rinse Cycle (Station 1)
print("Raising and starting reverse rinse...")
cnc.move_to_point(WASH_STATION1_X, WASH_STATION1_Y, 0, speed=500)
pump.send_tag(b"R1")  # Start reverse rinse (Pump 1 reversed)
time.sleep(15)  # 15-second rinse 
pump.send_tag(b"SR1") # Stop reverse rinse
pump.send_tag(b"SM1") # Stop Motor 1

# 2.5.5 Move to Washing Station 2
print("Moving CNC to wash station 2...")
cnc.move_to_point_safe(WASH_STATION2_X, WASH_STATION2_Y, 0, speed=3000)

# 2.5.6 Initial Pump Cycle (Station 2)
print("Starting pump 3 for 10 seconds...")
pump.send_tag(b"P3")  # Start Pump 3
time.sleep(10)
pump.send_tag(b"SP3") # Stop Pump 3

# 2.5.7 Mechanical Wash Cycle (Station 2)
print("Starting motor 2 and lowering viscometer...")
pump.send_tag(b"M2")  # Start 12V DC Motor 2
cnc.move_to_point(WASH_STATION2_X, WASH_STATION2_Y, WASH_STATION2_Z, speed=1000)
time.sleep(60)  # 60-second wash cycle

# 2.5.8 Final Raise and Rinse (Station 2) 
print("Raising and starting reverse rinse...")
cnc.move_to_point(WASH_STATION2_X, WASH_STATION2_Y, 0, speed=500)
pump.send_tag(b"R2")  # Start reverse rinse (Pump 3 reversed)
time.sleep(15)  # 15-second rinse
pump.send_tag(b"SR2") # Stop reverse rinse  
pump.send_tag(b"SM2") # Stop Motor 2

print("Washing sequence completed")
```

### Phase 3: Error Handling & Recovery

#### Torque Safety System
```python
# Critical failure: First RPM exceeds threshold or returns invalid data
if i == 0 and (max_torque >= TORQUE_BREAK_THRESHOLD or measurements is None):
    print("CRITICAL: First RPM failed - terminating entire cell")
    first_rpm_exceeded_threshold = True
    # Fill remaining RPMs with None and break cell testing
    for remaining_rpm in TEST_RPMS[i+1:]:
        rpm_torque_data[remaining_rpm] = None
    break

# High resistance condition: Later RPM fails
elif i > 0 and (max_torque >= TORQUE_BREAK_THRESHOLD or measurements is None):
    print("RESISTANCE: High resistance detected - stopping Z-level RPM sweep")
    # Fill remaining RPMs with None and break Z-level testing
    for remaining_rpm in TEST_RPMS[i+1:]:
        rpm_torque_data[remaining_rpm] = None
    break
```

#### Communication Error Recovery
```python
try:
    # Normal measurement operations
    data = client.read_single(timeout=2.0)
except Exception as e:
    print(f"Measurement error at RPM {rpm}: {e}")
    # Continue with next measurement attempt

# Hardware initialization with proper cleanup
except Exception as e:
    print(f"ERROR initializing hardware: {e}")
    try:
        if cnc:
            cnc.home()  # Safe position
        if pump:
            pump.send_tag(b"0")  # Emergency stop
            pump.close()
    except:
        pass
    return
```

#### Washing Sequence Error Handling
```python
def perform_washing_sequence(cnc, pump, global_cell):
    try:
        # Normal washing operations
        pass
    except Exception as e:
        print(f"Error during washing sequence for Cell {global_cell}: {e}")
        try:
            pump.send_tag(b"0")  # Emergency stop all pumps
            cnc.move_to_point(WASH_STATION1_X, WASH_STATION1_Y, 0, speed=500)
        except:
            pass
        raise  # Re-raise for outer handling
```

#### Experiment Interruption & Data Preservation
```python
try:
    # Main testing loop
    pass
except KeyboardInterrupt:
    print("EXPERIMENT INTERRUPTED BY USER (Ctrl+C)")
    if all_data:
        save_partial_data(all_data, timestamp, mode, completed_cells)
except Exception as e:
    print(f"ERROR during dynamic analysis: {e}")
    traceback.print_exc()
    if all_data:
        save_partial_data(all_data, timestamp, mode, completed_cells)
finally:
    # Always cleanup hardware safely
    cleanup_hardware(cnc, pump, client)
```

### Phase 4: System Shutdown & Data Management

#### Hardware Cleanup Sequence
```python
def cleanup_hardware(cnc, pump, client):
    """Safe shutdown of all hardware components"""
    try:
        # 4.1 Stop all pumps and motors with debug output
        if pump:
            pump.send_tag(b"0")  # Emergency stop all components
            pump.close()
            print("ESP32 pump controller stopped and closed")
        
        # 4.2 Stop and close viscometer
        if client:
            client.stop()  # Stop spindle
            client.close()  # Close 32-bit Python subprocess
            print("Viscometer connection closed")
            
    except Exception as e:
        print(f"Warning: Error closing connections: {e}")
    
    try:
        # 4.3 Return CNC to home position safely
        if cnc:
            cnc.home()
            print("CNC machine homed safely")
    except Exception as e:
        print(f"Warning: Error homing CNC: {e}")
    
    print("Cleanup completed")
```

#### Data Management & File Output
```python
# 4.4 Save results based on completion status
if experiment_completed_successfully:
    # Save complete results
    csv_filename = save_dynamic_analysis_data(all_data, timestamp, mode)
    print(f"Results saved to: {csv_filename}")
else:
    # Save partial results with special naming
    partial_filename = save_partial_data(all_data, timestamp, mode, completed_cells)
    print(f"Partial results saved to: {partial_filename}")

# 4.5 Generate comprehensive completion report
print(f"{'='*80}")
print("DYNAMIC ANALYSIS SUMMARY")
print(f"Mode: {mode.upper()}")
print(f"Attempted cells: {len(selected_cells)}")
print(f"Completed cells: {len(completed_cells)}")
print(f"Successful cells: {completed_cells}")
if len(completed_cells) < len(selected_cells):
    failed_cells = [cell for cell in selected_cells if cell not in completed_cells]
    print(f"Failed/Skipped cells: {failed_cells}")
print(f"{'='*80}")
```

#### Output File Structure
```python
# Complete results filename format
"dynamic_analysis_{mode}_{timestamp}.csv"

# Partial results filename format  
"dynamic_analysis_{mode}_PARTIAL_{timestamp}.csv"

# CSV file structure
headers = ["row", "cell", "Z_Height_mm", "RPM", "Elapsed_Time_s", "Torque_%"]

# Metadata header includes:
# - Test RPMs used
# - Timestamp 
# - Cell numbering convention
# - Completion status (partial vs complete)
# - Completed cell list (for partial results)
```

## Timing Parameters (Configurable)

### Movement Timing
- **SETTLE_TIME**: 1 second (mechanical settling after movement)
- **Z_FEED_RATE**: 500 mm/min (vertical movement speed)
- **Z_STEP_SIZE**: -0.5mm (incremental Z movement depth - reduced precision)

### Measurement Timing  
- **MEASUREMENT_DURATION**: 40 seconds (data collection per RPM)
- **SAMPLE_INTERVAL**: 10 seconds (between torque readings - increased from 2s)
- **DWELL_SECONDS**: 2 seconds (RPM change settling time)
- **INTER_RPM_PAUSE**: 2 seconds (between RPM tests)
- **AUTO_ZERO_DELAY**: 5 seconds (viscometer auto-zero settling time)

### Washing Timing (Per Station - Actual Implementation)
- **Initial pump cycle**: 10 seconds (pump only)
- **DC motor wash cycle**: 60 seconds (12V DC motor + simultaneous CNC lowering)
- **Reverse rinse cycle**: 15 seconds (reverse pump flow)
- **Total wash time per station**: ~85 seconds
- **Total wash time per cell**: ~170 seconds (both stations)

## Enhanced ESP32 Washing Station Commands

### Individual Component Control Protocol (Primary Interface)
```python
# Pump Control Commands
b"P1"  # Start Pump 1 (wash station 1 cleaning) - 170 PWM speed
b"SP1" # Stop Pump 1
b"P3"  # Start Pump 3 (wash station 2 cleaning) - 170 PWM speed  
b"SP3" # Stop Pump 3

# Motor Control Commands (12V DC Motors)
b"M1"  # Start 12V DC Motor 1 (wash station 1 agitation) - 160 PWM speed
b"SM1" # Stop 12V DC Motor 1
b"M2"  # Start 12V DC Motor 2 (wash station 2 agitation) - 160 PWM speed
b"SM2" # Stop 12V DC Motor 2

# Reverse Rinse Commands (Pump Direction Reversal)
b"R1"  # Start reverse rinse cycle (pump 1 reversed for station 1) - 170 PWM speed
b"SR1" # Stop reverse rinse (station 1)
b"R2"  # Start reverse rinse cycle (pump 3 reversed for station 2) - 170 PWM speed
b"SR2" # Stop reverse rinse (station 2)

# System Control & Monitoring
b"0"   # Emergency stop all pumps and motors
b"ST"  # Status request (returns detailed component states with debugging info)
```

### Component State Management & Conflict Detection
The ESP32 Arduino implementation includes sophisticated state tracking:
- **State Variables**: `pump1_running`, `motor1_running`, `reverse1_running`, etc.
- **Conflict Prevention**: Pumps and their reverse modes cannot run simultaneously
- **State Reporting**: Real-time monitoring of all component states
- **Debug Logging**: Detailed serial output for troubleshooting

### Legacy Sequence Commands (Backward Compatibility)
```python
# Automated Sequence Commands (for backward compatibility)
b"1"   # Run complete wash station 1 sequence (P1→M1→R1)
b"2"   # Run complete wash station 2 sequence (P3→M2→R2)
b"3"   # Run complete wash station 3 sequence (P5→M3→reverse) [Future expansion]
```

### Washing Station Hardware Configuration
```
Driver 1 (Wash Station 1):
- ENABLE1/IN1/IN2: Pump 1 (170 PWM) / Reverse 1 rinse (170 PWM)
- ENABLE2/IN3/IN4: 12V DC Motor 1 agitation (160 PWM)

Driver 2 (Wash Station 2):  
- ENABLE3/IN5/IN6: Pump 3 (170 PWM) / Reverse 2 rinse (170 PWM)
- ENABLE4/IN7/IN8: 12V DC Motor 2 agitation (160 PWM)

Driver 3 (Future Expansion):
- ENABLE5/IN9/IN10: Pump 5 (210 PWM) / Pump 6 reverse (210 PWM)
- ENABLE6/IN11/IN12: 12V DC Motor 3 agitation (160 PWM)
```

### Enhanced Status Reporting
The `ST` command returns comprehensive system status:
```
=== COMPONENT STATUS REPORT ===
Wash Station 1:
  Pump 1: RUNNING/STOPPED
  Motor 1: RUNNING/STOPPED  
  Reverse 1: RUNNING/STOPPED
Wash Station 2:
  Pump 3: RUNNING/STOPPED
  Motor 2: RUNNING/STOPPED
  Reverse 2: RUNNING/STOPPED
Future Use:
  Pump 5: RUNNING/STOPPED
  Motor 3: RUNNING/STOPPED

Timing Constants:
  Pump Stage: 10 seconds
  Wash Stage: 60 seconds  
  Rinse Stage: 15 seconds
================================
```

### PWM Speed Optimization
- **Pump Speeds**: 170/255 PWM (~67% power) for cleaning and rinse pumps
- **Motor Speeds**: 160/255 PWM (~63% power) for 12V DC agitation motors
- **Future Pump Speeds**: 210/255 PWM (~82% power) for higher-capacity pumps

## Data Collection & Storage

### Data Structure
```python
# Per-cell data structure
cell_data = {
    global_cell_number: {
        z_position: {
            rpm_value: [
                {
                    "timestamp": float,
                    "elapsed_time": float, 
                    "torque_percent": float,
                    "rpm": float
                }
            ]
        }
    }
}
```

### Output Files
- **Full results**: `dynamic_analysis_{mode}_{timestamp}.csv`
- **Partial results**: `dynamic_analysis_{mode}_PARTIAL_{timestamp}.csv`
- **Metadata**: Test parameters, timestamps, cell mappings

## Operating Modes

### Mode Selection & Configuration (No Runtime Input Required)
```python
# Set testing mode at top of all_cells_with_wash.py
TESTING_MODE = "custom"  # Options: "full", "row", "custom"

# FOR FULL MODE: Test all 18 cells (1-18)
# No additional configuration needed

# FOR ROW MODE: Specify which rows to test (1, 2, 3)
SELECTED_ROWS = [2]      # Example: Test row 2 (cells 7-12)

# FOR CUSTOM MODE: Specify which cells to test (1-18)
SELECTED_CELLS = [1, 8]  # Example: Test only cells 1 and 8
```

### Cell Selection Logic & Validation
```python
def get_selected_cells():
    """Validates configuration and returns mode and cell list"""
    if TESTING_MODE == "full":
        return "full", list(range(1, 19))  # All 18 cells
    
    elif TESTING_MODE == "row":
        # Convert rows to global cell numbers
        global_cells = []
        for row in SELECTED_ROWS:
            for local_cell in range(1, 7):  # 6 cells per row
                global_cells.append(row_and_local_to_global_cell(row, local_cell))
        return "row", sorted(global_cells)
    
    elif TESTING_MODE == "custom":
        return "custom", sorted(SELECTED_CELLS)
```

### Cell Coordinate Mapping
```python
def global_cell_to_row_and_local(global_cell: int) -> Tuple[int, int]:
    """Convert global cell number (1-18) to row and local cell (1-6)"""
    row = ((global_cell - 1) // 6) + 1
    local_cell = ((global_cell - 1) % 6) + 1
    return row, local_cell

def row_and_local_to_global_cell(row: int, local_cell: int) -> int:
    """Convert row and local cell to global cell number (1-18)"""
    return (row - 1) * 6 + local_cell
```

### Error Handling & Validation
- **Row validation**: Ensures SELECTED_ROWS contains only [1, 2, 3]
- **Cell validation**: Ensures SELECTED_CELLS contains only [1-18]
- **Configuration validation**: Validates mode selection before starting

## Safety & Quality Features

### Enhanced Torque Safety System
```python
# Multi-level safety with different responses
TORQUE_BREAK_THRESHOLD = 1000.0%  # Safety limit for all measurements

# Critical failure detection (first RPM)
if i == 0 and max_torque >= TORQUE_BREAK_THRESHOLD:
    print("CRITICAL: First RPM exceeded threshold - terminating entire cell")
    first_rpm_exceeded_threshold = True
    break  # Stop all testing for this cell

# Progressive failure detection (later RPMs)  
elif i > 0 and max_torque >= TORQUE_BREAK_THRESHOLD:
    print("SAFETY: Later RPM exceeded threshold - stopping Z-level RPM sweep")
    break  # Stop RPM sweep at current Z-level, continue to next Z-level

# High resistance detection (invalid measurements)
if measurements is None:
    if i == 0:
        print("CRITICAL: First RPM returned invalid torque (high resistance)")
        first_rpm_exceeded_threshold = True
    else:
        print("RESISTANCE: High resistance detected at this Z-level")
    break
```

### Data Quality Assurance
```python
# Measurement validation with detailed reporting
for measurement in measurements:
    if data and data.get("torque_valid") and data.get("torque_percent") is not None:
        # Valid measurement collected
        measurement = {
            "timestamp": current_time,
            "elapsed_time": current_time - start_time,
            "torque_percent": data["torque_percent"],
            "rpm": rpm
        }
    else:
        # Skip invalid measurements
        continue

# Statistical reporting per RPM
if measurements:
    torque_values = [m["torque_percent"] for m in measurements]
    avg_torque = sum(torque_values) / len(torque_values)
    min_torque = min(torque_values)
    max_torque = max(torque_values)
    print(f"RPM {rpm}: {len(measurements)} samples, Avg: {avg_torque:.2f}%, Range: {min_torque:.2f}% to {max_torque:.2f}%")
```

### Automated Data Recovery & Preservation
```python
# Real-time progress tracking
completed_cells = []  # Track successful cell completions

# Automatic partial data saving on interruption
try:
    # Normal testing operations
except (KeyboardInterrupt, Exception):
    if all_data:
        save_partial_data(all_data, timestamp, mode, completed_cells)
    
# Partial data includes:
# - All measurements from completed cells
# - Metadata about completion status
# - Clear identification as partial results
# - List of successfully completed cells
```

### Hardware State Management
```python
# ESP32 component state tracking with conflict prevention
# State variables: pump1_running, motor1_running, reverse1_running, etc.

# Conflict detection
if pump1_running and reverse1_running:
    print("ERROR: Pump 1 conflict - cannot run pump and reverse simultaneously")
    return False

# Real-time status reporting
b"ST"  # Returns comprehensive system status for debugging
```

### Auto-Zeroing & Calibration
```python
# Automated viscometer zeroing before each cell
try:
    print(f"Auto-zeroing viscometer for Cell {global_cell}...")
    client.zero()
    time.sleep(5)  # Allow auto-zero to complete
    client.stop()
    print("Viscometer auto-zero completed")
except Exception as e:
    print(f"Warning: Failed to auto-zero viscometer: {e}")
    # Continue with testing - non-critical warning
```

### Error Categorization & Response
```python
# Critical errors: Stop entire experiment
# - CNC initialization failure
# - Viscometer initialization failure  
# - First RPM threshold exceeded

# Warning errors: Log and continue
# - Auto-zero failure
# - Individual measurement timeout
# - Washing sequence communication errors

# Recovery errors: Attempt recovery then continue
# - Communication timeouts
# - Partial measurement failures
# - Non-critical hardware responses
```

## Maintenance & Calibration Points

### Regular Calibration
- **Z-axis calibration**: Verify contact detection accuracy
- **Torque calibration**: Validate viscometer readings
- **Pump flow rates**: Check washing effectiveness
- **Position accuracy**: Verify cell coordinate precision

### Preventive Maintenance
- **Spindle cleaning verification**: Post-wash inspection
- **Pump system maintenance**: Flow rate and pressure checks
- **CNC accuracy verification**: Position repeatability tests
- **Communication health**: Serial port reliability monitoring

---

This orchestration scenario provides a complete reference framework that you can customize and revise based on your specific requirements. All timing parameters, safety thresholds, and operational sequences are configurable through the parameter definitions at the top of your script.
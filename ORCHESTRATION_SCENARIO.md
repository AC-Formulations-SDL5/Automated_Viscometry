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
Wash Station 2: X = 383mm, Y = 147mm, Z = -67mm (contact)
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
pump = PumpESP32("COM11", 115200, virtual=False)
viscometer = ViscometerClient(PYTHON32, "viscometer_worker_32.py")

# 1.2 Home CNC machine
cnc.home()  # Move to (0,0,0) reference position

# 1.3 Open communication channels
pump.open()
viscometer.init(port="COM6", baud=115200, timeout=1.0, spindle_k=992.47)

# 1.4 Configure test parameters
TEST_RPMS = [3.0]  # Expandable to [3.0, 0.5, 1.0, 5.0, 10.0, 20.0, 50.0]
Z_STEP_SIZE = -1mm  # Incremental Z movement
TORQUE_BREAK_THRESHOLD = 1000.0%  # Safety limit
```

### Phase 2: Cell Processing Loop (Repeat for each selected cell)

For each cell in the test sequence:

#### Step 2.1: Pre-Movement Preparation
```python
# Calculate target coordinates
row_number, local_cell = global_cell_to_row_and_local(global_cell)
base_x = ROWS[row_number-1]['base_x']
target_x = base_x
target_y = BASE_Y + (local_cell - 1) * Y_OFFSET
safe_z = ROWS[row_number-1]['safe_z']
max_z = ROWS[row_number-1]['max_z_travel']
```

#### Step 2.2: Move to Cell Position
```python
# Safe movement with Z-retraction
cnc.move_to_point_safe(target_x, target_y, safe_z, speed=3000)
time.sleep(SETTLE_TIME)  # 1 second mechanical settling
```

#### Step 2.3: Dynamic Z-Series Analysis
```python
current_z = safe_z
step_count = 0

while current_z >= max_z_travel:
    step_count += 1
    
    # 2.3.1 Position viscometer at current Z-height
    if step_count == 1:
        cnc.move_to_point_safe(target_x, target_y, current_z, speed=3000)
    else:
        cnc.move_to_point(target_x, target_y, current_z, speed=Z_FEED_RATE)
    time.sleep(SETTLE_TIME)
    
    # 2.3.2 RPM Analysis at Current Z-Height
    for rpm in TEST_RPMS:
        # Set spindle speed
        viscometer.set_speed(rpm)
        time.sleep(DWELL_SECONDS)  # Allow spindle to stabilize
        
        # Collect measurements over 40-second duration
        measurements = []
        start_time = time.time()
        
        while time.time() - start_time < MEASUREMENT_DURATION:
            try:
                data = viscometer.read_single(timeout=2.0)
                if data and data["torque_valid"]:
                    measurements.append({
                        "timestamp": time.time(),
                        "elapsed_time": time.time() - start_time,
                        "torque_percent": data["torque_percent"],
                        "rpm": rpm
                    })
            except Exception as e:
                print(f"Measurement error: {e}")
            time.sleep(0.1)  # 100ms sampling interval
        
        # Safety check: abort if torque exceeds threshold
        if measurements:
            max_torque = max(abs(m["torque_percent"]) for m in measurements)
            if max_torque >= TORQUE_BREAK_THRESHOLD:
                print(f"SAFETY: Torque {max_torque}% exceeds threshold")
                break
        
        viscometer.stop()
        time.sleep(INTER_RPM_PAUSE)
    
    # 2.3.3 Increment to next Z position
    current_z += Z_STEP_SIZE  # Move deeper by 1mm
```

#### Step 2.4: Return to Safe Position
```python
# Move viscometer to safe height while spinning at low RPM
cnc.move_to_point(target_x, target_y, z=0, speed=Z_FEED_RATE)
viscometer.stop()
time.sleep(1)
```

#### Step 2.5: Enhanced Washing Station Sequence (Two Stations)
```python
# 2.5.1 Move CNC arm to washing station 1 location first
print("Step 2.5.1: Moving CNC to wash station 1...")
cnc.move_to_point_safe(WASH_STATION1_X, WASH_STATION1_Y, 0, speed=3000)

# 2.5.2 Start pump and run for 10 seconds
print("Step 2.5.2: Starting pump system for 10 seconds...")
pump.send_tag(b"P1")  # Start Pump 1 only
time.sleep(10)  # Pump runs for 10 seconds
pump.send_tag(b"SP1") # Stop Pump 1

# 2.5.3 Start 12V DC motor 1 for 60 seconds and simultaneously lower CNC arm
print("Step 2.5.3: Starting 12V DC motor 1 and lowering viscometer...")
pump.send_tag(b"M1")  # Start 12V DC motor 1
# Simultaneously lower viscometer into washing position
cnc.move_to_point(WASH_STATION1_X, WASH_STATION1_Y, WASH_STATION1_Z, speed=1000)
time.sleep(60)  # 12V DC motor 1 washing action for 60 seconds

# 2.5.4 Raise CNC arm to safe position and start reverse rinse cycle
print("Step 2.5.4: Raising to safe position and starting reverse rinse cycle...")
cnc.move_to_point(WASH_STATION1_X, WASH_STATION1_Y, 0, speed=500)
pump.send_tag(b"R1")  # Start reverse rinse cycle
time.sleep(15)  # Reverse rinse cycle
pump.send_tag(b"SR1") # Stop reverse rinse

# 2.5.5 Stop all pumps and motor 1
print("Step 2.5.5: Stopping all pumps and motor 1...")
pump.send_tag(b"SM1") # Stop motor 1

# 2.5.6 Move CNC to washing station 2 location
print("Step 2.5.6: Moving CNC to wash station 2...")
cnc.move_to_point_safe(WASH_STATION2_X, WASH_STATION2_Y, 0, speed=3000)

# 2.5.7 Start 12V DC motor 2 for 60 seconds and simultaneously lower CNC arm
print("Step 2.5.7: Starting 12V DC motor 2 and lowering viscometer...")
pump.send_tag(b"M2")  # Start 12V DC motor 2
# Simultaneously lower viscometer into washing position
cnc.move_to_point(WASH_STATION2_X, WASH_STATION2_Y, WASH_STATION2_Z, speed=1000)
time.sleep(60)  # 12V DC motor 2 washing action for 60 seconds

# 2.5.8 Raise CNC arm to safe position
print("Step 2.5.8: Raising CNC arm to safe position...")
cnc.move_to_point(WASH_STATION2_X, WASH_STATION2_Y, 0, speed=500)

# 2.5.9 Stop motor 2
print("Step 2.5.9: Stopping motor 2...")
pump.send_tag(b"SM2") # Stop motor 2
```

### Phase 3: Error Handling & Recovery

#### Emergency Procedures
```python
# 3.1 Torque Threshold Exceeded
if max_torque >= TORQUE_BREAK_THRESHOLD:
    viscometer.stop()
    cnc.move_to_point(current_x, current_y, 0, speed=500)  # Safe retraction
    if first_rpm_exceeded:
        break  # Skip remaining cells if first RPM fails

# 3.2 Communication Errors
try:
    # Normal operations
except Exception as e:
    print(f"Error: {e}")
    pump.send_tag(b"0")  # Emergency stop pumps
    viscometer.stop()    # Stop spindle
    cnc.move_to_point(current_x, current_y, 0, speed=500)  # Safe position

# 3.3 Partial Data Save on Interruption
if KeyboardInterrupt or SystemError:
    save_partial_data(collected_data, timestamp, mode, completed_cells)
```

### Phase 4: System Shutdown

```python
# 4.1 Return CNC to home position
cnc.home()

# 4.2 Stop all devices
viscometer.stop()
viscometer.close()
pump.send_tag(b"0")  # Ensure all pumps stopped
pump.close()

# 4.3 Save final results
save_results_to_csv(all_collected_data, timestamp, mode)
```

## Timing Parameters (Configurable)

### Movement Timing
- **SETTLE_TIME**: 1 second (mechanical settling after movement)
- **Z_FEED_RATE**: 500 mm/min (vertical movement speed)
- **SPINDLE_SETTLE_TIME**: 1 second (RPM stabilization time)

### Measurement Timing  
- **MEASUREMENT_DURATION**: 40 seconds (data collection per RPM)
- **SAMPLE_INTERVAL**: 10 seconds (between torque readings)
- **DWELL_SECONDS**: 2 seconds (RPM change settling time)
- **INTER_RPM_PAUSE**: 2 seconds (between RPM tests)

### Washing Timing (Adjustable)
- **Initial pump cycle**: 10 seconds (pump 1 only)
- **DC motor wash cycle**: 60 seconds (12V DC motor + simultaneous CNC lowering)
- **Reverse rinse cycle**: 15 seconds (pump 2)
- **Total wash time per cell**: ~85 seconds

## Enhanced ESP32 Washing Station Commands

### Individual Component Control Protocol
```python
# Pump Control Commands
b"P1"  # Start Pump 1 (wash station 1 cleaning)
b"SP1" # Stop Pump 1
b"P2"  # Start Pump 2 (wash station 1 rinse)
b"SP2" # Stop Pump 2
b"P3"  # Start Pump 3 (wash station 2 cleaning)
b"SP3" # Stop Pump 3
b"P4"  # Start Pump 4 (wash station 2 rinse)
b"SP4" # Stop Pump 4

# Motor Control Commands
b"M1"  # Start 12V DC Motor 1 (wash station 1)
b"SM1" # Stop 12V DC Motor 1
b"M2"  # Start 12V DC Motor 2 (wash station 2)
b"SM2" # Stop 12V DC Motor 2

# Reverse Rinse Commands
b"R1"  # Start reverse rinse cycle (station 1)
b"SR1" # Stop reverse rinse (station 1)
b"R2"  # Start reverse rinse cycle (station 2)
b"SR2" # Stop reverse rinse (station 2)

# System Control
b"0"   # Emergency stop all pumps and motors
b"ST"  # Status request (returns current component states)
```

### Legacy Sequence Commands (Backward Compatibility)
```python
# Automated Sequence Commands (for backward compatibility)
b"1"   # Run complete wash station 1 sequence (P1→M1→R1)
b"2"   # Run complete wash station 2 sequence (P3→M2→R2)
b"3"   # Run complete wash station 3 sequence (if configured)
```

### Washing Station Hardware Configuration
- **Pump 1**: Initial cleaning pump (wash station 1)
- **Pump 2**: Rinse pump (reverse flow for wash station 1) 
- **12V DC Motor 1**: Mechanical agitation for wash station 1 (60-second cycle)
- **Pump 3**: Initial cleaning pump (wash station 2)
- **Pump 4**: Rinse pump (reverse flow for wash station 2)
- **12V DC Motor 2**: Mechanical agitation for wash station 2 (60-second cycle)
- **Multiple valves**: Flow direction control
- **Sequential Operation**: Independent control of each component for coordinated CNC movement

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

### Mode Selection
```python
TESTING_MODE = "custom"  # Options: "full", "row", "custom"

# Full Mode: Test all 18 cells (1-18)
# Row Mode: Test specific rows 
SELECTED_ROWS = [2]      # Test row 2 (cells 7-12)
# Custom Mode: Test specific cells
SELECTED_CELLS = [3, 9]  # Test only cells 3 and 9
```

## Safety & Quality Features

### Torque Safety System
- **Real-time monitoring**: Continuous torque threshold checking
- **Automatic abort**: Stop cell testing if threshold exceeded
- **Progressive failure**: Skip remaining RPMs if later RPM fails
- **Critical failure**: Stop entire experiment if first RPM fails

### Data Quality Assurance
- **Measurement validation**: Verify torque data validity
- **Automatic retries**: Built-in error recovery
- **Partial data preservation**: Save progress on interruption
- **Timestamp tracking**: Full provenance of all measurements

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
# Orchestration Configuration Template
# This file provides easy parameter adjustment for different experimental scenarios

## Quick Configuration Profiles

### Profile 1: Fast Testing (Development/Debugging)
```python
# Measurement Parameters
TEST_RPMS = [3.0]                    # Single RPM for speed
MEASUREMENT_DURATION = 10.0          # Shorter measurement time
SAMPLE_INTERVAL = 2.0                # More frequent sampling
DWELL_SECONDS = 1.0                  # Faster RPM changes

# Movement Parameters  
Z_STEP_SIZE = -2.0                   # Larger steps (fewer Z positions)
SETTLE_TIME = 0.5                    # Faster settling
Z_FEED_RATE = 1000                   # Faster Z movement

# Washing Parameters (FAST)
WASH1_WAIT = 15                      # Shorter primary wash
WASH2_WAIT = 10                      # Shorter rinse
```

### Profile 2: Standard Production (Recommended)
```python
# Measurement Parameters
TEST_RPMS = [3.0, 1.0, 5.0, 10.0]   # Multiple RPMs for analysis
MEASUREMENT_DURATION = 40.0          # Full measurement duration
SAMPLE_INTERVAL = 10.0               # Standard sampling rate
DWELL_SECONDS = 2.0                  # Proper RPM stabilization

# Movement Parameters
Z_STEP_SIZE = -1.0                   # 1mm increments
SETTLE_TIME = 1.0                    # Standard settling
Z_FEED_RATE = 500                    # Conservative speed

# Washing Parameters (STANDARD)
WASH1_WAIT = 30                      # Standard primary wash
WASH2_WAIT = 15                      # Standard rinse
```

### Profile 3: Thorough Analysis (Research)
```python
# Measurement Parameters  
TEST_RPMS = [0.5, 1.0, 3.0, 5.0, 10.0, 20.0, 50.0]  # Full RPM range
MEASUREMENT_DURATION = 60.0          # Extended measurement time
SAMPLE_INTERVAL = 5.0                # High-resolution sampling
DWELL_SECONDS = 3.0                  # Extended RPM stabilization

# Movement Parameters
Z_STEP_SIZE = -0.5                   # Fine 0.5mm increments  
SETTLE_TIME = 2.0                    # Extended settling
Z_FEED_RATE = 250                    # Very careful movement

# Washing Parameters (THOROUGH)
WASH1_WAIT = 45                      # Extended primary wash
WASH2_WAIT = 20                      # Extended rinse
```

## Cell Selection Scenarios

### Scenario 1: Full Laboratory Survey
```python
TESTING_MODE = "full"
# Tests all 18 cells (approximately 3-4 hours with standard profile)
```

### Scenario 2: Row-by-Row Analysis  
```python
TESTING_MODE = "row"
SELECTED_ROWS = [1]        # Row 1: cells 1-6 (front row)
# SELECTED_ROWS = [2]      # Row 2: cells 7-12 (middle row)  
# SELECTED_ROWS = [3]      # Row 3: cells 13-18 (back row)
# SELECTED_ROWS = [1,3]    # Multiple rows
```

### Scenario 3: Targeted Testing
```python
TESTING_MODE = "custom"
SELECTED_CELLS = [1, 6, 7, 12, 13, 18]  # Corner cells from each row
# SELECTED_CELLS = [3, 9, 15]             # Center cells from each row
# SELECTED_CELLS = [2, 5, 8, 11, 14, 17] # Specific pattern testing
```

## Safety Parameter Adjustment

### Conservative Safety (High-Value Samples)
```python
TORQUE_BREAK_THRESHOLD = 500.0       # Lower threshold (50% torque)
TORQUE_READ_TIMEOUT = 3.0           # Longer timeout
```

### Standard Safety (Normal Operations)
```python  
TORQUE_BREAK_THRESHOLD = 1000.0     # Standard threshold (100% torque)
TORQUE_READ_TIMEOUT = 2.0           # Standard timeout
```

### Aggressive Testing (Known Safe Samples)
```python
TORQUE_BREAK_THRESHOLD = 1500.0     # Higher threshold (150% torque)
TORQUE_READ_TIMEOUT = 1.0           # Shorter timeout
```

## Washing Station Customization

### Light Contamination (Water-based samples)
```python
def minimal_wash_sequence(cnc, pump, global_cell):
    pump.send_tag(b"1")              # Light wash only
    cnc.move_to_wash_position()
    time.sleep(20)                   # Shorter wash time
    pump.send_tag(b"0")
    cnc.move_to_safe_position()
```

### Standard Contamination (Most samples)
```python
def standard_wash_sequence(cnc, pump, global_cell):
    pump.send_tag(b"1")              # Primary wash
    cnc.move_to_wash_position()  
    time.sleep(30)                   # Standard primary wash
    # Auto-switch to pump 2 (reverse rinse)
    time.sleep(15)                   # Standard rinse
    pump.send_tag(b"0")
    cnc.move_to_safe_position()
```

### Heavy Contamination (Viscous/sticky samples)
```python
def intensive_wash_sequence(cnc, pump, global_cell):
    # Pre-wash cycle
    pump.send_tag(b"1")              
    time.sleep(10)                   # Pre-wash head start
    
    cnc.move_to_wash_position()
    time.sleep(45)                   # Extended primary wash
    
    # Multiple rinse cycles
    time.sleep(25)                   # Extended rinse
    
    # Optional second wash station
    cnc.move_to_wash_station_2()
    pump.send_tag(b"2")
    time.sleep(20)                   # Secondary cleaning
    
    pump.send_tag(b"0")
    cnc.move_to_safe_position()
```

## Hardware-Specific Adjustments

### CNC Machine Tuning
```python
# For high-precision CNC
Z_FEED_RATE = 250                    # Slower, more precise
SETTLE_TIME = 2.0                    # Longer mechanical settling

# For faster CNC  
Z_FEED_RATE = 1000                   # Faster movement
SETTLE_TIME = 0.5                    # Shorter settling time

# Movement boundaries (adjust to your specific setup)
X_LOW_BOUND = 0;    X_HIGH_BOUND = 450
Y_LOW_BOUND = 0;    Y_HIGH_BOUND = 400  
Z_LOW_BOUND = -75;  Z_HIGH_BOUND = 0
```

### Viscometer Calibration
```python
# Spindle constant (depends on spindle type and viscometer model)
SPINDLE_K = 992.47                   # Default for your setup

# Communication settings
VISCO_PORT = "COM6"                  # Adjust to your system
VISCO_BAUD = 115200                  # Match viscometer settings
VISCO_TOUT = 1.0                     # Communication timeout
```

### ESP32 Pump Configuration
```python
ESP32_PORT = "COM11"                 # Adjust to your system
ESP32_BAUD = 115200                  # Match ESP32 settings
PUMP_VIRTUAL = False                 # Set True for testing without hardware

# Pump timing fine-tuning
ESP32_BOOT_DELAY_S = 1.5            # Allow ESP32 initialization
```

## Experimental Design Templates

### Template 1: Viscosity vs Z-Gap Study
```python
# Focus on Z-gap resolution with single RPM
TEST_RPMS = [3.0]
Z_STEP_SIZE = -0.5                   # Fine Z resolution
SELECTED_CELLS = [9]                 # Single representative cell
MEASUREMENT_DURATION = 60.0          # Extended measurement time
```

### Template 2: RPM Response Characterization  
```python
# Focus on RPM range with fixed Z-gap
TEST_RPMS = [0.5, 1.0, 3.0, 5.0, 10.0, 20.0, 50.0]
Z_STEP_SIZE = -2.0                   # Coarser Z resolution
MEASUREMENT_DURATION = 30.0          # Moderate measurement time
```

### Template 3: Sample-to-Sample Comparison
```python
# Focus on consistency across samples
TESTING_MODE = "custom"
SELECTED_CELLS = [1, 2, 3, 4, 5, 6] # Single row comparison
TEST_RPMS = [3.0, 10.0]             # Key RPMs only
MEASUREMENT_DURATION = 45.0          # Good statistics
```

## Performance Optimization

### Memory Management
```python
# For large datasets, implement batch processing
MAX_CELLS_PER_BATCH = 6             # Process 6 cells, save, continue
ENABLE_PARTIAL_SAVE = True          # Save progress every N cells
```

### Time Optimization
```python
# Parallel processing opportunities
ENABLE_CONCURRENT_WASH = True       # Start next cell prep during wash
OPTIMIZE_MOVEMENT = True            # Skip unnecessary Z=0 retractions
```

### Data Quality vs Speed Trade-offs
```python
# High-throughput mode (faster, less precision)
SAMPLE_INTERVAL = 15.0              # Less frequent sampling
MEASUREMENT_DURATION = 20.0         # Shorter measurements
Z_STEP_SIZE = -2.0                  # Coarser Z resolution

# High-precision mode (slower, better data)
SAMPLE_INTERVAL = 2.0               # Frequent sampling  
MEASUREMENT_DURATION = 80.0         # Extended measurements
Z_STEP_SIZE = -0.25                 # Very fine Z resolution
```

---

To use these configurations:

1. Copy the desired parameter set to your main script
2. Adjust `TESTING_MODE` and cell selection as needed
3. Modify timing parameters based on your sample requirements
4. Test with a single cell first (`SELECTED_CELLS = [9]`)
5. Scale up to full experiment once validated
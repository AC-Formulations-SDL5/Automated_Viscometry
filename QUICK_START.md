# Quick Start Guide - Orchestration Control

This guide shows how to use the orchestration reference files to control and customize your CNC-viscometer-washing station workflow.

## Files Overview

1. **[ORCHESTRATION_SCENARIO.md](ORCHESTRATION_SCENARIO.md)** - Complete technical reference
2. **[CONFIGURATION_PROFILES.md](CONFIGURATION_PROFILES.md)** - Ready-to-use parameter sets
3. **[orchestration_control.py](orchestration_control.py)** - Programmable control interface
4. **[run_viscometry.py](run_viscometry.py)** - Main entry point (hardware + web UI)

## Quick Configuration Changes

### 1. Change Testing Speed (Fast vs Thorough)

**In your current script**, modify these parameters at the top:

```python
# FOR FAST TESTING (development/debugging)
TEST_RPMS = [3.0]                    # Single RPM
MEASUREMENT_DURATION = 10.0          # Shorter measurement
Z_STEP_SIZE = -2.0                   # Larger Z steps
WASH1_WAIT = 15                      # Shorter wash times

# FOR THOROUGH ANALYSIS (research)  
TEST_RPMS = [0.5, 1.0, 3.0, 5.0, 10.0, 20.0, 50.0]  # Full RPM range
MEASUREMENT_DURATION = 60.0          # Extended measurement
Z_STEP_SIZE = -0.5                   # Fine Z steps
WASH1_WAIT = 45                      # Extended wash times
```

### 2. Change Which Cells to Test

```python
# Test single cell (for debugging)
TESTING_MODE = "custom"
SELECTED_CELLS = [9]                 # Middle cell for validation

# Test specific row
TESTING_MODE = "row" 
SELECTED_ROWS = [2]                  # Row 2 (cells 7-12)

# Test all cells 
TESTING_MODE = "full"                # All 18 cells
```

### 3. Adjust Safety Parameters

```python
# Conservative (for valuable samples)
TORQUE_BREAK_THRESHOLD = 500.0       # Lower threshold = safer

# Standard operation
TORQUE_BREAK_THRESHOLD = 1000.0      # Current setting

# Aggressive (for known safe samples)  
TORQUE_BREAK_THRESHOLD = 1500.0      # Higher threshold = more data
```

### 4. Modify Washing Timing

```python
# In move_to_locations.py, adjust these:
WASH1_WAIT = 30                      # Primary wash time (seconds)
WASH2_WAIT = 15                      # Rinse time (seconds)

# Or in your perform_washing_sequence() function:
time.sleep(30)                       # Primary wash duration
time.sleep(15)                       # Rinse duration
```

## Using the Control Interface

### Basic Usage

```python
from orchestration_control import OrchestrationController

# Initialize with different profiles
controller = OrchestrationController("fast")      # For development
controller = OrchestrationController("standard")  # For production  
controller = OrchestrationController("thorough")  # For research

# Connect hardware
controller.initialize_hardware(virtual_mode=False)

# Run different scenarios
controller.run_scenario("single_cell", cell_number=9)
controller.run_scenario("row_comparison", row_number=1) 
controller.run_scenario("full_survey")
```

### Custom Scenarios

```python
# Create custom configuration
controller = OrchestrationController("standard")

# Override specific parameters
controller.config['test_rpms'] = [1.0, 5.0, 20.0]     # Custom RPM set
controller.config['z_step_size'] = -0.75               # Custom Z resolution
controller.config['torque_threshold'] = 750.0          # Custom safety limit

# Run with custom settings
controller.run_scenario("single_cell", cell_number=5)
```

## Common Usage Patterns

### 1. Daily Validation Check
```python
# Test corner cells with fast profile
controller = OrchestrationController("fast")
controller.initialize_hardware()
controller.run_scenario("corner_cells")
```

### 2. Sample Comparison Study  
```python
# Test specific cells with standard profile
controller = OrchestrationController("standard")
controller.initialize_hardware()

# Test samples you want to compare
cells_of_interest = [3, 9, 15]  # One from each row
for cell in cells_of_interest:
    controller.run_scenario("single_cell", cell_number=cell)
```

### 3. Method Development
```python
# Z-gap optimization study
controller = OrchestrationController("thorough")
controller.initialize_hardware()
controller.run_scenario("z_gap_study", cell_number=9)

# RPM response characterization  
controller.run_scenario("rpm_characterization", cell_number=9)
```

### 4. Production Run
```python
# Full laboratory survey with standard settings
controller = OrchestrationController("standard")
controller.initialize_hardware()
controller.run_scenario("full_survey")  # All 18 cells
```

## Troubleshooting & Recovery

### 1. If Experiment Stops Mid-Run
- Your current script automatically saves partial data as `*_PARTIAL_*.csv`
- Check the terminal output for the last completed cell
- Resume from next cell by updating `SELECTED_CELLS`

### 2. If Hardware Communication Fails
```python
# Test individual components
controller.initialize_hardware(virtual_mode=True)  # Software testing
```

### 3. If Torque Threshold Exceeded Too Often
```python
# Temporarily lower safety threshold
TORQUE_BREAK_THRESHOLD = 750.0  # Or even 500.0 for very sensitive samples

# Or reduce RPM range
TEST_RPMS = [0.5, 1.0, 3.0]  # Gentler testing
```

### 4. If Washing Appears Insufficient
```python  
# Increase wash times
WASH1_WAIT = 45    # Extended primary wash
WASH2_WAIT = 25    # Extended rinse

# Or add manual inspection step
def manual_wash_check(cell_number):
    input(f"Check spindle cleanliness after cell {cell_number}. Press Enter to continue...")
```

## Performance Optimization

### For Speed (Development/High-Throughput)
- Use "fast" profile
- Single RPM: `TEST_RPMS = [3.0]`
- Coarse Z steps: `Z_STEP_SIZE = -2.0`  
- Quick measurements: `MEASUREMENT_DURATION = 15.0`

### For Data Quality (Research/Publication)
- Use "thorough" profile
- Full RPM range: `TEST_RPMS = [0.5, 1.0, 3.0, 5.0, 10.0, 20.0, 50.0]`
- Fine Z steps: `Z_STEP_SIZE = -0.25`
- Extended measurements: `MEASUREMENT_DURATION = 80.0`

### For Safety (Valuable Samples)
- Use "conservative" profile
- Lower threshold: `TORQUE_BREAK_THRESHOLD = 400.0`
- Slower movement: `Z_FEED_RATE = 200`
- Extended settling: `SETTLE_TIME = 3.0`

## Integration with Your Current Workflow

### Option 1: Modify Current Script
Copy parameters from `CONFIGURATION_PROFILES.md` into `src/viscometry/run/settings.py`

### Option 2: Use Control Interface
Import and use `OrchestrationController` class in your existing code

### Option 3: Hybrid Approach  
Use current script for main logic, but load configuration from profiles:

```python
# In src/viscometry/run/settings.py
import yaml

def load_config_profile(profile_name):
    # Load from CONFIGURATION_PROFILES.md or separate config file
    # Return parameter dictionary
    pass

config = load_config_profile("standard")
TEST_RPMS = config['test_rpms']
MEASUREMENT_DURATION = config['measurement_duration']
# ... etc
```

This orchestration system gives you complete control over timing, safety parameters, test sequences, and hardware coordination while maintaining flexibility for future modifications.
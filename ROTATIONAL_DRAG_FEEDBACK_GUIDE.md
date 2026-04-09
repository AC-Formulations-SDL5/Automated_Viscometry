# Rotational Drag Feedback Controller

## Overview

The Rotational Drag Feedback Controller is a sophisticated system that automatically detects when the viscometer reaches the sample surface (hit point) and terminates cell testing to prevent damage. It analyzes the trend of **Rotational Drag** (torque_% / RPM) vs Height to detect characteristic changes that occur when the viscometer contacts the sample.

## How It Works

### 1. Rotational Drag Calculation
For every measurement at each Z-height and RPM:
```
Rotational_Drag = |torque_%| / RPM
```

### 2. Trend Analysis
The controller analyzes the Rotational_Drag vs Height_mm trend for each RPM:
- **Normal behavior**: As height decreases (more negative Z), rotational drag increases with positive second derivative
- **Hit point**: Trend breaks into a plateau with oscillations (high coefficient of variation)

### 3. Detection Criteria
The controller uses multiple indicators to detect hit points:

#### a) **Negative Second Derivative Detection**
- Fits quadratic curve to Rotational_Drag vs Z-height data
- Detects when second derivative becomes negative (trend breaks down)
- Threshold: `SECOND_DERIVATIVE_THRESHOLD = -0.5`

#### b) **Plateau Detection (CV Jump)**
- Analyzes coefficient of variation (CV) in torque measurements
- Detects sudden jumps in CV indicating oscillations/instability
- Threshold: `CV_JUMP_THRESHOLD = 0.2`

#### c) **Trend Breakdown**
- Monitors R² of linear trend fit
- Poor linear fit (R² < 0.8) indicates trend breakdown
- Threshold: `TREND_R_SQUARED_MIN = 0.8`

### 4. Hit Point Decision
- Requires at least 50% of tested RPMs to show hit detection
- Combined confidence must exceed `HIT_POINT_CONFIDENCE_THRESHOLD = 0.6`
- When detected, cell testing terminates and moves to next cell

## Configuration Parameters

Edit these parameters in `all_cells_with_rotational_drag_feedback.py`:

```python
# ========== FEEDBACK CONTROLLER CONFIGURATION ==========
FEEDBACK_CONTROL_ENABLED = True             # Enable/disable feedback controller
MIN_DATA_POINTS_FOR_TREND = 3              # Minimum z-levels needed for trend analysis
SECOND_DERIVATIVE_THRESHOLD = -0.5          # Threshold for detecting trend break
CV_JUMP_THRESHOLD = 0.2                     # CV jump threshold for oscillation detection
PLATEAU_DETECTION_ENABLED = True            # Enable plateau detection using CV
TREND_R_SQUARED_MIN = 0.8                  # Minimum R² for valid trend line
HIT_POINT_CONFIDENCE_THRESHOLD = 0.6       # Confidence threshold for hit-point detection
```

### Parameter Tuning Guidelines

1. **More Sensitive Detection** (earlier hit detection):
   - Increase `SECOND_DERIVATIVE_THRESHOLD` (e.g., -0.3)
   - Decrease `CV_JUMP_THRESHOLD` (e.g., 0.15)
   - Decrease `HIT_POINT_CONFIDENCE_THRESHOLD` (e.g., 0.5)

2. **Less Sensitive Detection** (later hit detection):
   - Decrease `SECOND_DERIVATIVE_THRESHOLD` (e.g., -0.7)
   - Increase `CV_JUMP_THRESHOLD` (e.g., 0.3)
   - Increase `HIT_POINT_CONFIDENCE_THRESHOLD` (e.g., 0.7)

## Output and Data

### Console Output
During operation, you'll see:
```
  Rotational Drag Analysis:
      RPM 1.0: Avg Rotational_Drag = 1.2345, CV = 0.025
      RPM 5.0: Avg Rotational_Drag = 0.2469, CV = 0.031
    Feedback Controller: Analyzing trends for 2 RPMs...
    RPM 1: Normal trend (slope: -1.8898, R²: 0.993)
    RPM 5: HIT DETECTED (confidence: 0.90) - negative_second_derivative (-1.2), plateau_detected (0.45)
    *** HIT POINT DETECTED *** 
    Hit ratio: 50.0% (1/2 RPMs)
    Confidence: 0.45
    Estimated hit Z: -66.200
    Terminating Cell 13 due to hit-point detection
```

### CSV Data
The output CSV file includes a new `Rotational_Drag` column:
```csv
row,cell,Z_Height_mm,RPM,Elapsed_Time_s,Torque_%,Rotational_Drag
2,13,-65.500,1.0,0.00,1.234,1.234000
2,13,-65.500,5.0,0.00,6.789,1.357800
```

### Feedback Controller Summary
At the end of each cell:
```
  Feedback Controller Summary:
    Hit point detected: True
    Hit Z-level: -66.200
    Detection confidence: 0.75
    Total Z-levels analyzed: 8
    RPMs analyzed: 2
```

## Testing

Use the included test script to validate controller behavior:
```bash
python test_feedback_controller.py
```

This generates synthetic data with known hit points to verify the detection algorithm works correctly.

## Troubleshooting

### Problem: Hit point detected too early
- **Solution**: Increase sensitivity thresholds or confidence requirement
- Check if sample has unusual surface properties

### Problem: Hit point not detected (viscometer damage risk)
- **Solution**: Decrease sensitivity thresholds
- Verify TEST_RPMS includes appropriate values for your samples
- Check for hardware issues (torque calibration, movement precision)

### Problem: False positives (erratic detection)
- **Solution**: Increase `MIN_DATA_POINTS_FOR_TREND`
- Improve measurement stability (longer `DWELL_SECONDS`)
- Check for external vibrations or electromagnetic interference

### Problem: Controller disabled
- Verify `FEEDBACK_CONTROL_ENABLED = True`
- Check console output for "Feedback Control: ENABLED"
- Ensure adequate Z-step resolution (`Z_STEP_SIZE`)

## Safety Notes

1. **Always test with non-critical samples first** when tuning parameters
2. **Monitor initial runs closely** to validate hit detection timing
3. **Keep torque threshold** (`TORQUE_BREAK_THRESHOLD`) as backup safety
4. **Regular calibration** of torque sensor ensures accurate drag calculations
5. **Document parameter changes** for reproducibility

## Algorithm Details

For technical users, the detection algorithm:

1. Collects rotational drag data: `drag = |torque| / RPM`
2. Fits linear and quadratic trends to drag vs Z-height
3. Calculates second derivative of quadratic fit
4. Analyzes coefficient of variation patterns
5. Combines multiple detection criteria with confidence scoring
6. Makes termination decision based on aggregate confidence

The algorithm balances sensitivity (early detection) with specificity (avoiding false positives) to provide robust hit-point detection for automated viscometry workflows.
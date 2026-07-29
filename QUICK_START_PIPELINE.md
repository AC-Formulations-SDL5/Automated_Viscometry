"""
QUICK START GUIDE — Rheology Pipeline

Three ways to use the pipeline:
"""

# ============================================================================
# METHOD 1: COMMAND LINE (Fastest for batch processing)
# ============================================================================

"""
python analyze_viscometry.py --factory sample.csv
python analyze_viscometry.py --calibration height_normalized.csv sample.csv
python analyze_viscometry.py --calibration height_normalized.csv --output results.csv sample*.csv
"""


# ============================================================================
# METHOD 2: PYTHON SCRIPT (For integration or custom workflows)
# ============================================================================

import numpy as np
from rheology_pipeline_core import create_default_pipeline

# Create pipeline
pipeline = create_default_pipeline()

# Example 1: Single-RPM (Newtonian)
h = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
T = np.array([50, 47, 44, 41, 38])
rpm = 50.0

result = pipeline.predict_rheology(h, T, rpm)

print(f"Sample 1 (Single RPM):")
print(f"  Regime: {result['regime']}")
print(f"  Viscosity: {result['mu_app_cP']:.1f} cP")
print()

# Example 2: Multi-RPM (Non-Newtonian)
h_list = [
    np.array([0.0, 0.15, 0.30, 0.45]),
    np.array([0.0, 0.12, 0.24, 0.36]),
]
T_list = [
    np.array([75, 62, 50, 40]),
    np.array([65, 52, 40, 29]),
]
rpm_list = [25, 50]

result = pipeline.predict_rheology(h_list, T_list, rpm_list)

print(f"Sample 2 (Multi RPM):")
print(f"  Regime: {result['regime']}")
print(f"  Flow-behavior index (n): {result['n']:.3f}")
print(f"  Consistency (K): {result['K_Pas_n']:.2e} Pa·s^n")


# ============================================================================
# METHOD 3: JUPYTER NOTEBOOK (Interactive analysis)
# ============================================================================

# In a Jupyter cell:
"""
import numpy as np
from rheology_pipeline_core import RheologyPipeline

# Load calibration once
pipeline = RheologyPipeline()
cal = pipeline.load_silicone_calibration("height_normalized.csv")
print(f"Calibrated: h_c={cal['h_c']:.4f} mm")

# Analyze multiple samples
samples = {
    "PEG_5pct": (h1, T1, [25, 50, 100]),
    "Carbopol": (h2, T2, [25, 50, 100]),
}

for name, (h, T, rpms) in samples.items():
    result = pipeline.predict_rheology(h, T, rpms)
    print(f"{name}: {result['regime']}, n={result['n']:.2f}")
"""


# ============================================================================
# TYPICAL WORKFLOW
# ============================================================================

"""
1. Prepare your data:
   - CSV file with Height, Torque, RPM columns
   - Height in mm (will be re-zeroed to minimum)
   - Torque in % full-scale
   
2. Load calibration (if you have one):
   python analyze_viscometry.py --calibration height_normalized.csv ...
   
   OR use factory defaults:
   python analyze_viscometry.py --factory ...
   
3. Run analysis on sample(s):
   python analyze_viscometry.py --calibration height_normalized.csv \
                                 --output results.csv \
                                 sample1.csv sample2.csv sample3.csv
   
4. Check results in results.csv:
   - regime: 'Newtonian' / 'shear-thinning' / 'shear-thickening'
   - n: flow-behavior index
   - K_Pas_n: consistency (for non-Newtonian)
"""


# ============================================================================
# INTERPRETING RESULTS
# ============================================================================

"""
Output Dictionary Keys:
  mode          : 'newtonian' (single RPM) or 'powerlaw' (multi-RPM)
  regime        : Classification string
  n             : Flow-behavior index (1=Newtonian, <1=thin, >1=thick)
  K_Pas_n       : Consistency (Pa·s^n) — only for power-law
  mu_app_cP     : Viscosity (cP) — single RPM or callable for power-law
  tau           : Function: tau(gamma_dot) → shear stress (Pa)
  R2_powerlaw   : Fit quality (0-1) for power-law
  fit_quality   : Fit quality for single RPM

Classification Thresholds:
  n > 1.05  →  Shear-thickening (viscosity increases with shear)
  0.95 ≤ n ≤ 1.05  →  Newtonian (constant viscosity)
  n < 0.95  →  Shear-thinning (viscosity decreases with shear)

For power-law fluids, query viscosity at arbitrary shear rates:
  gamma_dot = 10.0
  eta = result['mu_app_cP'](gamma_dot)  # cP
  tau = result['tau'](gamma_dot)        # Pa
"""


# ============================================================================
# COMMON ISSUES & FIXES
# ============================================================================

"""
Problem: "Could not find height/torque/rpm columns"
Solution: Check CSV column names. Should be (case-insensitive):
  Height, h_mm, h  →  gap height
  Torque, T_pct, T  →  percent full scale
  RPM, rpm, speed  →  spindle speed

Problem: "Pipeline not calibrated"
Solution: Call one of:
  pipeline.set_calibration(h_c=0.25, k=3.5e-4, p=1.03)
  pipeline.load_silicone_calibration("height_normalized.csv")

Problem: "Error: invalid amplitude"
Solution: Drag profile fit failed. Check:
  - Are heights properly ordered?
  - Are there enough data points (≥4)?
  - Is torque measurement in right range?

Problem: Low R² (<0.7) fit quality
Solution:
  - Check for outliers in raw data
  - Ensure good height resolution (≥5 points)
  - Verify torque measurement accuracy
"""


# ============================================================================
# FILENAMES & STRUCTURE
# ============================================================================

"""
Your analysis directory should have:

  rheology_pipeline_core.py          ← Core module (keep here)
  analyze_viscometry.py              ← CLI tool (keep here)
  examples_pipeline_usage.py         ← Examples (optional)
  RHEOLOGY_PIPELINE_README.md        ← Full documentation
  height_normalized.csv              ← Silicone calibration data
  
  sample1.csv                        ← Your sample data
  sample2.csv
  results.csv                        ← Output (created after analysis)

Run from the directory containing these files:
  python analyze_viscometry.py --calibration height_normalized.csv sample1.csv
"""


# ============================================================================
# EXAMPLE: COMPLETE SCRIPT
# ============================================================================

"""
# analysis.py

import pandas as pd
import numpy as np
from pathlib import Path
from rheology_pipeline_core import RheologyPipeline

# Setup
data_dir = Path("data")
results = []

# Load calibration once
pipeline = RheologyPipeline()
cal = pipeline.load_silicone_calibration("height_normalized.csv")
print(f"Calibration loaded: h_c={cal['h_c']:.4f} mm, R²={cal['R2_calibration']:.3f}")

# Process all samples
for sample_file in data_dir.glob("*.csv"):
    print(f"Processing {sample_file.name}...")
    
    try:
        # Load data
        df = pd.read_csv(sample_file)
        
        # Check if single or multi-RPM
        unique_rpms = df['RPM'].unique()
        
        if len(unique_rpms) == 1:
            # Single RPM
            h = df['Height'].values - df['Height'].min()
            T = df['Torque'].values
            result = pipeline.predict_rheology(h, T, float(unique_rpms[0]))
        else:
            # Multi RPM
            h_list, T_list = [], []
            for rpm_val in sorted(unique_rpms):
                subset = df[df['RPM'] == rpm_val]
                h = subset['Height'].values - subset['Height'].min()
                T = subset['Torque'].values
                h_list.append(h)
                T_list.append(T)
            result = pipeline.predict_rheology(h_list, T_list, sorted(unique_rpms))
        
        # Store result
        result['sample'] = sample_file.stem
        results.append(result)
        
        print(f"  → {result['regime']}, n={result['n']:.2f}")
    
    except Exception as e:
        print(f"  ERROR: {e}")

# Save results
df_results = pd.DataFrame(results)
df_results.to_csv("results.csv", index=False)
print(f"\nResults saved to results.csv")

# Run from directory:
# python analysis.py
"""

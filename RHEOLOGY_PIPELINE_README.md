# Rheology Pipeline — Automated Viscometry Analysis

A modular, production-ready Python pipeline that converts raw cone-plate viscometry measurements into complete rheological characterization: **Newtonian** vs. **non-Newtonian** classification, flow-behavior index (*n*), and consistency (*K*).

---

## Overview

### What It Does

The pipeline automates the multi-step analysis from the `rheology_pipeline.ipynb` notebook:

1. **Drag-profile fitting**: Extracts amplitude *A* from height-dependent drag measurements
2. **Universal geometry calibration**: Determines gap offset *h_c* (once, from silicone oils)
3. **Amplitude-to-viscosity calibration**: Fits power law *A = k·μ^p* on Newtonian reference fluids
4. **Power-law characterization**: Fits *A(γ̇) = A₀·γ̇^(n-1)* for multi-RPM samples
5. **Rheological classification**: Outputs whether fluid is Newtonian, shear-thinning, or shear-thickening

### Key Outputs

For each sample:
- **`regime`** : Classification (`'Newtonian'`, `'shear-thinning'`, `'shear-thickening'`)
- **`n`** : Flow-behavior index (n=1 Newtonian, n<1 thinning, n>1 thickening)
- **`K_Pas_n`** : Consistency in Pa·s^n (power-law fluids)
- **`mu_app_cP`** : Apparent viscosity in cP (Newtonian or at reference shear rate)

---

## Installation

### Requirements

```bash
pip install numpy pandas scipy
```

### Files

Place these three files in your analysis directory:

- **`rheology_pipeline_core.py`** — Core pipeline module
- **`analyze_viscometry.py`** — Batch processing command-line tool
- **`examples_pipeline_usage.py`** — Usage examples (optional)

---

## Quick Start

### 1. **Factory Defaults** (No Calibration File)

```python
from rheology_pipeline_core import create_default_pipeline
import numpy as np

# Create pipeline with factory defaults
pipeline = create_default_pipeline()

# Single-RPM (Newtonian)
h = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
T = np.array([45, 42, 39, 36, 33])
rpm = 50.0

result = pipeline.predict_rheology(h, T, rpm)
print(f"Regime: {result['regime']}")
print(f"Viscosity: {result['mu_app_cP']:.1f} cP")
```

### 2. **Custom Calibration** (From Silicone Oils)

```python
from rheology_pipeline_core import RheologyPipeline

pipeline = RheologyPipeline()
pipeline.load_silicone_calibration("height_normalized.csv")

# Now use as above
result = pipeline.predict_rheology(h, T, rpm)
```

### 3. **Batch Processing** (Command Line)

```bash
# Single sample
python analyze_viscometry.py --calibration height_normalized.csv sample.csv

# Multiple samples with output
python analyze_viscometry.py \
  --calibration height_normalized.csv \
  --output results.csv \
  sample1.csv sample2.csv sample3.csv

# Verbose output
python analyze_viscometry.py \
  --calibration height_normalized.csv \
  -v \
  sample*.csv
```

---

## Detailed Usage

### A. Single-RPM Analysis (Newtonian)

When you have measurements at **one spindle speed**, the result is a single apparent viscosity (Newtonian).

```python
pipeline = create_default_pipeline()

h_mm = np.array([0.0, 0.05, 0.10, 0.15, 0.20, 0.25])
torque_pct = np.array([50.2, 48.5, 46.0, 43.5, 41.0, 38.5])
rpm = 75.0

result = pipeline.predict_rheology(h_mm, torque_pct, rpm)

print(f"Mode: {result['mode']}")           # 'newtonian'
print(f"Regime: {result['regime']}")       # 'Newtonian'
print(f"n: {result['n']}")                 # 1.0 (by definition)
print(f"μ_app: {result['mu_app_cP']:.1f} cP")
print(f"Shear rate: {result['gamma_dot']:.1f} s⁻¹")
print(f"Fit quality: {result['fit_quality']:.4f} (R²)")
```

### B. Multi-RPM Analysis (Non-Newtonian)

When you have measurements at **2 or more RPMs**, the pipeline fits a power law and determines *n*.

```python
# Three measurements at different RPMs
h_list = [
    np.array([0.0, 0.15, 0.30, 0.45, 0.60]),  # 25 RPM
    np.array([0.0, 0.12, 0.24, 0.36, 0.48]),  # 50 RPM
    np.array([0.0, 0.08, 0.16, 0.24, 0.32])   # 100 RPM
]

T_list = [
    np.array([75.2, 62.3, 50.1, 40.5, 32.0]),
    np.array([65.8, 52.0, 39.5, 29.0, 20.5]),
    np.array([55.0, 40.2, 27.5, 17.0, 10.0])
]

rpm_list = [25.0, 50.0, 100.0]

result = pipeline.predict_rheology(h_list, T_list, rpm_list)

print(f"Mode: {result['mode']}")              # 'powerlaw'
print(f"Regime: {result['regime']}")          # 'shear-thinning', etc.
print(f"n: {result['n']:.3f}")                # Flow-behavior index
print(f"K: {result['K_Pas_n']:.2e} Pa·s^n")  # Consistency

# Query viscosity/stress at arbitrary shear rates
gamma_dot_test = 10.0
eta = result['mu_app_cP'](gamma_dot_test)     # Apparent viscosity (cP)
tau = result['tau'](gamma_dot_test)           # Shear stress (Pa)
print(f"At γ̇={gamma_dot_test} s⁻¹: η={eta:.1f} cP, τ={tau:.1f} Pa")
```

### C. Calibration from Silicone Oils

Use your own silicone calibration data (instead of factory defaults):

```python
pipeline = RheologyPipeline()

# Load calibration from silicone measurements
cal_info = pipeline.load_silicone_calibration("height_normalized.csv")

print(f"Universal gap offset: h_c = {cal_info['h_c']:.4f} mm")
print(f"Calibration: A = {cal_info['k']:.2e} · μ^{cal_info['p']:.3f}")
print(f"Quality: R² = {cal_info['R2_calibration']:.4f}")

# Pipeline now uses these calibrated values
result = pipeline.predict_rheology(h, T, rpm)
```

---

## Input Data Format

### CSV Format

The pipeline accepts **flexible** CSV formats. Key columns recognized:

| Column Name(s) | Role |
|---|---|
| `Height`, `h_mm`, `h` | Gap height (mm, will be re-zeroed to minimum) |
| `Torque`, `T_pct`, `T` | Percent full-scale torque (%) |
| `RPM`, `speed`, `rpm` | Spindle speed (RPM) |

**Examples:**

```csv
Height,Torque,RPM
0.0,50.2,75
0.05,48.5,75
0.10,46.0,75
```

```csv
h_mm,T_pct,RPM
0.0,50.2,25
0.1,45.3,25
0.2,40.0,25
0.0,55.1,50
0.1,50.8,50
```

### Column Name Matching

The parser is **case-insensitive** and matches partial names:
- ✓ `Height`, `height`, `h_mm`, `h`
- ✓ `Torque`, `torque`, `T_pct`, `T`
- ✓ `RPM`, `rpm`, `Speed`, `speed`

---

## Output Interpretation

### Classification Thresholds

| Flow Index *n* | Regime | Behavior |
|---|---|---|
| 1.05 < *n* | Shear-thickening | Viscosity increases with shear rate (e.g., cornstarch suspensions) |
| 0.95 ≤ *n* ≤ 1.05 | Newtonian | Constant viscosity (e.g., silicone oils, water) |
| *n* < 0.95 | Shear-thinning | Viscosity decreases with shear rate (e.g., polymer solutions, gels) |

Adjust thresholds via `thinning_thr` and `thickening_thr` parameters if needed.

### Result Dictionary

For all analyses, `predict_rheology()` returns a dict:

```python
{
    'mode': 'newtonian' | 'powerlaw',                    # Analysis mode
    'regime': str,                                       # Classification
    'n': float,                                          # Flow-behavior index
    'K_Pas_n': float,                                    # Consistency (Pa·s^n)
    'mu_app_cP': float | callable,                       # Viscosity (single RPM) 
    'tau': callable,                                     # Stress function τ(γ̇)
    'R2_powerlaw': float,                                # Fit quality (multi-RPM)
    'gamma_dot': float | (float, float),                 # Shear rate / range
    'fit_quality': float,                                # R² (single RPM)
}
```

For power-law fluids, use the callables:

```python
if result['mode'] == 'powerlaw':
    gamma_dot_test = 10.0
    eta = result['mu_app_cP'](gamma_dot_test)  # Apparent viscosity at γ̇
    tau = result['tau'](gamma_dot_test)        # Shear stress at γ̇
```

---

## Command-Line Tool

### Batch Processing with `analyze_viscometry.py`

**Basic usage:**

```bash
python analyze_viscometry.py --calibration height_normalized.csv sample.csv
```

**With output:**

```bash
python analyze_viscometry.py \
  --calibration height_normalized.csv \
  --output results.csv \
  sample1.csv sample2.csv sample3.csv
```

**Options:**

| Flag | Description |
|---|---|
| `--calibration FILE` | Silicone calibration CSV |
| `--factory` | Use factory-default calibration (no file needed) |
| `--output FILE` | Save results to CSV |
| `--json FILE` | Save full results as JSON |
| `-v`, `--verbose` | Verbose output during processing |

**Output format (`--output results.csv`):**

```csv
sample,regime,n,K_Pas_n,R2_powerlaw,n_rpms,success,error
sample1,Newtonian,1.0,1.2e-3,NaN,1,true,
sample2,shear-thinning,0.85,4.3e-4,0.987,3,true,
sample3,ERROR,NaN,NaN,NaN,0,false,invalid amplitude
```

---

## Advanced Usage

### Custom Geometry

If your cone-plate has **different dimensions**:

```python
from rheology_pipeline_core import ConeGeometry, RheologyPipeline

# Define custom geometry
geo = ConeGeometry(
    cone_radius_mm=13.0,      # Different radius
    cone_angle_deg=2.5        # Different angle
)

pipeline = RheologyPipeline(geometry=geo)
pipeline.set_calibration(h_c=0.25, k=3.5e-4, p=1.03)

result = pipeline.predict_rheology(h, T, rpm)
```

### Adjusting Classification Thresholds

```python
# More lenient shear-thinning threshold (n < 0.90 instead of 0.95)
result = pipeline.predict_rheology(
    h_list, T_list, rpm_list,
    thinning_thr=0.90,          # Default: 0.95
    thickening_thr=1.10         # Default: 1.05
)
```

### Manual Calibration Setting

If you have pre-computed calibration values:

```python
pipeline = RheologyPipeline()
pipeline.set_calibration(
    h_c=0.2534,    # Universal gap offset (mm)
    k=3.45e-4,     # A = k·μ^p coefficient
    p=1.026        # Power-law exponent
)

result = pipeline.predict_rheology(h, T, rpm)
```

---

## Example: Complete Workflow

```python
from pathlib import Path
import pandas as pd
from rheology_pipeline_core import RheologyPipeline

# Step 1: Initialize pipeline with silicone calibration
pipeline = RheologyPipeline()
cal = pipeline.load_silicone_calibration("height_normalized.csv")
print(f"Calibrated: h_c={cal['h_c']:.4f} mm, R²={cal['R2_calibration']:.4f}")

# Step 2: Load sample CSV
data = pd.read_csv("sample_polymer.csv")
data = data.dropna(subset=['Height', 'Torque', 'RPM'])

# Step 3: Check if single or multi-RPM
unique_rpms = sorted(data['RPM'].unique())
print(f"RPMs: {unique_rpms}")

if len(unique_rpms) == 1:
    # Single-RPM Newtonian analysis
    h = data['Height'].values - data['Height'].min()
    T = data['Torque'].values
    result = pipeline.predict_rheology(h, T, unique_rpms[0])
else:
    # Multi-RPM power-law analysis
    h_list = []
    T_list = []
    for rpm_val in unique_rpms:
        subset = data[data['RPM'] == rpm_val].copy()
        h_rpm = subset['Height'].values - subset['Height'].min()
        T_rpm = subset['Torque'].values
        h_list.append(h_rpm)
        T_list.append(T_rpm)
    
    result = pipeline.predict_rheology(h_list, T_list, unique_rpms)

# Step 4: Display results
print(f"\n{'='*50}")
print(f"Classification: {result['regime']}")
print(f"Flow-behavior index n: {result['n']:.3f}")
if 'K_Pas_n' in result and pd.notna(result['K_Pas_n']):
    print(f"Consistency K: {result['K_Pas_n']:.2e} Pa·s^n")
if 'mu_app_cP' in result and pd.notna(result['mu_app_cP']):
    mu_val = result['mu_app_cP']
    print(f"Viscosity: {mu_val:.1f} cP")
print(f"{'='*50}")
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `RuntimeError: Pipeline not calibrated` | Call `pipeline.set_calibration()` or `load_silicone_calibration()` first |
| `ValueError: Could not find height/torque/rpm columns` | Check CSV column names; use `Height`, `Torque`, `RPM` or similar |
| `regime: "Error: invalid amplitude"` | Drag profile fit failed; check data quality, ensure heights are positive |
| `regime: "Error: < 2 valid RPMs"` | Need ≥2 RPMs for power-law fit; use single-RPM mode instead |
| Low fit quality (R² < 0.7) | Check for outliers, ensure good height resolution, verify torque measurement |

---

## References

- **Notebook**: See `rheology_pipeline.ipynb` for full physics and methodology
- **Cone-plate geometry**: *R* = 12 mm, *α* = 3°, *M_full* = 7187 dyne·cm
- **Power law**: τ = *K*·γ̇^*n* (consistency *K* in Pa·s^*n*, flow index *n* dimensionless)
- **Calibration**: Silicone oils (Newtonian) → universal *h_c*, amplitude calibration *A* = *k*·μ^*p*

---

## License & Attribution

This pipeline is based on the physics and methodology in `rheology_pipeline.ipynb` (Automated Cone-Plate Viscometry study).

**Contact**: See repository documentation for inquiries.

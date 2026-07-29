"""
Example: Using the Rheology Pipeline Programmatically

This script demonstrates how to use the rheology pipeline to analyze
viscometry data directly in Python code.
"""

import numpy as np
from pathlib import Path
from rheology_pipeline_core import RheologyPipeline, create_default_pipeline


def example_1_factory_defaults():
    """Example 1: Use factory-default calibration."""
    print("=" * 70)
    print("Example 1: Using Factory-Default Calibration")
    print("=" * 70)
    
    pipeline = create_default_pipeline()
    
    # Simulate a Newtonian sample (single RPM)
    h_single = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5])
    T_single = np.array([45.2, 42.5, 38.9, 35.0, 31.0, 28.0])
    rpm_single = 50.0
    
    result = pipeline.predict_rheology(h_single, T_single, rpm_single)
    
    print(f"\nSingle-RPM sample (Newtonian):")
    print(f"  Regime: {result['regime']}")
    print(f"  n = {result['n']:.3f}")
    print(f"  Apparent viscosity: {result['mu_app_cP']:.1f} cP")
    print(f"  Fit quality (R²): {result['fit_quality']:.4f}")
    
    # Simulate a non-Newtonian sample (multi-RPM)
    h_multi = [
        np.array([0.0, 0.15, 0.30, 0.45, 0.60]),  # RPM 25
        np.array([0.0, 0.12, 0.24, 0.36, 0.48]),  # RPM 50
        np.array([0.0, 0.10, 0.20, 0.30, 0.40])   # RPM 100
    ]
    T_multi = [
        np.array([75.2, 62.3, 50.1, 40.5, 32.0]),
        np.array([65.8, 52.0, 39.5, 29.0, 20.5]),
        np.array([55.0, 40.2, 27.5, 17.0, 10.0])
    ]
    rpm_multi = [25.0, 50.0, 100.0]
    
    result = pipeline.predict_rheology(h_multi, T_multi, rpm_multi)
    
    print(f"\nMulti-RPM sample (non-Newtonian):")
    print(f"  Regime: {result['regime']}")
    print(f"  Flow-behavior index (n): {result['n']:.3f}")
    print(f"  Consistency (K): {result['K_Pas_n']:.3e} Pa·s^n")
    print(f"  Fit quality (R²): {result['R2_powerlaw']:.4f}")
    print(f"  Shear-rate range: {result['gamma_dot_range'][0]:.1f} - {result['gamma_dot_range'][1]:.1f} s⁻¹")
    
    # Demonstrate viscosity query (for power-law fluids)
    if result['mode'] == 'powerlaw':
        gamma_dot_test = 10.0
        eta_at_test = result['mu_app_cP'](gamma_dot_test)
        print(f"\n  Apparent viscosity at γ̇ = {gamma_dot_test} s⁻¹: {eta_at_test:.1f} cP")
        
        tau_at_test = result['tau'](gamma_dot_test)
        print(f"  Shear stress at γ̇ = {gamma_dot_test} s⁻¹: {tau_at_test:.1f} Pa")


def example_2_custom_calibration():
    """Example 2: Load custom silicone calibration from file."""
    print("\n" + "=" * 70)
    print("Example 2: Custom Silicone Calibration")
    print("=" * 70)
    
    calibration_file = Path("height_normalized.csv")
    
    if not calibration_file.exists():
        print(f"\nCalibration file '{calibration_file}' not found.")
        print("Using factory defaults instead...\n")
        pipeline = create_default_pipeline()
    else:
        pipeline = RheologyPipeline()
        print(f"\nLoading calibration from {calibration_file}...")
        
        try:
            cal_info = pipeline.load_silicone_calibration(calibration_file)
            print(f"\nCalibration loaded successfully:")
            print(f"  Universal gap offset (h_c): {cal_info['h_c']:.4f} mm")
            print(f"  Amplitude calibration: A = {cal_info['k']:.2e} · μ^{cal_info['p']:.3f}")
            print(f"  Calibration quality (R²): {cal_info['R2_calibration']:.4f}")
            print(f"  Number of silicone samples: {cal_info['n_silicones']}")
        except Exception as e:
            print(f"Error loading calibration: {e}")
            return
    
    # Now analyze a sample
    h = np.array([0.0, 0.08, 0.16, 0.24, 0.32])
    T = np.array([32.1, 30.2, 27.8, 25.0, 22.5])
    rpm = 75.0
    
    result = pipeline.predict_rheology(h, T, rpm)
    print(f"\nAnalysis result:")
    print(f"  Regime: {result['regime']}")
    print(f"  Apparent viscosity: {result['mu_app_cP']:.1f} cP")


def example_3_classification():
    """Example 3: Classify different fluid types."""
    print("\n" + "=" * 70)
    print("Example 3: Fluid Classification (Newtonian vs. Non-Newtonian)")
    print("=" * 70)
    
    pipeline = create_default_pipeline()
    
    # Test cases with different rheological behaviors
    test_cases = {
        "Silicone Oil (Newtonian)": {
            "is_multi": False,
            "h": np.array([0.0, 0.1, 0.2, 0.3, 0.4]),
            "T": np.array([45.0, 42.0, 39.0, 36.0, 33.0]),
            "rpm": 50.0
        },
        "Shear-thinning Gel": {
            "is_multi": True,
            "h_list": [
                np.array([0.0, 0.15, 0.30, 0.45]),
                np.array([0.0, 0.12, 0.24, 0.36]),
                np.array([0.0, 0.08, 0.16, 0.24])
            ],
            "T_list": [
                np.array([70.0, 55.0, 42.0, 30.0]),
                np.array([60.0, 45.0, 32.0, 20.0]),
                np.array([50.0, 32.0, 18.0, 10.0])
            ],
            "rpm": [25.0, 50.0, 100.0]
        },
        "Shear-thickening Suspension": {
            "is_multi": True,
            "h_list": [
                np.array([0.0, 0.15, 0.30, 0.45]),
                np.array([0.0, 0.12, 0.24, 0.36]),
                np.array([0.0, 0.08, 0.16, 0.24])
            ],
            "T_list": [
                np.array([15.0, 20.0, 28.0, 38.0]),
                np.array([25.0, 35.0, 48.0, 65.0]),
                np.array([35.0, 52.0, 75.0, 105.0])
            ],
            "rpm": [25.0, 50.0, 100.0]
        }
    }
    
    print()
    for name, data in test_cases.items():
        if data["is_multi"]:
            result = pipeline.predict_rheology(
                data["h_list"], data["T_list"], data["rpm"]
            )
        else:
            result = pipeline.predict_rheology(
                data["h"], data["T"], data["rpm"]
            )
        
        print(f"{name}:")
        print(f"  Regime: {result['regime']:<30} n = {result['n']:.3f}")


def example_4_batch_analysis():
    """Example 4: Batch analysis of multiple samples."""
    print("\n" + "=" * 70)
    print("Example 4: Batch Analysis")
    print("=" * 70)
    
    pipeline = create_default_pipeline()
    
    # Create mock samples
    samples = {
        "PEG_300K_5pct": {
            "h_list": [
                np.array([0.0, 0.15, 0.30, 0.45]),
                np.array([0.0, 0.12, 0.24, 0.36])
            ],
            "T_list": [
                np.array([70.0, 55.0, 42.0, 30.0]),
                np.array([60.0, 45.0, 32.0, 20.0])
            ],
            "rpm": [25.0, 50.0]
        },
        "Carbopol_0.3pct": {
            "h_list": [
                np.array([0.0, 0.15, 0.30, 0.45]),
                np.array([0.0, 0.12, 0.24, 0.36]),
                np.array([0.0, 0.08, 0.16, 0.24])
            ],
            "T_list": [
                np.array([90.0, 70.0, 50.0, 35.0]),
                np.array([80.0, 60.0, 42.0, 28.0]),
                np.array([70.0, 48.0, 30.0, 16.0])
            ],
            "rpm": [10.0, 25.0, 50.0]
        },
        "Silicone_100cSt": {
            "h": np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5]),
            "T": np.array([75.0, 70.0, 65.0, 60.0, 55.0, 50.0]),
            "rpm": 100.0
        }
    }
    
    print("\nBatch Analysis Results:")
    print("-" * 80)
    print(f"{'Sample':<25} {'Regime':<25} {'n':<10} {'K or μ':<20}")
    print("-" * 80)
    
    for sample_name, data in samples.items():
        if "h" in data:  # Single RPM
            result = pipeline.predict_rheology(data["h"], data["T"], data["rpm"])
            regime = result["regime"]
            n = result["n"]
            param = f"{result['mu_app_cP']:.1f} cP"
        else:  # Multi-RPM
            result = pipeline.predict_rheology(
                data["h_list"], data["T_list"], data["rpm"]
            )
            regime = result["regime"]
            n = result["n"]
            param = f"{result['K_Pas_n']:.2e} Pa·s^n"
        
        print(f"{sample_name:<25} {regime:<25} {n:<10.3f} {param:<20}")


if __name__ == '__main__':
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  RHEOLOGY PIPELINE — USAGE EXAMPLES".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    
    example_1_factory_defaults()
    example_2_custom_calibration()
    example_3_classification()
    example_4_batch_analysis()
    
    print("\n" + "=" * 70)
    print("Examples complete. See output above.")
    print("=" * 70 + "\n")

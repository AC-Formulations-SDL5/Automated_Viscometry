"""
Batch Rheology Analysis Script

Processes one or more samples through the rheology pipeline and outputs
classification (Newtonian/non-Newtonian) plus rheological parameters.

Usage:
    python analyze_viscometry.py --calibration height_normalized.csv \\
                                 --output results.csv \\
                                 sample1.csv sample2.csv ...
"""

import argparse
import json
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd
import sys

from rheology_pipeline_core import (
    RheologyPipeline,
    create_default_pipeline,
    ConeGeometry
)


def load_sample_data(csv_path: Path) -> dict:
    """
    Load a sample CSV file.
    
    Expected format (flexible):
    - Columns: height, torque, rpm (or similar names)
    - One or more RPM values allowed
    - Long format (one row per measurement)
    
    Returns dict with:
        - 'is_multi_rpm': bool
        - 'single_rpm_data': {h, T, rpm} if single RPM
        - 'multi_rpm_data': [(h, T, rpm), ...] if multi-RPM
        - 'sample_name': str
    """
    df = pd.read_csv(csv_path)
    
    # Normalize column names
    cols_lower = {c: c.lower() for c in df.columns}
    df = df.rename(columns=cols_lower)
    
    # Try to find height/torque/rpm columns
    h_col = None
    t_col = None
    r_col = None
    
    for c in df.columns:
        if 'height' in c or 'h_mm' in c or c in ['h', 'height']:
            h_col = c
        elif 'torque' in c or 't_pct' in c or c in ['torque', 't']:
            t_col = c
        elif 'rpm' in c or c in ['rpm', 'speed']:
            r_col = c
    
    if h_col is None or t_col is None or r_col is None:
        raise ValueError(
            f"Could not find height, torque, and RPM columns in {csv_path.name}. "
            f"Available columns: {list(df.columns)}"
        )
    
    # Clean data
    df = df.dropna(subset=[h_col, t_col, r_col])
    df[[h_col, t_col, r_col]] = df[[h_col, t_col, r_col]].apply(pd.to_numeric, errors='coerce')
    df = df.dropna(subset=[h_col, t_col, r_col])
    
    if df.empty:
        raise ValueError(f"No valid data in {csv_path.name}")
    
    h = df[h_col].values.astype(float)
    t = df[t_col].values.astype(float)
    r = df[r_col].values.astype(float)
    
    # Re-zero heights to minimum
    h = h - h.min()
    
    # Check if single or multi-RPM
    unique_rpms = np.unique(np.round(r, 2))
    
    result = {
        'sample_name': csv_path.stem,
        'is_multi_rpm': len(unique_rpms) > 1,
        'unique_rpms': list(unique_rpms)
    }
    
    if len(unique_rpms) == 1:
        rpm_val = float(unique_rpms[0])
        result['single_rpm_data'] = {
            'h': h,
            'T': t,
            'rpm': rpm_val
        }
    else:
        # Group by RPM
        rpm_data = []
        for rpm_val in sorted(unique_rpms):
            mask = np.isclose(r, rpm_val, atol=0.05)
            if mask.sum() > 0:
                h_rpm = h[mask]
                t_rpm = t[mask]
                # Re-zero per RPM
                h_rpm = h_rpm - h_rpm.min()
                rpm_data.append({
                    'h': h_rpm,
                    'T': t_rpm,
                    'rpm': float(rpm_val)
                })
        result['multi_rpm_data'] = rpm_data
    
    return result


def analyze_sample(
    pipeline: RheologyPipeline,
    sample_data: dict,
    verbose: bool = False
) -> dict:
    """
    Analyze a single sample through the pipeline.
    
    Returns dict with classification and parameters.
    """
    sample_name = sample_data['sample_name']
    
    try:
        if sample_data['is_multi_rpm']:
            # Multi-RPM: power-law analysis
            h_list = [s['h'] for s in sample_data['multi_rpm_data']]
            T_list = [s['T'] for s in sample_data['multi_rpm_data']]
            rpm_list = [s['rpm'] for s in sample_data['multi_rpm_data']]
            
            result = pipeline.predict_rheology(h_list, T_list, rpm_list)
            
            if verbose:
                print(f"  {sample_name}: {len(rpm_list)} RPMs → {result['regime']}")
                if np.isfinite(result['n']):
                    print(f"    n = {result['n']:.3f}, K = {result['K_Pas_n']:.3e} Pa·s^n")
        else:
            # Single RPM: Newtonian analysis
            data = sample_data['single_rpm_data']
            result = pipeline.predict_rheology(data['h'], data['T'], data['rpm'])
            
            if verbose:
                print(f"  {sample_name}: {data['rpm']:.0f} RPM → {result['regime']}")
                if np.isfinite(result['mu_app_cP']):
                    print(f"    μ = {result['mu_app_cP']:.1f} cP")
        
        result['sample_name'] = sample_name
        result['success'] = True
        
    except Exception as e:
        result = {
            'sample_name': sample_name,
            'regime': f"ERROR: {str(e)}",
            'success': False,
            'error': str(e)
        }
        if verbose:
            print(f"  {sample_name}: ERROR - {str(e)}")
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Batch rheology analysis pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single-sample analysis
  python analyze_viscometry.py --calibration height_normalized.csv sample.csv
  
  # Batch processing with output
  python analyze_viscometry.py --calibration height_normalized.csv \\
                               --output results.csv \\
                               sample1.csv sample2.csv sample3.csv
  
  # With factory defaults (no calibration file)
  python analyze_viscometry.py --factory sample.csv
        """
    )
    
    parser.add_argument(
        'samples',
        nargs='+',
        type=Path,
        help='Sample CSV file(s) to analyze'
    )
    
    parser.add_argument(
        '--calibration',
        type=Path,
        default=None,
        help='Silicone calibration CSV (e.g., height_normalized.csv)'
    )
    
    parser.add_argument(
        '--factory',
        action='store_true',
        help='Use factory-default calibration (no calibration file needed)'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Save results to CSV file'
    )
    
    parser.add_argument(
        '--json',
        type=Path,
        default=None,
        help='Save full results as JSON'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # ========== Initialize pipeline ==========
    print("Initializing rheology pipeline...")
    
    if args.factory:
        pipeline = create_default_pipeline()
        print("  Using factory-default calibration")
    elif args.calibration:
        cal_path = Path(args.calibration)
        if not cal_path.exists():
            print(f"ERROR: Calibration file not found: {cal_path}")
            sys.exit(1)
        pipeline = RheologyPipeline()
        print(f"  Loading calibration from {cal_path.name}...")
        cal_info = pipeline.load_silicone_calibration(cal_path)
        print(f"    h_c = {cal_info['h_c']:.4f} mm")
        print(f"    A = {cal_info['k']:.2e} · μ^{cal_info['p']:.3f}")
        print(f"    R² = {cal_info['R2_calibration']:.4f}")
    else:
        print("ERROR: Must provide --calibration or --factory")
        sys.exit(1)
    
    # ========== Load and analyze samples ==========
    print(f"\nProcessing {len(args.samples)} sample(s)...\n")
    
    results = []
    
    for sample_path in args.samples:
        if not sample_path.exists():
            print(f"  WARNING: File not found: {sample_path}")
            continue
        
        try:
            if args.verbose:
                print(f"Loading {sample_path.name}...")
            sample_data = load_sample_data(sample_path)
            
            result = analyze_sample(pipeline, sample_data, verbose=args.verbose)
            results.append(result)
        
        except Exception as e:
            print(f"  ERROR loading {sample_path.name}: {str(e)}")
            results.append({
                'sample_name': sample_path.stem,
                'regime': f"LOAD_ERROR",
                'success': False,
                'error': str(e)
            })
    
    # ========== Output results ==========
    print("\n" + "="*70)
    print("RESULTS SUMMARY")
    print("="*70)
    
    # Print table
    print(f"\n{'Sample':<30} {'Regime':<25} {'n':<10} {'K (Pa·s^n)':<15}")
    print("-" * 80)
    
    for r in results:
        sample = r.get('sample_name', '?')[:29]
        regime = r.get('regime', 'UNKNOWN')[:24]
        
        n_val = r.get('n', np.nan)
        K_val = r.get('K_Pas_n', np.nan)
        
        n_str = f"{n_val:.3f}" if np.isfinite(n_val) else "—"
        K_str = f"{K_val:.2e}" if np.isfinite(K_val) else "—"
        
        print(f"{sample:<30} {regime:<25} {n_str:<10} {K_str:<15}")
    
    # ========== Save output ==========
    if args.output:
        out_path = Path(args.output)
        
        # Flatten results for CSV
        flat_results = []
        for r in results:
            flat_row = {
                'sample': r.get('sample_name', '?'),
                'regime': r.get('regime', 'UNKNOWN'),
                'n': r.get('n', np.nan),
                'K_Pas_n': r.get('K_Pas_n', np.nan),
                'R2_powerlaw': r.get('R2_powerlaw', np.nan),
                'n_rpms': r.get('n_rpms', 1),
                'success': r.get('success', False),
                'error': r.get('error', '')
            }
            flat_results.append(flat_row)
        
        df_out = pd.DataFrame(flat_results)
        df_out.to_csv(out_path, index=False)
        print(f"\nResults saved to: {out_path}")
    
    if args.json:
        json_path = Path(args.json)
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Detailed results saved to: {json_path}")
    
    print("\nDone.")


if __name__ == '__main__':
    main()

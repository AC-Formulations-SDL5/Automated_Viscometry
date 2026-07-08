"""
Automated Cone-Plate Viscometry Analysis Pipeline

A compact, reusable pipeline that converts raw drag-vs-height measurements
into full rheology characterization: Newtonian or non-Newtonian classification,
flow-behavior index (n), consistency (K), and viscosity predictions.

Usage:
    pipeline = RheologyPipeline(calibration_data_dir)
    result = pipeline.analyze_sample(heights, torques, rpms)
    print(result['regime'])  # 'Newtonian' / 'shear-thinning' / 'shear-thickening'
"""

from __future__ import annotations
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy import stats
import json

warnings.filterwarnings("ignore", category=FutureWarning)


# ============================================================================
# GEOMETRY & PHYSICAL CONSTANTS
# ============================================================================

class ConeGeometry:
    """Cone-plate viscometer geometry and unit conversions."""
    
    def __init__(self, cone_radius_mm: float = 12.0, cone_angle_deg: float = 3.0):
        self.R_MM = cone_radius_mm
        self.R_M = cone_radius_mm * 1e-3
        self.ANGLE_DEG = cone_angle_deg
        self.ANGLE_RAD = np.deg2rad(cone_angle_deg)
        
        # Torque calibration: full-scale torque for the instrument
        self.TORQUE_FULL_SCALE_DYNE_CM = 7187.0
        self.M_FULL_NM = self.TORQUE_FULL_SCALE_DYNE_CM * 1e-7  # 7.187e-4 N·m
        
        # Conversion factor: percent torque -> shear stress (Pa)
        self.PCT_TO_PA = (3.0 * (self.M_FULL_NM / 100.0)) / (2.0 * np.pi * self.R_M**3)
        self.CP_TO_PAS = 1.0e-3  # cP -> Pa·s
    
    def shear_rate(self, rpm: float | np.ndarray) -> float | np.ndarray:
        """Cone-plate shear rate (s^-1) from spindle RPM.
        
        γ̇ = ω/α = (2π·RPM)/(60·α)  ≈ 2·RPM  (for α=3°)
        """
        return 2.0 * np.pi * np.asarray(rpm, float) / (60.0 * self.ANGLE_RAD)
    
    def torque_to_stress(self, torque_pct: float | np.ndarray) -> float | np.ndarray:
        """Convert percent full-scale torque to absolute shear stress (Pa)."""
        return np.asarray(torque_pct, float) * self.PCT_TO_PA


# ============================================================================
# DRAG PROFILE FITTING
# ============================================================================

def fit_drag_profile(h: np.ndarray, drag: np.ndarray, h_c: float | None = None) -> dict:
    """
    Fit D(h) = A/(h + h_c) + B to extract amplitude A.
    
    Parameters
    ----------
    h : np.ndarray
        Gap heights (mm), re-zeroed to minimum.
    drag : np.ndarray
        Drag D = T(%) / RPM.
    h_c : float, optional
        If provided, hold h_c fixed. Otherwise fit it freely.
    
    Returns
    -------
    dict with keys: A, B, h_c, R2, n (number of points).
    """
    h = np.asarray(h, float)
    drag = np.asarray(drag, float)
    
    # Filter valid points
    m = np.isfinite(h) & np.isfinite(drag)
    h, drag = h[m], drag[m]
    
    if len(h) < 4:
        return dict(A=np.nan, B=np.nan, h_c=np.nan, R2=np.nan, n=len(h))
    
    try:
        if h_c is None:
            # 3-parameter fit: A, B, h_c (all free)
            def model(x, A, B, hc):
                return A / (x + hc) + B
            
            A0 = (drag.max() - drag.min()) * (h.min() + 0.25)
            popt, _ = curve_fit(
                model, h, drag,
                p0=[max(A0, 1e-3), float(np.median(drag[-5:])), 0.25],
                bounds=([0, -np.inf, 1e-3], [np.inf, np.inf, 5.0]),
                maxfev=20000
            )
            A, B, h_c_fit = popt
            pred = model(h, *popt)
        else:
            # 2-parameter fit: A, B (h_c fixed)
            def model(x, A, B):
                return A / (x + h_c) + B
            
            A0 = (drag.max() - drag.min()) * (h.min() + h_c)
            popt, _ = curve_fit(
                model, h, drag,
                p0=[max(A0, 1e-3), float(np.median(drag[-5:]))],
                maxfev=20000
            )
            A, B = popt
            h_c_fit = h_c
            pred = model(h, *popt)
        
        # Compute R²
        ss_r = np.sum((drag - pred) ** 2)
        ss_t = np.sum((drag - drag.mean()) ** 2)
        R2 = 1 - ss_r / ss_t if ss_t > 0 else np.nan
        
        return dict(A=float(A), B=float(B), h_c=float(h_c_fit), R2=float(R2), n=len(h))
    
    except Exception as e:
        return dict(A=np.nan, B=np.nan, h_c=h_c, R2=np.nan, n=len(h))


# ============================================================================
# POWER-LAW FITTING
# ============================================================================

def fit_power_law(gamma_dot: np.ndarray, A_vals: np.ndarray) -> dict:
    """
    Fit power law A(γ̇) = A0·γ̇^(n-1) via log-log linear regression.
    
    Returns dict with: n (flow-behavior index), A0, R2, n_pts.
    """
    g = np.asarray(gamma_dot, float)
    a = np.asarray(A_vals, float)
    
    # Filter valid points
    m = np.isfinite(g) & np.isfinite(a) & (g > 0) & (a > 0)
    g, a = g[m], a[m]
    
    if len(g) < 2:
        return dict(n=np.nan, A0=np.nan, R2=np.nan, n_pts=int(len(g)))
    
    if len(g) == 2:
        # Only two points: fit via them directly
        slope = (np.log(a[1]) - np.log(a[0])) / (np.log(g[1]) - np.log(g[0]))
        return dict(
            n=float(slope + 1.0),
            A0=float(a[0] * g[0] ** (-slope)),
            R2=np.nan,
            n_pts=2
        )
    
    # Linear log-log regression: ln(A) = ln(A0) + (n-1)·ln(γ̇)
    res = stats.linregress(np.log(g), np.log(a))
    return dict(
        n=float(res.slope + 1.0),
        A0=float(np.exp(res.intercept)),
        R2=float(res.rvalue ** 2),
        n_pts=int(len(g))
    )


# ============================================================================
# MAIN PIPELINE CLASS
# ============================================================================

class RheologyPipeline:
    """
    End-to-end pipeline for viscometry data analysis.
    
    Workflow:
    1. Load/set universal calibration from silicone oils (h_c, k, p)
    2. For each sample: fit drag profiles → extract amplitudes
    3. Fit power law (if multi-RPM) or report Newtonian viscosity
    4. Classify as Newtonian / shear-thinning / shear-thickening
    """
    
    def __init__(self, geometry: ConeGeometry | None = None):
        """
        Initialize pipeline.
        
        Parameters
        ----------
        geometry : ConeGeometry, optional
            If None, use default cone-plate geometry.
        """
        self.geo = geometry or ConeGeometry()
        
        # Calibration parameters (to be set via load_silicone_calibration or set manually)
        self.H_C_UNIVERSAL = None
        self.SILICONE_K = None
        self.SILICONE_P = None
        self.is_calibrated = False
    
    def set_calibration(self, h_c: float, k: float, p: float):
        """Manually set calibration parameters."""
        self.H_C_UNIVERSAL = float(h_c)
        self.SILICONE_K = float(k)
        self.SILICONE_P = float(p)
        self.is_calibrated = True
    
    def load_silicone_calibration(self, silicone_csv: Path | str):
        """
        Load silicone calibration data and fit h_c and A(μ) power law.
        
        Silicone CSV should have wide format:
            Height, <nom>kcp_<mu>_torque_%_rpm_<rpm>, ...
        """
        path = Path(silicone_csv)
        df = pd.read_csv(path)
        
        if "Height" not in df.columns:
            raise ValueError(f"Expected 'Height' column in {path.name}")
        
        # Parse wide format and extract amplitudes
        import re
        re_col = re.compile(
            r"^(?P<nom>[\d.]+)kcp_(?P<mu>[\d.]+)_torque_%_rpm_(?P<rpm>[\d.]+)$"
        )
        
        rows = []
        for col in df.columns:
            if col == "Height":
                continue
            m = re_col.match(col)
            if not m:
                continue
            
            mu_cP = float(m["mu"]) * 1000.0
            rpm = float(m["rpm"])
            
            sub = df[["Height", col]].dropna().rename(columns={col: "T_pct"})
            sub = sub.sort_values("Height")
            h = sub["Height"].values - sub["Height"].min()
            D = sub["T_pct"].values / rpm
            
            fit = fit_drag_profile(h, D, h_c=None)
            rows.append({
                "mu_cP": mu_cP,
                "rpm": rpm,
                "A": fit["A"],
                "h_c": fit["h_c"],
                "R2": fit["R2"]
            })
        
        if not rows:
            raise ValueError("No silicone data parsed from CSV")
        
        sil = pd.DataFrame(rows)
        
        # Extract universal h_c (trimmed median)
        mask = (sil["R2"] > 0.7) & sil["h_c"].between(0.05, 1.5)
        h_c_universal = float(np.median(sil.loc[mask, "h_c"]))
        
        # Fit A(μ) power law
        mask_good = (sil["R2"] > 0.7) & (sil["A"] > 0)
        mu = sil.loc[mask_good, "mu_cP"].values
        A = sil.loc[mask_good, "A"].values
        
        slope, intercept, r, _, _ = stats.linregress(np.log(mu), np.log(A))
        k = float(np.exp(intercept))
        p = float(slope)
        
        self.set_calibration(h_c_universal, k, p)
        
        return {
            "h_c": h_c_universal,
            "k": k,
            "p": p,
            "R2_calibration": float(r ** 2),
            "n_silicones": len(sil)
        }
    
    def amplitude_to_viscosity(self, A: float | np.ndarray) -> float | np.ndarray:
        """
        Invert silicone calibration: μ_app(cP) = (A/k)^(1/p).
        """
        if not self.is_calibrated:
            raise RuntimeError("Pipeline not calibrated. Call set_calibration() first.")
        
        A = np.asarray(A, float)
        out = np.full_like(A, np.nan, dtype=float)
        pos = A > 0
        out[pos] = (A[pos] / self.SILICONE_K) ** (1.0 / self.SILICONE_P)
        return out
    
    def analyze_single_rpm(self, h_mm: np.ndarray, torque_pct: np.ndarray, rpm: float) -> dict:
        """
        Analyze a single-RPM measurement → Newtonian result.
        
        Parameters
        ----------
        h_mm : np.ndarray
            Gap heights (mm).
        torque_pct : np.ndarray
            Torque (% full scale).
        rpm : float
            Spindle speed (RPM).
        
        Returns
        -------
        dict with analysis results.
        """
        if not self.is_calibrated:
            raise RuntimeError("Pipeline not calibrated.")
        
        # Compute drag
        D = torque_pct / float(rpm)
        
        # Fit drag profile
        fit = fit_drag_profile(h_mm, D, h_c=self.H_C_UNIVERSAL)
        A = fit["A"]
        
        if not np.isfinite(A) or A <= 0:
            return {
                "mode": "newtonian",
                "regime": "Error: invalid amplitude",
                "n": np.nan,
                "K_Pas_n": np.nan,
                "mu_app_cP": np.nan,
                "gamma_dot": float(self.geo.shear_rate(rpm)),
                "fit_quality": fit["R2"]
            }
        
        # Convert amplitude to viscosity
        mu_cP = float(self.amplitude_to_viscosity(np.array([A]))[0])
        K_Pas = mu_cP * self.geo.CP_TO_PAS
        
        return {
            "mode": "newtonian",
            "regime": "Newtonian",
            "n": 1.0,
            "K_Pas_n": K_Pas,
            "mu_app_cP": mu_cP,
            "gamma_dot": float(self.geo.shear_rate(rpm)),
            "fit_quality": fit["R2"],
            "A": A
        }
    
    def analyze_multi_rpm(
        self,
        h_mm_list: list[np.ndarray],
        torque_pct_list: list[np.ndarray],
        rpm_list: list[float] | np.ndarray,
        thinning_thr: float = 0.95,
        thickening_thr: float = 1.05
    ) -> dict:
        """
        Analyze multi-RPM measurement → power-law result.
        
        Parameters
        ----------
        h_mm_list : list of np.ndarray
            Gap heights for each RPM.
        torque_pct_list : list of np.ndarray
            Torque for each RPM.
        rpm_list : list or array of floats
            RPM values.
        thinning_thr, thickening_thr : float
            Flow-behavior index thresholds for classification.
        
        Returns
        -------
        dict with power-law parameters and classification.
        """
        if not self.is_calibrated:
            raise RuntimeError("Pipeline not calibrated.")
        
        # Extract amplitudes from each RPM
        A_pts = []
        for h, T, rpm in zip(h_mm_list, torque_pct_list, rpm_list):
            D = np.asarray(T, float) / float(rpm)
            fit = fit_drag_profile(np.asarray(h, float), D, h_c=self.H_C_UNIVERSAL)
            A = fit["A"]
            if np.isfinite(A) and A > 0:
                A_pts.append((float(rpm), A))
        
        if len(A_pts) < 2:
            return {
                "mode": "powerlaw",
                "regime": "Error: < 2 valid RPMs",
                "n": np.nan,
                "K_Pas_n": np.nan,
                "R2_powerlaw": np.nan,
                "n_rpms": len(A_pts)
            }
        
        # Fit power law
        rpms, As = map(np.array, zip(*A_pts))
        g = self.geo.shear_rate(rpms)
        pl = fit_power_law(g, As)
        
        # Compute consistency
        i_min = np.argmin(g)
        mu0 = float(self.amplitude_to_viscosity(np.array([As[i_min]]))[0])
        g0 = float(g[i_min])
        K_cP = mu0 * (g0 ** (1.0 - pl["n"]))
        K_Pas = K_cP * self.geo.CP_TO_PAS
        n = pl["n"]
        
        # Classify
        if n > thickening_thr:
            regime = "shear-thickening"
        elif n < thinning_thr:
            regime = "shear-thinning"
        else:
            regime = "Newtonian"
        
        return {
            "mode": "powerlaw",
            "regime": regime,
            "n": float(n),
            "K_Pas_n": K_Pas,
            "R2_powerlaw": pl["R2"],
            "n_rpms": len(A_pts),
            "gamma_dot_range": (float(g.min()), float(g.max())),
            "mu_app_cP_at_min_gamma_dot": mu0
        }
    
    def predict_rheology(
        self,
        h_mm,
        torque_pct,
        rpm,
        **kwargs
    ) -> dict:
        """
        Unified interface: automatically detects single vs. multi-RPM.
        
        Single RPM:
            h_mm, torque_pct : 1-D arrays
            rpm : scalar
        
        Multi RPM:
            h_mm, torque_pct : list of 1-D arrays
            rpm : list/array of scalars
        
        Returns dict with full rheology characterization.
        """
        if not self.is_calibrated:
            raise RuntimeError("Pipeline not calibrated.")
        
        # Detect mode: multi-RPM iff h_mm is a sequence of sequences
        try:
            is_seq = (
                hasattr(h_mm, "__len__")
                and not isinstance(h_mm, (str, bytes, np.ndarray))
                and hasattr(h_mm[0], "__len__")
                and not isinstance(h_mm[0], (str, bytes))
            )
        except (IndexError, TypeError):
            is_seq = False
        
        if not is_seq:
            # Single RPM
            return self.analyze_single_rpm(
                np.asarray(h_mm, float),
                np.asarray(torque_pct, float),
                float(rpm)
            )
        else:
            # Multi RPM
            return self.analyze_multi_rpm(
                [np.asarray(h, float) for h in h_mm],
                [np.asarray(T, float) for T in torque_pct],
                np.asarray(rpm, float),
                **kwargs
            )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_default_pipeline(silicone_calibration_csv: Path | str | None = None) -> RheologyPipeline:
    """
    Create a pipeline with default geometry.
    
    If silicone_calibration_csv is provided, load calibration from it.
    Otherwise, use factory-default values from a typical setup.
    """
    pipeline = RheologyPipeline()
    
    if silicone_calibration_csv is not None:
        path = Path(silicone_calibration_csv)
        if path.exists():
            pipeline.load_silicone_calibration(path)
            return pipeline
    
    # Factory defaults (from typical cone-plate setup with silicone oils)
    # These are approximate — for production, load from actual calibration CSV
    pipeline.set_calibration(
        h_c=0.2534,      # universal gap offset (mm)
        k=3.45e-4,       # A = k·μ^p calibration coefficient
        p=1.026          # power-law exponent (~1 for Newtonian, slight positive slope)
    )
    
    return pipeline


if __name__ == "__main__":
    # Example usage
    print("Rheology Pipeline Module")
    print("=" * 60)
    print("\nUsage:")
    print("  pipeline = RheologyPipeline()")
    print("  pipeline.load_silicone_calibration('height_normalized.csv')")
    print("  result = pipeline.predict_rheology(heights, torques, rpms)")
    print("  print(result['regime'])")  # Newtonian / shear-thinning / etc.

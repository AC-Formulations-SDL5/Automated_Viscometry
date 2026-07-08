"""Calibration constants for unified cone-plate rheology prediction."""

from __future__ import annotations

import numpy as np

R_CONE_MM = 12.0
CONE_ANGLE_DEG = 3.0
CONE_ANGLE_RAD = float(np.deg2rad(CONE_ANGLE_DEG))
R_CONE_M = R_CONE_MM * 1e-3

TORQUE_FULL_SCALE_DYNE_CM = 7187.0
M_FULL_NM = TORQUE_FULL_SCALE_DYNE_CM * 1e-7
PCT_TO_PA = (3.0 * (M_FULL_NM / 100.0)) / (2.0 * np.pi * R_CONE_M**3)
CP_TO_PAS = 1.0e-3

H_C_UNIVERSAL_MM = 0.2774
# Linear silicone calibration (p=1): mu_cP = A / SILICONE_K
SILICONE_K = 3.0e-04
SILICONE_P = 1.0

FIT_R2_MIN = 0.7

# Three-pathway characterization routing on n_stress
NEWTONIAN_N_LOW = 0.9
NEWTONIAN_N_HIGH = 1.1
STRONG_THINNING_N_MAX = 0.5

# Amplitude power-law regime labels (aligned with Newtonian band)
THINNING_THRESHOLD = NEWTONIAN_N_LOW
THICKENING_THRESHOLD = NEWTONIAN_N_HIGH


def shear_rate(rpm) -> np.ndarray:
    """Cone-plate shear rate (s^-1) from spindle RPM."""
    return 2.0 * np.pi * np.asarray(rpm, float) / (60.0 * CONE_ANGLE_RAD)

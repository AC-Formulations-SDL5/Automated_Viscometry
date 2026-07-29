import sys, re
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(r'C:\Users\mrast\OneDrive\Documents\GitHub\Automated_Viscometry')
sys.path.insert(0, str(REPO))
from rheology_pipeline_core import RheologyPipeline, fit_drag_profile

DATA_DIR  = REPO / 'Rheology_Newtonian_Non_Newtonian_Material'
CALIB_CSV = REPO / 'results' / 'Auto-runs' / 'height_normalized.csv'

pipeline = RheologyPipeline()
pipeline.load_silicone_calibration(CALIB_CSV)

# Load sepineo
def load_sample(path):
    df = pd.read_csv(path, encoding='latin-1', low_memory=False, skip_blank_lines=False)
    blank_sep = df[['Cell_Label', 'Z_Height_mm', 'RPM', 'Torque_%']].isna().all(axis=1)
    df['Experiment_ID'] = blank_sep.cumsum().astype(int)
    df = df[df['RPM'].astype(str).str.strip() != 'RPM'].copy()
    NUM_COLS = ['Z_Height_mm', 'RPM', 'Torque_%', 'Rotational_Drag']
    for c in NUM_COLS:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.dropna(subset=NUM_COLS)
    df = df[df['Torque_%'] > 0]
    df = df[df['RPM'] > 0]
    df['Cell_Label'] = (df['Cell_Label'].astype(str).str.strip() + ' | exp' + (df['Experiment_ID']+1).astype(str))
    df['h_mm'] = df.groupby('Cell_Label')['Z_Height_mm'].transform(lambda s: s - s.min())
    df['RPM_key'] = df['RPM'].round(4)
    df = (df.groupby(['Cell_Label','RPM_key','h_mm'], as_index=False)
          .agg(Z_Height_mm=('Z_Height_mm','mean'), RPM=('RPM','mean'),
               **{'Torque_%': ('Torque_%','mean')},
               Rotational_Drag=('Rotational_Drag','mean'),
               Experiment_ID=('Experiment_ID','first')))
    return df.reset_index(drop=True)

df = load_sample(DATA_DIR / 'sepineo.csv')
print('All cell labels:', df['Cell_Label'].unique())

for cl in df['Cell_Label'].dropna().unique():
    dfc = df[df['Cell_Label'] == cl]
    groups = []
    for rpm_key, sub in dfc.groupby('RPM_key', sort=True):
        sub = sub.sort_values('h_mm')
        if len(sub) >= 4:
            groups.append((float(sub['RPM'].mean()), sub['h_mm'].to_numpy(), sub['Torque_%'].to_numpy()))
    
    if not groups:
        continue
    
    per_rpm_rows = []
    for rpm, h, T in groups:
        D = T / float(rpm)
        fit = fit_drag_profile(h, D, h_c=pipeline.H_C_UNIVERSAL)
        A = fit['A']
        mu = float(pipeline.amplitude_to_viscosity(np.array([A]))[0]) if np.isfinite(A) and A > 0 else np.nan
        per_rpm_rows.append(dict(RPM=rpm, gamma_dot_1_s=float(pipeline.geo.shear_rate(rpm)), A=A, B=fit['B'], h_c=fit['h_c'], R2=fit['R2'], mu_app_cP=mu))
    
    per_rpm = pd.DataFrame(per_rpm_rows).sort_values('RPM').reset_index(drop=True)
    pr = per_rpm.dropna(subset=['mu_app_cP','gamma_dot_1_s'])
    pr = pr[(pr['mu_app_cP'] > 0) & (pr['gamma_dot_1_s'] > 0)]
    
    if len(pr) < 2:
        print(f'{cl}: not enough points')
        continue
    
    # Simple Power Law: tau = K * (gamma_dot)^n  => log(tau) = log(K) + n*log(gamma_dot)
    pr['tau_Pa'] = (pr['mu_app_cP'] / 1000.0) * pr['gamma_dot_1_s']
    g = pr['gamma_dot_1_s'].to_numpy()
    t = pr['tau_Pa'].to_numpy()
    m = (g > 0) & (t > 0) & np.isfinite(g) & np.isfinite(t)
    if m.sum() < 2:
        print(f'{cl}: insufficient finite points')
        continue
    lg, lt = np.log(g[m]), np.log(t[m])
    n, logK = np.polyfit(lg, lt, 1)
    K = float(np.exp(logK))
    print(f'{cl}: K={K:.2f}, n={n:.2f}')

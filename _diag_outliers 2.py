import sys
from pathlib import Path
import numpy as np, pandas as pd

REPO = Path(r"C:\Users\mrast\OneDrive\Documents\GitHub\Automated_Viscometry")
sys.path.insert(0, str(REPO))
from rheology_pipeline_core import RheologyPipeline, fit_drag_profile

DATA = REPO / "Rheology_Newtonian_Non_Newtonian_Material"
CAL  = REPO / "results" / "Auto-runs" / "height_normalized.csv"

p = RheologyPipeline(); p.load_silicone_calibration(CAL)

NUM = ["Z_Height_mm", "RPM", "Torque_%", "Rotational_Drag"]
def load(path):
    df = pd.read_csv(path, encoding="latin-1", low_memory=False)
    df = df[df["RPM"].astype(str).str.strip() != "RPM"]
    for c in NUM: df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=NUM); df = df[(df["Torque_%"]>0)&(df["RPM"]>0)]
    df["h_mm"] = df.groupby("Cell_Label")["Z_Height_mm"].transform(lambda s: s - s.min())
    df["RPM_key"] = df["RPM"].round(4)
    df = (df.groupby(["Cell_Label","RPM_key","h_mm"], as_index=False)
            .agg(Z_Height_mm=("Z_Height_mm","mean"), RPM=("RPM","mean"),
                 **{"Torque_%":("Torque_%","mean")}, Rotational_Drag=("Rotational_Drag","mean")))
    return df

def per_rpm(df_cell):
    rows=[]
    for _, sub in df_cell.groupby("RPM_key", sort=True):
        sub = sub.sort_values("h_mm")
        if len(sub)<4: continue
        rpm = float(sub["RPM"].mean())
        h = sub["h_mm"].to_numpy(); T = sub["Torque_%"].to_numpy()
        D = T/rpm; fit = fit_drag_profile(h, D, h_c=p.H_C_UNIVERSAL); A=fit["A"]
        mu = float(p.amplitude_to_viscosity(np.array([A]))[0]) if (np.isfinite(A) and A>0) else np.nan
        gdot = float(p.geo.shear_rate(rpm)); tau = (mu/1000.0)*gdot if np.isfinite(mu) else np.nan
        rows.append((rpm, gdot, mu, tau, fit["R2"]))
    return pd.DataFrame(rows, columns=["RPM","gdot","mu","tau","R2drag"])

def fit_pl(g, t):
    m = np.isfinite(g) & np.isfinite(t) & (g>0) & (t>0)
    if m.sum()<2: return float("nan"), float("nan"), float("nan")
    lg, lt = np.log(g[m]), np.log(t[m])
    n, lk = np.polyfit(lg, lt, 1); K = np.exp(lk)
    res = lt - (lk + n*lg); sr = float((res**2).sum()); st = float(((lt-lt.mean())**2).sum())
    return K, n, (1 - sr/st if st>0 else float("nan"))

def clean(d, r2min=0.85, k=2.5, min_keep=3, max_iter=6):
    base = (np.isfinite(d["gdot"]) & np.isfinite(d["tau"]) & (d["gdot"]>0) & (d["tau"]>0)).to_numpy()
    keep = base.copy()
    q = base & (d["R2drag"].to_numpy() >= r2min)
    min_req = max(min_keep + 1, int(0.6 * base.sum()), 5)
    if q.sum() >= min_req:
        keep = q
    if keep.sum() < min_keep:
        keep = base.copy()
    lg, lt = np.log(d["gdot"].to_numpy()), np.log(d["tau"].to_numpy())
    for _ in range(max_iter):
        idx = np.where(keep)[0]
        if len(idx) <= min_keep: break
        n, lk = np.polyfit(lg[idx], lt[idx], 1)
        res = lt[idx] - (lk + n*lg[idx])
        mad = np.median(np.abs(res - np.median(res))) or 1e-12
        w = int(np.argmax(np.abs(res)))
        if abs(res[w]) <= k * 1.4826 * mad: break
        keep[idx[w]] = False
    return keep

targets = {
    "PEG":     ["5%300K_577","10%300K_7158","5%600K_3254","6.5%600K_4109","10%600K_64250"],
    "sepineo": ["1%sep_2148","1.5%sep_17240","2%sep_50110"],
    "solagum": ["1%sola_522","2%sola_35860","3%sola_130700"],
    "carbopol":["980carb0.3%_49810","980carb0.4%_159700"],
}

print(f"{'sample':<9s} {'cell':<24s} {'K':>9s} {'n':>6s} {'R2_raw':>8s} {'R2_clean':>9s} {'kept':>8s}")
for s, cls in targets.items():
    df = load(DATA / f"{s}.csv")
    for cl in cls:
        sub = df[df["Cell_Label"]==cl]
        if sub.empty: continue
        pr = per_rpm(sub)
        _, _, R2b = fit_pl(pr["gdot"].to_numpy(), pr["tau"].to_numpy())
        keep = clean(pr)
        Ka, na, R2a = fit_pl(pr["gdot"].to_numpy()[keep], pr["tau"].to_numpy()[keep])
        print(f"{s:<9s} {cl:<24s} {Ka:>9.3g} {na:>6.2f} {R2b:>8.2f} {R2a:>9.2f} {str(int(keep.sum()))+'/'+str(len(pr)):>8s}")

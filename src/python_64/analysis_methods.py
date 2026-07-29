# Analysis methods that use the 64-bit ViscometerClient
import csv, time, pathlib
from typing import List
from viscometer_client import ViscometerClient

# SINGLE RPM — spin for a duration and sample periodically; write time-series CSV
def run_single_rpm(results_dir: pathlib.Path, client: ViscometerClient):
    RPM                = 4.6
    TOTAL_SECONDS      = 5
    SAMPLE_EVERY_SEC   = 1
    SETTLE_SECONDS     = 1.0
    CSV_NAME           = f"single_rpm_{RPM:.2f}.csv"

    out = results_dir / CSV_NAME
    out.parent.mkdir(parents=True, exist_ok=True)
    client.set_speed(RPM)
    time.sleep(SETTLE_SECONDS)
    t0 = time.time()
    next_t = t0 + SAMPLE_EVERY_SEC
    rows = []

    while True:
        now = time.time()
        if now - t0 >= TOTAL_SECONDS:
            break
        if now >= next_t:
            pkt = client.read_single(timeout=1.0)  
            if pkt:
                rows.append({
                    "time_s": round(now - t0, 2),
                    "rpm": RPM,
                    "torque_percent": pkt.get("torque_percent"),
                    "viscosity_cp": pkt.get("viscosity_cp"),
                })
            next_t += SAMPLE_EVERY_SEC
        else:
            time.sleep(0.05)

    client.stop()
    with out.open("w", newline="", encoding="utf-8") as f: # Write CSV
        w = csv.DictWriter(f, fieldnames=[
            "time_s", "rpm", "torque_percent", "viscosity_cp"
        ])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return str(out)

# DYNAMIC ANALYSIS: pass an array of 10 RPMs; dwell at each; read one data point at end; pause between; CSV
def run_dynamic_analysis(results_dir: pathlib.Path, client: ViscometerClient):
    RPMS              = [2.5, 3.0, 3.5, 4.0, 4.5, 4.5, 4.5, 5.0, 5.5, 6.0]  
    DWELL_SECONDS     = 90.0     
    SETTLE_SECONDS    = 1.0     
    INTER_PAUSE_SEC   = 1.0      
    CSV_NAME          = "dynamic_analysis.csv"

    out = results_dir / CSV_NAME
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for rpm in RPMS:
        client.set_speed(float(rpm))
        time.sleep(SETTLE_SECONDS)
        # dwell at rpm
        time.sleep(max(DWELL_SECONDS - SETTLE_SECONDS, 0.0))
        pkt = client.read_single(timeout=1.0)
        rows.append({
            "rpm": float(rpm),
            "torque_percent": None if not pkt else pkt.get("torque_percent"),
            "torque_valid": None if not pkt else pkt.get("torque_valid"),
            "temperature_c": None if not pkt else pkt.get("temperature_c"),
            "temp_valid":    None if not pkt else pkt.get("temp_valid"),
            "viscosity_cp":  None if not pkt else pkt.get("viscosity_cp"),
            "status":        None if not pkt else pkt.get("status"),
            "record":        None if not pkt else pkt.get("record_number"),
        })
        client.stop()
        time.sleep(INTER_PAUSE_SEC)

    with out.open("w", newline="", encoding="utf-8") as f:   # Write CSV 
        w = csv.DictWriter(f, fieldnames=[
            "rpm","torque_percent","torque_valid",
            "temperature_c","temp_valid","viscosity_cp","status","record"
        ])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return str(out)

# BISECTION: find rpm that hits a target torque, then final hold; write CSV of search history + final point
def run_bisection(results_dir: pathlib.Path, client: ViscometerClient):
    TARGET_TORQUE_PCT = 50.0    
    TOL_PCT           = 20.0    
    LOW_RPM           = 0.5
    HIGH_RPM          = 30
    MAX_ITERS         = 20
    SETTLE_SECONDS    = 60.0
    FINAL_HOLD_S      = 60.0     
    INTER_PAUSE_SEC   = 2.0     
    CSV_NAME          = "bisection_analysis.csv"

    out = results_dir / CSV_NAME
    out.parent.mkdir(parents=True, exist_ok=True)

    history = []
    lo, hi = float(LOW_RPM), float(HIGH_RPM)
    best_rpm, best_err = None, float("inf")

    for _ in range(MAX_ITERS):
        mid = (lo + hi) / 2.0
        client.set_speed(mid)
        time.sleep(SETTLE_SECONDS)
        pkt = client.read_single(timeout=1.0)
        client.stop()
        time.sleep(INTER_PAUSE_SEC)

        if not pkt or not pkt.get("torque_valid"):
            # treat as unusable datapoint; shrink range slightly around mid and continue
            lo = max(0.1, mid * 0.9)
            hi = min(200.0, mid * 1.1)
            continue

        tq = float(pkt["torque_percent"])
        err = abs(tq - TARGET_TORQUE_PCT)
        history.append({"rpm": mid, "torque_percent": tq, "viscosity_cp": pkt.get("viscosity_cp")})

        if err < best_err:
            best_err, best_rpm = err, mid
        if err <= TOL_PCT:
            break
        if tq < TARGET_TORQUE_PCT:
            lo = mid
        else:
            hi = mid

    # Final hold at best_rpm (if none, fall back to mid of last range)
    final_rpm = best_rpm if best_rpm is not None else (lo + hi) / 2.0
    client.set_speed(final_rpm)
    time.sleep(FINAL_HOLD_S)
    final_pkt = client.read_single(timeout=1.0)
    client.stop()

    # write CSV
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["# Target torque (%)", TARGET_TORQUE_PCT])
        w.writerow(["# Tolerance (%)", TOL_PCT])
        w.writerow(["# Final RPM", round(final_rpm, 3)])
        w.writerow([])
        w.writerow(["RPM", "Torque (%)", "Viscosity (cP)"])
        for h in history:
            w.writerow([round(h["rpm"], 3), h["torque_percent"], h["viscosity_cp"]])
        w.writerow([])
        w.writerow(["FINAL_RPM", round(final_rpm, 3)])
        if final_pkt:
            w.writerow(["FINAL_TORQUE_%", final_pkt.get("torque_percent")])
            w.writerow(["FINAL_VISCOSITY_cP", final_pkt.get("viscosity_cp")])
    return str(out)

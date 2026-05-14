# CNC-Viscometer-Washing Station Orchestration Scenario

This document is the working reference for how the automated viscometry rig behaves end-to-end,
from the **calibration / recalibration** workflow that establishes per-cell Z-hitpoints, through
the **per-cell Z-descent measurement loop** (Z-floor minimum, low-torque liquid hunting, smart
early exit, rotational-drag hit-point detection), into the **concurrent washing mechanism** that
overlaps wash-station fill/drain with CNC travel, and finally the **hyperbola predicted-viscosity
curve fit** that runs immediately after each cell.

The authoritative implementation is [src/python_64/all_cells_with_rotational_drag_feedback.py](src/python_64/all_cells_with_rotational_drag_feedback.py).
Supporting modules:
- Feedback / hit-point logic: [src/python_64/feedback_helper_function.py](src/python_64/feedback_helper_function.py)
- Calibration persistence: [src/python_64/calibration_store.py](src/python_64/calibration_store.py)
- Hardware I/O: `cnc_controller.py`, `viscometer_client.py`, `move_to_locations.py`
- Web orchestration: `web_interface.py`

---

## 1. System Overview

The system coordinates four cooperating subsystems:

| Subsystem | Purpose | Interface |
|---|---|---|
| **CNC** (GRBL) | 3-axis positioning of the viscometer spindle over a tray of 18 cells and 2 wash stations | COM12 @ 115200 |
| **Viscometer** (Brookfield DV2T Pro) | Sets RPM, returns torque % | COM6 @ 115200 (via 32-bit Python subprocess `worker32.py`) |
| **ESP32 wash controller** | Drives wash-station pumps and DC agitation motors | COM11 @ 115200 |
| **Web interface** | Run configuration, Start/Stop, live status / live torque / live feedback metrics | Flask + Socket.IO, browser |

### Cell tray layout (`ROWS`)

```
Row 1  (cells 1–6)   BASE_X = 10    safe_z = -65.5   max_z_travel = -66.500
Row 2  (cells 7–12)  BASE_X = 85    safe_z = -65.5   max_z_travel = -66.500
Row 3  (cells 13–18) BASE_X = 309   safe_z = -64.5   max_z_travel = -65.500

BASE_Y = 62,  Y_OFFSET = 67   →   Y = BASE_Y + (local_cell-1) * Y_OFFSET
```

Global cell `1..18` ↔ `(row, local_cell)` via `global_cell_to_row_and_local()` /
`row_and_local_to_global_cell()`.

### Wash stations

```
Station 1: X=383, Y=68,  Z=-67 (contact);  Z=0 is the travel-safe height
Station 2: X=383, Y=147, Z=-67 (contact)
```

### Run modes

`get_selected_cells()` resolves the run mode (returned as `mode`) which gates almost every
downstream branch:

| Mode string | Trigger | Cells visited |
|---|---|---|
| `"calibration"` | `CALIBRATION_MODE = True` | all 18 cells |
| `"recalibration"` | `RECALIBRATE_INDIVIDUAL_CELLS = True` | keys of `RECALIBRATION_CELLS` |
| `"full"` | `TESTING_MODE = "full"` | 1..18 |
| `"row"` | `TESTING_MODE = "row"` | `SELECTED_ROWS` expanded to global cells |
| `"custom"` | `TESTING_MODE = "custom"` | `SELECTED_CELLS` (per-cell RPMs via `CELL_RPM_MAP`) |

All run settings (mode, selected cells, RPMs, dwell, sample interval, feedback weights,
liquid-contact threshold, predicted-viscosity toggle, etc.) flow from the web UI into module
globals via `apply_runtime_settings_from_web()`.

---

## 2. Phase A — Run Start & Hardware Initialization

`main()` runs an outer `while True:` loop that, between runs, waits for the **Start Run** event
from the web UI (`web_interface.consume_start_command()` + `wait_for_start_command()`).

For each run:

1. `apply_runtime_settings_from_web()` — copies all web-form values into module globals.
2. `get_selected_cells()` — returns `(mode, selected_cells)`. `mode` is captured locally and
   reused for the rest of the run; later per-cell branches use
   `is_calibration_like_run = mode in ("calibration", "recalibration")` so that calibration
   semantics cannot drift mid-run even if globals are flipped.
3. Hardware bring-up, each in its own `try/except` (a failure aborts this run and waits for
   the next Start):
   - `CNC_Machine(...).home()`
   - `PumpESP32(...).open()` + `ST` (status) handshake — uses
     `send_command_with_ack()` when available, else legacy `send_tag(b"ST")`.
   - `ViscometerClient.init(...)` + one `read_single()` sanity check.
4. Empty `all_data: Dict[int, Dict[float, Dict[float, ...]]]` and `completed_cells = []`
   are created. A list `active_threads` collects background pump-threads for the final join.

---

## 3. Phase B — Per-Cell Loop (`for global_cell in selected_cells`)

For each cell:

1. **Auto-zero the viscometer** (`client.zero()` → 5 s settle → `client.stop()`).
2. **Resolve per-cell RPMs** via `get_rpms_for_cell(global_cell)` — uses `CELL_RPM_MAP[cell]`
   in custom mode, otherwise the global `TEST_RPMS` list.
3. **Status banner** is pushed to the web UI distinguishing calibration / recalibration /
   regular tests.
4. `test_cell_dynamic_z_series(...)` is called. The pump argument is `None` in
   calibration-like runs (no wash), otherwise the live pump handle is passed so the
   in-cell finalizer can fire the concurrent fill/motor threads (Section 6).
5. The returned `(cell_data, _fill_thread)` is recorded in `all_data[global_cell]`. The fill
   thread (if any) is appended to `active_threads`.
6. **Calibration-like run:** call `extract_rough_hitpoint(cell_data)` and store the result in
   the in-memory `calibration_cells[global_cell] = rough_z` (no wash happens — the run
   immediately moves to the next cell).
7. **Normal run:** `perform_washing_sequence(cnc, pump, global_cell, fill_thread=_fill_thread)`
   is invoked, then the cell is added to `web_interface.completed_cells`.

Any exception inside the loop saves partial data (`save_partial_data(...)`) and re-raises,
which the outer `try/except/finally` catches to drive the cleanup path.

---

## 4. Phase C — Z-Descent Inside a Single Cell

`test_cell_dynamic_z_series(...)` is where the bulk of the orchestration lives.

### 4.1 Choosing the starting Z

```python
if custom_starting_z is not None:
    current_z = custom_starting_z                          # per-cell recal override
elif not (CALIBRATION_MODE or RECALIBRATE_INDIVIDUAL_CELLS):
    safe_z = get_safe_z_for_cell(global_cell, safe_z,
                                 offset=CALIBRATION_OFFSET)  # cal hitpoint + 0.4 mm
    current_z = safe_z
else:
    current_z = safe_z                                     # row default for cal run
```

So in a **regular** run the cell starts only `CALIBRATION_OFFSET = 0.4 mm` above the stored
rough hitpoint (from `calibration_store.get_safe_z_for_cell`), saving a lot of empty descent.
Calibration runs always start from the row's `safe_z`.

### 4.2 Z-floor minimum

The loop is driven by `while current_z >= max_z_travel:` with `Z_STEP_SIZE` defaulting to
`-0.02 mm`. `max_z_travel` is the row-specific physical floor (`ROWS[*]['max_z_travel']`) and
is the absolute hard stop — if no hit is detected, the spindle still never goes below this
height. The step size and floor are both configurable per row / per run from the web UI.

### 4.3 Movement at each step

- First step uses `move_to_cell_position()` (safe move with Z-retraction).
- Subsequent steps use a direct `cnc.move_to_point(..., current_z, speed=Z_FEED_RATE)` —
  no retraction, which is how the rig achieves true incremental Z-descent.
- `SETTLE_TIME = 1.0 s` after each move.

### 4.4 RPM sweep at the current Z (`test_dynamic_analysis_at_z`)

For every RPM in `cell_rpms`:

- `measure_torque_at_rpm()` sets the spindle, waits `DWELL_SECONDS`, then samples on a fixed
  grid every `SAMPLE_INTERVAL` seconds from the start of the window (first recorded sample is
  at `1 * SAMPLE_INTERVAL`, no off-grid immediate read) for up to `MEASUREMENT_DURATION`.
- Every accepted sample is mirrored live to the web UI
  (`web_interface.update_live_torque`, `web_interface.add_measurement_point`).
- After the sweep: `client.stop()` + `INTER_RPM_PAUSE`.

**Safety / abort branches inside the RPM sweep:**

| Condition | First RPM in profile | Later RPM |
|---|---|---|
| `measurements is None` | `first_rpm_exceeded_threshold = True` → break entire cell | break the Z-level sweep, mark remaining RPMs `None` |
| `max(|torque%|) ≥ TORQUE_BREAK_THRESHOLD` | same — break cell | same — break Z-level |

`first_rpm_exceeded_threshold` propagates back from `test_dynamic_analysis_at_z`, and the
outer Z loop then breaks out of the cell.

### 4.5 Low-torque "liquid-contact hunt" Z-skip

Toggled by `LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED` (regular runs only — explicitly disabled
in calibration / recalibration). State is a single-element list
`liquid_contact_established_box = [False]` shared across Z-levels of the cell.

At each Z-level while `box[0] is False`:

1. The first RPM is sampled with `hunting_first_contact_min_pct=liquid_threshold_pct` passed
   into `measure_torque_at_rpm`.
2. The **first sample at `elapsed_time ≥ SAMPLE_INTERVAL`** is used as the gate. If its torque
   is `< liquid_threshold_pct` (`LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT`, default 20 %), the
   sample loop stops immediately, all RPMs at this Z are recorded as `None`, the Z row is
   marked with `_liquid_skipped_z = True` + a torque label like `"<20%"`, and the descent
   continues to the next Z (no hit-point inputs added).
3. If the gate passes, `box[0] = True` is latched: the hunt is over for this cell and all
   subsequent Z-levels go through the full sweep without the early-stop arm. Smart early
   exit (Section 4.6) is suppressed until this gate resolves.

### 4.6 Smart Early Exit

Inside `measure_torque_at_rpm`, when `SMART_EARLY_EXIT_ENABLED` is True:

- A rolling window of the last `SMART_WINDOW_SIZE` torque samples is kept.
- Once it is full and the liquid-contact gate is not pending (`hunting_unresolved` is False),
  `cv = pstdev/mean` is computed each new sample. If `cv < SMART_CV_THRESHOLD` the
  measurement window is terminated early — the torque is considered stable enough.
- This only ends the **current RPM at the current Z**; it does not affect descent.

### 4.7 Per-Z feedback metrics & hit-point detection

After the RPM sweep returns, `RotationalDragFeedbackController` (in
[src/python_64/feedback_helper_function.py](src/python_64/feedback_helper_function.py)) is fed:

```python
feedback_controller.add_measurements_at_z(z_rounded, rpm_data)
```

For each RPM, `analyze_trend_for_rpm()` computes from the rotational-drag-vs-Z series
(rotational drag ≡ `|torque%| / rpm`):

- a local-window linear regression over the last `slope_window` points → `trend_slope`, `trend_r_squared`;
- a 3-point second derivative of drag (`_approximate_second_derivative`);
- a moving second derivative of slope and CV from per-RPM histories;
- moving R² of slope and CV.

Each metric feeds a confidence weight. A `BaselineZScoreDetector` is used for the 2nd-derivative
"anomaly" channels (drag / cv / slope): the first `BASELINE_N_CALIBRATION` samples calibrate the
mean/std, after which a `|value - mean|/std > BASELINE_Z_THRESHOLD` returns a hit.

```
hit_confidence = Σ weight_i  for each fired channel
hit_detected   = hit_confidence ≥ HIT_POINT_CONFIDENCE_THRESHOLD
```

All metrics for the Z-level are stored under `cell_z_rpm_data[z]['_metrics'][rpm]` so they end
up in the CSV row-by-row.

**Persistent hit trigger (terminates the cell):**

```python
hit_confidence_threshold        = 0.80
required_consecutive_hit_steps  = 3
```

A streak counter `consecutive_high_confidence_steps` increments whenever the maximum
`Hit_Point_Confidence` across RPMs at the current Z is `≥ 0.80`, and resets otherwise. When
the streak reaches 3, the Z-loop breaks; the cell is considered hit-point-resolved and the
status line on the web UI reports `Cell N terminated early - hit-point detected at Z=...`.

### 4.8 End-of-cell cleanup (in `finally`)

When the Z-loop exits for any reason (hit detected, floor reached, safety abort), the
`finally` block:

1. If `pump is not None` (i.e. **not** a calibration run), launches the **two concurrent
   pump threads** that overlap with CNC retract / travel (see Section 6):
   - `_pump_fill_station1(pump)` — start `P1`, wait `STATION1_FILL_DURATION` (22 s), stop `SP1`.
   - `_motor1_start(pump)` — issue `M1` so the scrub motor is already running when the
     spindle arrives.
   The fill thread is captured in `_fill_thread` and returned to the caller.
2. Then the CNC retracts to `Z=0` for that cell's `(x,y)`, viscometer is stopped, and the
   controller summary is logged.
3. If `PREDICTED_VISCOSITY_ENABLED`, the curve fit (Section 7) is computed and stashed into
   `cell_z_rpm_data['_predicted_viscosity']`.

---

## 5. Phase D — Calibration / Recalibration Data Capture & Save

Calibration and recalibration **reuse the entire Z-descent / feedback pipeline** above — no
separate "calibration sweep" code path. The only differences are:

- `pump=None` is passed to `test_cell_dynamic_z_series` → no wash, no concurrent threads.
- Starting Z is the row default (or `RECALIBRATION_CELLS[cell]` if a custom start was
  supplied per cell).
- `LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED` is force-disabled inside the function so calibration
  always sweeps the full Z window.

### 5.1 Extracting the rough hitpoint

`extract_rough_hitpoint(cell_z_rpm_data)` walks the Z-levels in **descent order** (highest
Z first), builds a list of `(z, any_hit_detected)` tuples (taking `any` across RPMs in
`_metrics`), and returns the **last** Z where `Hit_Detected == False` **immediately followed
by at least 3 consecutive `True`** levels. If no such pattern exists, `None` is returned and
the cell is skipped during the save step (logged to the console). This is the same 3-step
rule used by the live trigger in Section 4.7, but applied post-hoc to the full record.

### 5.2 Saving to the calibration store

`calibration_store.py` writes the JSON file at:

```
src/python_64/calibration_data/per_cell_z_calibration.json
```

with this schema:

```json
{
  "version": 1,
  "calibrated_at": "2026-05-14T15:30:21-04:00",
  "cell_calibrated_at": { "1": "...", "2": "...", ... },
  "cells": { "1": -66.12, "2": -66.08, ... }
}
```

After the per-cell loop completes, `main()` calls one of:

| Run | Function | Behaviour |
|---|---|---|
| Full calibration (`CALIBRATION_MODE`) | `save_calibration(calibration_cells, calibrated_at=...)` | Replaces the entire `cells` object atomically (`.tmp` → `os.replace`). |
| Individual recalibration (`RECALIBRATE_INDIVIDUAL_CELLS`) | `update_calibration_for_cells(calibration_cells, calibrated_at=...)` | Loads existing JSON, **merges** the new entries (untouched cells preserved), rewrites atomically. |

In both cases, per-cell timestamps are stamped into `cell_calibrated_at[cell_id]`. A
`web_interface.emit_calibration_complete(get_calibration_summary())` follows so any open
browser sees the new state immediately.

### 5.3 Use of calibration during regular runs

`get_safe_z_for_cell(cell_id, default_safe_z, offset=CALIBRATION_OFFSET)` returns
`stored_hitpoint + 0.4 mm` when an entry exists, otherwise the row default. This is what makes
regular runs start `0.4 mm` above the known cell bottom rather than at the row safe height.

---

## 6. Phase E — Concurrent Washing Mechanism

The wash sequence is intentionally pipelined with CNC motion so that pump/motor idle time is
minimized.

### 6.1 Fired at the end of the previous cell

`test_cell_dynamic_z_series`'s `finally` block (Section 4.8) launches two daemon threads as
soon as the cell is done measuring:

```python
_fill_thread = _run_in_thread(_pump_fill_station1, pump)   # P1 → wait FILL → SP1
_run_in_thread(_motor1_start, pump)                        # issues M1 once
```

`STATION1_FILL_DURATION = 22 s`. While those run, the CNC retracts the spindle to `Z=0` over
the just-measured cell.

### 6.2 `perform_washing_sequence`

Triggered immediately after `test_cell_dynamic_z_series` returns. Steps:

1. **Travel to Station 1** at `Z=0` (`move_to_point_safe`, `speed=3000`). While the
   spindle is in flight, the background `_fill_thread` is finishing the fill. After
   arrival, the code does `_fill_thread.join(...)` to make sure the bath is actually full
   before descending.
2. **Lower into Station 1** to `WASH_STATION1_Z = -67`. Motor M1 (started concurrently) is
   already agitating.
3. **5 oscillation strokes** between `(383, 68)` and `(390, 68)` at the wash-Z height, with
   small dwells.
4. **Raise to `Z=0` and fire concurrent drain:**
   ```python
   cnc.move_to_point(WASH_STATION1_X, WASH_STATION1_Y, 0, speed=500)
   drain_thread = _run_in_thread(_drain_station1, pump)   # R1 → wait DRAIN → SR1
   _reliable_pump_command(pump, b"SM1", "Stop Motor 1")
   ```
   `STATION1_DRAIN_DURATION = 25 s`. The drain runs **in parallel** with the next move.
5. **Travel to Station 2** (`speed=3000`).
6. **Start M2**, lower to `WASH_STATION2_Z`, 5 oscillation strokes, raise, stop M2.
7. `drain_thread.join(...)` to confirm Station 1 is empty before the next cell.

This gives roughly a full station's worth of fill or drain overlapped with each travel leg.

### 6.3 Reliable command transport

All pump traffic goes through `_reliable_pump_command(...)`, which:

- Takes a global `_PUMP_IO_LOCK` so concurrent threads cannot interleave bytes on the serial
  port.
- Prefers `pump.send_command_with_ack(...)` (ESP32 acknowledgement protocol) when the
  controller advertises it, falling back to raw `send_tag` + a brief settle.
- Optionally calls `pump.get_status()` afterwards for verification.

### 6.4 ESP32 commands used

```
P1 / SP1   Pump 1 (fill station 1) start/stop
R1 / SR1   Reverse-rinse pump 1 (drain station 1) start/stop
M1 / SM1   12 V DC agitation motor 1 start/stop
M2 / SM2   12 V DC agitation motor 2 start/stop
0          Emergency stop (issued during shutdown / on error)
ST         Status request (used during init handshake)
```

### 6.5 Error path

`perform_washing_sequence` is wrapped in `try/except`: on any exception it issues `b"0"`
(emergency stop), retracts to `Z=0`, and re-raises. The outer per-cell handler will save
partial data and let the run's `finally` cleanup the rest.

---

## 7. Phase F — Predicted-Viscosity Curve Fit (Hyperbola)

When `PREDICTED_VISCOSITY_ENABLED` is True, **right after a cell finishes measuring** (still
inside `test_cell_dynamic_z_series`, before returning), `calculate_predicted_viscosity(...)`
is called per RPM.

### 7.1 Data selection

For each RPM, the function gathers every recorded sample whose
- `z >= hitpoint_z` (above the hitpoint — i.e. pre-contact descent region), **and**
- `torque_percent > torque_floor` (default 25 %).

This isolates the air-gap regime where the hyperbolic drag model is valid.

If the Z-span of the surviving points is larger than 0.3 mm, the data is trimmed to the
window `[hitpoint_z, hitpoint_z + 0.3 mm]` so the fit focuses on the near-surface region.
Fewer than 3 surviving points → fit is skipped (returns `(None, None, ([], []))`).

### 7.2 Model

```
drag(z) = a / (z - b)
```

Fit with `scipy.optimize.curve_fit`, with:

- Initial guesses derived from the data extents (`a_guess` ≈ `(drag_first - drag_last) * z_range`,
  `b_guess` ≈ `z_min - 0.5 * z_range`).
- `b` bounded to `[z_min - 5*z_range, z_min - 1e-6]` (pole strictly below the data — keeps the
  hyperbola well-conditioned).
- `maxfev=5000`.

Viscosity is reported as:

```
viscosity_kcP = |a| * m_hyp        (m_hyp = 2.330 by default)
```

### 7.3 Storage and live emission

The per-RPM result is stored on the cell record:

```python
cell_z_rpm_data['_predicted_viscosity'] = {rpm: (viscosity_kcP, h0_mm), ...}
```

and emitted to the web UI via `web_interface.emit_predicted_viscosity(...)`.

Both CSV writers (`save_dynamic_analysis_data`, `save_partial_data`) inspect this map and
embed a **"Predicted Viscosity Summary"** mini-table (`Cell, RPM, Predicted_Viscosity_kcP,
h0_mm, Status`) into the file header when the feature is enabled. Failed fits are written
out as `Status = "no_fit"` rather than dropped.

---

## 8. Phase G — Run Finalization & Persistence

After the per-cell loop completes successfully:

1. **Calibration-like runs** persist hitpoints via `save_calibration` /
   `update_calibration_for_cells` (Section 5.2) and emit
   `emit_calibration_complete(get_calibration_summary())`.
2. **All runs** call `save_dynamic_analysis_data(all_data, timestamp, mode, run_experiment_name)`
   which writes a single CSV per run:

   ```
   dynamic_analysis_<experiment_slug>_<mode>_<YYYYMMDD_HHMMSS>.csv
   ```

   CSV header columns:

   ```
   row, cell, Cell_Label, Z_Height_mm, RPM, Elapsed_Time_s, Torque_%, Rotational_Drag,
   CV, R2, Trend_Slope, Second_derivative,
   Second_derivative_drag, Second_derivative_cv, Second_derivative_slope,
   R2_drag, R2_cv, R2_slope,
   Hit_2nd_Deriv_Drag, Hit_2nd_Deriv_CV, Hit_2nd_Deriv_Slope,
   Hit_R2_Drag, Hit_R2_CV, Hit_R2_Slope,
   Samples_Collected_At_Z,
   Hit_Point_Confidence, Hit_Detected, Hit_Reasons
   ```

   Rows whose Z was skipped by the liquid-contact hunt are emitted with `Torque_pct =
   "<20%"` (or whatever label `_liquid_skip_torque_label` produced) and `SKIPPED` in the
   metric columns.

3. **Interrupted / errored runs** call `save_partial_data(...)` which writes the same schema
   but with a `_PARTIAL_` suffix in the filename and a warning comment in the metadata
   header listing which cells did complete.

### Cleanup (`finally`)

Always executed at run-end:

- `client.stop(); client.close()` — viscometer subprocess shut down.
- `_safe_pump_send_tag(pump, b"0")` — emergency stop all pumps/motors.
- `active_threads` (fill / drain background threads) are joined with a 10 s timeout each so
  no straggler keeps the pump driver busy past run-end.
- `pump.close()` — release COM port.
- `cnc.home()` — return CNC to home, push `(0,0,0)` to the web UI.
- `web_interface.set_running_state(False)` and clear instrument-status lights.

Control then returns to the outer `while True:` loop, where the script waits for the next
**Start Run** event.

---

## 9. Stop / Interrupt Semantics

Two parallel stop signals:

- `web_interface.should_stop()` is polled by `sleep_with_stop()` and `raise_if_stop_requested()`
  at every cooperative point (between Z-steps, during dwells, inside the wash sequence).
  Triggering it raises `KeyboardInterrupt("Stop requested from web interface")` from the
  next checkpoint, which the outer `main()` handler treats exactly like a Ctrl+C: partial
  data is saved, hardware is cleaned up, and the run loop returns to "Ready".
- A real keyboard `KeyboardInterrupt` does the same.

---

## 10. Key Tunables (web-configurable, with code defaults)

| Variable | Default | Purpose |
|---|---|---|
| `Z_STEP_SIZE` | `-0.02 mm` | Z increment per descent step |
| `Z_FEED_RATE` | `500 mm/min` | Vertical move speed inside a cell |
| `SETTLE_TIME` | `1.0 s` | Mechanical settling after each Z move |
| `DWELL_SECONDS` | `2.0 s` | Settle after RPM change |
| `INTER_RPM_PAUSE` | `2.0 s` | Pause between RPMs |
| `MEASUREMENT_DURATION` | `40.0 s` | Sampling window per RPM at one Z |
| `SAMPLE_INTERVAL` | `5.0 s` | Grid spacing of recorded samples |
| `TORQUE_BREAK_THRESHOLD` | `100.0 %` | Safety abort threshold |
| `SMART_EARLY_EXIT_ENABLED` | `False` | Per-RPM CV-based early termination |
| `SMART_CV_THRESHOLD` | `0.005` | CV trigger for smart exit |
| `SMART_WINDOW_SIZE` | `3` | Rolling window for smart exit |
| `LOW_TORQUE_LIQUID_CONTACT_SKIP_ENABLED` | `False` | Z-skip until liquid contact |
| `LOW_TORQUE_LIQUID_CONTACT_THRESHOLD_PCT` | `20.0 %` | Liquid-contact gate threshold |
| `FEEDBACK_CONTROL_ENABLED` | `True` | Master switch for hit-point detection |
| `MIN_DATA_POINTS_FOR_TREND` | `8` | Min Z-points before trend analysis is valid |
| `R2_DRAG_MIN`, `R2_CV_MIN`, `R2_SLOPE_MIN` | `0.975` | R² thresholds (hit if R² drops below) |
| `WEIGHT_*` | `0.2` each | Confidence weight per detection channel |
| `HIT_POINT_CONFIDENCE_THRESHOLD` | `0.8` | Per-Z `Hit_Detected` cutoff |
| `BASELINE_N_CALIBRATION` | `10` | Samples used to calibrate Z-score detectors |
| `BASELINE_Z_THRESHOLD` | `10.0` | Z-score threshold for 2nd-derivative hits |
| `CALIBRATION_OFFSET` | `0.4 mm` | Start-Z offset above stored hitpoint |
| `STATION1_FILL_DURATION` | `22 s` | Concurrent fill duration before wash |
| `STATION1_DRAIN_DURATION` | `25 s` | Concurrent drain duration after wash |
| `PREDICTED_VISCOSITY_ENABLED` | `False` | Toggle hyperbola curve fit per cell |

---

## 11. Quick Cross-Reference

| Concern | Symbol / Function | File |
|---|---|---|
| Run-mode resolution | `get_selected_cells()` | `all_cells_with_rotational_drag_feedback.py` |
| Per-cell Z descent | `test_cell_dynamic_z_series()` | same |
| RPM sweep + safety | `test_dynamic_analysis_at_z()`, `measure_torque_at_rpm()` | same |
| Liquid-contact hunt | `LOW_TORQUE_LIQUID_CONTACT_*`, `box[0]` latch | same |
| Smart early exit | `SMART_*` block in `measure_torque_at_rpm` | same |
| Hit-point feedback | `RotationalDragFeedbackController` | `feedback_helper_function.py` |
| Persistent hit trigger (3-streak) | `consecutive_high_confidence_steps` | `all_cells_with_rotational_drag_feedback.py` |
| Rough hitpoint extraction | `extract_rough_hitpoint()` | same |
| Calibration persistence | `save_calibration`, `update_calibration_for_cells`, `get_safe_z_for_cell` | `calibration_store.py` |
| Concurrent fill / drain | `_pump_fill_station1`, `_motor1_start`, `_drain_station1`, `_PUMP_IO_LOCK` | `all_cells_with_rotational_drag_feedback.py` |
| Wash choreography | `perform_washing_sequence()` | same |
| Predicted viscosity | `calculate_predicted_viscosity()` | same |
| CSV writers | `save_dynamic_analysis_data`, `save_partial_data` | same |

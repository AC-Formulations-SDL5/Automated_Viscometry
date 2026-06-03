# Universal Geometry-Dominated Scaling of Rotational Drag in a Custom Cone–Plate System: A Framework for Extracting Newtonian and Non-Newtonian Viscosity

**Authors:** _to be assigned_  
**Affiliation:** AC Formulations – SDL5, Automated Viscometry Project  
**Date:** June 2026

---

## Abstract

We report a systematic study of the rotational drag signal `D = T/RPM` measured by a custom cone–plate viscometer as a function of cone-to-plate gap height `h`. Across 23 silicone fluids spanning the true-viscosity range 1.07 kcP → 124 kcP, the log–log slope of `D` vs `h` is found to be nearly **viscosity-independent** with an average value of `m ≈ −0.22`, in stark contrast to the value `m = −1` expected from a naive lubrication-type model `D ∝ 1/h`. After normalisation, every measured curve collapses onto a single master curve, indicating a separable form `D(h, μ) = A(μ)·F(h)` in which viscosity controls the *amplitude* and geometry controls the *shape*. A regularised hyperbolic model `F(h) = 1/(h + h_c) + b` consistently provides the best fit, with a universal characteristic length `h_c ≈ 0.25 mm`. We propose that `h_c` reflects the effective truncation/zero-offset of the cone-plate geometry rather than fluid physics. The empirical master curve enables an inverse procedure: given a single gap-height sweep, the fluid amplitude `A` is extracted by fitting the universal shape, and the dynamic viscosity is recovered via a calibration `μ = g(A)`. Using the certified (measured) viscosities of the silicone standards, a single-parameter power law `A = k·μ^p` with `p ≈ 2.01` and `R² = 0.999` is obtained, giving a median leave-one-out prediction error of **≈ 3 %**. We discuss how the same protocol generalises to non-Newtonian fluids when the gap-sweep is repeated at multiple rotational speeds, yielding the consistency index `K` and power-law index `n` via `T/RPM ∝ RPM^(n−1)`.

---

## 1. Introduction

Conventional cone-plate rheometry produces a torque that is, to leading order, *independent* of the cone–plate gap because the local shear rate `γ̇ = ω/α` is set by the cone angle `α` alone. However, real instruments deviate from this ideal because the cone is truncated, the mechanical zero is offset, and the sample geometry departs from a perfect cone-on-plate near contact. In an automated, low-cost cone–plate system in which the gap is swept by CNC motion, these deviations dominate the measured signal and offer, paradoxically, a route to extract rheological information.

The present project aims to develop a **physics-based, assumption-free** methodology for converting the raw drag signal `D(h)` into the dynamic viscosity `μ` (and, for power-law fluids, the flow index `n` and consistency `K`). The work proceeds in two stages: (i) empirical characterisation of the universal scaling exhibited by `D(h)` across many fluids, and (ii) construction of an inverse calibration that maps the fitted amplitude `A(μ)` back to viscosity.

## 2. Experimental Section

### 2.1 Geometry

| Parameter | Value |
|---|---|
| Cone radius `R` | 12 mm |
| Cone half-angle `α` | 3° (0.0524 rad) |
| Sample volume | ≈ 1 mL |
| Gap sweep | 0.50 mm → contact |
| Gap increment `Δh` | 0.02 mm |

### 2.2 Acquisition

For each fluid, the rotational speed (RPM) was held constant while the cone-plate gap was decreased in 0.02 mm steps by CNC motion. The measured torque (in % of full scale) was averaged at each height and recorded together with the commanded RPM. The drag signal was defined as

$$ D(h) \;=\; \frac{T(h)}{\mathrm{RPM}}. $$

Two regions of each sweep were excluded from analysis: (a) the **no-contact region** at large `h` where the spindle did not fully wet the sample, and (b) the **contact region** at `h → 0` where the spindle touched the plate and the signal diverged. The system was zeroed (`T = 0`) before each test, ruling out a constant electronic offset.

### 2.3 Dataset

The compiled dataset `height_normalized.csv` contains 23 silicone fluids ranging from 1 kcP to 100 kcP nominal viscosity, each measured at the RPM chosen to keep the torque within instrument range.

## 3. Original Hypothesis: `D ∝ 1/h`

Lubrication theory of an annular thin film suggests the drag scales inversely with the gap, predicting a log–log slope `m = −1`:

$$ D(h) = \frac{A}{h} + B. $$

A direct log–log fit of the measured data, however, produced

$$ m \;\approx\; -0.22 \pm 0.03 $$

for *every* silicone tested. This single observation undermines the lubrication ansatz.

## 4. Why an Instrument Offset Cannot Explain the Discrepancy

A natural rescue is to invoke a constant background torque `B`:

$$ D_{\mathrm{corr}}(h) = D(h) - B, \qquad \log D_{\mathrm{corr}} \;\stackrel{?}{=}\; \mathrm{const} - \log h. $$

Empirically, choosing `B ≈ 9.5` for 12.5 kcP silicone does recover `m ≈ −1`. But repeating this exercise across all fluids yields the table below:

| Viscosity | Required `B` |
|---|---|
| 5 kcP | 4.6 |
| 8 kcP | 5.8 |
| 12.5 kcP | 9.5 |
| 25 kcP | 13 |
| 45 kcP | 30 |
| 70 kcP | 64 |
| 90 kcP | 73 |
| 100 kcP | 96 |

`B` scales with viscosity, which is incompatible with a constant mechanical/electronic offset. The "offset" is therefore a numerical artefact compensating for the curvature of the data — not a physical background.

## 5. Universal Scaling and Curve Collapse

### 5.1 Slope universality

Across the silicone series, the log–log slope is essentially flat:

| Viscosity | Slope `m` |
|---|---|
| 5k | −0.223 |
| 8k | −0.225 |
| 12.5k | −0.220 |
| 25k | −0.262 |
| 45k | −0.249 |
| 70k | −0.211 |
| 90k | −0.205 |
| 100k | −0.197 |

Mean `m ≈ −0.22`.

### 5.2 Curve collapse

When each dataset is normalised as `y_norm = D / D_max`, all curves collapse onto a single shape. The minimum of the normalised signal lies at 0.50–0.60 over the gap range 0.02 → 0.32 mm. This is approximately an order of magnitude larger than the `0.06` minimum that a true `1/h` law would predict.

### 5.3 Implication

The data support a **separable** form

$$ \boxed{\; D(h, \mu) \;=\; A(\mu) \cdot F(h) \;} $$

with a universal geometry function `F(h)` shared by all silicone fluids and an amplitude `A(μ)` that carries the fluid-specific physics.

## 6. Regularised Hyperbolic Model

The empirical observations are well captured by

$$ D(h) \;=\; \frac{A}{h + h_c} + B, $$

with `h_c ≈ 0.25–0.35 mm` recovered across all fluids:

| Fluid | `h_c` (mm) |
|---|---|
| 5k | 0.246 |
| 8k | 0.269 |
| 12.5k | 0.262 |
| 25k | 0.263 |
| 45k | 0.292 |
| 90k | 0.335 |

This constancy strongly suggests that `h_c` reflects a **geometric** length scale — most plausibly the truncation of the cone tip and/or the calibration offset of the mechanical zero — rather than fluid physics. The fully generalised model `D = A/(h+h_c)^n + B` is found to be over-parameterised and is not preferred.

## 7. Inverse Calibration: Recovering Viscosity from `D(h)`

Given that the curve shape is universal, viscosity can be extracted in three steps:

1. **Fit** the measured `D(h)` to the universal regularised hyperbola `D = A/(h + h_c) + B` with `h_c` fixed at the master value (here `h_c = 0.250 mm`).
2. **Extract** the amplitude `A` and (if available) a small `B`.
3. **Map** `A → μ` using the calibration established from the silicone standards.

Using the certified (second-number) viscosities of the 23 silicone standards, fitting `A` against the true `μ` yields

$$ A \;=\; (5.09 \times 10^{-9})\; \mu^{2.007}, \qquad R^{2} = 0.999. $$

The inverse is therefore `μ̂ = (A / 5.09×10⁻⁹)^(1/2.007)`. A leave-one-out cross-validation across the calibration set gives a **median absolute error of ≈ 3 %**, with most fluids predicted to within 5 % of their true viscosity. The fact that the exponent is so close to 2 (and not 1) reflects that the dataset was acquired at an RPM tuned to keep torque on-scale for each fluid; `A = T/RPM` therefore inherits an additional `RPM ∝ 1/μ` dependence, which compounds the underlying linear-in-μ physics into an apparent `A ∝ μ²`.

## 8. Extension to Non-Newtonian Fluids

For a power-law fluid `τ = K γ̇^n`, the cone-plate torque is

$$ T \;=\; \frac{2\pi R^{3}}{3}\,K\,\left(\frac{\omega}{\alpha}\right)^{n}, $$

so that

$$ D \;=\; T/\mathrm{RPM} \;\propto\; \mathrm{RPM}^{\,n-1}. $$

The full non-Newtonian protocol therefore is:

1. Acquire a gap sweep `D(h)` at several distinct RPMs.
2. At each RPM, fit the universal `F(h)` to extract an amplitude `A(\mathrm{RPM})`.
3. Plot `log A` vs `log(\mathrm{RPM})`. The slope yields `n−1`; the intercept (combined with `α` and `R`) yields `K`.
4. Newtonian behaviour is identified when `n ≈ 1` within uncertainty.

For the present single-RPM dataset, only the Newtonian calibration (Section 7) can be performed. Multi-RPM sweeps are recommended for the next experimental campaign.

## 9. Open Questions and Recommended Verifications

1. Is `h` truly measured in mm? Independent verification with a dial indicator or gauge blocks is recommended.
2. What is the cone-tip truncation diameter? This may quantitatively account for `h_c`.
3. How is `h = 0` defined operationally? Document the contact-detection routine.
4. Can the universal `F(h)` be derived analytically from the truncated-cone geometry? This is now the most important theoretical question.

## 10. Conclusions

1. The pure `D ∝ 1/h` lubrication ansatz is **rejected**: experimental slopes are `≈ −0.22`, not `−1`.
2. All silicone fluids exhibit identical scaling, implying a separable `D(h, μ) = A(μ)·F(h)`.
3. A regularised hyperbola with universal `h_c ≈ 0.25 mm` provides an excellent description and is consistent with a geometric, not rheological, origin.
4. The amplitude `A(μ)` provides a robust inverse route to viscosity: a single-parameter power-law calibration `A ∝ μ^2.01` (R² = 0.999) recovers the true viscosity of every silicone standard with a median leave-one-out error of **≈ 3 %**, validating the methodology end-to-end.
5. The protocol generalises to power-law fluids via multi-RPM gap sweeps: `T/RPM ∝ RPM^(n−1)` provides the flow index `n` and consistency `K`.

---

## 10b. Validation on Non-Newtonian Fluids (PEG 300 kDa, PEG 600 kDa, Sepineo P-600, Solagum)

To test whether the silicone-derived universal model generalises beyond Newtonian fluids, the same pipeline was applied to single-gap-sweep data on aqueous solutions of two polyethylene-glycol grades (PEG-300K at 5 % / 10 %; PEG-600K at 5 % / 6.5 % / 10 %), three concentrations of the carbomer-class polymer Sepineo P-600 (1 %, 1.5 %, 2 %), and three concentrations of the natural-gum thickener Solagum (1 %, 2 %, 3 %). Each sample provided one sweep at a single, sample-specific RPM chosen to keep torque on-scale, so labelled (manufacturer / low-shear) viscosities `μ_true` are encoded in the column name (`<concentration>%<polymer>_<μ_true_in_kcP>`).

**Methodology.** Z–torque sweeps were re-zeroed per sweep (`h = Z − Z_min`) and filtered to the dominant RPM mode (the system auto-shifts speed near contact). Instrument sentinel rows (`SKIPPED`, `<25 %`) were coerced to NaN and dropped. The universal-`F(h)` amplitude fit was applied with the silicone-derived `h_c = 0.250 mm`, and the silicone power calibration `A = 5.09·10⁻⁹ · μ^2.01` was inverted to obtain `μ̂`.

**Geometric universality holds.** The fitted hyperbola described every non-Newtonian sweep with `R²_fit = 0.88–0.99`, confirming that the `1/(h + h_c)` shape is a property of the **cone-plate geometry**, not of the fluid.

**Calibration generality is limited and shear-rate dependent.** Sorted by shear rate `γ̇ ≈ 2·RPM`:

| Sample | `μ_true` (cP) | RPM | `γ̇` (s⁻¹) | `μ̂` (cP) | error (%) |
|---|---:|---:|---:|---:|---:|
| Solagum 3 % | 130 700 | 0.4 | 0.8 | 49 893 | −61.8 |
| PEG-600K 10 % | 64 250 | 0.8 | 1.6 | 64 482 / 66 393 | +0.4 / +3.3 |
| Sepineo 2 % | 50 110 | 1.0 | 2.0 | 31 256 | −37.6 |
| Solagum 2 % | 35 860 | 1.4 | 2.8 | 25 456 | −29.0 |
| Sepineo 1.5 % | 17 240 | 2.9 | 5.8 | 17 986 | +4.3 |
| PEG-300K 10 % | 7 158 | 7.0 | 14 | 20 295 / 20 759 | +184 / +190 |
| PEG-600K 6.5 % | 4 109 | 12 | 24 | 14 421 / 14 783 | +251 / +260 |
| PEG-600K 5 % | 3 254 | 15 | 30 | 12 679 / 12 754 | +290 / +292 |
| Sepineo 1 % | 2 148 | 23 | 46 | 6 962 | +224 |
| PEG-300K 5 % | 577 | 90 | 180 | 3 749 / 4 286 | +550 / +643 |
| Solagum 1 % | 522 | 95 | 190 | 4 047 | +675 |

Median absolute error by family: **PEG-300K +370 %, PEG-600K +255 %, Solagum 62 %, Sepineo 38 %** — Solagum and Sepineo (associative-gel thickeners) cluster around an order-of-magnitude better calibration than the dilute flexible-polymer PEGs.

**Two clear diagnostic signatures emerge:**

1. **Master-curve collapse** — All PEG / Sepineo / Solagum `D/D_max` curves are *systematically flatter* than the silicone master, evidencing that the truncation/squeeze-film torque rise at small gaps is partially screened in polymer solutions (yield-like behaviour in Sepineo and the high-concentration Solagum gels; reduced effective viscosity in the truncation cavity for PEG).
2. **Amplitude–viscosity displacement** — On the silicone `A(μ)` calibration plot, Sepineo 2 % and Solagum 2 % / 3 % sit *below* the line (shear-thinning at `γ̇ ≤ 3 s⁻¹`), whereas the dilute flexible-polymer solutions (PEG-300K, PEG-600K, and the high-shear-rate Solagum 1 % data point) sit *above*. The upward offset is the fingerprint of **first-normal-stress (Weissenberg) contributions** from extensible polymer coils at moderate-to-high shear rates: elastic stresses inflate the measured torque beyond what a viscous-only model attributes to viscosity.

**Mechanistic summary.**

- For samples in their **low-shear-rate plateau** (`γ̇ ≤ 6 s⁻¹` here: PEG-600K 10 %, Sepineo 1.5 %), the silicone calibration recovers the labelled viscosity to within ±5 %.
- For **shear-thinning** samples at low γ̇ — Sepineo 2 % (`γ̇ = 2 s⁻¹`), Solagum 2 % (`γ̇ = 2.8 s⁻¹`) and Solagum 3 % (`γ̇ = 0.8 s⁻¹`) — `μ̂` under-predicts the labelled low-shear viscosity by 29–62 %, as expected when the test shear rate already lies past the shear-thinning knee.
- For **viscoelastic dilute polymer solutions** at moderate-to-high `γ̇` (PEG 5–10 %, Solagum 1 % @ 190 s⁻¹), `μ̂` over-predicts (+180 to +675 %) because the calibration absorbs elastic / normal-stress contributions into an effective viscosity, while the labelled `μ_true` is a manufacturer low-shear reference.

**Protocol recommendation.** The single-point, single-RPM calibration is therefore reliable only for Newtonian (or near-Newtonian) fluids tested in their viscous plateau. For non-Newtonian samples we recommend a **multi-RPM ladder at one intermediate gap** (e.g. four to six RPM values spanning a decade in `γ̇` at `h ≈ 0.3 mm`) and a power-law fit `T = K_T · γ̇^n` using the `fit_power_law` helper in `rheology_analysis_v3.ipynb`. This yields the flow index `n` and a consistency `K` per sample without conflating viscous and elastic contributions, completing the generalisation to non-Newtonian rheometry.

The full numerical results are written to `outputs_rheology/nonnewtonian_predictions.csv` and the two diagnostic figures to `figures_rheology/10_nonnewtonian_curves.png` and `10_nonnewtonian_parity.png`.

---

## Appendix A — Analysis Pipeline

The accompanying notebook `rheology_analysis_v3.ipynb` implements:

- per-fluid hyperbolic, regularised hyperbolic, and generalised power-law fits;
- log–log slope and local-slope `d log D / d log h` diagnostics;
- residual normality tests (Shapiro–Wilk, QQ plots);
- universal master-curve collapse and global fit;
- viscosity calibration `A(μ)` and the inverse `μ̂(D(h))` predictor;
- a placeholder for multi-RPM power-law extraction.

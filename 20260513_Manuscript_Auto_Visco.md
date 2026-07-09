**Autonomous Rheology Discovery for High-Viscosity Formulation Screening via Physics-Constrained Signal Interpretation**

Mohammad M Rastegardoosta, Ian Ngungab, Koketso Gaborekwec, Frantz Le Devedeca

# Abstract

The rheological characterization of high-viscosity fluids is a recognized bottleneck in formulation science, where manual cone-and-plate or parallel-plate measurements impose geometric-precision requirements that are fundamentally incompatible with robotic execution. We present an automated viscometry platform that reframes viscosity acquisition as a signal-interpretation problem rather than a geometric-precision problem. A cone-shaped rotational torquemeter is coupled to a Cartesian motion stage, an automated dual-stage washing module, and an asynchronous, multi-runtime control architecture; the descent of the spindle generates torque–displacement signatures that are decoded through a physics-constrained inference pipeline calibrated only once on a Newtonian silicone reference set. The pipeline reduces every raw descent to a calibrated stress–shear-rate curve and, for fluids measured at multiple rotation rates, returns the fitted power-law constitutive equation τ = Kγ̇n directly. Across mechanistically distinct chemistries — silicone oils, polyethylene glycol, glycerol, polysaccharide gums, associative polymeric thickeners, and crosslinked microgels — the platform recovers the manufacturer-quoted apparent viscosity within a ±2× envelope across the full shear-rate ladder, classifies Newtonian / shear-thinning / yield-stress regimes from the recovered flow-behaviour index n, and processes 18 samples within a five-hour autonomous run. The two main outputs of the system — a calibrated stress–shear-rate flow curve and the fitted power-law constitutive equation — are obtained from a single pass through a universal analysis pipeline with no per-chemistry retuning, demonstrating that an information-rich automated workflow can substitute for the precision hardware of conventional rotational rheometry. Beyond its standalone characterization performance, the platform is positioned as the foundational measurement layer of forthcoming rheology-discovery campaigns, in which Bayesian optimization and batch-wise active learning will propose formulations and processing conditions, the proposed samples will be characterized autonomously through this platform, and the recovered flow curves and constitutive coefficients will be fed back into the machine-learning loop to drive closed-loop material discovery across multi-component composition spaces.

**Keyword:** automated rheology, cone-and-plate viscometry, torque–displacement, physics-constrained inference, power-law fluids, self-driving laboratory, Bayesian optimization, active learning, material discovery, high-throughput characterization.

# 1. Introduction

The systematic mapping of viscosity in the 1,000–125,000 cP regime underpins the development of lubricants, specialty coatings, pharmaceutical excipients, personal-care emulsions, and advanced adhesives, where the rheological response is the dominant property determining processability, stability, and end-use performance. In these regimes, formulation spaces are typically explored across binary, ternary, or higher-order composition spaces in which viscosity evolves logarithmically and highly non-linearly with composition, so that resolving even a single property landscape can demand hundreds of independent measurements. Manual rotational rheometry, however, is fundamentally limited by its dependence on operator-controlled gap setting, sample loading, cleaning, and sequence pacing: the cumulative human time required to characterize even a modest design of experiments routinely exceeds days of skilled labour, and the inter-operator variance introduced at every step degrades the comparability of measurements collected across different sessions. The combination of long cycle times, operator dependency, and the structural impracticality of multi-component sweeps therefore constitutes a recognized bottleneck that has limited the experimental cadence of formulation development for decades.

A natural response to this bottleneck has been to substitute experimentation with empirical mixing models. The logarithmic blending rule, the Grunberg–Nissan equation, the Ramírez-de-Santiago model, and the Redlich–Kister polynomial framework are widely used to interpolate or extrapolate the viscosity of multi-component mixtures from a small number of pure-component or binary references. These models are quantitatively accurate in the dilute, near-ideal regimes for which they were originally calibrated, but they break down systematically at the concentration extremes and viscosity ranges that are most relevant industrially: hydrogen-bonding networks, associative interactions, polymer-chain entanglement, and microgel structuring all produce non-ideal behaviour that the empirical kernels cannot represent. As a result, even well-parameterized models routinely incur absolute-viscosity errors in excess of 50 % for ternary systems above 10,000 cP, and the absence of a reliable computational surrogate places physical ground-truth measurement back at the centre of any rigorous formulation programme. The accelerating convergence of experimental and computational workflows therefore depends on reducing the cost of the measurement itself, not on eliminating it.

The closed-loop integration of robotic sample handling, automated characterization, and machine-learning-guided decision making — collectively termed self-driving laboratories — has emerged as a pragmatic solution to this measurement-cost problem. Self-driving laboratories have been demonstrated convincingly in photovoltaic absorber discovery, heterogeneous catalyst optimization, polymer property design, and reaction-condition screening, where they shorten development cycles by orders of magnitude relative to manual workflows. Rheology, by contrast, remains conspicuously underrepresented in the autonomous-experimentation literature, because automating a rotational viscometer demands a combination of capabilities that few platforms simultaneously possess: sub-millimetre and repeatable spindle positioning across a multi-cell deck, reliable handling and dispensing of fluids with viscosities spanning more than two orders of magnitude, contamination-free sequential measurement of chemically dissimilar formulations, and an analysis layer that can convert the raw output of an imperfect robotic system into rheological descriptors of comparable fidelity to those obtained on a precision benchtop instrument. The intersection of these requirements has, until now, restricted automated rheology to either narrow viscosity ranges, single-chemistry case studies, or workflows in which the human operator remains in the critical path.

Closing this gap requires shifting the burden of precision from the hardware to the analysis pipeline. If the descent of the spindle is sampled densely enough, the resulting torque–displacement signature is information-rich: the shape of the rotational drag versus the spindle-to-floor gap encodes the viscosity through a hyperbolic dependence whose amplitude is invertible to an apparent viscosity, while the residual dependence on rotation rate at a fixed gap encodes the flow-behaviour index of the constitutive law. A physics-constrained inference framework can extract both descriptors from a single automated descent without relying on the absolute geometric accuracy of the robotic stage, provided the framework is calibrated once on a Newtonian reference set and applied without modification to subsequent samples. Such a framework converts the two long-standing weaknesses of robotic rheometry — backlash-limited positioning and the absence of an operator-tuned gap — into auxiliary nuisance parameters that the data analysis simply absorbs.

In this work we develop, validate, and characterize an end-to-end automated viscometry platform whose explicit objective is to deliver, for any high-viscosity fluid loaded into one of its sample cells, two quantitative outputs: (i) a calibrated stress–shear-rate flow curve, and (ii) the fitted power-law constitutive equation τ = Kγ̇n that summarizes the rheological regime of the sample. The contributions of the work are organized along three complementary axes. From a mechanical-engineering perspective, we designed and integrated the Cartesian motion stage, the cone-shaped rotational torquemeter, and the magnetically-driven dual-stage washing station into a single workstation capable of executing fully autonomous measurement and cleaning cycles across a multi-cell sample deck under a unified asynchronous control plane. From a physics and data science perspective, we treat the descent of the spindle as a physically structured signal rather than a single-point measurement: a generalized lubrication-theory framework is used to constrain the functional form of the rotational drag, and a data-driven inference layer fitted on top of that physics absorbs the residual mechanical and geometric uncertainties of the robotic stage into nuisance parameters, so that the calibrated apparent viscosity and the flow-behaviour index are recovered directly from the raw torque–displacement signature without per-chemistry retuning. From an autonomous-experimentation perspective, we deployed the calibrated platform across mechanistically distinct chemistries (silicone oils, polyethylene glycol, glycerol, polysaccharide gums, associative thickeners, and crosslinked microgels) and verified that it reproduces the manufacturer-quoted reference rheology within a ±2× envelope across the full shear-rate ladder, while completing 18-sample runs in approximately five hours of robot time and fewer than 20 min of human time. Taken together, these three contributions establish the platform as the foundational measurement layer of forthcoming rheology-discovery campaigns, in which Bayesian optimization and batch-wise active learning will propose new formulations and processing conditions, the resulting samples will be characterized autonomously through the platform, and the recovered flow curves and constitutive coefficients will be fed back into the machine-learning loop to drive closed-loop material discovery across multi-component composition spaces.

![](data:image/png;base64...)

**Figure 1.** (A) Manual rheology-data acquisition procedure (Biorender.com). (B) Schematic of the automated viscometry platform showing the Cartesian motion stage, the cone-shaped rotational torquemeter, the multi-cell sample deck, and the integrated dual-stage washing station.

# 2. Methods

The systematic characterization of material flow behaviour requires a clear alignment between the deformation type, the flow regime, and the measurement modality. Although rheology spans extensional, oscillatory, and steady-shear modalities — each yielding a distinct rheological descriptor (**Table 1**) — this study focuses on steady-state shear rheology acquired through a rotational, torque-based measurement, because this modality is (i) directly automatable on a Cartesian motion stage, (ii) sufficient to recover both Newtonian apparent viscosities and the power-law exponents that classify the dominant non-Newtonian regimes encountered in industrial formulations, and (iii) compatible with the dimensional constraints of a multi-cell sample deck. A standard manual workflow on this modality involves three operator-controlled steps — sample loading into a flat-bottom cell, precise spindle alignment relative to the cell floor, and torque acquisition under a programmed angular velocity — each of which the platform described below replaces with closed-loop, physics-constrained automation.

**Table 1.** Rheology Principles and Methods

|  |  |  |
| --- | --- | --- |
| Category | Principle/Method | Key Metric |
| Deformation Type | Shear Rheology | Shear Stress, Shear Rate |
|  | Extensional Rheology | Extensional Viscosity |
| Flow Regime | Steady-state Flow | Apparent Viscosity |
|  | Oscillatory (Dynamic) | Storage (G') & Loss (G'') Moduli |
| Measurement Method | Rotational (Torque-Based) | Torque-Displacement |
|  | Capillary/Pipe Flow | Pressure Drop |
|  | Microfluidics | Shear-thinning profiles |
| Material Response | Newtonian | Linear Stress-Strain relationship |
|  | Non-Newtonian | Power-law index |
|  | Viscoelastic | Phase Angle |

## 2.1 Hardware Architecture and Automated Workflow

The complete bill of materials of the platform is summarized in **Table S1**, and the integrated layout is shown in **Figure 1**. Sample containers are stainless-steel, flat-bottom, high-clearance cylinders chosen for their resistance to deformation under the vertical loads applied during near-contact descent; they are arranged in a modular workstation built from T-slotted aluminium rails (McMaster) with custom container holders fabricated by Fused Deposition Modeling (FDM) in PETG filament. The rotational sensing element is a 3°-cone-angle, 12.0 mm-diameter stainless-steel spindle coupled to a precision rotational torquemeter (AMETEK Brookfield; full-scale torque Mfull = 7187 dyne·cm). After this introduction, the instrument is referred to throughout the manuscript simply as the rotational torquemeter, and its quoted manufacturer flow curves are referred to as the reference rheology. Three-axis programmable motion is provided by a Cartesian CNC stage (Genmitsu 4040-PRO, SainSmart) actuated by NEMA 17 stepper motors and T10 lead screws. Dedicated peristaltic pumps (Chi.Bio, University of Oxford) handle the cleaning fluids of the integrated washing station.

The principal challenge in automating cone-and-plate rheometry is the high-precision spindle-to-floor positioning required to define the measurement gap. A dedicated washing station is therefore integrated into the workstation to clean the spindle after every characterization cycle and prevent cross-contamination between sequential samples. The station uses a bespoke magnetic-repulsion drive in which a motor-driven driving spinner — embedded with magnets and housed in a PETG container — actuates a driven spinner located inside a separate, chemically-resistant SLA washing vessel (Rigid 10K Resin V1, Formlabs). The two spinners are separated by a 3.0 mm gap and rotate through magnetic repulsion between inversely arranged poles, so that the motor electronics never contact the cleaning fluids. The spindle is cleaned by relative motion against a smooth mat on the driven spinner while detergent, water, and isopropanol are sequenced through the peristaltic pumps. We compared four washing protocols of progressively increasing complexity — from a static spindle in contact with a rotating spinner, through synchronous co-rotation, to lateral zig-zag oscillation across the cleaning mat — and found that a multi-modal protocol combining spindle rotation, lateral oscillation, and a brush-fitted spinner produces the only configuration in which no high-viscosity residue is left at the cone perimeter. The augmented mechanical-scrubbing protocol is therefore adopted as the platform default and is executed in parallel with the CNC travel motions to keep the washing time off the critical path of the experimental cycle.

The full process workflow is summarized in **Figure 2**. After system initialization and per-cell calibration of the safe spindle-to-container reference height, the platform executes an automated per-cell characterization cycle in which the spindle descends incrementally toward the container floor while continuously recording torque under a programmed RPM sweep. The descent is regulated by a physics-constrained feedback layer that combines rotational-drag tracking, statistical trend analysis, confidence-weighted hit-point detection, and second-derivative anomaly detection to identify the liquid-contact transition and the optimal termination point of the descent, while protecting the sensor from torque overload. At the end of each measurement, the system initiates a two-stage washing sequence concurrently with the CNC travel to the next cell, and the collected torque–displacement data are passed to the analysis pipeline. The full sequence — robotic positioning, torque-based rheometry, physics-informed feedback, autonomous washing, and real-time data orchestration — is closed-loop and operator-free for the duration of the run.

![](data:image/png;base64...)

**Figure 2.** Full workflow of the automated viscometry platform. CNC-controlled positioning, torque-based rotational rheometry, physics-informed descent feedback, autonomous hit-point detection, predictive viscosity estimation, and concurrent washing operations form a unified high-throughput experimental loop.

## 2.2 Physics-Informed Rheological Framework

The platform operates as a modified cone-and-plate configuration in which the cone spindle approaches the stationary plate while the generated torque is monitored as a function of the vertical displacement. Because automated descent inevitably traverses a much wider gap range than is admissible in a manual cone-and-plate experiment, the torque trace samples three hydrodynamically distinct regimes — parallel-plate-dominated, transition, and cone-and-plate-dominated — and a single closed-form analytical solution is therefore not adequate. We instead adopt a generalized lubrication-theory framework that interpolates continuously between the two asymptotic limits (**Fig. 3A**).

The local liquid thickness between the rotating cone and the stationary plate is

|  |  |
| --- | --- |
|  | Eq. 1 |

where h is the minimum tip clearance, r is the radial coordinate, and α is the cone half-angle. For large spindle separations (h ≫ r tan(α)), the gap thickness becomes nearly uniform throughout the radius (H(r) = h). In this regime, the system approaches classical parallel-plate rotational rheometry, where the torque scales approximately as:

|  |  |
| --- | --- |
|  | Eq. 2 |

Here, the viscous resistance is strongly governed by the global spindle-to-substrate distance. Conversely, for very small clearances (h→0), the radial contribution dominates the gap profile (H(r) ≈ r tan(α)) and the system converges toward the classical cone-and-plate rheometer limit with nearly uniform shear rate across the radius. The analytical torque expression becomes:

|  |  |
| --- | --- |
|  | Eq. 3 |

Between these two asymptotic limits lies a transition regime where both the finite tip clearance and cone geometry simultaneously influence the shear field. In this intermediate region, neither the parallel-plate approximation nor the ideal cone-and-plate solution alone can accurately describe the flow behavior. Therefore, a generalized lubrication-theory framework was employed to continuously capture the evolution of shear stress and torque throughout the entire displacement range.

Under incompressible, laminar, axisymmetric, and low-Reynolds-number conditions, the dominant fluid motion was assumed to be azimuthal while radial and axial inertia effects were neglected. The governing momentum equation reduces to:

|  |  |
| --- | --- |
|  | Eq. 4 |

Using no-slip boundary conditions at the rotating cone and stationary plate, the azimuthal velocity distribution becomes:

|  |  |
| --- | --- |
|  | Eq. 5 |

which yields the local shear stress:

|  |  |
| --- | --- |
|  | Eq. 6 |

The total torque was then obtained through radial integration of the local viscous moment contributions:

|  |  |
| --- | --- |
|  | Eq. 7 |

**Equation 7** provides a unified, physics-informed descriptor that is continuous across the parallel-plate, transition, and cone-and-plate regimes traversed by the automated descent.

The transition from manual to autonomous rheometry imposes its own precision constraint, because the gap height directly enters the shear-rate calculation. Although the Cartesian stage is built around NEMA 17 stepper motors and T10 lead screws with a manufacturer-quoted running accuracy of ±0.01 mm, cumulative mechanical uncertainties — backlash, thermal expansion of the metallic guides during continuous operation, and the structural compliance of the 3D-printed PETG fixtures — can push the effective positional variance to nearly 0.1 mm in the worst case (**Fig.3B**). Rather than chase this uncertainty at the hardware level, we exploit the physical structure of equations (1)–(7): the shape of the torque-versus-gap signature is a strong function of the fluid viscosity, so a real-time, feedback-driven analysis of the descent can detect both the liquid-contact transition and the safe termination point of the motion without relying on the absolute value of h. The physics-informed feedback layer therefore (i) absorbs the residual positional uncertainty as a fitted parameter rather than treating it as a calibration error, (ii) protects the torque sensor from collision-induced overload, and (iii) shortens the descent duration by terminating each cell as soon as the rotational-drag profile has been sampled densely enough for the inference pipeline.

![](data:image/png;base64...)

**Figure 3.** (A) Geometry of the governing lubrication-theory in physics-informed feedback layer. (B) Uncertainty caused by mechanical components’ accuracy as effective positional variance. (C) Scaling diagnosis of D(h) on the focus silicone. (D) Local slope drift away from −1 at intermediate gaps motivates regularization of the hyperbolic form. (E) Offset-scan diagnostic with a plateau near slope of −1.0 supports a hyperbolic core with a non-trivial baseline term. (F) Physical-space model comparison on the focus silicone dataset. (G-J) Residual and distribution diagnostics for the selected regularized-hyperbolic model. And (K) Master-curve construction with bootstrap envelope and best global regularized fit.

## 2.3 Data-Analysis Pipeline: from Raw Data to Rheological Behaviour

The analysis layer converts each automated-descent record (h, T(%), Ω) into calibrated rheological observables through a single, transferable workflow. The full inference chain is shown in **Figure 4** and is executed identically for Newtonian and non-Newtonian materials, with no per-chemistry redesign.

### 2.3.1 Signal transformation and scaling diagnosis

The first transformation is rotational drag normalisation,

|  |  |
| --- | --- |
|  | Eq. 8 |

which removes the trivial linear dependence of torque on angular speed for Newtonian response and isolates geometry-fluid coupling. A global and local log-log slope diagnosis on the silicone set showed that no single power law D ∝ h−n explains the full descent range (**Fig. 3C**): the local slope drifts toward −1 only near contact, indicating that a pure 1/h model is asymptotically correct but globally incomplete (**Fig. 3D**).

To identify the correct baseline structure, an offset-scan was performed by subtracting candidate constants B from D and refitting log-log slope on the positive residual (**Fig. 3E**). The resulting plateau near slope −1 confirms the leading-order form D = A/h + B.

### 2.3.2 Model selection in physical space

Four candidate models were compared in physical space (pure hyperbola, regularized hyperbola, generalized power, and saturation) using bounded Levenberg-Marquardt fitting and ranked by R2, adjusted R2, AIC, BIC, and cross-validated RMSE (**Fig. 3F**). The regularized hyperbola was the consistent winner:

|  |  |
| --- | --- |
|  | Eq. 9 |

Here, A carries viscosity information, hc absorbs effective zero-gap effects (slip layer, asperity, compliance, and residual geometric offsets), and B is a small parasitic baseline.

Residual diagnostics confirm that the selected model is unbiased and near-homoscedastic across gap height, supporting stable downstream inverse calibration (**Fig. 3G-J**).

### 2.3.3 Universality of geometry shape and fixed-hc production fitting

The factorization hypothesis D(h, μ) = A(μ) F(h) was tested by normalizing each sweep by its own maximum and overlaying all silicone traces on a common gap axis. The collapse to a single master shape validates a geometry-governed F(h) and fluid-dependent amplitude A (**Figure S1**).

**Figure 3K** shows a global fit to the normalized master curve highlights the regularized form as the most parsimonious representation, which justifies extracting a universal geometric regularization length h⋆c for production fitting.

Operationally, each sweep is first fitted with free hc, and the median of high-quality fits (R2 > 0.7, hc ∈ [0.05, 1.5] mm) defines h⋆c. All sweeps are then refitted with fixed hc = h⋆c, reducing parameter coupling and improving amplitude identifiability.

### 2.3.4 Calibration equations and constitutive extension

Silicone standards provide the one-shot amplitude-viscosity calibration,

|  |  |
| --- | --- |
|  | Eq. 10 |

For non-Newtonian materials measured at multiple RPM values, the amplitude becomes shear-rate dependent,

|  |  |
| --- | --- |
|  | Eq. 11 |

so the slope of “ln A” versus “ln γ̇” returns the flow-behaviour index “n”. Shear stress is computed directly from percent torque by the cone-plate conversion

|  |  |
| --- | --- |
| , | Eq. 12 |

Uncertainty and robustness procedures are also defined here through leave-the-k-smallest-out sensitivity on near-contact points, 500-iteration bootstrap confidence bands for (A, hc, B), and distributional analysis of per-sweep hc for universality checking.

![](data:image/png;base64...)

**Figure 4.** Inference-time view of the physics-constrained analysis pipeline. Green annotations mark the universal constants (h⋆c, k, p, cτ) calibrated once and reused across chemistry families.

## 2.4 Software Orchestration

The hardware-embedding strategy integrates rotational sensing, robotic positioning, and automated washing within a unified control plane. The rotational torquemeter is paired with the three-axis CNC stage to enable programmable sample traversal and repeatable spindle alignment across predefined sample and washing coordinates. All machine-level coordinates — sample positions, washing-station locations, safe-height offsets, and per-cell calibration data — are parameterized through YAML configuration files, so that the deck layout can be reconfigured without modifying the control software. An ESP32 microcontroller serves as the embedded actuator-control layer for the washing subsystem; its custom PCB carries L298N motor drivers under PWM control to actuate six DC pumps and three agitation motors, and a multiplexed channel-sharing configuration with diode-isolated switching provides independent fluid delivery while reducing hardware complexity. The microcontroller executes predefined detergent / water / isopropanol rinse cycles between measurements and exposes only a small command interface to the host (**Supplementary Information**).

At the host level, the platform employs a dual-Python asynchronous architecture that accommodates the hardware compatibility constraints of the rotational torquemeter while keeping experimental orchestration centralized. A 64-bit Python runtime manages high-level workflow execution, CNC motion control via G-code generation, washing-station sequencing, and data logging. Because the proprietary communication library of the rotational torquemeter requires a 32-bit DLL, viscometer communication is isolated within a dedicated 32-bit Python runtime, and the two processes communicate through synchronized file-based exchange and process-level coordination. The software stack is organized into modular hardware-abstraction layers (CNC control, viscometer communication, embedded washing control, and analysis trigger layer), and the ESP32 receives high-level serial commands from the host while executing the corresponding pump and motor sequences independently of the primary orchestration loop. The asynchronous design enables non-blocking concurrent execution of robotic motion, rheological acquisition, and washing operations — the throughput-determining property of the platform — and integrates traceability (calibration status, software version, operator annotations, environmental conditions) and recovery mechanisms (instrument reconnection, safe-motion interruption) to support long-duration autonomous operation. A real-time web dashboard exposes the live torque-displacement traces of every cell, current batch progress, and per-cell acquisition status to the operator, together with manual override, batch-abort, washing-protocol-selection, and calibration triggers, and at the end of every batch generates an automated experimental report containing per-cell summaries and recovered constitutive outputs.

# 3. Results and Discussion

The Methods section defines all equations, fitting rules, and uncertainty calculations. Results are therefore presented here as experimental evidence and scientific interpretation of platform performance in two stages: (i) acquisition reproducibility and statistical robustness of the automated measurement layer, then (ii) material-level rheological performance across Newtonian and non-Newtonian classes.

## 3.1 Acquisition Performance and Reproducibility

We first evaluated the automated measurement layer using silicone oils spanning 1–125 kcP, selected as a Newtonian reference family for calibration and reproducibility assessment. The objective of this stage was not only to determine whether viscosity could be recovered accurately, but also to establish whether the raw drag signatures generated during spindle descent contain a transferable physical structure that can be exploited for automated inference.

**Figure 5A** shows representative rotational drag traces acquired during spindle descent. For all fluids, drag increases monotonically with decreasing gap, consistent with the reduction in hydrodynamic resistance predicted by lubrication-type flow behaviour. Importantly, the traces remain systematically ordered according to viscosity across the entire operating range: higher-viscosity oils generate larger drag responses at every gap position, while preserving a similar overall profile shape. This observation suggests that viscosity primarily affects the magnitude of the drag response rather than its geometric dependence on gap. The raw torque–gap measurements used for calibration are shown in **Figure 5B**. These data constitute the direct experimental input to the inference pipeline and contain the complete information required for subsequent viscosity reconstruction. To determine whether the observed similarity between drag traces could be formalized, each curve was fitted using the regularized drag model D(h)=A / (h + hc) + B, and transformed into its normalized form ((D-B)/A). As shown in **Figure 5C**, all calibration samples collapse onto a single master curve. The collapse demonstrates that the gap dependence is effectively universal across the entire silicone-oil library, while viscosity information is isolated into the fitted amplitude parameter (A). Physically, this indicates that the measurement can be factorized into a geometry-controlled component and a viscosity-dependent scaling factor. This factorization is the key assumption enabling a single calibration to be transferred across multiple fluids without chemistry-specific retuning. Having established a universal drag representation, we next assessed calibration accuracy. **Figure 5D** compares predicted and reference viscosities for all calibration samples. Predicted values closely follow the one-to-one parity line across more than two orders of magnitude in viscosity, indicating that the inferred amplitude parameter provides a reliable surrogate for viscosity throughout the operating range. The corresponding error distribution is shown in **Figure 5E**. No systematic trend with viscosity is observed, suggesting that prediction performance remains approximately uniform from low- to high-viscosity oils and that the calibration does not preferentially overestimate or underestimate any particular viscosity regime. The aggregate error statistics are summarized in **Figure 5F**. Prediction errors remain narrowly distributed around zero, with the mean error close to the unbiased condition. **Figure 5G** further compares true and predicted viscosities on a sample-by-sample basis, confirming that agreement is maintained across the entire calibration set rather than being dominated by a small subset of measurements. Together, these results demonstrate that a single universal calibration successfully captures the viscosity dependence of all reference fluids investigated.

We then examined whether the inferred geometric parameter (hc) represents a physically meaningful characteristic of the measurement geometry or merely an artefact of the fitting procedure. **Figure 5H** shows a leave-the-(k)-smallest-out sensitivity analysis in which progressively more near-contact points are removed before refitting. The recovered (hc) remains effectively constant within uncertainty, indicating that parameter estimation is not driven by a small number of potentially ill-conditioned measurements acquired near wall contact. Similarly, the fitted amplitude (A) changes only marginally under successive point removal, demonstrating that viscosity estimation is robust to local perturbations in the shortest-gap region. To quantify statistical uncertainty, bootstrap resampling was performed on the drag profiles. **Figure 5I** presents the median bootstrap prediction together with the 95% confidence envelope for a representative sample. The narrow uncertainty band indicates that repeated resampling produces nearly identical drag reconstructions, implying strong parameter identifiability. The corresponding bootstrap distribution of (hc) is shown in **Figure 5J**. The distribution is narrow and unimodal, with variance substantially smaller than the viscosity span of the calibration set. This result supports the interpretation of (hc) as a geometry-linked descriptor that can be fixed globally during calibration, reducing the inverse problem from three free parameters to two and eliminating parameter entanglement between (A) and (hc). Collectively, the sensitivity and bootstrap analyses demonstrate that uncertainty originating from the fitting layer is substantially smaller than the material-to-material variation that the system is designed to resolve. Mechanical imperfections such as backlash, compliance, wetting variability and minor positioning errors are therefore effectively absorbed into the regularized drag representation without compromising viscosity recovery.

**Figure 5K** highlights the accuracy of platform by comparing the automatically collected data with manually collected data. Results show consistent accuracy in automatically data aqcuisiton by platform. Finally, **Figure 5L** places the automated workflow in the context of experimental throughput. The complete acquisition, washing, analysis and sample-handling sequence processed 18 samples in approximately five hours without operator intervention. Compared with an equivalent fully manual workflow, the majority of experimental time is shifted from human interaction to autonomous execution. This throughput advantage is particularly significant because it is achieved while simultaneously generating calibrated stress–shear-rate data suitable for downstream constitutive modelling, establishing the automated measurement layer as a practical foundation for future closed-loop rheology discovery campaigns.

![](data:image/png;base64...)

**Figure 5.** Calibration, validation and robustness of the automated viscometry platform. (A) Rotational drag profiles acquired during spindle descent for silicone oils spanning the calibration range. (B) Raw torque–gap data used for model fitting. (C) Collapse of normalized drag profiles onto a universal master curve, indicating geometry-controlled gap dependence and viscosity-dependent amplitude scaling. (D) Predicted versus reference viscosities. (E) Relative prediction error as a function of viscosity. (F) Distribution of prediction errors across all calibration measurements. (G) Sample-by-sample comparison of reference and predicted viscosities. (H) Sensitivity of the fitted geometric length scale (hc) to removal of near-contact data points. (I) Bootstrap reconstruction of a representative drag profile showing the median fit and 95% confidence interval. (J) Bootstrap distribution of (hc), supporting its interpretation as a geometry-linked parameter. (K) Comparative Evaluation of Human and Robotic Data Acquisition. (L) Time breakdown of the autonomous workflow compared with an equivalent manual procedure, demonstrating high-throughput operation of the platform.

## 3.2 Material Performance: Newtonian and Non-Newtonian Materials

Following the acquisition-level reproducibility, we evaluate whether the autonomous platform can recover physically meaningful rheology across distinct chemistries using one fixed inference workflow. This section closes the methodological loop established including the automated hardware sequence, physics-constrained signal interpretation, universal fitting and calibration transfer, and software orchestration for unattended execution. The central question is not only whether the system is repeatable, but whether it preserves constitutive meaning when moving from Newtonian standards to complex, structure-forming materials. The composite evidence is summarized in **Figure 6**.

### 3.2.1 Lubricant (Newtonian Anchor)

Silicone oils provide the Newtonian anchor set for the platform and validate the core decoding hypothesis: the drag-amplitude signal can be mapped to stable apparent viscosity without geometry-specific retuning. **Figure 6(A-1)** shows that drag profiles are consistent with the expected single-regime response, and the reconstructed stress-shear-rate behavior remains close to linear in τ-γ̇ space (equivalently, near-constant μapp over the measured window) (**Figure 6(A-2)**). This behavior is expected for chemically simple, weakly structured fluids where viscous dissipation dominates and no shear-induced microstructural evolution occurs. The Newtonian response therefore serves as a physics-based baseline that anchors subsequent non-Newtonian interpretation.

### 3.2.2 Rheology Modifier Materials

When the same pipeline is applied to PEG, Sepineo, Solagum, and Carbopol under multi-RPM sweeps, the recovered trends transition from Newtonian-like to strongly non-Newtonian behavior in a chemically interpretable sequence. PEG exhibits mild-to-moderate shear thinning, consistent with chain alignment and reduced hydrodynamic resistance at increasing shear rates (**Figure 6(B)**). Sepineo and Solagum show stronger shear thinning, reflecting progressive breakdown/reorganization of polymer-entangled or associative networks under shear (**Figure 6(C-D)**). Carbopol approaches yield-pseudoplastic behavior, where an apparent low-shear resistance is followed by flow after structural yielding, then shear-thinning transport at higher rates (**Figure 6(E)**). Importantly, these distinct constitutive signatures emerge from a single calibrated model stack, demonstrating that chemistry-specific behavior is resolved by the data rather than imposed by per-material parameter tuning.

### 3.2.3 Thermal Interface Materials

Thermal interface material (TIM) formulations including SYY, Sekisui B-41, and HY-500 extend the test space to highly filled, application-driven materials with complex internal architecture. Despite this added complexity, the platform returns stable drag-to-stress reconstructions and class-resolved flow responses within the same autonomous workflow used for lubricants and rheology modifiers (**Figure 6(F-H)**). However, the extracted trend-level rheological signatures shows that the data density and smoothness are reduced relative to lubricants and rheology modifiers. **Figure 6(F-1)** shows the raw drag profile of SYY which is visibly non-smooth. This propagates into uncertainty in the reconstructed constitutive behavior in **Figure 6(F-2)**, reflected by weak fit robustness in the recovered shear-thinning response. In **Figure 6(G)**, the response of Sekisui-B41 is also shear-thinning, but only three valid points are available for the stress-shear-rate reconstruction. Practically, this indicates that only three spindle-height conditions remained within the measurable torque window; at lower heights, the generated torque exceeded the instrument capability and those conditions could not be retained. In **Figure 6(H)**, the model reports apparent shear-thickening behaviour of HY-500, but this inference is based on only two points. With such sparse sampling, the trend is not statistically reliable and should be treated as preliminary rather than definitive constitutive evidence. These observations are consistent with the current hardware limits of the platform: (i) maximum measurable spring torque of 7187.0 dyne·cm and (ii) minimum spindle speed of 0.1 rpm. For highly solid-like, high-viscosity TIM systems, these constraints compress the usable operating window, yielding non-smooth drag traces and too few valid points for robust non-Newtonian classification. Therefore, TIM results here should be interpreted as feasibility-level outputs under range-limited measurement conditions, motivating future upgrades in torque dynamic range and low-speed control for reliable dense sampling

![](data:image/png;base64...)

**Figure 6.** Rheology overview of representative Newtonian lubricants and non-Newtonian rheology modifiers/thermal interface materials, showing paired experimental responses for each formulation: drag-response profiles (panels ending in 1, e.g. A-1, B-1, etc.) and corresponding stress-based rheology curves (panels ending in 1, e.g. A-2, B-2, etc.). Specifically, (A) silicone, (B) PEG, (C) Sepineo, (D) Solagum, (E) Carbopol, (F) SYY, (G) Sekisui B-41, and (H) HY-500.

**Figure 7** consolidates the central scientific result of the workflow by placing all materials on a single apparent viscosity and shear rate map, where rheological class is encoded directly by slope and curvature rather than by isolated viscosity values. The silicone datasets occupy near- horizontal apparent viscosity, consistent with Newtonian behavior and confirming that the calibration backbone remains physically coherent across the tested shear-rate window. In contrast, PEG, Solagum, Sepineo, and Carbopol systematically deviate to varied effective slopes, demonstrating shear-thinning responses of increasing strength and showing that the same inference chain captures both mild and strong non-Newtonian regimes without chemistry-specific retuning. The silicone reference is shown as a near-horizontal Newtonian response, while PEG, Sepineo, Solagum, and Carbopol are shown with fitted power-law trends to highlight their non-Newtonian shear-thinning behavior (n<1). This unified plot summarizes the rheological fingerprint of each class under a common calibration and analysis pipeline. This rheogram indicates that the geometry-normalized drag formalism and fixed-parameter calibration transfer preserve constitutive meaning across mechanistically distinct formulations. This unified map is also operationally useful, because it allows rapid material ranking by process-relevant shear response (pumpability, spreadability, coating behavior) within one consistent coordinate system.

![](data:image/png;base64...)

**Figure 7.** Master flow-curve comparison of representative formulations across material families, plotted as apparent viscosity versus shear rate.

# 4. Conclusion

We have presented an end-to-end automated viscometry platform that delivers, for any high-viscosity fluid loaded into one of its sample cells, two quantitative outputs — a calibrated stress–shear-rate flow curve and the fitted power-law constitutive equation — through a single physics-constrained inference pipeline applied directly to the raw torque–displacement output of an automated descent. The platform integrates a Cartesian motion stage, a cone-shaped rotational torquemeter, a magnetically-driven dual-stage washing station, and an asynchronous multi-runtime control architecture; the inference pipeline interpolates continuously between the parallel-plate and cone-and-plate limits using a regularised-hyperbolic drag fit anchored by a universal geometric offset h⋆c a one-shot silicone power-law calibration A = kμp, and a single cone-plate stress conversion cτ. The calibrated pipeline reproduces the manufacturer-quoted reference rheology of mechanistically distinct chemistries — silicone oils, polyethylene glycol, polysaccharide gums, associative thickeners, and crosslinked microgels — within a ±2× envelope across the full shear-rate ladder, classifies Newtonian, shear-thinning, and yield-stress regimes from the recovered flow-behaviour index “n”, and processes 18 samples within a five-hour autonomous run with fewer than 20 min of human time. The platform therefore demonstrates that the long-standing weaknesses of robotic rheometry — backlash-limited positioning and the absence of an operator-tuned gap — can be absorbed as nuisance parameters by a sufficiently information-rich physics-constrained analysis layer, and that an automated workflow can substitute for the precision hardware of conventional manual rotational rheometry without sacrificing the fidelity of either of its two primary descriptors.

The immediate application of the platform is as the foundational measurement layer of forthcoming rheology-discovery campaigns, in which Bayesian optimization and batch-wise active learning will propose new formulations and processing conditions, the resulting samples will be characterized autonomously through the platform, and the recovered flow curves and constitutive coefficients will be fed back into the machine-learning loop to drive closed-loop material discovery across multi-component composition spaces. Building on this foundation, future extensions of the framework will (i) generalize the constitutive layer beyond steady power-law fluids to Herschel–Bulkley yield-stress and Maxwell viscoelastic models, (ii) develop the inverse rheological problem of inferring molecular-level interaction parameters from torque–displacement signatures, (iii) couple the platform to inline spectroscopic characterization (NIR, Raman) for simultaneous compositional and rheological monitoring, and (iv) scale the architecture to larger multi-spindle decks for use as the rheological characterization layer of a self-driving formulation laboratory.

# 5. Supplementary Information

**Table S1.** Bill of Materials for the Automated Rheology Platform

|  |  |  |  |
| --- | --- | --- | --- |
| Component | Specification/Model | Manufacturer/Source | Material/Notes |
| Robotic Motion | 4040-PRO Desktop CNC | Genmitsu (SainSmart) | Cartesian coordinate system |
| Torque Senser | Torquemeter (Max: 7,187.0 dyne-cm) | AMETEK Brookfield | Real-time torque-displacement |
| Rotational Spindle | Cone-shaped (3° angle, 12.0 mm diameter) | AMETEK Brookfield | Stainless steel construction |
| Sample Containers | Flat-bottom, high-clearance cylinders | Custom/Commercial | Stainless steel; resistant to deformation |
| Workstation Layout | T-Slotted Aluminum Rails | Mc-Master | Modular design for scalable layout |
| Container Holders | Custom fitting for T-slotted rails | Fabricated (FDM) | PETG filament (Bambu 3D Printer) |
| Washing Module Housing | Motor container and driving spinner | Fabricated (FDM) | PETG filament (Bambu 3D Printer) |
| Washing Container | High-chemical resistance vessel | Fabricated (SLA) | Rigid 10K Resin (Formlabs) |
| Washing Drive System | DC Motor (12 mm, 1,000:1 gear ratio) | Various | Driving/Driven spinners with magnetic repulsion |
| Fluid Management | Peristaltic Pumps | Chi.Bio (Univ. of Oxford) | Regulates media input and waste removal |
| Cleaning Interfaces | Smooth contact mat and weatherstrip brush | Various | Contact mat mounted on driven spinner and brush lining container holder for spindle cleaning |

![](data:image/png;base64...)

**Figure S1.** Dimensionless collapse of silicone drag curves, supporting factorization into geometry shape and viscosity amplitude.

* CNC calibration map methodology and positional-variance dataset.
* Lubrication-theory validation against the analytical parallel-plate and cone-and-plate limits.
* Full washing-protocol comparison data and visual residue analysis.
* PCB design and embedded motor-control architecture of the automated washing subsystem.
* Software orchestration and asynchronous communication architecture of the autonomous platform.
* Raw torque–displacement traces for all batches.
* Sensitivity, bootstrap, and cross-validation diagnostics of the regularised-hyperbolic fit.

Washing Station:

![](data:image/png;base64...)

![](data:image/png;base64...)

Figure X. PCB design and embedded motor-control architecture of the automated washing subsystem.

![](data:image/png;base64...)

Figure Y. Software orchestration and asynchronous communication architecture of the autonomous rheological characterization platform.
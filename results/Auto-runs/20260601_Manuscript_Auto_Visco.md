Physics-Constrained Automated Viscometry Using Torque–Displacement for Rheological Discovery in Self-Driving Laboratory

Or

Rheological Formulation Discovery via Physics-Constrained Automated Viscometry and Batch-Aware Multi-Objective Bayesian Optimization in a Self-Driving Laboratory

Mohammad M Rastegardoosta, Ian Ngungab, Koketso Gaborekwec, Frantz Le Devedeca

# Abstract

One-paragraph structured abstract covering: motivation (viscosity mapping bottleneck), platform description (SDL + automated viscometry), the sim-to-real gap problem, and key results (convergence in 2–3 batches, <20 min human time, validated binary and ternary Newtonian systems).

**Keyword:** Self-driving laboratory, Bayesian optimization, automated rheology, Gaussian process, multi-objective optimization, torque–displacement, silicone oil, Pareto front, sim-to-real gap.

# 1. Introduction

* High-Viscosity Formulation Bottleneck:
  + Industrial relevance of mapping high-viscosity spaces (1,000–100,000 cP): lubricants, specialty coatings, pharmaceutical excipients, advanced adhesives.
  + Manual rheological characterization is time-prohibitive, operator-dependent, and impractical for multi-component composition spaces.
  + Binary and ternary mixture spaces exhibit logarithmic, highly non-linear viscosity landscapes requiring hundreds of experiments to resolve manually.
* "Sim-to-Real" Discrepancy in Viscosity Prediction:
  + Overview of empirical mixing laws: the logarithmic blending rule, the Grunberg–Nissan equation, the Ramírez-de-Santiago model, and the Redlich–Kister polynomial framework.
  + Fundamental limitation: these models are calibrated on ideal or near-ideal systems and break down catastrophically at extreme concentration limits and high viscosity regimes due to non-ideal molecular interactions.
  + Quantitative framing: even a well-parameterized model can produce errors of >50% in absolute viscosity for ternary systems above 10,000 cP.
  + Physical ground-truth measurement is irreplaceable; no computational surrogate alone can close this gap.
* Paradigm Shift to Self-Driving Labs (SDLs)
  + Definition and architecture of an SDL: closed-loop integration of robotic sample preparation, automated characterization, and machine learning-guided decision-making.
  + Review of SDLs in materials discovery (photovoltaics, catalysts, polymers), with a critical observation that rheological property spaces remain underexplored in autonomous platforms.
  + Key challenge unique to rheology automation: the requirement for precision sub-millimeter spindle positioning, high-viscosity liquid handling, and contamination-free sequential measurements.
* Scope and Contributions of This Work
  + Present the integrated hardware–software SDL for rheological discovery.
  + Introduce the two-tier case study: (i) binary silicone oil optimization using physics-grounded mixing models as the predictive kernel, and (ii) ternary formulation discovery using multi-objective Bayesian optimization against physical ground truth.
  + Enumerate specific contributions: physics-constrained torque–displacement framework, automated washing platform, q-EHVI batch acquisition matched to hardware deck capacity, and quantitative sim-to-real gap characterization.

# 2. Methods

The systematic characterization of material flow behavior necessitates a clear alignment between deformation types, flow regimes, and measurement techniques. While rheological principles span various modalities including extensional deformation and oscillatory regimes for viscoelastic profiling, this study focuses on Shear Rheology within a Steady-state Flow regime (**Table 1**). By utilizing a Rotational (Torque-Based) measurement method, the developed system establishes a robust baseline using Newtonian liquids, while maintaining the architectural flexibility required to extend characterization to complex Non-Newtonian fluids. This approach allows for the high-throughput discovery of material properties by linking mechanical torque-displacement recordings directly to fundamental physics-informed descriptors.

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

The system is engineered to automate the characterization of material rheology, a process traditionally requiring meticulous manual intervention. In a standard manual workflow: (i) the sample is loaded into a flat-bottomed container; (ii) a rotational spindle featuring a cone or plate geometry and integrated torque sensor is positioned at a precise axial height to establish a defined gap relative to the container floor; and (iii) as the spindle rotates at a programmed speed, the system calculates rheological properties by correlating the measured torque to the resultant shear stress, utilizing the known shear rate derived from the spindle geometry and rotational velocity.

## 2.1 Automated Characterization

### 2.1.1 Hardware Architecture and Bill of Materials

The hardware architecture designed to automate the manual protocols described above is detailed in the Bill of Materials (**Table 2**). To ensure high-fidelity measurements, the experimental setup utilizes robust stainless-steel containers with high-clearance, flat-bottom surfaces to mitigate deformation under stress. These containers are organized within a modular workstation constructed from T-slotted aluminum rails, providing the design flexibility required for variable component arrangements and scalable sample throughput. To interface these components, custom container holders were designed and fabricated via Fused Deposition Modeling (FDM) using Polyethylene Terephthalate Glycol-modified (PETG) filament.

**Table 2.** Bill of Materials for the Automated Rheology Platform

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

The core sensing unit consists of a unique cone-shaped rotational spindle (3° cone angle, 12.0 mm diameter) integrated with a precision torquemeter (AMETEK Brookfield; maximum torque of 7,187.0 dyne-cm). The primary challenge in automating this characterization lies in the high-precision positioning required to maintain the critical gap between the spindle and the container floor. To address this, a Cartesian-coordinate computer numerical control (CNC) machine (Genmitsu 4040-PRO, SainSmart) was employed to provide accurate, repeatable motion across the three-dimensional workspace of the workstation. To maintain measurement integrity and prevent cross-contamination between sequential samples, a dedicated washing station was designed and developed within the workstation to clean the spindle after each characterization cycle.

![Schematic of Automated Viscometry Platform](../../Images/platform.png)

**Figure 1.** Schematic of Automated Viscometry Platform.

### 2.1.2 Automated Washing Platform

Given the necessity of preventing cross-contamination between sequential measurements, an automated cleaning cycle is integrated into the workflow, consisting of dedicated washing and drying stations. The washing station utilizes a bespoke magnetic repulsion drive system to isolate the electronics from the cleaning fluids. In this configuration, a motor-driven spinner—embedded with driving magnets and housed in a PETG container—actuates a secondary driven spinner located within a separate washing container (***Supplementary Information***).

The two spinners are separated by a 3.0 mm gap, achieving rotation through magnetic repulsion between inversely arranged poles. While the motor housing was 3D-printed via FDM, the washing container was fabricated using Stereolithography (SLA) with a glass-filled photopolymer (Formlabs Rigid 10K Resin V1) for enhanced chemical resistance and structural integrity. The spindle is cleaned through relative motion against a smooth mat on the driven spinner, with fluid exchange regulated by external peristaltic pumps (Chi.Bio, University of Oxford) and a dedicated electronic control interface.

To optimize the efficacy of the automated cleaning cycle, four distinct washing protocols were evaluated based on their ability to remove residual sample while balancing system simplicity and operational timing. These scenarios ranged from a static spindle in contact with a rotating spinner to synchronous rotation and dynamic "zig-zag" lateral oscillation across the cleaning mat. The most comprehensive method, augmented mechanical scrubbing, combined spindle rotation and lateral oscillation against a rotating spinner equipped with a specialized brush attachment to dislodge sample accumulation on the cone edges. Comparative visual analysis demonstrated that while simpler protocols often left high-viscosity residues at the spindle’s perimeter, the augmented mechanical scrubbing protocol provided superior cleanliness. Consequently, this multi-modal approach was selected as the optimal configuration for the self-driving laboratory, achieving high-fidelity cleaning within a condensed timeframe without a significant increase in mechanical complexity.

### 2.1.3 Full process workflow

The automated rheological characterization platform operates through a fully integrated closed-loop workflow that combines robotic positioning, torque-based rheometry, physics-informed feedback analysis, autonomous washing, and real-time data orchestration. Unlike conventional rheometry workflows that rely heavily on manual positioning and operator intervention, the developed system performs sequential characterization of multiple samples autonomously within a self-driving laboratory framework.

The workflow begins with system initialization and calibration, during which the CNC positioning platform, rotational viscometer, and washing subsystems are synchronized. A calibration routine establishes the safe spindle-to-container reference heights for each sample cell, enabling precise control of the critical measurement gap during subsequent experiments. After calibration, the system executes an automated per-cell characterization cycle in which the spindle descends incrementally toward the container floor while continuously recording torque responses under controlled rotational speeds.

At each axial position, the spindle performs a programmed RPM sweep and measures torque evolution over time. These measurements are processed through a physics-constrained feedback framework based on rotational drag behavior, statistical trend analysis, confidence-weighted hit-point detection, and second-derivative anomaly analysis. The framework autonomously identifies liquid-contact transitions and determines the optimal termination point of the descent process while maintaining protection against excessive torque loading.

Following characterization of each sample, the system automatically initiates a two-stage washing procedure to prevent cross-contamination between sequential measurements. Importantly, the washing cycle operates concurrently with CNC travel motions to minimize idle time and maximize experimental throughput. The collected torque–displacement data are then analyzed using a hyperbolic drag model to estimate viscosity-related descriptors and generate predictive rheological metrics. The complete orchestration architecture therefore integrates hardware automation, adaptive sensing, real-time feedback control, and physics-informed data interpretation into a unified high-throughput rheological discovery platform suitable for autonomous experimentation and self-driving laboratory environments.
![Physics-constrained automated viscometry workflow](../../Images/Workflow_diagram.svg)

**Figure 2.** Full workflow of the physics-constrained automated viscometry platform. The self-driving rheological characterization system integrates CNC-controlled positioning, torque-based rotational rheometry, physics-informed feedback analysis, autonomous hit-point detection, predictive viscosity estimation, and concurrent washing operations into a unified high-throughput experimental framework.

## 2.2 Physics-Informed Mixture Rheology

### 2.2.1 Generalized Theory Framework

The proposed automated viscometry platform was developed based on a modified cone-and-plate rheological configuration in which a rotating cone spindle approaches a stationary flat plate while the generated torque is continuously monitored as a function of vertical displacement. Unlike conventional cone-and-plate rheometers where the cone tip nearly touches the plate, the present system operates across a broad range of gap heights, resulting in three distinct hydrodynamic regimes: parallel-plate dominated, transition, and cone-and-plate dominated behavior.

The local liquid thickness is defined as (Eq. 1):
$$H(r) = h + r \tan \alpha$$

where h is the minimum tip clearance, r is the radial coordinate, and α is the cone half-angle. For large spindle separations (h ≫ r tan(α)), the gap thickness becomes nearly uniform throughout the radius (H(r) = h).

In this regime, the system approaches classical parallel-plate rotational rheometry, where the torque scales approximately as (Eq. 2):
$$T \propto \frac{\mu \omega R^4}{h}$$

Here, the viscous resistance is strongly governed by the global spindle-to-substrate distance. Conversely, for very small clearances (h→0), the radial contribution dominates the gap profile (H(r) ≈ r tan(α)). and the system converges toward the classical cone-and-plate rheometer limit with nearly uniform shear rate across the radius. The analytical torque expression becomes (Eq. 3):
$$T = \frac{2\pi}{3} \frac{\mu \omega R^3}{\tan \alpha}$$

Between these two asymptotic limits lies a transition regime where both the finite tip clearance and cone geometry simultaneously influence the shear field. In this intermediate region, neither the parallel-plate approximation nor the ideal cone-and-plate solution alone can accurately describe the flow behavior. Therefore, a generalized lubrication-theory framework was employed to continuously capture the evolution of shear stress and torque throughout the entire displacement range.

Under incompressible, laminar, axisymmetric, and low-Reynolds-number conditions, the dominant fluid motion was assumed to be azimuthal while radial and axial inertia effects were neglected. The governing momentum equation reduces to (Eq. 4):
$$\mu \frac{\partial^2 u_\theta}{\partial z^2} = 0$$

Using no-slip boundary conditions at the rotating cone and stationary plate, the azimuthal velocity distribution becomes (Eq. 5):
$$u_\theta(r,z) = \frac{\omega r z}{H(r)}$$

which yields the local shear stress (Eq. 6):
$$\tau(r) = \frac{\mu \omega r}{H(r)}$$

The total torque was then obtained through radial integration of the local viscous moment contributions (Eq. 7):
$$T = 2\pi\mu\omega \int_{0}^{R} \frac{r^3}{H(r)} \, dr$$

This unified physics-informed formulation enables continuous rheological characterization across parallel-plate, transition, and cone-and-plate operating regimes using automated torque–displacement measurements.

### 2.2.2 Positional Uncertainty and Micro-Scale Reproducibility

The transition from manual to autonomous rheology characterization necessitates a rigorous evaluation of the mechanical precision afforded by the robotic interface, as the gap height between the spindle and the container floor fundamentally dictates the accuracy of shear rate calculations. While the Cartesian CNC platform utilizes NEMA 17 stepper motors and T10 lead screws for high-resolution motion, cumulative mechanical uncertainties often exceed the manufacturer-specified running accuracy of ±0.1 mm. In practice, positional variance can reach a range of nearly 1.0 mm due to the synergistic effects of mechanical backlash, thermal expansion of metallic components during continuous operation, and the structural compliance of 3D-printed PETG fixtures. To mitigate these inherent mechanical limitations, we implemented a physics-constrained orchestration logic that utilizes real-time torque-displacement feedback. This approach bypasses the unreliability of static coordinates by applying physical principles and statistical monitoring to dynamically detect sample-contact and container-bottom zones. By transitioning from open-loop positioning to a feedback-driven system, the framework effectively resolves positional uncertainty while simultaneously optimizing experimental runtime and protecting the hardware from collision-induced damage.

![Physics Problem](../../Images\Physics_Workflow_diagram.svg)

**Figure 3.** ???

### 2.2.3 GPU-Accelerated Simulation Framework

A GPU-accelerated computational framework was developed using NVIDIA Warp to simulate torque evolution during automated spindle motion. The computational pipeline consisted of: (i) cone-geometry definition, (ii) radial discretization of the fluid domain, (iii) parallel computation of local shear stress and differential torque contributions, and (iv) numerical integration of total torque across the radius. The framework automatically performed parameter sweeps over gap height and angular velocity to generate torque–displacement and torque–RPM relationships. Each GPU thread was assigned to a radial discretization cell, enabling efficient large-scale simulations and rapid convergence analysis. Numerical stabilization procedures were implemented near the h→0 regime to avoid singular behavior and ensure consistency with the classical cone-and-plate rheometer limit. The modular architecture was designed for future extension toward transient flow simulations, non-Newtonian constitutive models, viscoelastic fluids, squeeze-film hydrodynamics, and machine-learning-assisted viscosity estimation in autonomous self-driving laboratory environments.

## 2.3 System Orchestration and Software Integration

### 2.3.1 Hardware Embedding

The hardware embedding strategy focused on low-level integration of rheological sensing, robotic positioning, and automated washing within a unified autonomous characterization platform. A Brookfield DVT rotational viscometer was integrated with a three-axis CNC positioning system to enable programmable sample traversal and repeatable spindle alignment across predefined sample and washing coordinates. System coordinates, including sample positions, washing-station locations, and safe-height offsets, were parameterized through YAML configuration files, enabling rapid reconfiguration without modification of the control software.

An ESP32 microcontroller served as the embedded actuator-control layer for the washing subsystem. The custom PCB architecture employed L298N motor drivers with PWM-based control to actuate six DC pumps and three agitation motors. To reduce hardware complexity while maintaining independent fluid delivery, a multiplexed channel-sharing configuration using diode-isolated switching was implemented for sequential pump operation. The washing module executed predefined detergent, water, and isopropanol rinse cycles between measurements to minimize cross-contamination and improve experimental reproducibility (***Supplementary Information***).

### 2.3.2 Digital Control and Asynchronous Software Architecture

The automated viscometer platform employed a dual-Python asynchronous software architecture to accommodate hardware compatibility constraints while maintaining centralized experimental orchestration. A 64-bit Python environment managed high-level workflow execution, CNC motion control through G-code generation, washing-station sequencing, and rheological data processing. Because the Brookfield communication library required a proprietary 32-bit DLL, viscometer communication was isolated within a dedicated 32-bit Python environment. The two runtime environments communicated through synchronized file-based data exchange and process-level coordination. The software stack was organized into modular hardware abstraction layers for CNC control, viscometer communication, embedded washing control, and rheological analysis. The ESP32 controller received high-level serial commands from the host computer (e.g., washing and rinsing triggers) and executed predefined pump and motor sequences independently from the primary orchestration loop. This asynchronous architecture enabled non-blocking execution of robotic motion, rheological acquisition, and washing operations during autonomous experimentation. To ensure experimental traceability and reproducibility, all measurement outputs were archived together with system metadata, including calibration status, software version, operator annotations, and environmental conditions. Integrated recovery mechanisms, including viscometer reconnection and safe-motion interruption protocols, further improved robustness during long-duration autonomous operation (***Supplementary Information***).

### 2.3.3 User Interface

* Real-time dashboard: live torque–displacement traces per sample cell, current batch progress, GP posterior mean and variance map on ternary simplex, evolving Pareto front visualization.
* Operator controls: manual override, batch abort, washing protocol selection, calibration triggers.
* Automated report generation: per-batch experimental summary, convergence metrics, recommended next formulation.

# 3. Results and Discussion

## 3.1 Hardware and Automation

* A: Data Acquisition within range of 1.0k to 125.0k cP.
* B, C, D: Viscosity Extrapolation from rotational drag data (18 samples data collection, trimming, curve fitting, viscosity error)
* E: Execution reliability over extended runs: success rate per sample cell, liquid measurement reliability for fluids up to 100,000 cP.
* F: Throughput quantification: timeline breakdown of blending (human), dispensing (human), characterization (robot), and washing (robot) within the 5-hour/18-sample window.

![Results 1](../../Images\Figure_1.svg)

**Figure 4.** End-to-end performance of the automated viscometry platform: (A) Normalized rotational-drag traces across the working range of 1.0–125.0 k cP. (B–D) Viscosity-extrapolation pipeline on an 18-sample run, showing (B) raw rotational-drag data, (C) partially-calibrated traces with hyperbolic fits, and (D) predicted vs. reference viscosity per cell with the corresponding relative error. (E) Execution reliability over several runs, summarized as the distribution of relative errors for fluids up to 125,000 cP. (F) Stacked timeline breakdown of the full process compared against the equivalent fully-manual workflow.

## 3.2 Cross-Material Generalization Autonomous Rheological Characterization

A central challenge in autonomous rheological characterization lies in achieving robust operation across chemically distinct formulation spaces while preserving predictive fidelity under highly nonlinear viscosity evolution. To evaluate the generalizability of the proposed platform, we investigated both molecularly distinct Newtonian fluid systems and nonlinear binary formulation spaces exhibiting strong composition-dependent rheological behavior.

### 3.2.1 Molecularly Distinct Fluid Systems

To evaluate the generalizability of the autonomous viscometry platform beyond a single formulation chemistry, the system was investigated across mechanistically distinct high-viscosity fluid systems spanning substantially different molecular architectures and rheological interaction pathways. The selected materials included non-polar silicone oils, polar polymeric PEG systems, hydrogen-bond-dominated glycerol formulations, polysaccharide-based Solagum systems, associative polymeric Sepineo gels, and crosslinked Carbopol 980 hydrogel formulations. Rather than representing simple variations of viscosity magnitude, these materials were intentionally selected to probe fundamentally different viscosity-generation mechanisms and fluid-structure interactions encountered in practical formulation environments.

From a mechanistic rheology perspective, the investigated systems can be broadly categorized into polymeric chain-entanglement fluids (silicone oils and PEG), intermolecular friction-dominated molecular liquids (glycerol), polysaccharide-thickened biopolymer systems (Solagum), associative rheology modifiers governed by transient hydrophobic network formation (Sepineo), and crosslinked microgel structures exhibiting swollen polymer-network interactions (Carbopol 980). These distinct material classes introduce substantial variations in wetting dynamics, meniscus formation, drag evolution, spindle immersion response, and local microstructural resistance during automated characterization.

Despite these fundamentally different rheological environments, the proposed physics-constrained Z-descent and torque-acquisition framework maintained stable operation throughout the investigated viscosity range. The adaptive hit-point detection strategy enabled reliable spindle-floor gap control under varying interfacial conditions, while the automated dual-stage washing architecture effectively minimized residual contamination between chemically and structurally dissimilar formulations.

*[Insert cross-material viscosity characterization results, predicted-versus-reference comparison plots, representative torque acquisition trajectories]*

Overall, the results demonstrate that the proposed platform is not restricted to a single calibration fluid family or formulation chemistry, but instead generalizes across mechanistically distinct rheological systems exhibiting substantially different molecular and microstructural interaction behaviors. Having established cross-material robustness, we next investigate autonomous characterization within nonlinear formulation spaces where experimentally observed viscosity evolution deviates from idealized empirical mixing predictions.
![Not-Newtonian Polymers Rheology](../../Images\non-newtonian_samples.png)

**Figure 5.** Conceptual schematic for differentiating high-viscosity fluid systems and their molecular rheology mechanisms.

### 3.2.2 Autonomous Rheological Mapping of Nonlinear Formulation Spaces

Beyond single-component fluids, practical formulation environments are governed by nonlinear composition–property relationships that are not fully captured by classical empirical mixing laws. To probe this regime, we investigate binary silicone–silicone systems as a controlled formulation space with predictable but non-ideal rheological behavior under idealized theoretical models.

In these systems, viscosity evolves nonlinearly with composition due to underlying molecular weight distribution effects and interaction-dependent deviations from ideal logarithmic mixing rules (e.g., Grunberg–Nissan-type formulations). A virtual reference landscape was first constructed using conventional logarithmic and Grunberg–Nissan-type mixing assumptions, providing a baseline prediction of viscosity evolution across composition space. However, systematic deviations are observed when compared to experimentally measured values, particularly in high-viscosity regimes where small compositional variations induce amplified nonlinear responses.

The autonomous viscometry platform captures these deviations through physics-constrained Z-descent characterization and torque-based viscosity inference, enabling high-resolution mapping of the true rheological landscape without reliance on predefined constitutive assumptions. The resulting dataset reveals structured disagreement between idealized models and physical measurements, highlighting the importance of closed-loop experimental correction in high-viscosity formulation spaces.

*[Insert mixing-law prediction vs experimental ground truth heatmaps, deviation/error surface, and representative composition–viscosity curves.]*

Overall, these results demonstrate that the platform generates high-fidelity, model-corrected rheological datasets across nonlinear formulation spaces. While not explicitly implementing active learning or Bayesian optimization in this study, the resulting structured dataset and uncertainty-aware measurements establish a direct foundation for future integration with data-driven exploration frameworks, including active learning and batch-efficient experimental design strategies.

# 4. Conclusion

* Summary of the integrated SDL architecture and its two-tier validation (binary physics-model validation + ternary multi-objective discovery).
* Key finding: empirical mixing models are necessary but insufficient; physical ground-truth feedback via the automated viscometry loop is the critical enabling component.
* Efficiency statement: the platform compresses what would require weeks of manual experimentation into overnight autonomous runs.
* Future Work:
  + Extension of the physics-informed torque framework to non-Newtonian and viscoelastic fluids (power-law, Herschel–Bulkley, Maxwell models).
  + Inverse rheological analysis: inferring molecular-level interaction parameters from torque–displacement signatures.
  + Transfer learning across fluid families to accelerate warm-starting of the GP surrogate.
  + Integration of inline spectroscopic characterization (NIR, Raman) for simultaneous compositional and rheological monitoring.
  + Scale-up to larger batch decks and parallelized multi-spindle platforms.

# 5. Supplementary Information

* Full Bill of Materials (Table S1).
* CNC calibration map methodology and positional variance dataset.
* GPU simulation validation against analytical limits (parallel-plate and cone-and-plate).
* Full washing protocol comparison data.
* Complete GP hyperparameter optimization details and kernel selection justification.
* Raw torque–displacement traces for all batches.
* q-EHVI implementation details and convergence diagnostics.

Washing Station:

![](data:image/png;base64...)

![](data:image/png;base64...)

Figure X. PCB design and embedded motor-control architecture of the automated washing subsystem.

![](data:image/png;base64...)

Figure Y. Software orchestration and asynchronous communication architecture of the autonomous rheological characterization platform.
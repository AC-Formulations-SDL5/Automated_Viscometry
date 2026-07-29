"""Generate the rheology-analysis pipeline diagram (SVG).

Mirrors the visual language of ``Workflow_diagram.py`` (Google-Sans typography,
soft pastel boxes with stroked headers, hard-coded SVG payload).  Renders the
end-to-end data path: raw automated-descent recordings (height, torque %, RPM)
→ drag-profile fit → silicone calibration → Newtonian / power-law branching
→ shear-stress conversion → regime classification & Brookfield validation
→ unified rheology output.

Run with no arguments to drop the SVG next to this script:
    python Rheology_analysis_pipeline.py
Or supply an explicit output path:
    python Rheology_analysis_pipeline.py C:/somewhere/out.svg
"""

from pathlib import Path
import sys


SVG_CONTENT = """<svg width="1220" height="1380" viewBox="0 0 1220 1380" xmlns="http://www.w3.org/2000/svg">

  <defs>
    <style>
      .bg { fill: #FFFFFF; }
      .box { rx: 18; ry: 18; stroke-width: 1.5; }
      .title { font: 600 22px Google Sans, Arial, sans-serif; fill: #202124; text-anchor: middle; }
      .text  { font: 20px Google Sans, Arial, sans-serif; fill: #3C4043; }
      .small { font: 17px Google Sans, Arial, sans-serif; fill: #5F6368; font-style: italic; }
      .arrow { fill: none; stroke: #3C4043; stroke-width: 2; marker-end: url(#arrowhead); }
      .arrow-branch { fill: none; stroke: #5F6368; stroke-width: 2; stroke-dasharray: 6 4; marker-end: url(#arrowhead); }
      .icon-bg { fill: #FFFFFF; stroke-width: 1.5; }
      .icon-line { fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
      .icon-fill { stroke: none; }
    </style>

    <marker id="arrowhead" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
      <polyline points="1.5,1.5 7,4 1.5,6.5" fill="none" stroke="#3C4043" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>

    <filter id="shadow">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#000000" flood-opacity="0.12"/>
    </filter>
  </defs>

  <rect x="0" y="0" width="1220" height="1380" class="bg"/>

  <!-- ============================================================== -->
  <!-- 1  RAW DATA INGEST  (LEFT)                                      -->
  <!-- ============================================================== -->
  <rect x="80" y="40" width="541" height="150" fill="#E8F0FE" stroke="#1A73E8" class="box" filter="url(#shadow)"/>
  <line x1="207" y1="100" x2="207" y2="170" stroke="#DADCE0" stroke-width="1.5"/>
  <text x="350" y="75" class="title" fill="#1A73E8">1. Raw Data Ingest</text>
  <text x="230" y="105" class="text">• Per-sweep recordings  (h, T%, RPM)</text>
  <text x="230" y="128" class="text">• Sample / family / concentration labels</text>
  <text x="230" y="151" class="text">• Re-zero h to its minimum; γ̇ = 2π·RPM / (60·α)</text>
  <text x="230" y="174" class="small">silicones · Carbopol · PEG · Sepineo · Solagum</text>
  <g transform="translate(0 0)">
    <circle cx="135" cy="115" r="28" class="icon-bg" stroke="#1A73E8"/>
    <circle cx="135" cy="115" r="22" fill="none" stroke="#D2E3FC" stroke-width="2"/>
    <rect x="121" y="100" width="28" height="20" fill="none" stroke="#1A73E8" stroke-width="2" rx="2"/>
    <line x1="125" y1="106" x2="145" y2="106" class="icon-line" stroke="#1A73E8"/>
    <line x1="125" y1="112" x2="145" y2="112" class="icon-line" stroke="#1A73E8"/>
    <line x1="125" y1="118" x2="140" y2="118" class="icon-line" stroke="#1A73E8"/>
  </g>

  <!-- ============================================================== -->
  <!-- 2  DRAG PROFILE CONSTRUCTION  (RIGHT)                           -->
  <!-- ============================================================== -->
  <rect x="680" y="40" width="541" height="150" fill="#F3E8FD" stroke="#A142F4" class="box" filter="url(#shadow)"/>
  <line x1="807" y1="100" x2="807" y2="170" stroke="#DADCE0" stroke-width="1.5"/>
  <text x="950" y="75" class="title" fill="#A142F4">2. Build Drag Profile  D(h) = T%/RPM</text>
  <text x="830" y="105" class="text">• One D(h) curve per (fluid, RPM) sweep</text>
  <text x="830" y="128" class="text">• Average / smooth replicates at each h</text>
  <text x="830" y="151" class="text">• Carries all rheology information per sweep</text>
  <text x="830" y="174" class="small">raw_long  →  one curve per (fluid_id, rpm)</text>
  <g transform="translate(0 0)">
    <circle cx="735" cy="115" r="28" class="icon-bg" stroke="#A142F4"/>
    <circle cx="735" cy="115" r="22" fill="none" stroke="#E9D7FE" stroke-width="2"/>
    <polyline points="722,128 729,116 736,121 743,104 750,108" class="icon-line" stroke="#A142F4"/>
    <line x1="721" y1="128" x2="752" y2="128" class="icon-line" stroke="#A142F4"/>
  </g>

  <!-- ============================================================== -->
  <!-- 3  DRAG-VS-HEIGHT FIT  (LEFT)                                   -->
  <!-- ============================================================== -->
  <rect x="80" y="220" width="541" height="160" fill="#F3E8FD" stroke="#A142F4" class="box" filter="url(#shadow)"/>
  <line x1="207" y1="280" x2="207" y2="360" stroke="#DADCE0" stroke-width="1.5"/>
  <text x="350" y="255" class="title" fill="#A142F4">3. Drag Fit   D(h) = A/(h + h_c) + B</text>
  <text x="230" y="285" class="text">• Per-sweep amplitude A  (and offset B)</text>
  <text x="230" y="308" class="text">• First pass: h_c free  →  per-sweep value</text>
  <text x="230" y="331" class="text">• Quality check via R²  (typ. &gt; 0.95)</text>
  <text x="230" y="354" class="small">amps_free  →  (A, B, h_c, R²)</text>
  <g transform="translate(0 0)">
    <circle cx="135" cy="295" r="28" class="icon-bg" stroke="#A142F4"/>
    <circle cx="135" cy="295" r="22" fill="none" stroke="#E9D7FE" stroke-width="2"/>
    <path d="M120 305 Q126 285 135 285 Q150 285 150 305" class="icon-line" stroke="#A142F4"/>
    <line x1="118" y1="307" x2="152" y2="307" class="icon-line" stroke="#A142F4"/>
  </g>

  <!-- ============================================================== -->
  <!-- 4  UNIVERSAL h_c  (RIGHT, calibration)                          -->
  <!-- ============================================================== -->
  <rect x="680" y="220" width="541" height="160" fill="#E6F4EA" stroke="#188038" class="box" filter="url(#shadow)"/>
  <line x1="807" y1="280" x2="807" y2="360" stroke="#DADCE0" stroke-width="1.5"/>
  <text x="950" y="255" class="title" fill="#188038">4. Universal Geometric Offset  h_c*</text>
  <text x="830" y="285" class="text">• Median of per-sweep h_c on silicones</text>
  <text x="830" y="308" class="text">• Confirms a single, instrument-only value</text>
  <text x="830" y="331" class="text">• Re-fit every sweep with h_c = h_c* fixed</text>
  <text x="830" y="354" class="small">h_c* ≈ 0.277 mm  →  amps table</text>
  <g transform="translate(0 0)">
    <circle cx="735" cy="295" r="28" class="icon-bg" stroke="#188038"/>
    <circle cx="735" cy="295" r="22" fill="none" stroke="#CEEAD6" stroke-width="2"/>
    <circle cx="735" cy="295" r="11" class="icon-line" stroke="#188038"/>
    <circle cx="735" cy="295" r="4" class="icon-fill" fill="#188038"/>
    <line x1="735" y1="278" x2="735" y2="285" class="icon-line" stroke="#188038"/>
    <line x1="735" y1="305" x2="735" y2="312" class="icon-line" stroke="#188038"/>
    <line x1="718" y1="295" x2="725" y2="295" class="icon-line" stroke="#188038"/>
    <line x1="745" y1="295" x2="752" y2="295" class="icon-line" stroke="#188038"/>
  </g>

  <!-- ============================================================== -->
  <!-- 5  SILICONE NEWTONIAN CALIBRATION  (LEFT, calibration)          -->
  <!-- ============================================================== -->
  <rect x="80" y="410" width="541" height="160" fill="#E6F4EA" stroke="#188038" class="box" filter="url(#shadow)"/>
  <line x1="207" y1="470" x2="207" y2="550" stroke="#DADCE0" stroke-width="1.5"/>
  <text x="350" y="445" class="title" fill="#188038">5. Silicone Newtonian Calibration  A = k·μ^p</text>
  <text x="230" y="475" class="text">• Log-log fit on silicones of known μ</text>
  <text x="230" y="498" class="text">• Establishes (k, p)  →  amplitude ↔ viscosity</text>
  <text x="230" y="521" class="text">• Inverse:  μ_app = (A/k)^(1/p)</text>
  <text x="230" y="544" class="small">k ≈ 5.9e-9,  p ≈ 2.01,  R² ≈ 0.999  (n = 23)</text>
  <g transform="translate(0 0)">
    <circle cx="135" cy="485" r="28" class="icon-bg" stroke="#188038"/>
    <circle cx="135" cy="485" r="22" fill="none" stroke="#CEEAD6" stroke-width="2"/>
    <polyline points="120,498 128,488 137,484 145,476" class="icon-line" stroke="#188038"/>
    <circle cx="120" cy="498" r="2.5" class="icon-fill" fill="#188038"/>
    <circle cx="128" cy="488" r="2.5" class="icon-fill" fill="#188038"/>
    <circle cx="137" cy="484" r="2.5" class="icon-fill" fill="#188038"/>
    <circle cx="145" cy="476" r="2.5" class="icon-fill" fill="#188038"/>
  </g>

  <!-- ============================================================== -->
  <!-- 6  TORQUE → STRESS  (RIGHT)                                     -->
  <!-- ============================================================== -->
  <rect x="680" y="410" width="541" height="160" fill="#E0F2F1" stroke="#00ACC1" class="box" filter="url(#shadow)"/>
  <line x1="807" y1="470" x2="807" y2="550" stroke="#DADCE0" stroke-width="1.5"/>
  <text x="950" y="445" class="title" fill="#00ACC1">6. Torque → Absolute Stress</text>
  <text x="830" y="475" class="text">• Cone-plate formula τ = 3M / (2πR³)</text>
  <text x="830" y="498" class="text">• Full-scale M = 7187 dyne·cm  →  τ = c·T%</text>
  <text x="830" y="521" class="text">• c ≈ 1.986 Pa/%  (R = 12 mm,  α = 3°)</text>
  <text x="830" y="544" class="small">independent of any per-fluid calibration</text>
  <g transform="translate(0 0)">
    <circle cx="735" cy="485" r="28" class="icon-bg" stroke="#00ACC1"/>
    <circle cx="735" cy="485" r="22" fill="none" stroke="#CDEFF3" stroke-width="2"/>
    <path d="M725 478 H745 M725 488 H740 M725 498 H735" class="icon-line" stroke="#00ACC1"/>
    <polyline points="747,476 753,482 747,488" class="icon-line" stroke="#00ACC1"/>
  </g>

  <!-- ============================================================== -->
  <!-- 7  DECISION : SINGLE-RPM vs MULTI-RPM  (CENTER WIDE)            -->
  <!-- ============================================================== -->
  <rect x="220" y="600" width="780" height="120" fill="#FEF7E0" stroke="#F9AB00" class="box" filter="url(#shadow)"/>
  <line x1="360" y1="640" x2="360" y2="710" stroke="#DADCE0" stroke-width="1.5"/>
  <text x="610" y="640" class="title" fill="#F9AB00">7. Decision — How many distinct RPMs were recorded?</text>
  <text x="380" y="675" class="text">• 1 RPM   →   Newtonian-by-assumption  (no flow curve possible)</text>
  <text x="380" y="700" class="text">• ≥ 2 RPMs  →  Power-law fit  A(γ̇) = A₀·γ̇^(n−1)</text>
  <g transform="translate(0 0)">
    <circle cx="280" cy="660" r="28" class="icon-bg" stroke="#F9AB00"/>
    <circle cx="280" cy="660" r="22" fill="none" stroke="#FEEFC3" stroke-width="2"/>
    <polygon points="280,646 296,660 280,674 264,660" fill="none" stroke="#F9AB00" stroke-width="2"/>
    <text x="280" y="665" font="600 14px Arial" text-anchor="middle" fill="#F9AB00">?</text>
  </g>

  <!-- ============================================================== -->
  <!-- 8A  NEWTONIAN BRANCH  (LEFT)                                    -->
  <!-- ============================================================== -->
  <rect x="80" y="760" width="541" height="170" fill="#E8F0FE" stroke="#1A73E8" class="box" filter="url(#shadow)"/>
  <line x1="207" y1="820" x2="207" y2="910" stroke="#DADCE0" stroke-width="1.5"/>
  <text x="350" y="795" class="title" fill="#1A73E8">8A. Newtonian Branch  (1 RPM)</text>
  <text x="230" y="825" class="text">• μ_app = (A / k)^(1/p)   from silicone calib.</text>
  <text x="230" y="848" class="text">• K = μ_app · 1e-3  (Pa·s),   n ≡ 1</text>
  <text x="230" y="871" class="text">• τ(γ̇) = K·γ̇   (straight line through origin)</text>
  <text x="230" y="894" class="small">regime label = "Newtonian (single RPM)"</text>
  <text x="230" y="915" class="small">single point cannot distinguish thinning/thickening</text>
  <g transform="translate(0 0)">
    <circle cx="135" cy="840" r="28" class="icon-bg" stroke="#1A73E8"/>
    <circle cx="135" cy="840" r="22" fill="none" stroke="#D2E3FC" stroke-width="2"/>
    <line x1="120" y1="855" x2="150" y2="825" class="icon-line" stroke="#1A73E8"/>
    <line x1="118" y1="857" x2="152" y2="857" class="icon-line" stroke="#1A73E8"/>
  </g>

  <!-- ============================================================== -->
  <!-- 8B  POWER-LAW BRANCH  (RIGHT)                                   -->
  <!-- ============================================================== -->
  <rect x="680" y="760" width="541" height="170" fill="#FCE8E6" stroke="#D93025" class="box" filter="url(#shadow)"/>
  <line x1="807" y1="820" x2="807" y2="910" stroke="#DADCE0" stroke-width="1.5"/>
  <text x="950" y="795" class="title" fill="#D93025">8B. Power-Law Branch  (≥ 2 RPMs)</text>
  <text x="830" y="825" class="text">• Log-log fit   ln A = ln A₀ + (n−1)·ln γ̇</text>
  <text x="830" y="848" class="text">• Recover n  (flow index)  and  K (Pa·s^n)</text>
  <text x="830" y="871" class="text">• η_app(γ̇) = K·γ̇^(n−1),   τ(γ̇) = K·γ̇^n</text>
  <text x="830" y="894" class="small">anchor K from μ_app at γ̇_min</text>
  <text x="830" y="915" class="small">R² of log-log fit reports model quality</text>
  <g transform="translate(0 0)">
    <circle cx="735" cy="840" r="28" class="icon-bg" stroke="#D93025"/>
    <circle cx="735" cy="840" r="22" fill="none" stroke="#FAD2CF" stroke-width="2"/>
    <path d="M722 855 Q734 832 750 826" class="icon-line" stroke="#D93025"/>
    <line x1="720" y1="857" x2="752" y2="857" class="icon-line" stroke="#D93025"/>
  </g>

  <!-- ============================================================== -->
  <!-- 9  CLASSIFY REGIME  (LEFT)                                      -->
  <!-- ============================================================== -->
  <rect x="80" y="970" width="541" height="160" fill="#FCE8E6" stroke="#D93025" class="box" filter="url(#shadow)"/>
  <line x1="207" y1="1030" x2="207" y2="1110" stroke="#DADCE0" stroke-width="1.5"/>
  <text x="350" y="1005" class="title" fill="#D93025">9. Classify Rheology Regime</text>
  <text x="230" y="1035" class="text">• n &gt; 1.05   →   shear-thickening</text>
  <text x="230" y="1058" class="text">• 0.95 ≤ n ≤ 1.05   →   Newtonian</text>
  <text x="230" y="1081" class="text">• n &lt; 0.95   →   shear-thinning  (gel / yield-stress if n→0)</text>
  <text x="230" y="1104" class="small">also reports K, η_app(γ̇), τ(γ̇) callable</text>
  <g transform="translate(0 0)">
    <circle cx="135" cy="1045" r="28" class="icon-bg" stroke="#D93025"/>
    <circle cx="135" cy="1045" r="22" fill="none" stroke="#FAD2CF" stroke-width="2"/>
    <line x1="120" y1="1058" x2="150" y2="1032" class="icon-line" stroke="#D93025"/>
    <line x1="120" y1="1058" x2="150" y2="1058" class="icon-line" stroke="#D93025"/>
    <path d="M120 1058 Q135 1058 150 1032" class="icon-line" stroke="#D93025" stroke-dasharray="3 3"/>
  </g>

  <!-- ============================================================== -->
  <!-- 10  BROOKFIELD VALIDATION  (RIGHT)                              -->
  <!-- ============================================================== -->
  <rect x="680" y="970" width="541" height="160" fill="#E0F2F1" stroke="#00ACC1" class="box" filter="url(#shadow)"/>
  <line x1="807" y1="1030" x2="807" y2="1110" stroke="#DADCE0" stroke-width="1.5"/>
  <text x="950" y="1005" class="title" fill="#00ACC1">10. Brookfield Reference Validation</text>
  <text x="830" y="1035" class="text">• Look up μ_ref(γ̇), τ_ref(γ̇)  from label CSV</text>
  <text x="830" y="1058" class="text">• Log-log interpolation in γ̇  →  per-sweep ref</text>
  <text x="830" y="1081" class="text">• Parity plots  μ_app vs μ_ref  and  τ vs τ_ref</text>
  <text x="830" y="1104" class="small">flags fluids outside ±2× Brookfield band</text>
  <g transform="translate(0 0)">
    <circle cx="735" cy="1045" r="28" class="icon-bg" stroke="#00ACC1"/>
    <circle cx="735" cy="1045" r="22" fill="none" stroke="#CDEFF3" stroke-width="2"/>
    <path d="M723 1058 L747 1034" class="icon-line" stroke="#00ACC1" stroke-dasharray="3 3"/>
    <polygon points="730,1050 740,1040 743,1043 733,1053" fill="#00ACC1"/>
    <circle cx="727" cy="1055" r="2.5" class="icon-fill" fill="#00ACC1"/>
    <circle cx="744" cy="1037" r="2.5" class="icon-fill" fill="#00ACC1"/>
  </g>

  <!-- ============================================================== -->
  <!-- 11  UNIFIED OUTPUT  (CENTER WIDE)                               -->
  <!-- ============================================================== -->
  <rect x="220" y="1180" width="780" height="160" fill="#E8F0FE" stroke="#1A73E8" class="box" filter="url(#shadow)"/>
  <line x1="360" y1="1220" x2="360" y2="1320" stroke="#DADCE0" stroke-width="1.5"/>
  <text x="610" y="1215" class="title" fill="#1A73E8">11. Unified Rheology Output  —  predict_rheology()</text>
  <text x="380" y="1245" class="text">• Regime label + (n, K, η_app, τ) callables</text>
  <text x="380" y="1268" class="text">• Master rheogram  τ vs γ̇  (silicone grid + polymer curves)</text>
  <text x="380" y="1291" class="text">• Per-family small-multiples  measurement ⊕ fit ⊕ reference</text>
  <text x="380" y="1314" class="small">artefacts: amplitudes.csv · flow_curves.csv · stress_measurements.csv</text>
  <g transform="translate(0 0)">
    <circle cx="280" cy="1235" r="28" class="icon-bg" stroke="#1A73E8"/>
    <circle cx="280" cy="1235" r="22" fill="none" stroke="#D2E3FC" stroke-width="2"/>
    <path d="M266 1245 Q272 1228 280 1233 Q288 1238 294 1222" class="icon-line" stroke="#1A73E8"/>
    <line x1="264" y1="1248" x2="296" y2="1248" class="icon-line" stroke="#1A73E8"/>
  </g>

  <!-- ============================================================== -->
  <!-- FLOW CONNECTORS                                                 -->
  <!-- ============================================================== -->
  <!-- 1 → 2  -->
  <path d="M621 115 H680" class="arrow"/>
  <!-- 2 → 3  (right-down-left)  -->
  <path d="M950 190 V205 H350 V220" class="arrow"/>
  <!-- 3 → 4  -->
  <path d="M621 300 H680" class="arrow"/>
  <!-- 4 → 5  (right-down-left)  -->
  <path d="M950 380 V395 H350 V410" class="arrow"/>
  <!-- 5 → 6  -->
  <path d="M621 490 H680" class="arrow"/>
  <!-- 5 → 7 (left feed into decision)  -->
  <path d="M350 570 V585 H460 V600" class="arrow"/>
  <!-- 6 → 7 (right feed into decision; informs stress for both branches)  -->
  <path d="M950 570 V585 H760 V600" class="arrow-branch"/>
  <!-- 7 → 8A (left branch) -->
  <path d="M350 720 V740 H350 V760" class="arrow"/>
  <!-- 7 → 8B (right branch) -->
  <path d="M870 720 V740 H950 V760" class="arrow"/>
  <!-- 8A → 9 -->
  <path d="M350 930 V970" class="arrow"/>
  <!-- 8B → 9 (right-down-left to classify) -->
  <path d="M950 930 V950 H350 V970" class="arrow-branch"/>
  <!-- 8B → 10 -->
  <path d="M950 930 V970" class="arrow"/>
  <!-- 9 → 11 -->
  <path d="M350 1130 V1160 H610 V1180" class="arrow"/>
  <!-- 10 → 11 -->
  <path d="M950 1130 V1160 H610 V1180" class="arrow"/>

  <!-- ============================================================== -->
  <!-- LEGEND  (top-right corner of the canvas)                        -->
  <!-- ============================================================== -->

</svg>
"""


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    output_path = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else script_dir / "Rheology_analysis_pipeline.svg"
    )
    output_path.write_text(SVG_CONTENT, encoding="utf-8")
    print(f"SVG generated at: {output_path}")


if __name__ == "__main__":
    main()

/** Pastel RPM colors for live rotational-drag plot only (summary/history keep this.palette). */
const LIVE_RPM_PASTEL_PALETTE = [
    "#8ab4f8", "#fdd663", "#81c995", "#f6aea9",
    "#c58af9", "#78d9ec", "#aecbfa", "#ceead6",
    "#ffe082", "#b39ddb", "#80cbc4", "#efa17c",
];

const LIVE_PLOT_BELOW_FILL = "#f6aea9";
const LIVE_PLOT_BELOW_LINE = "#e57373";

/** Mode-aware protocol steps and compact orchestration flow (see ORCHESTRATION_SCENARIO.md). */
const PROTOCOL_DEFINITIONS = {
    idle: {
        badge: "Idle",
        badgeClass: "mode-idle",
        steps: [{ id: "idle", label: "Standby" }],
        flow: [{ id: "idle", short: "Idle" }],
        stepToFlow: { idle: "idle" },
    },
    regular: {
        badge: "Regular",
        badgeClass: "",
        steps: [
            { id: "init", label: "Initialize hardware" },
            { id: "move", label: "Move to cell" },
            { id: "zero", label: "Auto-zero viscometer" },
            { id: "measure", label: "Z-descent & measure" },
            { id: "retract", label: "Retract to safe Z" },
            { id: "wash_after", label: "Washing after cell" },
            { id: "wash1_travel", label: "Wash Station 1 — travel" },
            { id: "wash1_scrub", label: "Wash Station 1 — scrub" },
            { id: "wash1_drain", label: "Wash Station 1 — drain" },
            { id: "wash2_travel", label: "Wash Station 2 — travel" },
            { id: "wash2_scrub", label: "Wash Station 2 — scrub / dry" },
            { id: "save", label: "Save results" },
            { id: "cleanup", label: "Cleanup & homing" },
            { id: "done", label: "Run complete" },
        ],
        flow: [
            { id: "init", short: "Init" },
            { id: "move", short: "Move" },
            { id: "zero", short: "Zero" },
            { id: "measure", short: "Measure" },
            { id: "retract", short: "Retract" },
            { id: "wash1", short: "WS1" },
            { id: "wash2", short: "WS2" },
            { id: "save", short: "Save" },
        ],
        stepToFlow: {
            init: "init",
            move: "move",
            zero: "zero",
            measure: "measure",
            retract: "retract",
            wash_after: "wash1",
            wash1_travel: "wash1",
            wash1_scrub: "wash1",
            wash1_drain: "wash1",
            wash2_travel: "wash2",
            wash2_scrub: "wash2",
            save: "save",
            cleanup: "save",
            done: "save",
        },
    },
    calibration: {
        badge: "Calibration",
        badgeClass: "mode-calibration",
        steps: [
            { id: "init", label: "Initialize hardware" },
            { id: "move", label: "Move to cell" },
            { id: "zero", label: "Auto-zero viscometer" },
            { id: "measure", label: "Z-descent & hitpoint hunt" },
            { id: "review", label: "Review calibration data" },
            { id: "save", label: "Save calibration" },
            { id: "cleanup", label: "Cleanup & homing" },
            { id: "done", label: "Run complete" },
        ],
        flow: [
            { id: "init", short: "Init" },
            { id: "move", short: "Move" },
            { id: "zero", short: "Zero" },
            { id: "measure", short: "Measure" },
            { id: "review", short: "Review" },
            { id: "save", short: "Save" },
        ],
        stepToFlow: {
            init: "init",
            move: "move",
            zero: "zero",
            measure: "measure",
            review: "review",
            save: "save",
            cleanup: "save",
            done: "save",
        },
    },
    recalibration: {
        badge: "Recalibration",
        badgeClass: "mode-recalibration",
        steps: [
            { id: "init", label: "Initialize hardware" },
            { id: "move", label: "Move to cell" },
            { id: "zero", label: "Auto-zero viscometer" },
            { id: "measure", label: "Z-descent & hitpoint hunt" },
            { id: "review", label: "Review recalibration data" },
            { id: "save", label: "Save recalibration" },
            { id: "cleanup", label: "Cleanup & homing" },
            { id: "done", label: "Run complete" },
        ],
        flow: [
            { id: "init", short: "Init" },
            { id: "move", short: "Move" },
            { id: "zero", short: "Zero" },
            { id: "measure", short: "Measure" },
            { id: "review", short: "Review" },
            { id: "save", short: "Save" },
        ],
        stepToFlow: {
            init: "init",
            move: "move",
            zero: "zero",
            measure: "measure",
            review: "review",
            save: "save",
            cleanup: "save",
            done: "save",
        },
    },
    discovery: {
        badge: "Discovery",
        badgeClass: "mode-discovery",
        steps: [
            { id: "init", label: "Initialize hardware" },
            { id: "move", label: "Move to cell" },
            { id: "zero", label: "Auto-zero viscometer" },
            { id: "discovery_rpm", label: "RPM discovery probes" },
            { id: "measure", label: "Z-descent & measure" },
            { id: "retract", label: "Retract to safe Z" },
            { id: "wash_after", label: "Washing after cell" },
            { id: "save", label: "Save results" },
            { id: "cleanup", label: "Cleanup & homing" },
            { id: "done", label: "Run complete" },
        ],
        flow: [
            { id: "init", short: "Init" },
            { id: "discovery_rpm", short: "RPM" },
            { id: "measure", short: "Measure" },
            { id: "wash1", short: "WS1" },
            { id: "wash2", short: "WS2" },
            { id: "save", short: "Save" },
        ],
        stepToFlow: {
            init: "init",
            move: "move",
            zero: "zero",
            discovery_rpm: "discovery_rpm",
            measure: "measure",
            retract: "retract",
            wash_after: "wash1",
            wash1_travel: "wash1",
            wash1_scrub: "wash1",
            wash1_drain: "wash1",
            wash2_travel: "wash2",
            wash2_scrub: "wash2",
            save: "save",
            cleanup: "save",
            done: "save",
        },
    },
};

/** Ordered rules: first match wins. Tests receive normalized lowercase message. */
const PROTOCOL_STATUS_RULES = [
    { id: "idle", test: (m) => /ready - configure|start cancelled|configure the run/.test(m) },
    { id: "done", test: (m) => /experiment completed|review calibration data — save/.test(m) },
    { id: "cleanup", test: (m) => /cleaning up|cleanup:|stop requested — retract|cleanup: homing|experiment interrupted/.test(m) },
    { id: "save", test: (m) => /saving final|run finished — review/.test(m) },
    { id: "review", test: (m) => /review calibration|save or discard each cell/.test(m) },
    { id: "wash2_scrub", test: (m) => /wash station 2: scrub|drying station: scrub|motor 2/.test(m) && !/travelling/.test(m) },
    { id: "wash2_travel", test: (m) => /wash station 2: travel|drying station: travel/.test(m) },
    { id: "wash1_drain", test: (m) => /wash station 1: drain/.test(m) },
    { id: "wash1_scrub", test: (m) => /wash station 1: scrub/.test(m) },
    { id: "wash1_travel", test: (m) => /wash station 1: travel/.test(m) },
    { id: "wash_after", test: (m) => /washing after cell/.test(m) },
    { id: "retract", test: (m) => /retracting to safe|cnc retract|wash skipped/.test(m) },
    { id: "discovery_rpm", test: (m) => /discovery:/.test(m) },
    { id: "measure", test: (m) => /measuring at|testing cell|calibrating cell|recalibrating|terminated early|hit-point|hit point|surface detected|z-step|descending z/.test(m) },
    { id: "zero", test: (m) => /auto-zero|zeroing viscometer/.test(m) },
    { id: "move", test: (m) => /moving to cell/.test(m) },
    { id: "init", test: (m) => /initializing hardware|initializing cnc|initializing viscometer|initializing esp32/.test(m) },
];

class ViscometryDashboard {
    constructor() {
        this.platform = {
            width: 450,
            height: 400,
            cells: [],
            washStations: []
        };

        this.socket = null;
        this.isConnected = false;
        this.isRunning = false;
        this.currentCell = null;
        this.currentRPM = 0;
        this.currentTorquePercent = 0;
        this.currentMeasuringZ = null;
        this.position = { x: 0, y: 0, z: 0 };
        this.statusLog = [];
        this.measurements = [];
        this.measurementsByCell = new Map();
        this.latestTorqueByCell = new Map();
        this.measuredCells = new Set();
        this.completedCells = new Set();
        this.washingCell = null;
        this._pendingCompletedCell = null;
        this.plannedCells = [];
        this.cellStates = new Map();
        this.hitPoints = new Map();
        this.selectedGraphCell = null;
        this.zLatestOnly = false;
        this.zConnectDots = false;
        this.zCalConnectDots = false;
        this.zDiscoveryConnectDots = false;
        this.zDiscoveryLatestOnly = false;
        this.selectedCalGraphCell = null;
        this.selectedDiscoveryGraphCell = null;
        this.activeTabId = "layout-tab";
        this._preCalibrationSettingsSnapshot = null;
        this._wasCalibrationLikeRun = false;
        this.currentPhase = 0;
        this.protocolRunMode = "idle";
        this.protocolCurrentStepId = "idle";
        this.protocolLastStatusMessage = "";
        this._protocolRenderedMode = null;
        this.gaugeDisplayRPM = 0;
        this.gaugeAnimationFrame = null;
        this.zPlotInitialized = false;
        this.torquePlotInitialized = false;
        this.calDragPlotInitialized = false;
        this.discoveryDragPlotInitialized = false;
        this.dwellPlotInitialized = false;
        this.charts = { drag: null, torque: null, calDrag: null, discoveryDrag: null, dwell: null };
        this.dwellSeriesByCell = new Map();
        this.dwellZVisibility = new Map();
        this.runSaveAllSampleData = false;
        this._mapVisualCache = new Map();
        this._stationActive = null;
        this._mapVisualSyncTimer = null;
        this._renderPaused = false;
        this._liveChartsDirty = false;
        this._dwellChartsDirty = false;
        this._dwellPlotRefreshTimer = null;
        this._mapVisualsDirty = false;
        this.timerInterval = null;
        this.experimentStart = null;
        this.cellStart = null;
        this.pendingRender = false;
        this.disconnectedBannerTimeout = null;
        this.statusError = false;
        this.sparklineData = [];
        this.uiState = "idle";
        this.experimentHistory = [];
        this.selectedExperimentId = null;
        this.selectedLoadExperimentId = null;
        this.runMeasurementStartIndex = 0;
        this.lastRunStartTsSec = null;
        this.completedSaveLock = false;
        this.summaryPlotInitialized = false;
        this._summaryHistoryPollIntervalId = null;
        this._summaryHistoryPollMs = 8000;
        /** Debounce heavy Plotly / table DOM work during streaming measurements (remote viewers). */
        this._plotRefreshTimer = null;
        this._calPlotRefreshTimer = null;
        this._discoveryPlotRefreshTimer = null;
        this._stateResyncIntervalId = null;
        this._stateResyncInflight = false;
        this._tableRefreshTimer = null;
        this._graphTabIdsKey = "";
        this.isSavingFinalResults = false;
        this.cellRpmMap = {};   // { cellId (number): [rpm, ...] }
        this.cellContentMap = {}; // { cellId (number): "sample label" }
        this.discoveryEtaGuessMap = {}; // { cellId: viscosity cP or null }
        this.discoveryContentMap = {};
        this.discoveryModeActive = false;
        this.discoveryResultsByCell = {};
        /** Converged discovery RPM per cell; survives partial ladder/probing updates during Z-scan. */
        this.discoveryConvergedRpmByCell = {};
        this.discoveryConfig = null;
        this.latestControlSettings = {};
        /** Settings frozen at run start for experiment history (avoids stale latestControlSettings). */
        this.runSettingsSnapshot = null;
        this.predictedViscosityData = {};
        this.predictedViscositySummaryKey = "__summary__";
        this.viscosityPredictionMode = "off";
        this.calibrationSummary = { is_calibrated: false, cell_count: 0, cells: {}, calibrated_at: null };
        this.calibrationPanelOpen = false;
        this.calChecksComplete = false;
        this.isCalibrationRun = false;
        this.testingDeviceStates = {
            washing_rotor: "idle",
            drying_rotor: "idle",
            filling_pump: "idle",
            draining_pump: "idle",
        };
        this.testingRequestInFlight = new Set();
        this.testingGateInProgress = false;
        this.testingBackendBusy = false;
        this.testingSessionConnected = false;
        this.testingSessionLastError = null;
        this.manualTerminateQueued = false;
        this.cellTerminationReasons = new Map();
        /** @type {Map<number, Map<string, string>>} cellId -> rpmKey -> active|dropped */
        this.rpmTorqueStatusByCell = new Map();

        this.palette = [
            "#5EA1FF", "#F5A623", "#39C5BB", "#2EA043", "#E25A5A", "#9BB5FF",
            "#B6E388", "#FFC47E", "#8FDDE5", "#EA9CB9", "#B9A0FF", "#8FD66B",
            "#73B0F9", "#FFD36A", "#69D5C7", "#86E0A8", "#EFA17C", "#BFC7D5"
        ];

    this.calibrationModeActive = false;  // Server's calibration mode state (persists across page reloads)
    this.recalibrationModeActive = false;
    this.recalibrationTargetCount = 0;
        this.calibrationReviewSession = null;
        this.calibrationReviewActiveCellId = null;
        this.calibrationReviewPending = false;
        this.calibrationReviewPlotState = { initialized: false, layout: null };
        this.calibrationReviewDecisionInFlight = false;
        this.calibrationReviewCommitInFlight = false;
        this.experimentReviewSession = null;
        this.experimentReviewActiveCellId = null;
        this.experimentReviewPending = false;
        this.experimentReviewPlotState = { initialized: false, layout: null };
        this.experimentReviewDecisionInFlight = false;
        this.experimentReviewCommitInFlight = false;

        this.initElements();
        this.bindUI();
        this.handleLogoFallback();
        this.initStaticLayout();
        this.initPlot();
        this.initGauge();
        this.initSummaryPlot();
        this.startTimerLoop();
        this.fetchInitialData();
        this.loadControlSettings();
        this.rebuildCellRpmTable();
        this.rebuildCellContentTable();
        this.rebuildDiscoveryEtaTable();
        this.rebuildDiscoveryContentTable();
        this.fetchDiscoveryConfig();
        this.loadExperimentHistory();

        // Restore active tab from localStorage
        let activeTab = localStorage.getItem("activeTab") || "layout-tab";
        if (activeTab === "data-tab") {
            activeTab = "data-processing-tab";
        }
        this.switchTab(activeTab);
        this.connectSocket();
        this.startStateResyncLoop();
    }

    initElements() {
        this.el = {
            body: document.body,
            disconnectBanner: document.getElementById("disconnect-banner"),
            runPill: document.getElementById("run-pill"),
            connectionDot: document.getElementById("connection-dot"),
            completionChip: document.getElementById("completion-chip"),
            completionBar: document.getElementById("completion-bar"),
            completionText: document.getElementById("completion-text"),
            experimentCompleteBanner: document.getElementById("experiment-complete-banner"),
            experimentTerminatedBanner: document.getElementById("experiment-terminated-banner"),
            experimentNamePromptBackdrop: document.getElementById("experiment-name-prompt-backdrop"),
            experimentNamePromptInput: document.getElementById("experiment-name-prompt-input"),
            experimentNamePromptProceed: document.getElementById("experiment-name-prompt-proceed"),
            experimentNamePromptContinue: document.getElementById("experiment-name-prompt-continue"),
            map: document.getElementById("platform-map"),
            armDot: document.getElementById("arm-dot"),
            protocolModeBadge: document.getElementById("protocol-mode-badge"),
            protocolCurrentStep: document.getElementById("protocol-current-step"),
            protocolStepList: document.getElementById("protocol-step-list"),
            protocolFlowchart: document.getElementById("protocol-flowchart"),
            protocolProgressFill: document.getElementById("protocol-progress-fill"),
            summaryPredictedViscosity: document.getElementById("summary-predicted-viscosity"),
            statusLog: document.getElementById("status-log"),
            zSparklinePlot: document.getElementById("z-sparkline-plot"),
            zSparklineCanvas: document.getElementById("z-sparkline-canvas"),
            zSparklineEmpty: document.getElementById("z-sparkline-empty"),
            torqueZPlot: document.getElementById("torque-z-plot"),
            torqueZCanvas: document.getElementById("torque-z-canvas"),
            torqueZEmpty: document.getElementById("torque-z-empty"),
            graphCellTabs: document.getElementById("graph-cell-tabs"),
            experimentName: document.getElementById("experiment-name"),
            testingMode: document.getElementById("testing-mode"),
            testRpms: document.getElementById("test-rpms"),
            selectedRows: document.getElementById("selected-rows"),
            selectedCells: document.getElementById("selected-cells"),
            cellRpmPanel: document.getElementById("cell-rpm-panel"),
            cellRpmTable: document.getElementById("cell-rpm-table"),
            cellContentPanel: document.getElementById("cell-content-panel"),
            cellContentTable: document.getElementById("cell-content-table"),
            zStepSize: document.getElementById("z-step-size"),
            measurementDuration: document.getElementById("measurement-duration"),
            sampleInterval: document.getElementById("sample-interval"),
            dwellSeconds: document.getElementById("dwell-seconds"),
            interRpmPause: document.getElementById("inter-rpm-pause"),
            torqueBreakThreshold: document.getElementById("torque-break-threshold"),
            feedbackEnabled: document.getElementById("feedback-control-enabled"),
            smartEarlyExitEnabled: document.getElementById("smart-early-exit-enabled"),
            failSafeEnabled: document.getElementById("fail-safe-enabled"),
            smartCvThreshold: document.getElementById("smart-cv-threshold"),
            smartWindowSize: document.getElementById("smart-window-size"),
            lowTorqueLiquidContactSkipEnabled: document.getElementById("low-torque-liquid-contact-skip-enabled"),
            lowTorqueLiquidContactThresholdPct: document.getElementById("low-torque-liquid-contact-threshold-pct"),
            viscosityPredictionToggleRow: document.getElementById("viscosity-prediction-toggle-row"),
            viscosityPredictionEnabled: document.getElementById("viscosity-prediction-enabled"),
            saveAllSampleData: document.getElementById("save-all-sample-data"),
            zStartOffsetRow: document.getElementById("z-start-offset-row"),
            zStartOffsetMm: document.getElementById("z-start-offset-mm"),
            controlsChartsDwellRow: document.getElementById("controls-charts-dwell-row"),
            dwellTimeDragCard: document.getElementById("dwell-time-drag-card"),
            dwellTimeCanvas: document.getElementById("dwell-time-canvas"),
            dwellTimeEmpty: document.getElementById("dwell-time-empty"),
            dwellZSections: document.getElementById("dwell-z-sections"),
            dwellTimeCellLabel: document.getElementById("dwell-time-cell-label"),
            predictedViscosityChartsCard: document.getElementById("predicted-viscosity-charts-card"),
            liveViscosityTableBody: document.getElementById("live-viscosity-table-body"),
            liveViscosityEmpty: document.getElementById("live-viscosity-empty"),
            predictedViscosityCharts: document.getElementById("predicted-viscosity-charts"),
            predictedViscosityChartsEmpty: document.getElementById("predicted-viscosity-charts-empty"),
            r2DragMin: document.getElementById("r2-drag-min"),
            r2CvMin: document.getElementById("r2-cv-min"),
            r2SlopeMin: document.getElementById("r2-slope-min"),
            hitPointConfidenceThreshold: document.getElementById("hit-point-confidence-threshold"),
            weight2ndDerivDrag: document.getElementById("weight-2nd-deriv-drag"),
            weight2ndDerivCv: document.getElementById("weight-2nd-deriv-cv"),
            weight2ndDerivSlope: document.getElementById("weight-2nd-deriv-slope"),
            weightR2Drag: document.getElementById("weight-r2-drag"),
            weightR2Cv: document.getElementById("weight-r2-cv"),
            weightR2Slope: document.getElementById("weight-r2-slope"),
            baselineNCalibration: document.getElementById("baseline-n-calibration"),
            baselineZThreshold: document.getElementById("baseline-z-threshold"),
            applySettings: document.getElementById("apply-settings"),
            startRun: document.getElementById("start-run"),
            stopRun: document.getElementById("stop-run"),
            terminateCurrentCell: document.getElementById("terminate-current-cell"),
            controlStatus: document.getElementById("control-status"),
            cellFlip: document.getElementById("cell-flip"),
            cellMeta: document.getElementById("cell-meta"),
            gaugeValue: document.getElementById("gauge-value"),
            gaugeNeedle: document.getElementById("gauge-needle"),
            gaugeText: document.getElementById("gauge-rpm"),
            calGaugeValue: document.getElementById("cal-gauge-value"),
            calGaugeNeedle: document.getElementById("cal-gauge-needle"),
            calGaugeText: document.getElementById("cal-gauge-rpm"),
            xyzX: document.getElementById("xyz-x"),
            xyzY: document.getElementById("xyz-y"),
            xyzZ: document.getElementById("xyz-z"),
            torqueFill: document.getElementById("torque-fill"),
            torqueValue: document.getElementById("torque-value"),
            rotationalDragDisplay: document.getElementById("rotational-drag-display"),
            dragLiveBox: document.getElementById("drag-live-box"),
            zMeasuringDisplay: document.getElementById("z-measuring-display"),
            calZMeasuringDisplay: document.getElementById("cal-z-measuring-display"),
            sidebarRpm: document.getElementById("sidebar-rpm"),
            sidebarSecondDerivDrag: document.getElementById("sidebar-2nd-deriv-drag"),
            sidebarSecondDerivCv: document.getElementById("sidebar-2nd-deriv-cv"),
            sidebarSecondDerivSlope: document.getElementById("sidebar-2nd-deriv-slope"),
            sidebarR2Drag: document.getElementById("sidebar-r2-drag"),
            sidebarR2Cv: document.getElementById("sidebar-r2-cv"),
            sidebarR2Slope: document.getElementById("sidebar-r2-slope"),
            sidebarMethod2ndDerivDrag: document.getElementById("sidebar-method-2nd-deriv-drag"),
            sidebarMethod2ndDerivCv: document.getElementById("sidebar-method-2nd-deriv-cv"),
            sidebarMethod2ndDerivSlope: document.getElementById("sidebar-method-2nd-deriv-slope"),
            sidebarMethodR2Drag: document.getElementById("sidebar-method-r2-drag"),
            sidebarMethodR2Cv: document.getElementById("sidebar-method-r2-cv"),
            sidebarMethodR2Slope: document.getElementById("sidebar-method-r2-slope"),
            sidebarConfidence: document.getElementById("sidebar-confidence"),
            sidebarFailSafe: document.getElementById("sidebar-fail-safe"),
            sidebarHit: document.getElementById("sidebar-hit"),
            dragZRpmLegend: document.getElementById("drag-z-rpm-legend"),
            dragZRpmLegendNote: document.getElementById("drag-z-rpm-legend-note"),
            elapsed: document.getElementById("elapsed"),
            elapsedCell: document.getElementById("elapsed-cell"),
            calElapsed: document.getElementById("cal-elapsed"),
            calElapsedCell: document.getElementById("cal-elapsed-cell"),
            tableBody: document.getElementById("measurement-table"),
            zFilterAll: document.getElementById("z-filter-all"),
            zFilterLatest: document.getElementById("z-filter-latest"),
            zConnectDots: document.getElementById("z-connect-dots"),
            liveTerminationPill: document.getElementById("live-termination-pill"),
            exportTable: document.getElementById("table-export"),
            themeToggle: document.getElementById("theme-toggle"),
            cncStatus: document.getElementById("cnc-status"),
            viscometerStatus: document.getElementById("viscometer-status"),
            pumpStatus: document.getElementById("pump-status"),
            summaryCards: document.getElementById("experiment-cards"),
            summaryEmpty: document.getElementById("summary-empty"),
            summaryDetail: document.getElementById("summary-detail"),
            summaryMetaLeft: document.getElementById("summary-meta-left"),
            summaryMetaRight: document.getElementById("summary-meta-right"),
            summaryDownload: document.getElementById("summary-download"),
            summaryAlignHitpoint: document.getElementById("summary-align-hitpoint"),
            summaryPlot: document.getElementById("summary-plot"),
            tabButtons: document.querySelectorAll(".tab-button"),
            tabPanels: document.querySelectorAll(".tab-panel"),
            testingTabButton: document.getElementById("testing-tab-button"),
            testingRunLockPill: document.getElementById("testing-run-lock-pill"),
            testingActionButtons: document.querySelectorAll(".testing-action-btn"),
            testingDevices: document.querySelectorAll(".testing-device"),
            testingStatusWashingRotor: document.getElementById("testing-status-washing-rotor"),
            testingStatusDryingRotor: document.getElementById("testing-status-drying-rotor"),
            testingStatusFillingPump: document.getElementById("testing-status-filling-pump"),
            testingStatusDrainingPump: document.getElementById("testing-status-draining-pump"),
            calibrateTabButton: document.getElementById("calibrate-tab-button"),
            controlsTabButton: document.getElementById("controls-tab-button"),
            discoveryTabButton: document.getElementById("discovery-tab-button"),
            discoveryExperimentName: document.getElementById("discovery-experiment-name"),
            discoverySelectedCells: document.getElementById("discovery-selected-cells"),
            discoveryEtaTable: document.getElementById("discovery-eta-table"),
            discoveryContentTable: document.getElementById("discovery-content-table"),
            discoveryCellValidation: document.getElementById("discovery-cell-validation"),
            discoveryCalibrationPill: document.getElementById("discovery-calibration-pill"),
            discoveryCalibrationStatusText: document.getElementById("discovery-calibration-status-text"),
            discoveryApplySettings: document.getElementById("discovery-apply-settings"),
            discoveryStartRun: document.getElementById("discovery-start-run"),
            discoveryStopRun: document.getElementById("discovery-stop-run"),
            discoveryTerminateCurrentCell: document.getElementById("discovery-terminate-current-cell"),
            discoveryControlStatus: document.getElementById("discovery-control-status"),
            discoveryProbeTableBody: document.getElementById("discovery-probe-table-body"),
            discoveryProbeEmpty: document.getElementById("discovery-probe-empty"),
            discoveryStatusPill: document.getElementById("discovery-status-pill"),
            discoveryStatusCell: document.getElementById("discovery-status-cell"),
            discoveryStatusRpm: document.getElementById("discovery-status-rpm"),
            discoveryStatusEta: document.getElementById("discovery-status-eta"),
            discoveryStatusNProbe: document.getElementById("discovery-status-n-probe"),
            discoveryStatusLanding: document.getElementById("discovery-status-landing"),
            discoveryZStartOffsetRow: document.getElementById("discovery-z-start-offset-row"),
            discoveryZStartOffsetMm: document.getElementById("discovery-z-start-offset-mm"),
            discoveryGaugeValue: document.getElementById("discovery-gauge-value"),
            discoveryGaugeNeedle: document.getElementById("discovery-gauge-needle"),
            discoveryGaugeText: document.getElementById("discovery-gauge-rpm"),
            discoveryZMeasuringDisplay: document.getElementById("discovery-z-measuring-display"),
            discoveryElapsed: document.getElementById("discovery-elapsed"),
            discoveryElapsedCell: document.getElementById("discovery-elapsed-cell"),
            discoveryZSparklineCanvas: document.getElementById("discovery-z-sparkline-canvas"),
            discoveryZSparklineEmpty: document.getElementById("discovery-z-sparkline-empty"),
            discoveryZConnectDots: document.getElementById("discovery-z-connect-dots"),
            discoveryZFilterAll: document.getElementById("discovery-z-filter-all"),
            discoveryZFilterLatest: document.getElementById("discovery-z-filter-latest"),
            discoveryGraphCellTabs: document.getElementById("discovery-graph-cell-tabs"),
            discoveryDragZRpmLegend: document.getElementById("discovery-drag-z-rpm-legend"),
            discoveryDragZRpmLegendNote: document.getElementById("discovery-drag-z-rpm-legend-note"),
            discoveryDragZCellLabel: document.getElementById("discovery-drag-z-cell-label"),
            discoverySidebarRpm: document.getElementById("discovery-sidebar-rpm"),
            discoverySidebarSecondDerivDrag: document.getElementById("discovery-sidebar-2nd-deriv-drag"),
            discoverySidebarSecondDerivCv: document.getElementById("discovery-sidebar-2nd-deriv-cv"),
            discoverySidebarSecondDerivSlope: document.getElementById("discovery-sidebar-2nd-deriv-slope"),
            discoverySidebarR2Drag: document.getElementById("discovery-sidebar-r2-drag"),
            discoverySidebarR2Cv: document.getElementById("discovery-sidebar-r2-cv"),
            discoverySidebarR2Slope: document.getElementById("discovery-sidebar-r2-slope"),
            discoverySidebarMethod2ndDerivDrag: document.getElementById("discovery-sidebar-method-2nd-deriv-drag"),
            discoverySidebarMethod2ndDerivCv: document.getElementById("discovery-sidebar-method-2nd-deriv-cv"),
            discoverySidebarMethod2ndDerivSlope: document.getElementById("discovery-sidebar-method-2nd-deriv-slope"),
            discoverySidebarMethodR2Drag: document.getElementById("discovery-sidebar-method-r2-drag"),
            discoverySidebarMethodR2Cv: document.getElementById("discovery-sidebar-method-r2-cv"),
            discoverySidebarMethodR2Slope: document.getElementById("discovery-sidebar-method-r2-slope"),
            discoverySidebarConfidence: document.getElementById("discovery-sidebar-confidence"),
            discoverySidebarFailSafe: document.getElementById("discovery-sidebar-fail-safe"),
            discoverySidebarHit: document.getElementById("discovery-sidebar-hit"),
            calibrationCellsStatusPill: document.getElementById("calibration-cells-status-pill"),
            calibrationCellsStatusText: document.getElementById("calibration-cells-status-text"),
            calPanelSection: document.getElementById("calibration-panel-section"),
            calStatusPill: document.getElementById("cal-status-pill"),
            calStatusText: document.getElementById("cal-status-text"),
            calPanelBody: document.getElementById("cal-panel-body"),
            calCheckEmpty: document.getElementById("cal-check-empty"),
            calZSparklineCanvas: document.getElementById("cal-z-sparkline-canvas"),
            calZSparklineEmpty: document.getElementById("cal-z-sparkline-empty"),
            calZConnectDots: document.getElementById("cal-z-connect-dots"),
            calGraphCellTabs: document.getElementById("cal-graph-cell-tabs"),
            calDragZRpmLegend: document.getElementById("cal-drag-z-rpm-legend"),
            calDragZCellLabel: document.getElementById("cal-drag-z-cell-label"),
            calApplyZStep: document.getElementById("cal-apply-z-step"),
            calApplyRpm: document.getElementById("cal-apply-rpm"),
            calApplyDuration: document.getElementById("cal-apply-duration"),
            calApplyInterval: document.getElementById("cal-apply-interval"),
            calApplyAll: document.getElementById("cal-apply-all-recommended"),
            calExistingInfo: document.getElementById("cal-existing-info"),
            calExistingEmpty: document.getElementById("cal-existing-empty"),
            calExistingContent: document.getElementById("cal-existing-content"),
            calExistingSelect: document.getElementById("cal-existing-select"),
            calExistingDetail: document.getElementById("cal-existing-detail"),
            calClearBtn: document.getElementById("cal-clear-btn"),
            calStartBtn: document.getElementById("cal-start-btn"),
            calStartRecalibrationBtn: document.getElementById("cal-start-recalibration-btn"),
            calStopBtn: document.getElementById("cal-stop-btn"),
            calTerminateCurrentCell: document.getElementById("cal-terminate-current-cell"),
            calRecalibrateIndividual: document.getElementById("cal-recalibrate-individual"),
            calRecalibrationIgnoreMaxZ: document.getElementById("cal-recalibration-ignore-max-z"),
            calCellSelectorContainer: document.getElementById("cal-cell-selector-container"),
            calCellChecks: document.querySelectorAll(".cal-cell-check"),
            calCellZInputs: document.getElementById("cal-cell-z-inputs"),
            calActionHint: document.getElementById("cal-action-hint"),
            loadOldExperimentDetails: document.getElementById("load-old-experiment-details"),
            loadOldExperimentList: document.getElementById("load-old-experiment-list"),
            loadOldExperimentBtn: document.getElementById("load-old-experiment-btn"),
            loadOldExperimentStatus: document.getElementById("load-old-experiment-status"),
            calReviewBackdrop: document.getElementById("calibration-review-backdrop"),
            calReviewModal: document.getElementById("calibration-review-modal"),
            calReviewTabs: document.getElementById("calibration-review-tabs"),
            calReviewPlot: document.getElementById("calibration-review-plot"),
            calReviewSummary: document.getElementById("calibration-review-summary"),
            calReviewSave: document.getElementById("calibration-review-save"),
            calReviewDiscard: document.getElementById("calibration-review-discard"),
            expReviewBackdrop: document.getElementById("experiment-review-backdrop"),
            expReviewModal: document.getElementById("experiment-review-modal"),
            expReviewTitle: document.getElementById("experiment-review-title"),
            expReviewSubtitle: document.getElementById("experiment-review-subtitle"),
            expReviewTabs: document.getElementById("experiment-review-tabs"),
            expReviewPlot: document.getElementById("experiment-review-plot"),
            expReviewSummary: document.getElementById("experiment-review-summary"),
            expReviewSave: document.getElementById("experiment-review-save"),
            expReviewDiscard: document.getElementById("experiment-review-discard"),
            calSavedBackdrop: document.getElementById("calibration-saved-backdrop"),
            calSavedBody: document.getElementById("calibration-saved-body"),
            calSavedClose: document.getElementById("calibration-saved-close"),
            calSavedOk: document.getElementById("calibration-saved-ok"),
            expSavedBackdrop: document.getElementById("experiment-saved-backdrop"),
            expSavedBody: document.getElementById("experiment-saved-body"),
            expSavedClose: document.getElementById("experiment-saved-close"),
            expSavedOk: document.getElementById("experiment-saved-ok"),
        };
    }

    bindUI() {
        if (this.el.exportTable) {
            this.el.exportTable.addEventListener("click", () => this.exportCSV());
        }
        if (this.el.viscosityPredictionEnabled) {
            this.el.viscosityPredictionEnabled.addEventListener("change", () => {
                const mode = this.el.viscosityPredictionEnabled.checked ? "on" : "off";
                this._setViscosityPredictionModeUI(mode);
                this._updatePredictedViscosityChartsCardVisibility(mode !== "off");
                this.applyControlSettings(true);
            });
        }
        if (this.el.saveAllSampleData) {
            this.el.saveAllSampleData.addEventListener("change", () => {
                this._updateSaveAllSampleDataUI(Boolean(this.el.saveAllSampleData.checked));
                this.applyControlSettings(true);
            });
        }
        this.el.applySettings.addEventListener("click", () => this.applyControlSettings());
        if (this.el.loadOldExperimentBtn) {
            this.el.loadOldExperimentBtn.addEventListener("click", () => {
                this.loadSelectedExperimentIntoDesign();
            });
        }
        if (this.el.loadOldExperimentDetails) {
            this.el.loadOldExperimentDetails.addEventListener("toggle", () => {
                if (this.el.loadOldExperimentDetails.open) {
                    this.loadExperimentHistory();
                }
            });
        }
        this.el.startRun.addEventListener("click", () => this.startRunFromUI());
        this.el.stopRun.addEventListener("click", () => this.stopRunFromUI());
        if (this.el.terminateCurrentCell) {
            this.el.terminateCurrentCell.addEventListener("click", () => this.terminateCurrentCellFromUI());
        }
        if (this.el.discoveryApplySettings) {
            this.el.discoveryApplySettings.addEventListener("click", () => this.applyDiscoverySettings());
        }
        if (this.el.discoveryStartRun) {
            this.el.discoveryStartRun.addEventListener("click", () => this.startDiscoveryRunFromUI());
        }
        if (this.el.discoveryStopRun) {
            this.el.discoveryStopRun.addEventListener("click", () => this.stopRunFromUI());
        }
        if (this.el.discoveryTerminateCurrentCell) {
            this.el.discoveryTerminateCurrentCell.addEventListener("click", () => this.terminateCurrentCellFromUI());
        }
        if (this.el.discoverySelectedCells) {
            this.el.discoverySelectedCells.addEventListener("input", () => {
                this.validateDiscoveryCells();
                this.rebuildDiscoveryEtaTable();
                this.rebuildDiscoveryContentTable();
            });
        }
        if (this.el.themeToggle) {
            this.el.themeToggle.addEventListener("click", () => this.toggleTheme());
        }
        if (this.el.zFilterAll) {
            this.el.zFilterAll.addEventListener("click", () => {
                this.zLatestOnly = false;
                this.updateZFilterButtons();
                this.refreshLivePlots();
            });
        }
        if (this.el.zFilterLatest) {
            this.el.zFilterLatest.addEventListener("click", () => {
                this.zLatestOnly = true;
                this.updateZFilterButtons();
                this.refreshLivePlots();
            });
        }
        if (this.el.zConnectDots) {
            this.el.zConnectDots.addEventListener("click", () => {
                this.zConnectDots = !this.zConnectDots;
                this.el.zConnectDots.textContent = `Connect Dots: ${this.zConnectDots ? "On" : "Off"}`;
                this.el.zConnectDots.classList.toggle("dots-on", this.zConnectDots);
                this.refreshLivePlots();
            });
        }
        if (this.el.summaryDownload) {
            this.el.summaryDownload.addEventListener("click", () => this.downloadSelectedCSV());
        }
        if (this.el.summaryAlignHitpoint) {
            this.el.summaryAlignHitpoint.addEventListener("change", () => {
                if (this.selectedExperimentId) this.selectExperiment(this.selectedExperimentId);
            });
        }

        document.addEventListener("keydown", (event) => {
            if (event.key.toLowerCase() === "e") {
                this.exportCSV();
            }
        });

        window.addEventListener("resize", () => this.handleWindowResize());

        document.addEventListener("visibilitychange", () => this.handleVisibilityChange());

        const settingsForm = document.getElementById("run-settings-form");
        if (settingsForm) {
            settingsForm.addEventListener("input", () => {
                if (!this.isRunning && this.uiState === "ready") {
                    this.setUiState("idle");
                }
            });
        }
        if (this.el.lowTorqueLiquidContactThresholdPct) {
            this.el.lowTorqueLiquidContactThresholdPct.addEventListener("input", () => {
                this._schedulePlotRefresh();
            });
        }

        // Rebuild cell-RPM table when mode or cell list changes
        if (this.el.testingMode) {
            this.el.testingMode.addEventListener("change", () => {
                this.rebuildCellRpmTable();
                this.rebuildCellContentTable();
            });
        }
        if (this.el.selectedCells) {
            this.el.selectedCells.addEventListener("input", () => {
                this.rebuildCellRpmTable();
                this.rebuildCellContentTable();
            });
        }

        // Tab switching functionality
        this.el.tabButtons.forEach(button => {
            button.addEventListener("click", () => this.switchTab(button.dataset.tab));
        });

        document.querySelectorAll(".btn, .seg").forEach((btn) => {
            btn.addEventListener("pointerdown", () => {
                btn.classList.add("btn-pressed");
                setTimeout(() => btn.classList.remove("btn-pressed"), 200);
            });
        });

        if (this.el.calZConnectDots) {
            this.el.calZConnectDots.addEventListener("click", () => {
                this.zCalConnectDots = !this.zCalConnectDots;
                this.el.calZConnectDots.textContent = `Connect Dots: ${this.zCalConnectDots ? "On" : "Off"}`;
                this.el.calZConnectDots.classList.toggle("dots-on", this.zCalConnectDots);
                this.refreshCalibrationLivePlots();
            });
        }
        if (this.el.discoveryZConnectDots) {
            this.el.discoveryZConnectDots.addEventListener("click", () => {
                this.zDiscoveryConnectDots = !this.zDiscoveryConnectDots;
                this.el.discoveryZConnectDots.textContent = `Connect Dots: ${this.zDiscoveryConnectDots ? "On" : "Off"}`;
                this.el.discoveryZConnectDots.classList.toggle("dots-on", this.zDiscoveryConnectDots);
                this.refreshDiscoveryLivePlots();
            });
        }
        if (this.el.discoveryZFilterAll) {
            this.el.discoveryZFilterAll.addEventListener("click", () => {
                this.zDiscoveryLatestOnly = false;
                this.updateDiscoveryZFilterButtons();
                this.refreshDiscoveryLivePlots();
            });
        }
        if (this.el.discoveryZFilterLatest) {
            this.el.discoveryZFilterLatest.addEventListener("click", () => {
                this.zDiscoveryLatestOnly = true;
                this.updateDiscoveryZFilterButtons();
                this.refreshDiscoveryLivePlots();
            });
        }

        if (this.el.calCheckEmpty) {
            this.el.calCheckEmpty.addEventListener("change", () => this.validateCalibrationChecklist());
        }

        if (this.el.experimentNamePromptProceed) {
            this.el.experimentNamePromptProceed.addEventListener("click", () => {
                this._onExperimentNamePromptProceed();
            });
        }
        if (this.el.experimentNamePromptContinue) {
            this.el.experimentNamePromptContinue.addEventListener("click", () => {
                this._closeExperimentNamePromptModal();
                this._startRegularRunAfterNameCheck();
            });
        }
        if (this.el.experimentNamePromptInput) {
            this.el.experimentNamePromptInput.addEventListener("input", () => {
                this._updateExperimentNamePromptProceedState();
            });
        }

        // Apply recommended settings buttons
        if (this.el.calApplyZStep) {
            this.el.calApplyZStep.addEventListener("click", () => {
                if (this.el.zStepSize) this.el.zStepSize.value = "-0.02";
                this.setUiState("idle");
            });
        }
        if (this.el.calApplyRpm) {
            this.el.calApplyRpm.addEventListener("click", () => {
                if (this.el.testRpms) this.el.testRpms.value = "1";
                this.setUiState("idle");
            });
        }
        if (this.el.calApplyDuration) {
            this.el.calApplyDuration.addEventListener("click", () => {
                if (this.el.measurementDuration) this.el.measurementDuration.value = "6";
                this.setUiState("idle");
            });
        }
        if (this.el.calApplyInterval) {
            this.el.calApplyInterval.addEventListener("click", () => {
                if (this.el.sampleInterval) this.el.sampleInterval.value = "3";
                this.setUiState("idle");
            });
        }
        if (this.el.calApplyAll) {
            this.el.calApplyAll.addEventListener("click", () => {
                if (this.el.zStepSize) this.el.zStepSize.value = "-0.02";
                if (this.el.testRpms) this.el.testRpms.value = "1";
                if (this.el.measurementDuration) this.el.measurementDuration.value = "6";
                if (this.el.sampleInterval) this.el.sampleInterval.value = "3";
                this.setUiState("idle");
            });
        }

        // Clear calibration data
        if (this.el.calClearBtn) {
            this.el.calClearBtn.addEventListener("click", () => {
                if (!confirm("Clear all per-cell Z-height calibration data?")) return;
                fetch("/api/calibration/clear", { method: "POST" })
                    .then((r) => r.json())
                    .then(() => {
                        this.calibrationSummary = { is_calibrated: false, cell_count: 0, cells: {}, calibrated_at: null };
                        this.applyCalibrationStatus(this.calibrationSummary);
                        this.pushStatusMessage("Calibration data cleared");
                    })
                    .catch(() => this.pushStatusMessage("Failed to clear calibration data"));
            });
        }
        if (this.el.calExistingSelect) {
            this.el.calExistingSelect.addEventListener("change", () => this.renderSelectedCalibrationCellDetail());
        }

        // Start calibration run
        if (this.el.calStartBtn) {
            this.el.calStartBtn.addEventListener("click", () => this.startCalibrationRun());
        }

        // Recalibrate individual cells toggle
        if (this.el.calRecalibrateIndividual) {
            this.el.calRecalibrateIndividual.addEventListener("change", () => {
                this.handleRecalibrateToggle();
            });
        }

        // Cell checkboxes for recalibration
        if (this.el.calCellChecks) {
            this.el.calCellChecks.forEach((checkbox) => {
                checkbox.addEventListener("change", () => {
                    this.updateRecalibrationCellInputs();
                    this.updateRecalibrationButtonState();
                });
            });
        }

        // Start recalibration run
        if (this.el.calStartRecalibrationBtn) {
            this.el.calStartRecalibrationBtn.addEventListener("click", () => this.startRecalibrationRun());
        }
        if (this.el.calStopBtn) {
            this.el.calStopBtn.addEventListener("click", () => this.stopCalibrationFromUI());
        }
        if (this.el.calTerminateCurrentCell) {
            this.el.calTerminateCurrentCell.addEventListener("click", () => this.terminateCalibrationCellFromUI());
        }

        if (this.el.calReviewSave) {
            this.el.calReviewSave.addEventListener("click", () => this.onCalibrationReviewSave());
        }
        if (this.el.calReviewDiscard) {
            this.el.calReviewDiscard.addEventListener("click", () => this.onCalibrationReviewDiscard());
        }
        if (this.el.expReviewSave) {
            this.el.expReviewSave.addEventListener("click", () => this.onExperimentReviewSave());
        }
        if (this.el.expReviewDiscard) {
            this.el.expReviewDiscard.addEventListener("click", () => this.onExperimentReviewDiscard());
        }
        if (this.el.calSavedClose) {
            this.el.calSavedClose.addEventListener("click", () => this.hideCalibrationSavedModal());
        }
        if (this.el.calSavedOk) {
            this.el.calSavedOk.addEventListener("click", () => this.hideCalibrationSavedModal());
        }
        if (this.el.expSavedClose) {
            this.el.expSavedClose.addEventListener("click", () => this.hideExperimentSavedModal());
        }
        if (this.el.expSavedOk) {
            this.el.expSavedOk.addEventListener("click", () => this.hideExperimentSavedModal());
        }
        this.updateRunControlButtons();
        this.bindTestingControls();
    }

    switchTab(tabId, options = {}) {
        const force = Boolean(options.force);
        if (!force && tabId === "testing-tab" && this.isRunning) {
            this.pushStatusMessage("Testing is disabled while a viscometry run is active");
            return;
        }
        if (!force && tabId === "controls-tab" && this._isPerformExperimentTabLocked()) {
            this.pushStatusMessage("Perform Experiment is disabled during calibration or recalibration");
            return;
        }
        if (!force && tabId === "calibrate-tab" && this._isCalibrateTabLocked()) {
            this.pushStatusMessage("Calibrate is disabled during an active experiment run");
            return;
        }
        if (!force && tabId === "discovery-tab" && this._isDiscoveryTabLocked()) {
            this.pushStatusMessage("Discovery is only available during Discovery Mode runs");
            return;
        }
        // Remove active class from all buttons and panels
        this.el.tabButtons.forEach(button => button.classList.remove("active"));
        this.el.tabPanels.forEach(panel => panel.classList.remove("active"));

        // Add active class to selected button and panel
        const activeButton = document.querySelector(`[data-tab="${tabId}"]`);
        const activePanel = document.getElementById(tabId);

        if (activeButton && activePanel) {
            activeButton.classList.add("active");
            activePanel.classList.add("active");
        }

        this.activeTabId = tabId;
        // Store active tab in localStorage
        localStorage.setItem("activeTab", tabId);

        if (this.el.body) {
            this.el.body.classList.toggle("discovery-active", tabId === "discovery-tab");
        }

        this._cancelInactivePlotTimers(tabId);

        if (tabId === "summary-tab") {
            this.startSummaryHistoryPolling();
        } else {
            this.stopSummaryHistoryPolling();
        }
        if (tabId === "testing-tab") {
            this.fetchTestingStatus();
        }
        if (tabId === "layout-tab") {
            this.applyArmPosition();
            this.syncMapVisuals({ force: true });
            this._mapVisualsDirty = false;
        } else if (tabId === "calibrate-tab") {
            this.updateCalGraphCellTabs();
            this.refreshCalibrationLivePlots({ force: true });
            this.updateGauge(this.currentRPM, { force: true });
        } else if (tabId === "controls-tab") {
            this.refreshLivePlots({ force: true });
            this.refreshDwellTimePlot({ force: true });
            this.renderLiveViscosityPredictionsTable();
            this.updateGauge(this.currentRPM, { force: true });
        } else if (tabId === "discovery-tab") {
            this.validateDiscoveryCells();
            this.rebuildDiscoveryEtaTable();
            this.rebuildDiscoveryContentTable();
            this.updateDiscoveryZStartOffsetAvailability();
            this.fetchDiscoveryConfig();
            if (this.charts.discoveryDrag) {
                this.charts.discoveryDrag.resize();
            }
            this.refreshDiscoveryLivePlots({ force: true });
            this.updateDiscoveryGraphCellTabs();
            this.updateGauge(this.currentRPM, { force: true });
        }
        if (this._liveChartsDirty) {
            this._refreshActiveTabCharts({ force: true });
            this._liveChartsDirty = false;
        }
    }

    _isCalibrationLikeProtocolMode() {
        const mode = this.getProtocolRunMode();
        return mode === "calibration" || mode === "recalibration";
    }

    _isPerformExperimentTabLocked() {
        return this.isRunning && (
            this._isCalibrationLikeProtocolMode()
            || this.getProtocolRunMode() === "discovery"
        );
    }

    _isCalibrateTabLocked() {
        const mode = this.getProtocolRunMode();
        return this.isRunning && (mode === "regular" || mode === "discovery");
    }

    _isDiscoveryTabLocked() {
        return this.isRunning && !this._isDiscoveryRunActive();
    }

    _isDiscoveryRunActive() {
        return this.isRunning && this.getProtocolRunMode() === "discovery";
    }

    _chartTabForFamily(family) {
        if (family === "perform") {
            return "controls-tab";
        }
        if (family === "calibration") {
            return "calibrate-tab";
        }
        if (family === "discovery") {
            return "discovery-tab";
        }
        return null;
    }

    _shouldRefreshChartFamily(family, { force = false } = {}) {
        if (force) {
            return true;
        }
        return this.activeTabId === this._chartTabForFamily(family);
    }

    _shouldRefreshLiveCharts(options = {}) {
        return this._shouldRefreshChartFamily("perform", options);
    }

    _shouldRefreshCalibrationCharts(options = {}) {
        return this._shouldRefreshChartFamily("calibration", options);
    }

    _discoveryLivePlottingEnabled(options = {}) {
        if (options.force) {
            return true;
        }
        if (this._isDiscoveryTabLocked()) {
            return false;
        }
        return this.activeTabId === "discovery-tab";
    }

    _shouldSyncMapVisuals() {
        return this.activeTabId === "layout-tab";
    }

    _cancelPerformPlotRefresh() {
        if (this._plotRefreshTimer) {
            window.clearTimeout(this._plotRefreshTimer);
            this._plotRefreshTimer = null;
        }
        if (this._dwellPlotRefreshTimer) {
            window.clearTimeout(this._dwellPlotRefreshTimer);
            this._dwellPlotRefreshTimer = null;
        }
    }

    _cancelCalibrationPlotRefresh() {
        if (this._calPlotRefreshTimer) {
            window.clearTimeout(this._calPlotRefreshTimer);
            this._calPlotRefreshTimer = null;
        }
    }

    _cancelDiscoveryPlotRefresh() {
        if (this._discoveryPlotRefreshTimer) {
            window.clearTimeout(this._discoveryPlotRefreshTimer);
            this._discoveryPlotRefreshTimer = null;
        }
    }

    _cancelInactivePlotTimers(activeTabId) {
        if (activeTabId !== "controls-tab") {
            this._cancelPerformPlotRefresh();
        }
        if (activeTabId !== "calibrate-tab") {
            this._cancelCalibrationPlotRefresh();
        }
        if (activeTabId !== "discovery-tab") {
            this._cancelDiscoveryPlotRefresh();
        }
    }

    _refreshActiveTabCharts(options = {}) {
        if (this.activeTabId === "controls-tab") {
            this.refreshLivePlots(options);
            this.refreshDwellTimePlot(options);
        } else if (this.activeTabId === "calibrate-tab") {
            this.refreshCalibrationLivePlots(options);
        } else if (this.activeTabId === "discovery-tab") {
            this.refreshDiscoveryLivePlots(options);
        }
    }

    _resizeActiveTabCharts() {
        if (this.activeTabId === "controls-tab") {
            if (this.charts.drag) {
                this.charts.drag.resize();
            }
            if (this.charts.torque) {
                this.charts.torque.resize();
            }
            if (this.charts.dwell) {
                this.charts.dwell.resize();
            }
        } else if (this.activeTabId === "calibrate-tab") {
            if (this.charts.calDrag) {
                this.charts.calDrag.resize();
            }
        } else if (this.activeTabId === "discovery-tab") {
            if (this.charts.discoveryDrag) {
                this.charts.discoveryDrag.resize();
            }
        }
    }

    updateRunTabAvailability() {
        const performLocked = this._isPerformExperimentTabLocked();
        const calibrateLocked = this._isCalibrateTabLocked();
        const discoveryLocked = this._isDiscoveryTabLocked();
        if (this.el.controlsTabButton) {
            this.el.controlsTabButton.classList.toggle("is-disabled", performLocked);
            this.el.controlsTabButton.disabled = performLocked;
        }
        if (this.el.calibrateTabButton) {
            this.el.calibrateTabButton.classList.toggle("is-disabled", calibrateLocked);
            this.el.calibrateTabButton.disabled = calibrateLocked;
        }
        if (this.el.discoveryTabButton) {
            this.el.discoveryTabButton.classList.toggle("is-disabled", discoveryLocked);
            this.el.discoveryTabButton.disabled = discoveryLocked;
        }
        if (discoveryLocked) {
            this._cancelDiscoveryPlotRefresh();
        }
        if (performLocked && this.activeTabId === "controls-tab") {
            this.switchTab("calibrate-tab", { force: true });
        } else if (discoveryLocked && this.activeTabId === "discovery-tab") {
            const mode = this.getProtocolRunMode();
            if (mode === "regular") {
                this.switchTab("controls-tab", { force: true });
            } else {
                this.switchTab("calibrate-tab", { force: true });
            }
        } else if (calibrateLocked && this.activeTabId === "calibrate-tab") {
            const mode = this.getProtocolRunMode();
            if (mode === "discovery") {
                this.switchTab("discovery-tab", { force: true });
            } else {
                this.switchTab("controls-tab", { force: true });
            }
        }
    }

    startSummaryHistoryPolling() {
        if (this._summaryHistoryPollIntervalId) {
            return;
        }
        this._summaryHistoryPollIntervalId = window.setInterval(() => {
            this.pollExperimentHistoryWhileSummaryOpen();
        }, this._summaryHistoryPollMs);
        this.pollExperimentHistoryWhileSummaryOpen();
    }

    stopSummaryHistoryPolling() {
        if (!this._summaryHistoryPollIntervalId) {
            return;
        }
        window.clearInterval(this._summaryHistoryPollIntervalId);
        this._summaryHistoryPollIntervalId = null;
    }

    pollExperimentHistoryWhileSummaryOpen() {
        if (!this.selectedExperimentId) {
            return;
        }
        if (!this.el.summaryDetail || this.el.summaryDetail.classList.contains("hidden")) {
            return;
        }

        const selectedId = this.selectedExperimentId;
        const prevJson = JSON.stringify(this.experimentHistory.find((e) => e.id === selectedId));

        fetch("/api/experiment_history")
            .then((r) => r.json())
            .then((history) => {
                if (!Array.isArray(history)) return;
                const nextExp = history.find((e) => e.id === selectedId);
                if (!nextExp) return;
                const nextJson = JSON.stringify(nextExp);
                if (nextJson === prevJson) {
                    return;
                }
                this.experimentHistory = history;
                this.renderExperimentCards();
                this.selectExperiment(selectedId);
            })
            .catch(() => {});
    }

    handleLogoFallback() {
        const logo = document.getElementById("ac-logo");
        const fallback = document.getElementById("logo-fallback");
        logo.addEventListener("error", () => {
            logo.classList.add("hidden");
            fallback.classList.remove("hidden");
        });
    }

    initStaticLayout() {
        this.platform.cells = this.buildCells();
        this.platform.washStations = [
            { id: "W1", x: 27, y: 86 },
            { id: "W2", x: 42, y: 86 }
        ];

        this.platform.cells.forEach((cell) => {
            this.cellStates.set(cell.id, "pending");
        });

        this.renderMap();
        this.setUiState("idle");
        this.updateCompletionChip();
        this.updateZFilterButtons();
        this.updateDiscoveryZFilterButtons();
        this.renderProtocolUI();
    }

    buildCells() {
        const cells = [];
        for (let r = 1; r <= 6; r += 1) {
            cells.push({ id: r, label: `Cell ${r}`, col: 2, row: r });
        }
        for (let r = 1; r <= 6; r += 1) {
            cells.push({ id: 6 + r, label: `Cell ${6 + r}`, col: 3, row: r });
        }
        for (let r = 1; r <= 6; r += 1) {
            cells.push({ id: 12 + r, label: `Cell ${12 + r}`, col: 6, row: r });
        }
        return cells;
    }

    mmToPct(x, y) {
        return {
            x: (x / this.platform.width) * 100,
            y: (y / this.platform.height) * 100
        };
    }

    renderMap() {
        const body = document.getElementById("platform-grid-body");
        if (!body) {
            return;
        }
        body.innerHTML = "";

        const occupied = new Map();
        this.platform.cells.forEach((cell) => {
            occupied.set(`${cell.col}-${cell.row}`, { type: "cell", cell });
        });
        occupied.set("7-1", { type: "station", id: "WASH", label: "WASH" });
        occupied.set("7-2", { type: "station", id: "DRY", label: "DRY" });

        for (let row = 1; row <= 7; row += 1) {
            for (let col = 1; col <= 8; col += 1) {
                const key = `${col}-${row}`;
                const slot = occupied.get(key);
                const node = document.createElement("div");

                if (!slot) {
                    node.className = "pg-empty";
                } else if (slot.type === "station") {
                    node.className = "pg-station";
                    node.id = `station-${slot.id}`;
                    node.dataset.station = slot.id;
                    node.textContent = slot.label;
                } else {
                    const cell = slot.cell;
                    const state = this.cellStates.get(cell.id) || "pending";
                    node.className = `pg-cell state-${state}`;
                    node.id = `cell-node-${cell.id}`;
                    node.dataset.cellId = String(cell.id);
                    node.textContent = cell.label;

                    const torque = this.latestTorqueByCell?.get(cell.id);
                    if (torque !== undefined) {
                        node.title = `${cell.label} - last torque ${torque.toFixed(2)}%`;
                    }
                }

                body.appendChild(node);
            }
        }

        this.applyArmPosition();
        this._resetMapVisualCache();
        this.syncMapVisuals({ force: true });
    }

    updateCellNode(cellId, state, title) {
        const node = document.getElementById(`cell-node-${cellId}`);
        if (!node) {
            return;
        }
        const resolvedState = state || this.cellStates.get(cellId) || "pending";
        node.className = `pg-cell state-${resolvedState}`;
        if (title !== undefined) {
            node.title = title;
        }
    }

    _resolveMapVisualContext() {
        const statusLower = (this.statusLog[0] || "").toLowerCase();
        const hasErrorStatus = statusLower.includes("error") || statusLower.includes("fail") || statusLower.includes("critical");
        let activeStation = null;
        if (statusLower.includes("wash station 1") || statusLower.includes("motor 1") || statusLower.includes("pump 1")) {
            activeStation = "WASH";
        } else if (statusLower.includes("wash station 2") || statusLower.includes("motor 2") || statusLower.includes("pump 2")) {
            activeStation = "DRY";
        }

        const desiredStates = new Map();
        this.platform.cells.forEach((cell) => {
            let state = this.cellStates.get(cell.id) || "pending";

            if (this.currentCell === cell.id && hasErrorStatus) {
                state = "error";
            } else if (this.currentCell === cell.id && this.currentRPM > 0) {
                state = "measuring";
            } else if (this.currentCell === cell.id && this.currentRPM === 0) {
                state = "active";
            } else if (this.washingCell === cell.id) {
                state = "washing";
            } else if (this.completedCells.has(cell.id)) {
                state = "completed";
            }

            this.cellStates.set(cell.id, state);
            desiredStates.set(cell.id, state);
        });

        return { desiredStates, activeStation };
    }

    _cellMapTitle(cell) {
        const torque = this.latestTorqueByCell?.get(cell.id);
        if (torque !== undefined) {
            return `${cell.label} - last torque ${torque.toFixed(2)}%`;
        }
        return cell.label;
    }

    _resetMapVisualCache() {
        this._mapVisualCache.clear();
        this._stationActive = null;
    }

    _scheduleMapVisualSync() {
        if (!this._shouldSyncMapVisuals()) {
            this._mapVisualsDirty = true;
            return;
        }
        if (this._mapVisualSyncTimer) {
            window.clearTimeout(this._mapVisualSyncTimer);
        }
        this._mapVisualSyncTimer = window.setTimeout(() => {
            this._mapVisualSyncTimer = null;
            this.syncMapVisuals();
        }, 200);
    }

    syncMapVisuals({ force = false } = {}) {
        if (this._renderPaused && !force) {
            this._mapVisualsDirty = true;
            return;
        }

        const { desiredStates, activeStation } = this._resolveMapVisualContext();

        this.platform.cells.forEach((cell) => {
            const state = desiredStates.get(cell.id) || "pending";
            const title = this._cellMapTitle(cell);
            const cached = this._mapVisualCache.get(cell.id);
            if (!cached || cached.state !== state || cached.title !== title) {
                this.updateCellNode(cell.id, state, title);
                this._mapVisualCache.set(cell.id, { state, title });
            }
        });

        if (this._stationActive !== activeStation) {
            ["WASH", "DRY"].forEach((id) => {
                const node = document.getElementById(`station-${id}`);
                if (!node) {
                    return;
                }
                node.classList.toggle("station-active", activeStation === id);
            });
            this._stationActive = activeStation;
        }

        this._mapVisualsDirty = false;
    }

    applyArmPosition() {
        const xPct = (this.position.x / 450) * 100;
        const yPct = (this.position.y / 400) * 100;
        if (this.el.armDot) {
            this.el.armDot.style.left = `${xPct}%`;
            this.el.armDot.style.top = `${yPct}%`;
        }
    }

    _buildLivePlotLayout({ yTitle, xReversed = false, showLegend = false }) {
        const plotFont = '"DM Sans", -apple-system, BlinkMacSystemFont, sans-serif';
        const plotText = "rgb(72, 84, 110)";
        const axisTitleFont = { family: plotFont, size: 12, color: plotText };
        const axisTickFont = { family: plotFont, size: 11, color: plotText };
        const axisStyle = {
            gridcolor: "rgba(180, 200, 230, 0.45)",
            linecolor: "rgba(150, 175, 215, 0.60)",
            tickcolor: "rgb(138, 150, 175)",
            zeroline: false,
            tickfont: axisTickFont,
        };
        const layout = {
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            font: { family: plotFont, color: plotText, size: 12 },
            xaxis: {
                ...axisStyle,
                title: { text: "Z-Height (mm)", standoff: 8, font: axisTitleFont },
                autorange: xReversed ? "reversed" : true,
            },
            yaxis: {
                ...axisStyle,
                title: { text: yTitle, standoff: 10, font: axisTitleFont },
            },
            margin: { t: 16, r: 16, b: 48, l: 62 },
            showlegend: false,
        };
        if (showLegend) {
            layout.legend = {
                bgcolor: "rgba(0,0,0,0)",
                bordercolor: "rgba(150, 175, 215, 0.60)",
                font: { family: plotFont, size: 11, color: plotText },
            };
        }
        return layout;
    }

    _shadeHexColor(hex, factor = 0.82) {
        if (!hex || typeof hex !== "string" || !hex.startsWith("#")) {
            return hex;
        }
        const raw = hex.slice(1);
        const full = raw.length === 3
            ? raw.split("").map((c) => c + c).join("")
            : raw.slice(0, 6);
        const clamp = (v) => Math.max(0, Math.min(255, Math.round(v)));
        const r = clamp(parseInt(full.slice(0, 2), 16) * factor);
        const g = clamp(parseInt(full.slice(2, 4), 16) * factor);
        const b = clamp(parseInt(full.slice(4, 6), 16) * factor);
        return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
    }

    initPlot() {
        this.initLiveCharts();
    }

    _getLiveChartTheme() {
        const isDark = this.el?.body?.classList?.contains("theme-dark");
        return {
            text: isDark ? "rgb(200, 210, 230)" : "rgb(72, 84, 110)",
            grid: isDark ? "rgba(120, 140, 180, 0.35)" : "rgba(180, 200, 230, 0.45)",
            tick: isDark ? "rgb(160, 170, 190)" : "rgb(138, 150, 175)",
            border: isDark ? "rgba(120, 140, 180, 0.50)" : "rgba(150, 175, 215, 0.60)",
        };
    }

    _buildLiveChartOptions({ yTitle, theme, isDragChart }) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 0 },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: () => "",
                        label: (context) => {
                            const rpmLabel = context.dataset.label || "";
                            const point = context.raw;
                            const lines = [rpmLabel, `Z ${Number(point.x).toFixed(3)} mm`];
                            if (isDragChart) {
                                lines.push(`Drag ${Number(point.y).toFixed(4)}`);
                                if (point.torque != null) {
                                    lines.push(`Torque ${Number(point.torque).toFixed(2)}%`);
                                }
                            } else {
                                lines.push(`Torque ${Number(point.y).toFixed(2)}%`);
                            }
                            return lines;
                        },
                    },
                },
            },
            scales: {
                x: {
                    type: "linear",
                    title: {
                        display: true,
                        text: "Z-Height (mm)",
                        color: theme.text,
                        font: { family: '"DM Sans", sans-serif', size: 12 },
                    },
                    ticks: {
                        color: theme.tick,
                        font: { family: '"DM Sans", sans-serif', size: 11 },
                    },
                    grid: { color: theme.grid },
                    border: { color: theme.border },
                },
                y: {
                    title: {
                        display: true,
                        text: yTitle,
                        color: theme.text,
                        font: { family: '"DM Sans", sans-serif', size: 12 },
                    },
                    ticks: {
                        color: theme.tick,
                        font: { family: '"DM Sans", sans-serif', size: 11 },
                    },
                    grid: { color: theme.grid },
                    border: { color: theme.border },
                },
            },
        };
    }

    initLiveCharts() {
        if (typeof Chart === "undefined") {
            console.warn("Chart.js not loaded; live charts unavailable");
            return;
        }

        const theme = this._getLiveChartTheme();

        if (this.el.zSparklineCanvas) {
            this.charts.drag = new Chart(this.el.zSparklineCanvas, {
                type: "scatter",
                data: { datasets: [] },
                options: this._buildLiveChartOptions({
                    yTitle: "Rotational Drag (torque / RPM)",
                    theme,
                    isDragChart: true,
                }),
            });
            this.zPlotInitialized = true;
        }

        if (this.el.torqueZCanvas) {
            this.charts.torque = new Chart(this.el.torqueZCanvas, {
                type: "scatter",
                data: { datasets: [] },
                options: this._buildLiveChartOptions({
                    yTitle: "Torque (%)",
                    theme,
                    isDragChart: false,
                }),
            });
            this.torquePlotInitialized = true;
        }

        if (this.el.calZSparklineCanvas) {
            this.charts.calDrag = new Chart(this.el.calZSparklineCanvas, {
                type: "scatter",
                data: { datasets: [] },
                options: this._buildLiveChartOptions({
                    yTitle: "Rotational Drag (torque / RPM)",
                    theme,
                    isDragChart: true,
                }),
            });
            this.calDragPlotInitialized = true;
        }

        if (this.el.discoveryZSparklineCanvas) {
            this.charts.discoveryDrag = new Chart(this.el.discoveryZSparklineCanvas, {
                type: "scatter",
                data: { datasets: [] },
                options: this._buildLiveChartOptions({
                    yTitle: "Rotational Drag (torque / RPM)",
                    theme,
                    isDragChart: true,
                }),
            });
            this.discoveryDragPlotInitialized = true;
        }

        if (this.el.dwellTimeCanvas) {
            this.charts.dwell = new Chart(this.el.dwellTimeCanvas, {
                type: "scatter",
                data: { datasets: [] },
                options: this._buildDwellChartOptions(theme),
            });
            this.dwellPlotInitialized = true;
        }

        this._refreshActiveTabCharts({ force: true });
    }

    updateLiveChartTheme() {
        if (!this.charts.drag && !this.charts.torque && !this.charts.calDrag && !this.charts.discoveryDrag) {
            return;
        }
        const theme = this._getLiveChartTheme();
        if (this.charts.drag) {
            this.charts.drag.options = this._buildLiveChartOptions({
                yTitle: "Rotational Drag (torque / RPM)",
                theme,
                isDragChart: true,
            });
            if (this._shouldRefreshLiveCharts()) {
                this.charts.drag.update("none");
            }
        }
        if (this.charts.torque) {
            this.charts.torque.options = this._buildLiveChartOptions({
                yTitle: "Torque (%)",
                theme,
                isDragChart: false,
            });
            if (this._shouldRefreshLiveCharts()) {
                this.charts.torque.update("none");
            }
        }
        if (this.charts.calDrag) {
            this.charts.calDrag.options = this._buildLiveChartOptions({
                yTitle: "Rotational Drag (torque / RPM)",
                theme,
                isDragChart: true,
            });
            if (this._shouldRefreshCalibrationCharts()) {
                this.charts.calDrag.update("none");
            }
        }
        if (this.charts.discoveryDrag) {
            this.charts.discoveryDrag.options = this._buildLiveChartOptions({
                yTitle: "Rotational Drag (torque / RPM)",
                theme,
                isDragChart: true,
            });
            if (this._discoveryLivePlottingEnabled()) {
                this.charts.discoveryDrag.update("none");
            }
        }
        if (this.charts.dwell) {
            this.charts.dwell.options = this._buildDwellChartOptions(theme);
            if (this._shouldRefreshLiveCharts()) {
                this.charts.dwell.update("none");
            }
        }
    }

    handleWindowResize() {
        this.applyArmPosition();
        this._resizeActiveTabCharts();
    }

    handleVisibilityChange() {
        if (document.hidden) {
            this._renderPaused = true;
            return;
        }
        this._renderPaused = false;
        if (this._liveChartsDirty) {
            this._refreshActiveTabCharts({ force: true });
        }
        if (this._dwellChartsDirty && this.activeTabId === "controls-tab") {
            this.refreshDwellTimePlot({ force: true });
        }
        if (this._mapVisualsDirty && this._shouldSyncMapVisuals()) {
            this.syncMapVisuals({ force: true });
        }
        this._liveChartsDirty = false;
        this._dwellChartsDirty = false;
        this._mapVisualsDirty = false;
    }

    initGauge() {
        const circumference = 2 * Math.PI * 72;
        this.gaugeArcLength = circumference * 0.75;
        const initGaugeArc = (gaugeValue) => {
            if (!gaugeValue) {
                return;
            }
            gaugeValue.style.strokeDasharray = `${this.gaugeArcLength} ${circumference}`;
            gaugeValue.style.strokeDashoffset = `${this.gaugeArcLength}`;
        };
        initGaugeArc(this.el.gaugeValue);
        initGaugeArc(this.el.calGaugeValue);
        initGaugeArc(this.el.discoveryGaugeValue);
        this.updateGauge(0);
    }

    startTimerLoop() {
        this.timerInterval = window.setInterval(() => {
            this.updateTimers();
        }, 1000);
    }

    fetchInitialData() {
        Promise.allSettled([
            fetch("/api/status").then((r) => r.json()),
            fetch("/api/measurement_data").then((r) => r.json()),
            fetch("/api/calibration/status").then((r) => r.json()),
            fetch("/api/predicted_viscosity").then((r) => r.json()),
            fetch("/api/testing/status").then((r) => r.json()),
        ])
            .then(([statusRes, measurementRes, calRes, predictedRes, testingRes]) => {
                const status = statusRes.status === "fulfilled" ? statusRes.value : null;
                const measurementData = measurementRes.status === "fulfilled" ? measurementRes.value : null;
                const calSummary = calRes.status === "fulfilled" ? calRes.value : null;
                const predictedViscosity = predictedRes.status === "fulfilled" ? predictedRes.value : null;
                const testingStatus = testingRes.status === "fulfilled" ? testingRes.value : null;

                if (status && typeof status === "object") {
                    this.applyStatusSnapshot(status);
                    this.applyTestingStatus(testingStatus || status.testing_status);
                    if (status.calibration_review) {
                        this.openCalibrationReview(status.calibration_review);
                    }
                    if (status.experiment_review) {
                        this.openExperimentReview(status.experiment_review);
                    }
                }
                if (Array.isArray(measurementData)) {
                    measurementData.forEach((m) => this.ingestMeasurement(m, true));
                    this._refreshActiveTabCharts({ force: true });
                }
                this._hydratePredictedViscosityFromServer(
                    predictedViscosity || status?.predicted_viscosity_results
                );
                if (calSummary && typeof calSummary === "object") {
                    this.applyCalibrationStatus(calSummary);
                }
                this.el.body.classList.remove("loading");
                if (status) {
                    this.pushStatusMessage(status.status_message || "Connected and ready");
                } else {
                    this.statusError = true;
                    this.pushStatusMessage("Status bootstrap partially failed, waiting for live socket updates");
                }
            })
            .catch(() => {
                this.statusError = true;
                this.pushStatusMessage("Status bootstrap failed, waiting for live socket updates");
            });
    }

    startStateResyncLoop() {
        if (this._stateResyncIntervalId) {
            return;
        }
        this._stateResyncIntervalId = window.setInterval(() => {
            if (this._stateResyncInflight) {
                return;
            }
            this._stateResyncInflight = true;
            fetch("/api/status")
                .then((r) => r.json())
                .then((status) => {
                    if (status && typeof status === "object") {
                        this.applyStatusSnapshot(status);
                    }
                })
                .catch(() => {})
                .finally(() => {
                    this._stateResyncInflight = false;
                });
        }, 5000);
    }

    loadControlSettings() {
        fetch("/api/control_settings")
            .then((response) => response.json())
            .then((settings) => {
                this.populateControlSettings(settings);
                this.el.body.classList.remove("loading");
            })
            .catch(() => {
                this.setControlStatus("Unable to load control settings");
            });
    }

    populateControlSettings(settings) {
        if (!settings) {
            return;
        }

        this.el.testingMode.value = settings.testing_mode || "custom";
        if (this.el.experimentName) {
            this.el.experimentName.value = settings.experiment_name || "";
        }
        this.el.testRpms.value = Array.isArray(settings.test_rpms) ? settings.test_rpms.join(", ") : "0.8";
        this.el.selectedRows.value = Array.isArray(settings.selected_rows) ? settings.selected_rows.join(", ") : "";
        this.el.selectedCells.value = Array.isArray(settings.selected_cells) ? settings.selected_cells.join(", ") : "";
        this.el.zStepSize.value = settings.z_step_size ?? -0.02;
        this.el.measurementDuration.value = settings.measurement_duration ?? 40;
        this.el.sampleInterval.value = settings.sample_interval ?? 5;
        this.el.dwellSeconds.value = settings.dwell_seconds ?? 2;
        this.el.interRpmPause.value = settings.inter_rpm_pause ?? 2;
        this.el.torqueBreakThreshold.value = settings.torque_break_threshold ?? 100;
        this.el.feedbackEnabled.checked = Boolean(settings.feedback_control_enabled);
        if (this.el.smartEarlyExitEnabled) {
            this.el.smartEarlyExitEnabled.checked = settings.smart_early_exit_enabled !== false;
        }
        if (this.el.failSafeEnabled) {
            this.el.failSafeEnabled.checked = settings.fail_safe_enabled !== false;
        }
        if (this.el.smartCvThreshold) this.el.smartCvThreshold.value = settings.smart_cv_threshold ?? 0.005;
        if (this.el.smartWindowSize) this.el.smartWindowSize.value = settings.smart_window_size ?? 3;
        if (this.el.lowTorqueLiquidContactSkipEnabled) {
            this.el.lowTorqueLiquidContactSkipEnabled.checked = settings.low_torque_liquid_contact_skip_enabled !== false;
        }
        if (this.el.lowTorqueLiquidContactThresholdPct) {
            this.el.lowTorqueLiquidContactThresholdPct.value = settings.low_torque_liquid_contact_threshold_pct ?? 25;
        }
        const mode = this._normalizeViscosityPredictionMode(
            settings.viscosity_prediction_mode,
            settings.predicted_viscosity_enabled
        );
        this._setViscosityPredictionModeUI(mode);
        this._updatePredictedViscosityChartsCardVisibility(mode !== "off");
        if (this.el.saveAllSampleData) {
            this.el.saveAllSampleData.checked = Boolean(settings.save_all_sample_data);
        }
        if (this.el.zStartOffsetMm) {
            this.el.zStartOffsetMm.value = settings.z_start_offset_mm ?? 0.4;
        }
        this._updateSaveAllSampleDataUI(Boolean(settings.save_all_sample_data));
        this.updateZStartOffsetAvailability();
        if (this.el.r2DragMin) this.el.r2DragMin.value = settings.r2_drag_min ?? 0.975;
        if (this.el.r2CvMin) this.el.r2CvMin.value = settings.r2_cv_min ?? 0.975;
        if (this.el.r2SlopeMin) this.el.r2SlopeMin.value = settings.r2_slope_min ?? 0.975;
        if (this.el.hitPointConfidenceThreshold) this.el.hitPointConfidenceThreshold.value = settings.hit_point_confidence_threshold ?? 0.8;
        if (this.el.weight2ndDerivDrag) this.el.weight2ndDerivDrag.value = settings.weight_2nd_deriv_drag ?? 0.2;
        if (this.el.weight2ndDerivCv) this.el.weight2ndDerivCv.value = settings.weight_2nd_deriv_cv ?? 0.2;
        if (this.el.weight2ndDerivSlope) this.el.weight2ndDerivSlope.value = settings.weight_2nd_deriv_slope ?? 0.2;
        if (this.el.weightR2Drag) this.el.weightR2Drag.value = settings.weight_r2_drag ?? 0.2;
        if (this.el.weightR2Cv) this.el.weightR2Cv.value = settings.weight_r2_cv ?? 0.2;
        if (this.el.weightR2Slope) this.el.weightR2Slope.value = settings.weight_r2_slope ?? 0.2;
        if (this.el.baselineNCalibration) this.el.baselineNCalibration.value = settings.baseline_n_calibration ?? 10;
        if (this.el.baselineZThreshold) this.el.baselineZThreshold.value = settings.baseline_z_threshold ?? 5;

        // Restore per-cell RPM map
        if (settings.cell_rpm_map && typeof settings.cell_rpm_map === "object") {
            this.cellRpmMap = {};
            Object.entries(settings.cell_rpm_map).forEach(([k, v]) => {
                const cellId = parseInt(k, 10);
                if (!Number.isNaN(cellId) && Array.isArray(v)) {
                    this.cellRpmMap[cellId] = v.map(Number).filter((n) => !Number.isNaN(n));
                }
            });
        }
        if (settings.cell_content_map && typeof settings.cell_content_map === "object") {
            this.cellContentMap = {};
            Object.entries(settings.cell_content_map).forEach(([k, v]) => {
                const cellId = parseInt(k, 10);
                const text = String(v ?? "").trim();
                if (!Number.isNaN(cellId) && text.length > 0) {
                    this.cellContentMap[cellId] = text;
                }
            });
        }
        this.rebuildCellRpmTable();
        this.rebuildCellContentTable();
        this._syncPlannedCells(settings);
        this.updateZStartOffsetAvailability();
        this.latestControlSettings = JSON.parse(JSON.stringify(settings));

        // Sync discovery-tab fields so settings are shared across all connected devices
        if (settings.discovery_mode_enabled) {
            if (this.el.discoveryExperimentName) {
                this.el.discoveryExperimentName.value = settings.experiment_name || "";
            }
            if (this.el.discoverySelectedCells && Array.isArray(settings.selected_cells)) {
                this.el.discoverySelectedCells.value = settings.selected_cells.join(", ");
            }
        }
        const setDiscoveryInput = (id, val) => {
            const el = document.getElementById(id);
            if (el && val != null) el.value = val;
        };
        setDiscoveryInput("discovery-z-step-size", settings.z_step_size);
        setDiscoveryInput("discovery-measurement-duration", settings.measurement_duration);
        setDiscoveryInput("discovery-sample-interval", settings.sample_interval);
        setDiscoveryInput("discovery-dwell-seconds", settings.dwell_seconds);
        setDiscoveryInput("discovery-inter-rpm-pause", settings.inter_rpm_pause);
        setDiscoveryInput("discovery-torque-break-threshold", settings.torque_break_threshold);
        setDiscoveryInput("discovery-probe-duration-s", settings.discovery_probe_duration_s);
        setDiscoveryInput("discovery-duck-torque-pct", settings.discovery_duck_torque_pct);
        setDiscoveryInput("discovery-handoff-pause-s", settings.discovery_handoff_pause_s);
        if (this.el.discoveryZStartOffsetMm && settings.z_start_offset_mm != null) {
            this.el.discoveryZStartOffsetMm.value = settings.z_start_offset_mm;
        }

        this.setControlStatus("Settings loaded");
        this.updateCompletionBar();
        this.refreshLivePlots();
    }

    rebuildCellRpmTable() {
        const panel = this.el.cellRpmPanel;
        const table = this.el.cellRpmTable;
        if (!panel || !table) return;

        const mode = this.el.testingMode ? this.el.testingMode.value : "custom";
        if (mode !== "custom") {
            panel.classList.add("hidden");
            return;
        }

        // Parse currently selected cells from the input
        const raw = this.el.selectedCells ? this.el.selectedCells.value : "";
        const cells = raw.split(",")
            .map((s) => parseInt(s.trim(), 10))
            .filter((n) => !Number.isNaN(n) && n >= 1 && n <= 18);

        if (cells.length === 0) {
            panel.classList.add("hidden");
            return;
        }

        panel.classList.remove("hidden");
        table.innerHTML = "";

        cells.forEach((cellId) => {
            const row = document.createElement("div");
            row.className = "cell-rpm-row";

            const label = document.createElement("span");
            label.className = "cell-rpm-label";
            label.textContent = `Cell ${cellId}`;

            const input = document.createElement("input");
            input.type = "text";
            input.className = "cell-rpm-input";
            input.placeholder = "e.g. 0.8, 1.0";
            input.dataset.cellId = String(cellId);

            // Restore any previously entered value
            const existing = this.cellRpmMap[cellId];
            if (existing && existing.length > 0) {
                input.value = existing.join(", ");
            }

            // Update cellRpmMap on every change
            input.addEventListener("input", () => {
                const vals = input.value.split(",")
                    .map((s) => parseFloat(s.trim()))
                    .filter((n) => !Number.isNaN(n) && n > 0);
                if (vals.length > 0) {
                    this.cellRpmMap[cellId] = vals;
                } else {
                    delete this.cellRpmMap[cellId];
                }
            });

            row.appendChild(label);
            row.appendChild(input);
            table.appendChild(row);
        });
    }

    _parseDiscoverySelectedCells() {
        const raw = this.el.discoverySelectedCells ? this.el.discoverySelectedCells.value : "";
        return raw.split(",")
            .map((s) => parseInt(s.trim(), 10))
            .filter((n) => !Number.isNaN(n) && n >= 1 && n <= 18);
    }

    _isCellCalibrated(cellId) {
        const cells = this.calibrationSummary?.cells || {};
        return Object.prototype.hasOwnProperty.call(cells, String(cellId));
    }

    validateDiscoveryCells() {
        const all = this._parseDiscoverySelectedCells();
        const valid = all.filter((id) => this._isCellCalibrated(id));
        const invalid = all.filter((id) => !this._isCellCalibrated(id));
        if (this.el.discoveryCellValidation) {
            if (invalid.length > 0) {
                this.el.discoveryCellValidation.textContent =
                    `Cells ${invalid.join(", ")} are not calibrated and cannot be used for Discovery.`;
            } else if (all.length === 0) {
                this.el.discoveryCellValidation.textContent = "Select at least one calibrated cell.";
            } else {
                this.el.discoveryCellValidation.textContent = "";
            }
        }
        if (invalid.length > 0 && this.el.discoverySelectedCells) {
            this.el.discoverySelectedCells.value = valid.join(", ");
        }
        this.updateDiscoveryZStartOffsetAvailability(valid);
        this.updateDiscoveryStartGuard(valid);
        return valid;
    }

    updateDiscoveryZStartOffsetAvailability(cellsOverride = null) {
        const cells = cellsOverride || this.validateDiscoveryCells();
        const enabled = cells.length > 0 && cells.every((id) => this._isCellCalibrated(id));
        if (this.el.discoveryZStartOffsetRow) {
            this.el.discoveryZStartOffsetRow.classList.toggle("is-disabled", !enabled);
        }
        if (this.el.discoveryZStartOffsetMm) {
            this.el.discoveryZStartOffsetMm.disabled = !enabled;
        }
    }

    updateDiscoveryStartGuard(validCells = null) {
        const cells = validCells || this.validateDiscoveryCells();
        const nameOk = Boolean((this.el.discoveryExperimentName?.value || "").trim());
        const blocked = cells.length === 0 || !nameOk;
        if (this.el.discoveryStartRun && this.uiState === "ready") {
            this.el.discoveryStartRun.disabled = blocked;
        }
    }

    rebuildDiscoveryEtaTable() {
        const table = this.el.discoveryEtaTable;
        if (!table) return;

        const cells = this._parseDiscoverySelectedCells();
        table.innerHTML = "";

        if (cells.length === 0) {
            return;
        }

        cells.forEach((cellId) => {
            const row = document.createElement("div");
            row.className = "cell-rpm-row";
            if (!this._isCellCalibrated(cellId)) {
                row.classList.add("discovery-cell-row-disabled");
            }

            const label = document.createElement("span");
            label.className = "cell-rpm-label";
            label.textContent = `Cell ${cellId}`;
            const badge = document.createElement("span");
            badge.className = `discovery-cell-badge ${this._isCellCalibrated(cellId) ? "calibrated" : "uncalibrated"}`;
            badge.textContent = this._isCellCalibrated(cellId) ? "Calibrated" : "Not calibrated";
            label.appendChild(badge);

            const input = document.createElement("input");
            input.type = "text";
            input.className = "cell-rpm-input discovery-eta-input";
            input.placeholder = "e.g. 10000 (cP)";
            input.dataset.cellId = String(cellId);
            input.disabled = !this._isCellCalibrated(cellId);

            const existing = this.discoveryEtaGuessMap[cellId];
            if (existing != null && existing > 0) {
                input.value = String(existing);
            }

            input.addEventListener("input", () => {
                const text = String(input.value || "").trim();
                if (!text) {
                    delete this.discoveryEtaGuessMap[cellId];
                    return;
                }
                const val = parseFloat(text);
                if (!Number.isNaN(val) && val > 0) {
                    this.discoveryEtaGuessMap[cellId] = val;
                } else {
                    delete this.discoveryEtaGuessMap[cellId];
                }
            });

            row.appendChild(label);
            row.appendChild(input);
            table.appendChild(row);
        });
    }

    rebuildDiscoveryContentTable() {
        const table = this.el.discoveryContentTable;
        if (!table) return;

        const cells = this._parseDiscoverySelectedCells();
        table.innerHTML = "";

        cells.forEach((cellId) => {
            const row = document.createElement("div");
            row.className = "cell-content-row";

            const label = document.createElement("span");
            label.className = "cell-content-label";
            label.textContent = `Cell ${cellId}`;

            const input = document.createElement("input");
            input.type = "text";
            input.className = "cell-content-input";
            input.placeholder = "e.g. unknown_silicone_A";
            input.dataset.cellId = String(cellId);

            const existing = this.discoveryContentMap[cellId];
            if (existing) {
                input.value = existing;
            }

            input.addEventListener("input", () => {
                const text = String(input.value || "").trim();
                if (text.length > 0) {
                    this.discoveryContentMap[cellId] = text;
                } else {
                    delete this.discoveryContentMap[cellId];
                }
            });

            row.appendChild(label);
            row.appendChild(input);
            table.appendChild(row);
        });
    }

    fetchDiscoveryConfig() {
        return fetch("/api/discovery/config")
            .then((r) => r.json())
            .then((cfg) => {
                this.discoveryConfig = cfg;
                if (this.el.discoveryZStartOffsetMm && cfg.hit_point_offset_mm != null) {
                    this.el.discoveryZStartOffsetMm.value = Number(cfg.hit_point_offset_mm).toFixed(2);
                }
                return cfg;
            })
            .catch(() => undefined);
    }

    buildDiscoveryEtaGuessMapPayload() {
        const payload = {};
        Object.entries(this.discoveryEtaGuessMap).forEach(([cellId, eta]) => {
            if (eta != null && eta > 0) {
                payload[String(cellId)] = eta;
            }
        });
        return payload;
    }

    buildDiscoveryContentMapPayload() {
        const payload = {};
        Object.entries(this.discoveryContentMap).forEach(([cellId, content]) => {
            const text = String(content || "").trim();
            if (text.length > 0) {
                payload[String(cellId)] = text;
            }
        });
        return payload;
    }

    readDiscoverySettings() {
        const parseList = (value) => value.split(",").map((item) => item.trim()).filter(Boolean);
        const getNum = (id, fallback) => {
            const el = document.getElementById(id);
            return el ? Number(el.value) : fallback;
        };
        const getBool = (id, fallback) => {
            const el = document.getElementById(id);
            return el ? Boolean(el.checked) : fallback;
        };

        return {
            experiment_name: (this.el.discoveryExperimentName?.value || "").trim(),
            testing_mode: "custom",
            selected_cells: this.validateDiscoveryCells(),
            discovery_mode_enabled: true,
            discovery_eta_guess_map: this.buildDiscoveryEtaGuessMapPayload(),
            discovery_probe_duration_s: getNum("discovery-probe-duration-s", 60),
            discovery_duck_torque_pct: getNum("discovery-duck-torque-pct", 80),
            discovery_handoff_pause_s: getNum("discovery-handoff-pause-s", 10),
            low_torque_liquid_contact_skip_enabled: false,
            z_step_size: getNum("discovery-z-step-size", -0.02),
            measurement_duration: getNum("discovery-measurement-duration", 40),
            sample_interval: getNum("discovery-sample-interval", 5),
            dwell_seconds: getNum("discovery-dwell-seconds", 2),
            inter_rpm_pause: getNum("discovery-inter-rpm-pause", 2),
            torque_break_threshold: getNum("discovery-torque-break-threshold", 100),
            smart_early_exit_enabled: getBool("discovery-smart-early-exit-enabled", true),
            fail_safe_enabled: getBool("discovery-fail-safe-enabled", true),
            feedback_control_enabled: getBool("discovery-feedback-control-enabled", true),
            viscosity_prediction_mode: getBool("discovery-viscosity-prediction-enabled", false) ? "on" : "off",
            save_all_sample_data: getBool("discovery-save-all-sample-data", false),
            z_start_offset_mm: getNum("discovery-z-start-offset-mm", 0.4),
            cell_content_map: this.buildDiscoveryContentMapPayload(),
            r2_drag_min: Number(this.el.r2DragMin?.value ?? 0.975),
            r2_cv_min: Number(this.el.r2CvMin?.value ?? 0.975),
            r2_slope_min: Number(this.el.r2SlopeMin?.value ?? 0.975),
            hit_point_confidence_threshold: Number(this.el.hitPointConfidenceThreshold?.value ?? 0.8),
            weight_2nd_deriv_drag: Number(this.el.weight2ndDerivDrag?.value ?? 0.2),
            weight_2nd_deriv_cv: Number(this.el.weight2ndDerivCv?.value ?? 0.2),
            weight_2nd_deriv_slope: Number(this.el.weight2ndDerivSlope?.value ?? 0.2),
            weight_r2_drag: Number(this.el.weightR2Drag?.value ?? 0.2),
            weight_r2_cv: Number(this.el.weightR2Cv?.value ?? 0.2),
            weight_r2_slope: Number(this.el.weightR2Slope?.value ?? 0.2),
            baseline_n_calibration: Number(this.el.baselineNCalibration?.value ?? 10),
            baseline_z_threshold: Number(this.el.baselineZThreshold?.value ?? 5),
            smart_cv_threshold: Number(this.el.smartCvThreshold?.value ?? 0.005),
            smart_window_size: Number(this.el.smartWindowSize?.value ?? 3),
        };
    }

    setDiscoveryControlStatus(message) {
        if (this.el.discoveryControlStatus) {
            this.el.discoveryControlStatus.textContent = message;
        }
    }

    applyDiscoverySettings(silent = false) {
        const settings = this.readDiscoverySettings();
        return fetch("/api/control_settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(settings),
        })
            .then((response) => response.json())
            .then((saved) => {
                if (!silent) {
                    this.setDiscoveryControlStatus("Settings applied");
                }
                if (!silent && !this.isRunning) {
                    this.setUiState("ready");
                }
                this.updateDiscoveryStartGuard();
                return saved;
            })
            .catch(() => {
                this.setDiscoveryControlStatus("Failed to apply settings");
            });
    }

    startDiscoveryRunFromUI() {
        if (this.calibrationReviewPending || this.experimentReviewPending) {
            this.pushStatusMessage("Finish the data save review before starting a new run");
            return;
        }
        if (this.uiState !== "ready") {
            this.setDiscoveryControlStatus("Apply settings before starting");
            return;
        }
        const name = (this.el.discoveryExperimentName?.value || "").trim();
        if (!name) {
            this.setDiscoveryControlStatus("Experiment name is required");
            return;
        }
        const cells = this.validateDiscoveryCells();
        if (cells.length === 0) {
            this.setDiscoveryControlStatus("Select at least one calibrated cell");
            return;
        }
        this.discoveryModeActive = true;
        this.setUiState("running");
        this.applyDiscoverySettings(true)
            .then(() => {
                const settings = this.readDiscoverySettings();
                try {
                    this.runSettingsSnapshot = JSON.parse(JSON.stringify(settings));
                } catch {
                    this.runSettingsSnapshot = settings;
                }
                this._syncPlannedCells(settings);
                return fetch("/api/run/start_discovery", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(settings),
                });
            })
            .then((response) => response.json())
            .then((result) => {
                if (result.error) {
                    throw new Error(result.error);
                }
                this.setDiscoveryControlStatus("Discovery run started");
                this.discoveryModeActive = true;
            })
            .catch((err) => {
                this.discoveryModeActive = false;
                this.setUiState("ready");
                this.setDiscoveryControlStatus(err.message || "Failed to start discovery run");
            });
    }

    _formatDiscoveryLandingChip(entry) {
        const status = entry?.landing_status;
        if (!status || status === "na") {
            return { text: "N/A", cls: "discovery-landing-na" };
        }
        const tBottom = entry?.T_bottom;
        const suffix = tBottom != null ? ` (${Number(tBottom).toFixed(1)}%)` : "";
        if (status === "ok") {
            return { text: `OK${suffix}`, cls: "discovery-landing-ok" };
        }
        if (status === "high") {
            return { text: `High${suffix}`, cls: "discovery-landing-warn" };
        }
        if (status === "low") {
            return { text: `Low${suffix}`, cls: "discovery-landing-warn" };
        }
        return { text: "—", cls: "discovery-landing-na" };
    }

    _discoveryProbeRowHtml(p, idx) {
        const target = p.ladder_target_pct != null
            ? Number(p.ladder_target_pct).toFixed(0)
            : "—";
        return `<tr><td>${idx + 1}</td><td class="mono">${target}</td>`
            + `<td class="mono">${Number(p.rpm).toFixed(2)}</td>`
            + `<td class="mono">${Number(p.torque).toFixed(2)}</td>`
            + `<td class="mono">${p.eta_est != null ? Number(p.eta_est).toLocaleString(undefined, { maximumFractionDigits: 0 }) : "—"}</td></tr>`;
    }

    _buildDiscoveryStage2SummaryHtml(entry) {
        if (!entry) {
            return "";
        }
        const nProbe = entry.n_probe != null ? Number(entry.n_probe).toFixed(3) : "—";
        const path = entry.discovery_path
            ? `<span class="protocol-mode-badge mode-discovery">${this._escapeHtml(String(entry.discovery_path))}</span>`
            : "";
        const landing = this._formatDiscoveryLandingChip(entry);
        const landingHtml = `<span class="discovery-landing-chip ${landing.cls}">${this._escapeHtml(landing.text)}</span>`;
        const ladderRpms = [30, 40, 50, 60, 70].map((t) => {
            const rpm = entry[`rpm_${t}`];
            return rpm != null ? `${t}%→${Number(rpm).toFixed(2)}` : null;
        }).filter(Boolean).join(" · ");
        return `
            <div class="summary-discovery-stage2-block">
                <div><strong>Rheology</strong> ${path}</div>
                <div class="discovery-stage2-metrics">
                    <span>n<sub>probe</sub> = <span class="mono">${nProbe}</span></span>
                    <span>T<sub>top</sub> = <span class="mono">${entry.T_top != null ? Number(entry.T_top).toFixed(1) : "—"}%</span></span>
                    <span>T<sub>bottom</sub> = <span class="mono">${entry.T_bottom != null ? Number(entry.T_bottom).toFixed(1) : "—"}%</span></span>
                    <span>S = <span class="mono">${entry.S != null ? Number(entry.S).toFixed(3) : "—"}</span></span>
                    <span>Landing: ${landingHtml}</span>
                </div>
                ${ladderRpms ? `<div class="discovery-ladder-rpm-line">Ladder RPM: ${this._escapeHtml(ladderRpms)}</div>` : ""}
            </div>`;
    }

    ingestDiscoveryUpdate(payload) {
        if (!payload) return;
        const cellId = payload.cell_id != null ? Number(payload.cell_id) : null;
        if (cellId != null) {
            this.discoveryResultsByCell[String(cellId)] = payload;
            this._syncDiscoveryConvergedRpmCache(cellId, payload);
        }
        if (!this._discoveryLivePlottingEnabled()) {
            return;
        }
        const status = payload.status || "probing";
        if (this.el.discoveryStatusPill) {
            this.el.discoveryStatusPill.textContent = status;
            this.el.discoveryStatusPill.className = "discovery-status-pill";
            if (status === "converged" || status === "converged_by_stability") {
                this.el.discoveryStatusPill.classList.add("converged");
            } else if (
                status === "over_range"
                || status === "under_range"
                || status === "probe_failed"
                || status === "ladder_failed"
                || status === "ladder_over_range"
                || status === "ladder_under_range"
            ) {
                this.el.discoveryStatusPill.classList.add("failed");
            } else if (status === "probing" || status === "ladder_probing") {
                this.el.discoveryStatusPill.classList.add("probing");
            }
        }
        if (this.el.discoveryStatusCell) {
            this.el.discoveryStatusCell.textContent = payload.cell_id != null ? String(payload.cell_id) : "—";
        }
        if (this.el.discoveryStatusRpm) {
            this.el.discoveryStatusRpm.textContent = payload.rpm != null ? Number(payload.rpm).toFixed(2) : "—";
        }
        if (this.el.discoveryStatusEta) {
            this.el.discoveryStatusEta.textContent = payload.eta_estimate != null
                ? Number(payload.eta_estimate).toLocaleString(undefined, { maximumFractionDigits: 0 })
                : "—";
        }
        if (this.el.discoveryStatusNProbe) {
            this.el.discoveryStatusNProbe.textContent = payload.n_probe != null
                ? Number(payload.n_probe).toFixed(3)
                : "—";
        }
        if (this.el.discoveryStatusLanding) {
            const landing = this._formatDiscoveryLandingChip(payload);
            this.el.discoveryStatusLanding.textContent = landing.text;
            this.el.discoveryStatusLanding.className = `discovery-landing-chip ${landing.cls}`;
        }
        const probes = payload.probes || [];
        if (this.el.discoveryProbeTableBody) {
            this.el.discoveryProbeTableBody.innerHTML = probes.map((p, idx) => (
                this._discoveryProbeRowHtml(p, idx)
            )).join("");
        }
        if (this.el.discoveryProbeEmpty) {
            this.el.discoveryProbeEmpty.classList.toggle("hidden", probes.length > 0);
        }
        this.updateDiscoveryGraphCellTabs();
        this._scheduleDiscoveryPlotRefresh();
        this._refreshDiscoveryRheologyPanels();
    }

    _isDiscoveryConvergedStatus(status) {
        const normalized = String(status || "");
        return normalized === "converged" || normalized === "converged_by_stability";
    }

    _syncDiscoveryConvergedRpmCache(cellId, entry) {
        if (cellId == null || !entry || entry.rpm == null) {
            return;
        }
        if (!this._isDiscoveryConvergedStatus(entry.status)) {
            return;
        }
        const rpm = Number(entry.rpm);
        if (Number.isFinite(rpm) && rpm > 0) {
            this.discoveryConvergedRpmByCell[String(cellId)] = rpm;
        }
    }

    _hydrateDiscoveryConvergedRpmCache(results = null) {
        const source = results || this.discoveryResultsByCell || {};
        Object.entries(source).forEach(([cellKey, entry]) => {
            const cellId = Number(cellKey);
            if (Number.isFinite(cellId) && entry) {
                this._syncDiscoveryConvergedRpmCache(cellId, entry);
            }
        });
    }

    _inferDiscoveryPlotRpmFromMeasurements(cellId) {
        if (!this._isDiscoveryRunActive()) {
            return null;
        }
        const points = this.measurementsByCell.get(cellId) || [];
        if (points.length === 0) {
            return null;
        }
        const last = points[points.length - 1];
        const rpm = Number(last?.rpm);
        return Number.isFinite(rpm) && rpm > 0 ? rpm : null;
    }

    _getDiscoveredRpmForCell(cellId) {
        const key = String(cellId);
        const cached = this.discoveryConvergedRpmByCell[key];
        if (cached != null) {
            const cachedRpm = Number(cached);
            if (Number.isFinite(cachedRpm) && cachedRpm > 0) {
                return cachedRpm;
            }
        }

        const entry = this.discoveryResultsByCell[key];
        if (entry && entry.rpm != null && this._isDiscoveryConvergedStatus(entry.status)) {
            const rpm = Number(entry.rpm);
            if (Number.isFinite(rpm) && rpm > 0) {
                return rpm;
            }
        }

        return this._inferDiscoveryPlotRpmFromMeasurements(cellId);
    }

    _buildDiscoveryProbeTableHtml(probes, options = {}) {
        if (!Array.isArray(probes) || probes.length === 0) {
            return "";
        }
        const review = Boolean(options.review);
        const rows = probes.map((p, idx) => this._discoveryProbeRowHtml(p, idx)).join("");
        const tableHtml = `
            <table class="duration-table discovery-probe-table discovery-review-table">
                <thead>
                    <tr><th>#</th><th>Target %</th><th>RPM</th><th>Torque %</th><th>η est (cP)</th></tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>`;
        if (review) {
            return `<div class="discovery-review-probe-scroll">${tableHtml}</div>`;
        }
        return tableHtml;
    }

    _buildDiscoverySummaryBlockHtml(cellId, entry) {
        if (!entry || !Array.isArray(entry.probes) || entry.probes.length === 0) {
            return "";
        }
        const status = entry.status || "—";
        const rpm = entry.rpm != null ? Number(entry.rpm).toFixed(2) : "—";
        const eta = entry.eta_estimate != null
            ? Number(entry.eta_estimate).toLocaleString(undefined, { maximumFractionDigits: 0 })
            : "—";
        return `
            <div class="summary-discovery-cell-block">
                <strong>Cell ${cellId} — RPM discovery</strong>
                <div>Status: ${this._escapeHtml(String(status))} · Discovered RPM: ${rpm} · η est: ${eta} cP</div>
                ${this._buildDiscoveryStage2SummaryHtml(entry)}
                ${this._buildDiscoveryProbeTableHtml(entry.probes)}
            </div>`;
    }

    _refreshDiscoveryRheologyPanels() {
        if (!this.el.predictedViscosityCharts) {
            return;
        }
        Object.entries(this.discoveryResultsByCell || {}).forEach(([cellKey, entry]) => {
            const cellId = Number(cellKey);
            if (!Number.isFinite(cellId)) {
                return;
            }
            const wrap = this.el.predictedViscosityCharts.querySelector(`[data-pv-cell-id="${cellId}"]`);
            if (!wrap) {
                return;
            }
            let panel = wrap.querySelector(`[data-dr-panel="${cellId}"]`);
            if (!panel) {
                return;
            }
            panel.innerHTML = this._buildDiscoveryRheologyPanelInnerHtml(entry);
        });
    }

    _buildDiscoveryRheologyPanelInnerHtml(entry) {
        if (!entry || entry.n_probe == null && entry.T_top == null) {
            return `<div class="discovery-rheology-empty">No Stage 2 discovery data for this cell.</div>`;
        }
        const landing = this._formatDiscoveryLandingChip(entry);
        const rows = [
            ["n_probe", entry.n_probe != null ? Number(entry.n_probe).toFixed(3) : "—"],
            ["Newtonian", entry.is_newtonian == null ? "—" : (entry.is_newtonian ? "Yes" : "No")],
            ["T_top", entry.T_top != null ? `${Number(entry.T_top).toFixed(1)}%` : "—"],
            ["T_bottom", entry.T_bottom != null ? `${Number(entry.T_bottom).toFixed(1)}%` : "—"],
            ["S", entry.S != null ? Number(entry.S).toFixed(3) : "—"],
            ["Landing", landing.text],
        ];
        const ladderRows = [30, 40, 50, 60, 70].map((t) => {
            const rpm = entry[`rpm_${t}`];
            if (rpm == null) {
                return "";
            }
            return `<tr><td>${t}%</td><td class="mono">${Number(rpm).toFixed(2)}</td></tr>`;
        }).filter(Boolean).join("");
        return `
            <div class="discovery-rheology-title">Discovery Rheology</div>
            <table class="discovery-rheology-metrics-table">
                ${rows.map(([k, v]) => `<tr><th>${k}</th><td class="mono">${this._escapeHtml(String(v))}</td></tr>`).join("")}
            </table>
            ${ladderRows ? `<table class="discovery-rheology-ladder-table"><thead><tr><th>Target</th><th>RPM</th></tr></thead><tbody>${ladderRows}</tbody></table>` : ""}
            <div class="discovery-landing-chip ${landing.cls}">${this._escapeHtml(landing.text)}</div>`;
    }

    getActiveDiscoveryGraphCellId() {
        if (this.selectedDiscoveryGraphCell !== null) {
            return this.selectedDiscoveryGraphCell;
        }
        if (this.currentCell) {
            return this.currentCell;
        }
        const ids = this.getGraphCellIds();
        return ids.length ? ids[ids.length - 1] : null;
    }

    updateDiscoveryGraphCellTabs() {
        if (!this.el.discoveryGraphCellTabs) {
            return;
        }
        const ids = this.getGraphCellIds();
        this.el.discoveryGraphCellTabs.innerHTML = "";

        const currentBtn = document.createElement("button");
        currentBtn.className = `cell-tab${this.selectedDiscoveryGraphCell === null ? " active" : ""}`;
        currentBtn.textContent = "Current Cell";
        currentBtn.addEventListener("click", () => {
            this.selectedDiscoveryGraphCell = null;
            this.updateDiscoveryGraphCellTabs();
            this.refreshDiscoveryLivePlots();
        });
        this.el.discoveryGraphCellTabs.appendChild(currentBtn);

        ids.forEach((cellId) => {
            const btn = document.createElement("button");
            btn.className = `cell-tab${this.selectedDiscoveryGraphCell === cellId ? " active" : ""}`;
            btn.textContent = `Cell ${cellId}`;
            btn.addEventListener("click", () => {
                this.selectedDiscoveryGraphCell = cellId;
                this.updateDiscoveryGraphCellTabs();
                this.refreshDiscoveryLivePlots();
            });
            this.el.discoveryGraphCellTabs.appendChild(btn);
        });
    }

    renderDiscoveryDragZRpmLegend(cellId, orderedRpms) {
        if (!this.el.discoveryDragZRpmLegend) {
            return;
        }
        const floor = this._torqueFloorPctForLivePlots();
        if (this.el.discoveryDragZRpmLegendNote) {
            this.el.discoveryDragZRpmLegendNote.textContent =
                `Below torque floor (${floor}%): red (all RPMs)`;
        }
        this.el.discoveryDragZRpmLegend.innerHTML = orderedRpms.map((rpm) => {
            const label = Number(rpm).toFixed(2);
            const color = this.colorForRpm(rpm);
            return (
                `<div class="rpm-legend-item">`
                + `<span class="rpm-legend-swatch" style="background:${color}"></span>`
                + `<span class="rpm-legend-label">RPM ${label}</span>`
                + `</div>`
            );
        }).join("");
    }

    refreshDiscoveryLivePlots(options = {}) {
        if (!this._discoveryLivePlottingEnabled(options)) {
            if (!options.force) {
                this._liveChartsDirty = true;
            }
            return;
        }
        const activeCell = this.getActiveDiscoveryGraphCellId();
        const source = activeCell ? (this.measurementsByCell.get(activeCell) || []) : [];
        const torqueFloor = this._torqueFloorPctForLivePlots();

        let zData = source;
        if (this.zDiscoveryLatestOnly && source.length > 0) {
            const latestByHeightRpm = new Map();
            source.forEach((m) => {
                const key = `${Number(m.height).toFixed(3)}|${Number(m.rpm).toFixed(3)}`;
                const prev = latestByHeightRpm.get(key);
                if (!prev || (Number(m.timestamp) || 0) >= (Number(prev.timestamp) || 0)) {
                    latestByHeightRpm.set(key, m);
                }
            });
            zData = [...latestByHeightRpm.values()];
        }

        const orderedRpms = activeCell ? this.expandRpmsWithObserved(this.getRpmsForCell(activeCell), zData) : [];
        const buckets = this.partitionMeasurementsByRpm(zData, orderedRpms);

        const dragDatasets = orderedRpms
            .map((rpm) => {
                const key = Number(rpm).toFixed(3);
                const points = buckets.get(key) || [];
                if (points.length === 0) {
                    return null;
                }
                return this._buildDragDatasetForRpm(rpm, points, torqueFloor, orderedRpms, {
                    connectDots: this.zDiscoveryConnectDots,
                });
            })
            .filter(Boolean);

        if (this.discoveryDragPlotInitialized && this.charts.discoveryDrag) {
            this.charts.discoveryDrag.data.datasets = dragDatasets;
            if (this.el.discoveryZSparklineEmpty) {
                this.el.discoveryZSparklineEmpty.classList.toggle("hidden", dragDatasets.length > 0);
            }
            this.renderDiscoveryDragZRpmLegend(activeCell, orderedRpms);
        }
        if (this.el.discoveryDragZCellLabel) {
            this.el.discoveryDragZCellLabel.textContent = activeCell ? `Cell ${activeCell}` : "All Cells";
        }

        if (this._renderPaused) {
            this._liveChartsDirty = true;
            return;
        }

        if (this.charts.discoveryDrag) {
            this.charts.discoveryDrag.resize();
            this.charts.discoveryDrag.update("none");
        }
    }

    updateDiscoveryCalibrationPill(summary) {
        const pill = this.el.discoveryCalibrationPill;
        const text = this.el.discoveryCalibrationStatusText;
        if (!pill || !text) return;
        const count = Number(summary?.cell_count) || 0;
        text.textContent = `${count}/18 cells calibrated`;
        pill.classList.remove("cal-cells-status-all", "cal-cells-status-partial", "cal-cells-status-none");
        if (count >= 18) {
            pill.classList.add("cal-cells-status-all");
        } else if (count > 0) {
            pill.classList.add("cal-cells-status-partial");
        } else {
            pill.classList.add("cal-cells-status-none");
        }
    }

    rebuildCellContentTable() {
        const panel = this.el.cellContentPanel;
        const table = this.el.cellContentTable;
        if (!panel || !table) return;

        const mode = this.el.testingMode ? this.el.testingMode.value : "custom";
        if (mode !== "custom") {
            panel.classList.add("hidden");
            return;
        }

        const raw = this.el.selectedCells ? this.el.selectedCells.value : "";
        const cells = raw.split(",")
            .map((s) => parseInt(s.trim(), 10))
            .filter((n) => !Number.isNaN(n) && n >= 1 && n <= 18);

        if (cells.length === 0) {
            panel.classList.add("hidden");
            return;
        }

        panel.classList.remove("hidden");
        table.innerHTML = "";

        cells.forEach((cellId) => {
            const row = document.createElement("div");
            row.className = "cell-content-row";

            const label = document.createElement("span");
            label.className = "cell-content-label";
            label.textContent = `Cell ${cellId}`;

            const input = document.createElement("input");
            input.type = "text";
            input.className = "cell-content-input";
            input.placeholder = "e.g. Sample A, Buffer, Blank";
            input.dataset.cellId = String(cellId);

            const existing = this.cellContentMap[cellId];
            if (existing) {
                input.value = existing;
            }

            input.addEventListener("input", () => {
                const text = String(input.value || "").trim();
                if (text.length > 0) {
                    this.cellContentMap[cellId] = text;
                } else {
                    delete this.cellContentMap[cellId];
                }
            });

            row.appendChild(label);
            row.appendChild(input);
            table.appendChild(row);
        });
    }

    buildCellRpmMapPayload() {
        // Returns { "1": [0.8, 1.0], "7": [5.0] } with string keys for JSON safety
        const payload = {};
        Object.entries(this.cellRpmMap).forEach(([cellId, rpms]) => {
            if (Array.isArray(rpms) && rpms.length > 0) {
                payload[String(cellId)] = rpms;
            }
        });
        return payload;
    }

    buildCellContentMapPayload() {
        const payload = {};
        Object.entries(this.cellContentMap).forEach(([cellId, content]) => {
            const text = String(content || "").trim();
            if (text.length > 0) {
                payload[String(cellId)] = text;
            }
        });
        return payload;
    }

    regularRunModeClearFlags() {
        return {
            calibration_mode: false,
            recalibrate_individual_cells: false,
            recalibration_cells: {},
            recalibration_ignore_max_z_travel: false,
            discovery_mode_enabled: false,
        };
    }

    readControlSettings() {
        const parseList = (value) => value.split(",").map((item) => item.trim()).filter(Boolean);

        return {
            experiment_name: (this.el.experimentName?.value || "").trim(),
            testing_mode: this.el.testingMode.value,
            test_rpms: parseList(this.el.testRpms.value).map((value) => Number(value)).filter((value) => !Number.isNaN(value)),
            selected_rows: parseList(this.el.selectedRows.value).map((value) => Number.parseInt(value, 10)).filter((value) => !Number.isNaN(value)),
            selected_cells: parseList(this.el.selectedCells.value).map((value) => Number.parseInt(value, 10)).filter((value) => !Number.isNaN(value)),
            z_step_size: Number(this.el.zStepSize.value),
            measurement_duration: Number(this.el.measurementDuration.value),
            sample_interval: Number(this.el.sampleInterval.value),
            dwell_seconds: Number(this.el.dwellSeconds.value),
            inter_rpm_pause: Number(this.el.interRpmPause.value),
            torque_break_threshold: Number(this.el.torqueBreakThreshold.value),
            smart_early_exit_enabled: Boolean(this.el.smartEarlyExitEnabled?.checked),
            fail_safe_enabled: this.el.failSafeEnabled?.checked ?? true,
            smart_cv_threshold: Number(this.el.smartCvThreshold?.value ?? 0.005),
            smart_window_size: Number(this.el.smartWindowSize?.value ?? 3),
            low_torque_liquid_contact_skip_enabled: Boolean(this.el.lowTorqueLiquidContactSkipEnabled?.checked),
            low_torque_liquid_contact_threshold_pct: Number(this.el.lowTorqueLiquidContactThresholdPct?.value ?? 25),
            r2_drag_min: Number(this.el.r2DragMin?.value ?? 0.975),
            r2_cv_min: Number(this.el.r2CvMin?.value ?? 0.975),
            r2_slope_min: Number(this.el.r2SlopeMin?.value ?? 0.975),
            hit_point_confidence_threshold: Number(this.el.hitPointConfidenceThreshold?.value ?? 0.8),
            weight_2nd_deriv_drag: Number(this.el.weight2ndDerivDrag?.value ?? 0.2),
            weight_2nd_deriv_cv: Number(this.el.weight2ndDerivCv?.value ?? 0.2),
            weight_2nd_deriv_slope: Number(this.el.weight2ndDerivSlope?.value ?? 0.2),
            weight_r2_drag: Number(this.el.weightR2Drag?.value ?? 0.2),
            weight_r2_cv: Number(this.el.weightR2Cv?.value ?? 0.2),
            weight_r2_slope: Number(this.el.weightR2Slope?.value ?? 0.2),
            baseline_n_calibration: Number(this.el.baselineNCalibration?.value ?? 10),
            baseline_z_threshold: Number(this.el.baselineZThreshold?.value ?? 5),
            feedback_control_enabled: this.el.feedbackEnabled.checked,
            viscosity_prediction_mode: this._getViscosityPredictionMode(),
            save_all_sample_data: Boolean(this.el.saveAllSampleData?.checked),
            z_start_offset_mm: Number(this.el.zStartOffsetMm?.value ?? 0.4),
            cell_rpm_map: this.buildCellRpmMapPayload(),
            cell_content_map: this.buildCellContentMapPayload(),
        };
    }

    setControlStatus(message) {
        this.el.controlStatus.textContent = message;
    }

    applyControlSettings(silent = false) {
        const settings = this.readControlSettings();
        return fetch("/api/control_settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(settings)
        })
            .then((response) => response.json())
            .then((saved) => {
                this.populateControlSettings(saved);
                if (!silent) {
                    this.setControlStatus("Settings applied");
                }
                if (!silent && !this.isRunning) {
                    this.setUiState("ready");
                }
                return saved;
            })
            .catch((error) => {
                this.setControlStatus("Failed to apply settings");
                throw error;
            });
    }

    startRunFromUI() {
        if (this.calibrationReviewPending || this.experimentReviewPending) {
            this.pushStatusMessage("Finish the data save review before starting a new run");
            return;
        }
        if (this.uiState !== "ready") {
            this.setControlStatus("Apply settings before starting");
            return;
        }
        const name = (this.el.experimentName?.value || "").trim();
        if (!name) {
            this._openExperimentNamePromptModal();
            return;
        }
        this._startRegularRunAfterNameCheck();
    }

    _openExperimentNamePromptModal() {
        if (!this.el.experimentNamePromptBackdrop) {
            this._startRegularRunAfterNameCheck();
            return;
        }
        if (this.el.experimentNamePromptInput) {
            this.el.experimentNamePromptInput.value = "";
        }
        this._updateExperimentNamePromptProceedState();
        this.el.experimentNamePromptBackdrop.classList.remove("hidden");
        this.el.experimentNamePromptBackdrop.setAttribute("aria-hidden", "false");
        this.el.body.classList.add("experiment-name-prompt-active");
        window.setTimeout(() => this.el.experimentNamePromptInput?.focus(), 50);
    }

    _closeExperimentNamePromptModal() {
        if (this.el.experimentNamePromptBackdrop) {
            this.el.experimentNamePromptBackdrop.classList.add("hidden");
            this.el.experimentNamePromptBackdrop.setAttribute("aria-hidden", "true");
        }
        this.el.body.classList.remove("experiment-name-prompt-active");
    }

    _updateExperimentNamePromptProceedState() {
        const hasName = Boolean((this.el.experimentNamePromptInput?.value || "").trim());
        if (this.el.experimentNamePromptProceed) {
            this.el.experimentNamePromptProceed.disabled = !hasName;
        }
    }

    _onExperimentNamePromptProceed() {
        const name = (this.el.experimentNamePromptInput?.value || "").trim();
        if (!name) {
            return;
        }
        if (this.el.experimentName) {
            this.el.experimentName.value = name;
        }
        this._closeExperimentNamePromptModal();
        this._startRegularRunAfterNameCheck();
    }

    _startRegularRunAfterNameCheck() {
        this.discoveryModeActive = false;
        this.setUiState("running");
        this.applyControlSettings(true)
            .then((settings) => {
                this._captureRunSettingsSnapshot();
                this._syncPlannedCells(this.readControlSettings());
                return fetch("/api/run/start", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ ...settings, ...this.regularRunModeClearFlags() }),
                });
            })
            .then((response) => response.json())
            .then((result) => {
                if (result.error) {
                    throw new Error(result.error);
                }
                this.setControlStatus(result.status_message || "Run started");
            })
            .catch((err) => {
                this.setUiState("idle");
                this.setControlStatus(err?.message || "Failed to start run");
            });
    }

    _requestRunStop(statusMessageFallback = "Stop requested") {
        this.setUiState("idle");
        return fetch("/api/run/stop", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({})
        })
            .then((response) => response.json())
            .then((result) => {
                const message = result.status_message || statusMessageFallback;
                this.setControlStatus(message);
                return result;
            });
    }

    _requestTerminateCurrentCell() {
        return fetch("/api/run/terminate_current_cell", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({})
        }).then((response) => response.json());
    }

    stopRunFromUI() {
        this._requestRunStop("Stop requested").catch(() => {
            this.setControlStatus("Failed to stop run");
        });
    }

    stopCalibrationFromUI() {
        if (!this.isRunning || !this._isCalibrationLikeProtocolMode()) {
            this.pushStatusMessage("Stop is only available during an active calibration or recalibration run");
            return;
        }
        const label = this.recalibrationModeActive ? "Recalibration" : "Calibration";
        this._requestRunStop(`${label} stop requested`).catch(() => {
            this.setControlStatus(`Failed to stop ${label.toLowerCase()}`);
        });
    }

    terminateCurrentCellFromUI() {
        if (!this.isRunning || this.calibrationModeActive || this.recalibrationModeActive) {
            this.pushStatusMessage("Manual current-cell termination is only available during regular runs");
            return;
        }
        if (this.manualTerminateQueued) {
            this.pushStatusMessage("Manual current-cell termination already queued");
            return;
        }
        this.manualTerminateQueued = true;
        this.updateRunControlButtons();
        this._requestTerminateCurrentCell()
            .then((result) => {
                this.setControlStatus(result.status_message || "Manual current-cell termination queued");
                this.pushStatusMessage(result.status_message || "Manual current-cell termination queued");
            })
            .catch(() => {
                this.manualTerminateQueued = false;
                this.updateRunControlButtons();
                this.setControlStatus("Failed to queue manual current-cell termination");
            });
    }

    terminateCalibrationCellFromUI() {
        if (!this.isRunning || !this._isCalibrationLikeProtocolMode()) {
            this.pushStatusMessage("Stop in this cell is only available during calibration or recalibration");
            return;
        }
        if (this.manualTerminateQueued) {
            this.pushStatusMessage("Stop in this cell already queued");
            return;
        }
        this.manualTerminateQueued = true;
        this.updateRunControlButtons();
        this._requestTerminateCurrentCell()
            .then((result) => {
                const fallback = this.recalibrationModeActive
                    ? "Recalibration in this cell stop queued"
                    : "Calibration in this cell stop queued";
                this.pushStatusMessage(result.status_message || fallback);
            })
            .catch(() => {
                this.manualTerminateQueued = false;
                this.updateRunControlButtons();
                this.pushStatusMessage("Failed to queue stop in this cell");
            });
    }

    _markSocketConnected() {
        if (this.isConnected) {
            return;
        }
        this.isConnected = true;
        this.el.connectionDot.classList.remove("disconnected");
        this.el.connectionDot.classList.add("connected");
        this.showDisconnectedBanner(false);
    }

    _markSocketDisconnected() {
        this.isConnected = false;
        this.el.connectionDot.classList.remove("connected");
        this.el.connectionDot.classList.add("disconnected");
        this.showDisconnectedBanner(true);
    }

    connectSocket() {
        if (typeof io !== "function") {
            this._markSocketDisconnected();
            this.pushStatusMessage("Socket.IO client script not loaded yet; retrying...");
            setTimeout(() => this.connectSocket(), 2000);
            return;
        }

        this.socket = io({
            autoConnect: false,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            timeout: 10000,
        });

        this.socket.on("connect", () => {
            this._markSocketConnected();
            this.pushStatusMessage("Socket connection established");
        });

        this.socket.on("disconnect", () => {
            this._markSocketDisconnected();
        });

        this.socket.on("connect_error", () => {
            if (!this.isConnected) {
                this._markSocketDisconnected();
            }
        });

        this.socket.on("status_update", (data) => {
            this._markSocketConnected();
            if (data && typeof data === "object") {
                if (data.position || data.current_cell !== undefined || data.current_rpm !== undefined || data.is_running !== undefined) {
                    this.applyStatusSnapshot(data);
                }
                if (data.status_message) {
                    this.pushStatusMessage(data.status_message);
                    this.consumeStatusForPhase(data.status_message);
                }
            }
        });

        this.socket.on("control_settings_update", (settings) => {
            this.populateControlSettings(settings);
        });

        this.socket.on("position_update", (data) => {
            this.position = {
                x: Number(data.x) || 0,
                y: Number(data.y) || 0,
                z: Number(data.z) || 0
            };
            this.queueRender();
        });

        this.socket.on("cell_update", (data) => {
            this.setActiveCell(data.current_cell ?? null);
        });

        this.socket.on("rpm_update", (data) => {
            this.currentRPM = Number(data.current_rpm) || 0;
            this.updateGauge(this.currentRPM);
            if (this._shouldSyncMapVisuals()) {
                this._scheduleMapVisualSync();
            }
        });

         this.socket.on("new_measurement", (data) => {
            this._markSocketConnected();
            this.addPointToChart(
                data.cell_id,
                data.height,
                data.rotational_drag,
                data.rpm,
                data.timestamp,
                data.hit_detected
            );
            if (this.activeTabId === "controls-tab") {
                const torquePercent = Number.isFinite(Number(data.torque_percent))
                    ? Number(data.torque_percent)
                    : (Number(data.rotational_drag) || 0) * (Number(data.rpm) || 0);
                this.updateTorqueBar(torquePercent);
                this.updateLiveTorqueDisplay(torquePercent);
                this.updateLiveRotationalDragDisplay(data.rotational_drag);
            }
        });

        this.socket.on("discovery_update", (payload) => {
            this.ingestDiscoveryUpdate(payload);
        });

        this.socket.on("torque_update", (data) => {
            if (this.activeTabId !== "controls-tab") {
                return;
            }
            const torquePercent = Number(data.torque_percent);
            if (!Number.isNaN(torquePercent)) {
                this.updateTorqueBar(torquePercent);
                this.updateLiveTorqueDisplay(torquePercent);
            }
            const drag = Number.isFinite(Number(data.rotational_drag))
                ? Number(data.rotational_drag)
                : ((Number(data.torque_percent) || 0) / (Number(data.rpm) || 1));
            this.updateLiveRotationalDragDisplay(drag);
        });

        this.socket.on("z_update", (data) => {
            const currentZ = Number(data.current_z);
            if (!Number.isNaN(currentZ)) {
                this.updateMeasuringZDisplay(currentZ);
            }
        });

        this.socket.on("running_state_update", (data) => {
            this._markSocketConnected();
            const wasRunning = this.isRunning;
            if (data.is_running && !this.isRunning) {
                this.runMeasurementStartIndex = this.measurements.length;
                this.completedSaveLock = false;
                this._captureRunSettingsSnapshot();
            }
            if (!data.is_running && wasRunning) {
                this.isRunning = false;
                this.discoveryModeActive = false;
                if (!this.experimentReviewPending && !this.calibrationReviewPending) {
                    this.saveCompletedExperiment();
                }
            } else if (data.is_running && wasRunning) {
                // Keep discoveryModeActive during an active discovery run (hard refresh reconnect).
            } else if (data.is_running && !wasRunning) {
                const settings = data.control_settings || {};
                if (settings.discovery_mode_enabled) {
                    this.discoveryModeActive = true;
                }
            }
            if (data.is_running && data.discovery_mode_active !== undefined) {
                this.discoveryModeActive = Boolean(data.discovery_mode_active);
            }
            this.setRunningState(Boolean(data.is_running), wasRunning);
        });

        this.socket.on("experiment_start", (data) => {
            const startTs = Number(data?.start_ts);
            this.experimentStart = Number.isFinite(startTs) ? startTs * 1000 : Date.now();
            this.lastRunStartTsSec = Number.isFinite(startTs) ? startTs : (this.experimentStart / 1000);
            this._captureRunSettingsSnapshot();
            this.cellStart = Date.now();
            this._hideExperimentCompleteMessage();
            this._hideExperimentTerminatedMessage();
            if (this.el.elapsed) {
                this.el.elapsed.textContent = "00:00:00";
            }
            if (this.el.calElapsed) {
                this.el.calElapsed.textContent = "00:00:00";
            }
            if (this.el.discoveryElapsed) {
                this.el.discoveryElapsed.textContent = "00:00:00";
            }
        });

        this.socket.on("experiment_stop", () => {
            this.experimentStart = null;
            this.cellStart = null;
        });

        this.socket.on("completed_cells_update", (data) => {
            if (!Array.isArray(data?.completed_cells)) {
                return;
            }
            this.completedCells = new Set(
                data.completed_cells
                    .map((c) => Number(c))
                    .filter((c) => Number.isInteger(c) && c > 0)
            );
            this.measuredCells = new Set(this.completedCells);
            this.completedCells.forEach((cellId) => this.cellStates.set(cellId, "completed"));
            if (data?.cell_termination_reasons && typeof data.cell_termination_reasons === "object") {
                this.cellTerminationReasons = new Map(
                    Object.entries(data.cell_termination_reasons).map(([k, v]) => [Number(k), String(v)])
                );
            }
            this.recalibrationModeActive = Boolean(data?.recalibration_mode_active);
            this.recalibrationTargetCount = Number(data?.recalibration_target_count) || 0;
            this.updateCompletionBar();
            this.updateCellVisuals();
            this.updateLiveTerminationBadge();
            this.updateRunControlButtons();
        });

        this.socket.on("manual_terminate_current_cell_update", (data) => {
            this.manualTerminateQueued = Boolean(data?.requested);
            this.updateRunControlButtons();
        });

        this.socket.on("instrument_status_update", (status) => {
            if (!status) {
                return;
            }
            this.setInstrumentStatus("cnc", Boolean(status.cnc));
            this.setInstrumentStatus("viscometer", Boolean(status.viscometer));
            this.setInstrumentStatus("pump", Boolean(status.pump));
        });

        this.socket.on("calibration_mode_update", (data) => {
            if (data && typeof data === "object") {
                this.calibrationModeActive = Boolean(data.calibration_mode);
                if (Array.isArray(data.completed_cells)) {
                    this.completedCells = new Set(
                        data.completed_cells
                            .map((c) => Number(c))
                            .filter((c) => Number.isInteger(c) && c > 0)
                    );
                    this.measuredCells = new Set(this.completedCells);
                    this.completedCells.forEach((cellId) => this.cellStates.set(cellId, "completed"));
                }
                this.recalibrationModeActive = Boolean(data.recalibration_mode_active);
                this.recalibrationTargetCount = Number(data.recalibration_target_count) || 0;
                this.updateCompletionBar();
                this.updateCellVisuals();
                this.renderProtocolUI();
                this.updateRunTabAvailability();
                this.updateRunControlButtons();
            }
        });

        this.socket.on("discovery_mode_update", (data) => {
            if (!data || typeof data !== "object") {
                return;
            }
            if (data.discovery_mode_active !== undefined) {
                if (data.discovery_mode_active) {
                    this.discoveryModeActive = true;
                } else if (!this.isRunning) {
                    this.discoveryModeActive = false;
                } else if (
                    this.latestControlSettings?.discovery_mode_enabled
                    || this.runSettingsSnapshot?.discovery_mode_enabled
                ) {
                    // Ignore pre-run false from request_start(); running_state_update is authoritative.
                } else {
                    this.discoveryModeActive = false;
                }
            }
            if (data.discovery_results_by_cell && typeof data.discovery_results_by_cell === "object") {
                this.discoveryResultsByCell = { ...data.discovery_results_by_cell };
                this._hydrateDiscoveryConvergedRpmCache();
                Object.values(this.discoveryResultsByCell).forEach((entry) => {
                    if (entry) {
                        this.ingestDiscoveryUpdate(entry);
                    }
                });
            }
            this.updateRunTabAvailability();
            this.renderProtocolUI();
            this.updateRunControlButtons();
        });

        this.socket.on("feedback_metrics_update", (data) => {
            if (!data) {
                return;
            }
            if (this._isDiscoveryRunActive()) {
                this.updateDiscoveryDragZSidebar(data);
            } else if (this.activeTabId === "controls-tab") {
                this.updateDragZSidebar(data);
            }
        });

        this.socket.on("clear_dashboard", () => {
            this.clearDashboard();
        });

        this.socket.on("predicted_viscosity_update", (payload) => {
            this._ingestPredictedViscosityUpdate(payload);
        });

        this.socket.on("predicted_viscosity_summary_update", (payload) => {
            this._ingestPredictedViscositySummaryUpdate(payload);
        });

        this.socket.on("rpm_torque_status_update", (payload) => {
            if (!payload || payload.cell_id == null) {
                return;
            }
            const cellId = Number(payload.cell_id);
            const statusMap = new Map();
            const statuses = payload.statuses || {};
            Object.keys(statuses).forEach((rpmKey) => {
                statusMap.set(rpmKey, statuses[rpmKey] === "dropped" ? "dropped" : "active");
            });
            this.rpmTorqueStatusByCell.set(cellId, statusMap);
            const ordered = this.expandRpmsWithObserved(
                this.getRpmsForCell(cellId),
                this.measurementsByCell.get(cellId) || []
            );
            if (this._isDiscoveryRunActive() && this.getActiveDiscoveryGraphCellId() === cellId) {
                this.renderDiscoveryDragZRpmLegend(cellId, ordered);
            } else if (this.getActiveGraphCellId() === cellId && !this._isDiscoveryRunActive()) {
                this.renderDragZRpmLegend(cellId, ordered);
            }
        });

        this.socket.on("calibration_status_update", (summary) => {
            this.applyCalibrationStatus(summary);
        });

        this.socket.on("calibration_complete", (summary) => {
            if (summary) {
                this.applyCalibrationStatus(summary);
            }
            this.isCalibrationRun = false;
        });

        this.socket.on("calibration_review_open", (session) => {
            this.openCalibrationReview(session);
        });

        this.socket.on("calibration_review_update", (session) => {
            this.syncCalibrationReviewSession(session);
        });

        this.socket.on("calibration_review_committed", (payload) => {
            this.onCalibrationReviewCommitted(payload);
        });

        this.socket.on("experiment_review_open", (session) => {
            this.openExperimentReview(session);
        });

        this.socket.on("experiment_review_update", (session) => {
            this.syncExperimentReviewSession(session);
        });

        this.socket.on("experiment_review_committed", (payload) => {
            this.onExperimentReviewCommitted(payload);
        });

        this.socket.connect();
    }

    clearDashboard() {
        this.measurements = [];
        this.predictedViscosityData = {};
        if (this.el.predictedViscosityCharts) {
            this.el.predictedViscosityCharts.innerHTML = "";
        }
        this.renderLiveViscosityPredictionsTable();
        this.measurementsByCell.clear();
        this.latestTorqueByCell.clear();
        this.hitPoints.clear();
        this.measuredCells.clear();
        this.completedCells.clear();
        this.rpmTorqueStatusByCell.clear();
        this.cellStates.forEach((_, cellId) => this.cellStates.set(cellId, "pending"));
        this.washingCell = null;
        this._pendingCompletedCell = null;
        this.selectedGraphCell = null;
        this.selectedCalGraphCell = null;
        this.selectedDiscoveryGraphCell = null;
        this.discoveryResultsByCell = {};
        this.discoveryConvergedRpmByCell = {};
        this.sparklineData = [];
        this.position = { x: 0, y: 0, z: 0 };
        this.currentCell = null;
        this.currentRPM = 0;
        this.currentTorquePercent = 0;
        this.currentMeasuringZ = null;
        this.experimentStart = null;
        this.cellStart = null;
        this.isSavingFinalResults = false;
        this.runMeasurementStartIndex = 0;
        this.runSettingsSnapshot = null;
        this.currentPhase = 0;
        this.protocolCurrentStepId = "idle";
        this.protocolLastStatusMessage = "";
        this._protocolRenderedMode = null;
        this._graphTabIdsKey = "";
        if (this._plotRefreshTimer) {
            window.clearTimeout(this._plotRefreshTimer);
            this._plotRefreshTimer = null;
        }
        if (this._calPlotRefreshTimer) {
            window.clearTimeout(this._calPlotRefreshTimer);
            this._calPlotRefreshTimer = null;
        }
        if (this._discoveryPlotRefreshTimer) {
            window.clearTimeout(this._discoveryPlotRefreshTimer);
            this._discoveryPlotRefreshTimer = null;
        }
        if (this._tableRefreshTimer) {
            window.clearTimeout(this._tableRefreshTimer);
            this._tableRefreshTimer = null;
        }
        if (this._mapVisualSyncTimer) {
            window.clearTimeout(this._mapVisualSyncTimer);
            this._mapVisualSyncTimer = null;
        }
        this._resetMapVisualCache();

        if (this.el.statusLog) {
            this.el.statusLog.innerHTML = "";
        }
        if (this.el.cellFlip) {
            this.el.cellFlip.dataset.cell = "-";
            this.el.cellFlip.textContent = "-";
        }
        if (this.el.cellMeta) {
            this.el.cellMeta.textContent = "Row -, local -";
        }
        if (this.el.elapsed) {
            this.el.elapsed.textContent = "00:00:00";
        }
        if (this.el.calElapsed) {
            this.el.calElapsed.textContent = "00:00:00";
        }
        if (this.el.elapsedCell) {
            this.el.elapsedCell.textContent = "Cell 00:00:00";
        }
        if (this.el.calElapsedCell) {
            this.el.calElapsedCell.textContent = "Cell 00:00:00";
        }
        if (this.el.discoveryElapsed) {
            this.el.discoveryElapsed.textContent = "00:00:00";
        }
        if (this.el.discoveryElapsedCell) {
            this.el.discoveryElapsedCell.textContent = "Cell 00:00:00";
        }
        if (this.el.zMeasuringDisplay) {
            this.el.zMeasuringDisplay.textContent = "-";
        }
        if (this.el.calZMeasuringDisplay) {
            this.el.calZMeasuringDisplay.textContent = "-";
        }
        if (this.el.discoveryZMeasuringDisplay) {
            this.el.discoveryZMeasuringDisplay.textContent = "-";
        }
        if (this.el.rotationalDragDisplay) {
            this.el.rotationalDragDisplay.textContent = "0.000";
        }
        if (this.el.torqueValue) {
            this.el.torqueValue.textContent = "0.00%";
        }
        if (this.el.sidebarRpm) this.el.sidebarRpm.textContent = "-";
        if (this.el.sidebarSecondDerivDrag) this.el.sidebarSecondDerivDrag.textContent = "-";
        if (this.el.sidebarSecondDerivCv) this.el.sidebarSecondDerivCv.textContent = "-";
        if (this.el.sidebarSecondDerivSlope) this.el.sidebarSecondDerivSlope.textContent = "-";
        if (this.el.sidebarR2Drag) this.el.sidebarR2Drag.textContent = "-";
        if (this.el.sidebarR2Cv) this.el.sidebarR2Cv.textContent = "-";
        if (this.el.sidebarR2Slope) this.el.sidebarR2Slope.textContent = "-";
        if (this.el.sidebarConfidence) this.el.sidebarConfidence.textContent = "-";
        if (this.el.sidebarFailSafe) {
            this.el.sidebarFailSafe.textContent = "No";
            this.el.sidebarFailSafe.className = "sidebar-value mono fail-safe-no";
        }
        if (this.el.sidebarHit) {
            this.el.sidebarHit.textContent = "No";
            this.el.sidebarHit.className = "sidebar-value mono hit-no";
        }
        this._resetDragZSidebarElements(this._discoveryDragZSidebarElements());
        this.renderDragZRpmLegend(null, []);

        this.platform.cells.forEach((cell) => this.cellStates.set(cell.id, "pending"));
        this.renderMap();
        this.updateCellDisplay();
        if (this._shouldSyncMapVisuals()) {
            this.syncMapVisuals({ force: true });
        } else {
            this._mapVisualsDirty = true;
        }
        this.updateCompletionBar();
        this.updateGauge(0, { force: true });
        this.updateTorqueBar(0);
        this.updateLiveTorqueDisplay(0);
        this.updateLiveRotationalDragDisplay(0);
        if (this.el.zMeasuringDisplay) {
            this.el.zMeasuringDisplay.textContent = "-";
        }
        if (this.el.calZMeasuringDisplay) {
            this.el.calZMeasuringDisplay.textContent = "-";
        }
        this.updateGraphCellTabs();
        this.updateCalGraphCellTabs();
        this.updateDiscoveryGraphCellTabs();
        if (this.el.discoveryProbeTableBody) {
            this.el.discoveryProbeTableBody.innerHTML = "";
        }
        if (this.el.discoveryProbeEmpty) {
            this.el.discoveryProbeEmpty.classList.remove("hidden");
        }
        if (this.el.discoveryStatusPill) {
            this.el.discoveryStatusPill.textContent = "Idle";
            this.el.discoveryStatusPill.className = "discovery-status-pill idle";
        }
        this._refreshActiveTabCharts({ force: true });
        this.updateTable();
    }

    applyStatusSnapshot(status) {
        if (status.position) {
            this.position = {
                x: Number(status.position.x) || 0,
                y: Number(status.position.y) || 0,
                z: Number(status.position.z) || 0
            };
            this.queueRender();
        }

        if (Array.isArray(status.cell_positions) && status.cell_positions.length === 18) {
            this.platform.cells = status.cell_positions.map((c) => ({
                id: c.id,
                row: c.local_cell,
                local: c.local_cell,
                col: c.row === 1 ? 2 : (c.row === 2 ? 3 : (c.row === 3 ? 6 : 8)),
                x: c.x,
                y: c.y
            }));
            this.renderMap();
        }

        if (Array.isArray(status.wash_stations) && status.wash_stations.length > 0) {
            this.platform.washStations = status.wash_stations.map((w) => ({
                id: `W${w.id}`,
                x: w.x,
                y: w.y
            }));
            this.renderMap();
        }

        if (status.current_cell !== undefined) {
            this.setActiveCell(status.current_cell);
        }

        if (Array.isArray(status.completed_cells)) {
            this.completedCells = new Set(
                status.completed_cells
                    .map((c) => Number(c))
                    .filter((c) => Number.isInteger(c) && c > 0)
            );
            this.measuredCells = new Set(this.completedCells);
            this.completedCells.forEach((cellId) => this.cellStates.set(cellId, "completed"));
            if (status.cell_termination_reasons && typeof status.cell_termination_reasons === "object") {
                this.cellTerminationReasons = new Map(
                    Object.entries(status.cell_termination_reasons).map(([k, v]) => [Number(k), String(v)])
                );
            }
            this.updateCompletionBar();
            this.updateCellVisuals();
            this.updateLiveTerminationBadge();
        }
        if (status.manual_terminate_current_cell_requested !== undefined) {
            this.manualTerminateQueued = Boolean(status.manual_terminate_current_cell_requested);
            this.updateRunControlButtons();
        }
        if (status.recalibration_mode_active !== undefined) {
            this.recalibrationModeActive = Boolean(status.recalibration_mode_active);
        }
        if (status.recalibration_target_count !== undefined) {
            this.recalibrationTargetCount = Number(status.recalibration_target_count) || 0;
        }

        if (status.calibration_mode !== undefined) {
            this.calibrationModeActive = Boolean(status.calibration_mode);
        }

        const settings = status.control_settings || {};
        if (status.discovery_mode_active !== undefined || settings.discovery_mode_enabled !== undefined) {
            const discoveryFlag = status.discovery_mode_active ?? settings.discovery_mode_enabled;
            if (status.is_running) {
                this.discoveryModeActive = Boolean(discoveryFlag);
            } else if (!this.isRunning) {
                this.discoveryModeActive = false;
            }
        }

        if (status.discovery_results_by_cell && typeof status.discovery_results_by_cell === "object") {
            this.discoveryResultsByCell = { ...status.discovery_results_by_cell };
            this._hydrateDiscoveryConvergedRpmCache();
            Object.values(this.discoveryResultsByCell).forEach((entry) => {
                if (entry) {
                    this.ingestDiscoveryUpdate(entry);
                }
            });
        }
        this.updateRunTabAvailability();

        if (status.calibration_review_pending !== undefined) {
            this.calibrationReviewPending = Boolean(status.calibration_review_pending);
            this.updateReviewStartGuard();
        }
        if (status.calibration_review) {
            this.openCalibrationReview(status.calibration_review);
        }

        if (status.experiment_review_pending !== undefined) {
            this.experimentReviewPending = Boolean(status.experiment_review_pending);
            this.updateReviewStartGuard();
        }
        if (status.experiment_review) {
            this.openExperimentReview(status.experiment_review);
        }

        if (status.calibration_summary && typeof status.calibration_summary === "object") {
            this.applyCalibrationStatus(status.calibration_summary);
        }

        if (status.current_rpm !== undefined) {
            this.currentRPM = Number(status.current_rpm) || 0;
            this.updateGauge(this.currentRPM);
        }

        if (status.current_torque_percent !== undefined) {
            const torquePercent = Number(status.current_torque_percent);
            if (!Number.isNaN(torquePercent)) {
                this.updateTorqueBar(torquePercent);
                this.updateLiveTorqueDisplay(torquePercent);
            }
        }

        const statusDrag = Number(status.current_torque_percent) / (Number(status.current_rpm) || 1);
        if (!Number.isNaN(statusDrag) && Number.isFinite(statusDrag)) {
            this.updateLiveRotationalDragDisplay(statusDrag);
        }

        if (status.current_z_measuring !== undefined && status.current_z_measuring !== null) {
            const currentZ = Number(status.current_z_measuring);
            if (!Number.isNaN(currentZ)) {
                this.updateMeasuringZDisplay(currentZ);
            }
        }

        if (status.instrument_status) {
            this.setInstrumentStatus("cnc", Boolean(status.instrument_status.cnc));
            this.setInstrumentStatus("viscometer", Boolean(status.instrument_status.viscometer));
            this.setInstrumentStatus("pump", Boolean(status.instrument_status.pump));
        }

        if (status.is_running !== undefined) {
            this.setRunningState(Boolean(status.is_running));
            if (!status.is_running && this.uiState === "running") {
                this.setUiState("idle");
            }
        }
        if (status.experiment_start_ts) {
            const startTs = Number(status.experiment_start_ts);
            if (Number.isFinite(startTs)) {
                this.experimentStart = startTs * 1000;
                this.lastRunStartTsSec = startTs;
            }
        }
        if (status.current_cell_start_ts) {
            const cellStartTs = Number(status.current_cell_start_ts);
            if (Number.isFinite(cellStartTs)) {
                this.cellStart = cellStartTs * 1000;
            }
        }

        if (Array.isArray(status.measurement_data) && status.measurement_data.length > 0) {
            status.measurement_data.forEach((m) => this.ingestMeasurement(m, true));
            this._refreshActiveTabCharts();
        }

        if (status.predicted_viscosity_results) {
            this._hydratePredictedViscosityFromServer(status.predicted_viscosity_results);
        }
        if (status.testing_status) {
            this.applyTestingStatus(status.testing_status);
        }

        if (status.status_message) {
            this.consumeStatusForPhase(status.status_message);
        }
    }

    queueRender(options = {}) {
        if (!options.force && !this._shouldSyncMapVisuals()) {
            this._mapVisualsDirty = true;
            return;
        }
        if (this.pendingRender) {
            return;
        }

        this.pendingRender = true;
        requestAnimationFrame(() => {
            this.pendingRender = false;
            this.applyArmPosition();
            this.updateXYZ();
        });
    }

    updateXYZ() {
        this.el.xyzX.textContent = this.position.x.toFixed(1);
        this.el.xyzY.textContent = this.position.y.toFixed(1);
        this.el.xyzZ.textContent = this.position.z.toFixed(2);

        [this.el.xyzX, this.el.xyzY, this.el.xyzZ].forEach((node) => {
            const holder = node.parentElement;
            holder.classList.add("flash");
            window.setTimeout(() => holder.classList.remove("flash"), 220);
        });
    }

    setActiveCell(cellId) {
        if (cellId === this.currentCell) {
            return;
        }

        const previousCell = this.currentCell;
        this.currentCell = cellId === null ? null : Number(cellId);

        if (this._isDiscoveryRunActive() && this.currentCell !== previousCell) {
            this.selectedDiscoveryGraphCell = null;
        }

        if (previousCell && this.currentCell !== previousCell) {
            this.measuredCells.add(previousCell);
            this._pendingCompletedCell = previousCell;
            this.cellStates.set(previousCell, "washing");
            this.playChime(660, 0.08);
            this.updateCompletionBar();
        }

        if (this.currentCell && this.currentCell !== previousCell) {
            this.protocolCurrentStepId = "move";
            this.currentPhase = 1;
            this.updateTimeline();
        }

        if (this.currentCell) {
            this.cellStates.set(this.currentCell, "active");
            this.cellStart = Date.now();
        }

        if (this.currentCell === null && !this.isRunning && this.completedCells.size > 0) {
            this.playChime(880, 0.12);
        }

        this.updateCellDisplay();
        this.updateCellVisuals();
        this.updateTable();
        this.updateGraphCellTabs();
        this._refreshActiveTabCharts();
    }

    updateCellDisplay() {
        const previousText = this.el.cellFlip.dataset.cell;
        const nextText = this.currentCell ? String(this.currentCell) : "-";

        if (previousText !== nextText) {
            this.el.cellFlip.classList.remove("flip");
            void this.el.cellFlip.offsetWidth;
            this.el.cellFlip.classList.add("flip");
        }

        this.el.cellFlip.dataset.cell = nextText;
        this.el.cellFlip.textContent = nextText;

        if (!this.currentCell) {
            this.el.cellMeta.textContent = "Row -, local -";
            return;
        }

        const row = Math.floor((this.currentCell - 1) / 6) + 1;
        const local = ((this.currentCell - 1) % 6) + 1;
        this.el.cellMeta.textContent = `Row ${row}, local ${local}`;
    }

    updateCellVisuals() {
        if (this._shouldSyncMapVisuals()) {
            this.syncMapVisuals();
        } else {
            this._mapVisualsDirty = true;
        }
    }

    getProtocolRunMode() {
        if (!this.isRunning) {
            return "idle";
        }
        if (this.recalibrationModeActive) {
            return "recalibration";
        }
        if (this.calibrationModeActive) {
            return "calibration";
        }
        if (this.discoveryModeActive) {
            return "discovery";
        }
        return "regular";
    }

    resolveProtocolStep(message) {
        const normalized = (message || "").toLowerCase().trim();
        if (!normalized) {
            return this.protocolCurrentStepId || "idle";
        }
        const mode = this.getProtocolRunMode();
        for (const rule of PROTOCOL_STATUS_RULES) {
            if (!rule.test(normalized)) {
                continue;
            }
            if (mode !== "regular" && mode !== "discovery" && /^wash/.test(rule.id)) {
                continue;
            }
            if ((mode === "regular" || mode === "discovery") && rule.id === "review") {
                continue;
            }
            return rule.id;
        }
        return this.protocolCurrentStepId || (mode === "idle" ? "idle" : "init");
    }

    consumeStatusForPhase(message) {
        if (!message) {
            return;
        }
        this.protocolLastStatusMessage = message;
        const normalized = message.toLowerCase();
        const stepId = this.resolveProtocolStep(message);
        if (stepId) {
            this.protocolCurrentStepId = stepId;
        }

        const legacyPhaseMap = {
            init: 1,
            move: 1,
            zero: 2,
            measure: 3,
            retract: 4,
            wash_after: 5,
            wash1_travel: 5,
            wash1_scrub: 5,
            wash1_drain: 5,
            wash2_travel: 6,
            wash2_scrub: 6,
            save: 4,
            review: 4,
            cleanup: 4,
            done: 6,
            idle: 0,
        };
        this.currentPhase = legacyPhaseMap[stepId] ?? this.currentPhase;
        this.updateTimeline();

        const washMatch = message.match(/washing after cell\s+(\d+)/i);
        if (washMatch) {
            this.washingCell = Number(washMatch[1]);
        }
        if (
            normalized.includes("completed") ||
            normalized.includes("stopping motor 2") ||
            normalized.includes("wash sequence completed")
        ) {
            this._finalizePendingCompletedCell();
        }

        if (normalized.includes("saving final results")) {
            this.isSavingFinalResults = true;
        }

        if (normalized.includes("hit point") || normalized.includes("surface detected")) {
            const match = message.match(/-?\d+(?:\.\d+)?/g);
            if (match && match.length > 0 && this.currentCell) {
                const maybeHeight = Number(match[match.length - 1]);
                if (!Number.isNaN(maybeHeight)) {
                    this.hitPoints.set(this.currentCell, maybeHeight);
                    this.refreshLivePlots();
                }
            }
        }
    }

    updateTimeline() {
        this.renderProtocolUI();
    }

    renderProtocolUI() {
        const mode = this.getProtocolRunMode();
        const def = PROTOCOL_DEFINITIONS[mode] || PROTOCOL_DEFINITIONS.idle;
        const stepId = this.protocolCurrentStepId || def.steps[0]?.id || "idle";
        const stepIndex = Math.max(0, def.steps.findIndex((s) => s.id === stepId));

        if (this.el.protocolModeBadge) {
            this.el.protocolModeBadge.textContent = def.badge;
            this.el.protocolModeBadge.className = `protocol-mode-badge ${def.badgeClass || ""}`.trim();
        }

        if (this.el.protocolCurrentStep) {
            const stepLabel = def.steps.find((s) => s.id === stepId)?.label;
            const detail = (this.protocolLastStatusMessage || "").trim();
            this.el.protocolCurrentStep.textContent = detail
                ? detail
                : (stepLabel || "Waiting for run…");
        }

        if (this.el.protocolProgressFill) {
            const fillPct = def.steps.length > 1
                ? Math.min(1, (stepIndex + 1) / def.steps.length)
                : 0;
            this.el.protocolProgressFill.style.transform = `scaleX(${fillPct})`;
        }

        if (this.el.protocolStepList) {
            if (this._protocolRenderedMode !== mode) {
                this._protocolRenderedMode = mode;
                this.el.protocolStepList.innerHTML = def.steps.map((step) => (
                    `<li data-step-id="${step.id}">${step.label}</li>`
                )).join("");
            }
            this.el.protocolStepList.querySelectorAll("li").forEach((node, idx) => {
                node.classList.remove("current", "done");
                if (idx < stepIndex) {
                    node.classList.add("done");
                } else if (idx === stepIndex) {
                    node.classList.add("current");
                }
            });
        }

        if (this.el.protocolFlowchart) {
            const flowId = def.stepToFlow[stepId] || stepId;
            const flowIndex = def.flow.findIndex((n) => n.id === flowId);
            const parts = [];
            def.flow.forEach((node, idx) => {
                let cls = "protocol-flow-node";
                if (flowIndex >= 0) {
                    if (idx < flowIndex) {
                        cls += " done";
                    } else if (idx === flowIndex) {
                        cls += " active";
                    }
                } else if (node.id === flowId) {
                    cls += " active";
                }
                parts.push(`<span class="${cls}">${node.short}</span>`);
                if (idx < def.flow.length - 1) {
                    parts.push('<span class="protocol-flow-arrow" aria-hidden="true">→</span>');
                }
            });
            this.el.protocolFlowchart.innerHTML = parts.join("");
        }
    }

     _schedulePlotRefresh() {
        if (this.activeTabId === "calibrate-tab") {
            this._scheduleCalibrationPlotRefresh();
        } else if (this.activeTabId === "discovery-tab") {
            this._scheduleDiscoveryPlotRefresh();
        } else if (this.activeTabId === "controls-tab") {
            if (this._plotRefreshTimer) {
                window.clearTimeout(this._plotRefreshTimer);
            }
            this._plotRefreshTimer = window.setTimeout(() => {
                this._plotRefreshTimer = null;
                this.refreshLivePlots();
            }, 110);
        }
    }

    _scheduleCalibrationPlotRefresh() {
        if (this._calPlotRefreshTimer) {
            window.clearTimeout(this._calPlotRefreshTimer);
        }
        this._calPlotRefreshTimer = window.setTimeout(() => {
            this._calPlotRefreshTimer = null;
            this.refreshCalibrationLivePlots();
        }, 110);
    }

    _scheduleDiscoveryPlotRefresh() {
        if (!this._discoveryLivePlottingEnabled()) {
            return;
        }
        if (this._discoveryPlotRefreshTimer) {
            window.clearTimeout(this._discoveryPlotRefreshTimer);
        }
        this._discoveryPlotRefreshTimer = window.setTimeout(() => {
            this._discoveryPlotRefreshTimer = null;
            this.refreshDiscoveryLivePlots();
        }, 110);
    }

    _scheduleTableRefresh() {
        if (this._tableRefreshTimer) {
            window.clearTimeout(this._tableRefreshTimer);
        }
        this._tableRefreshTimer = window.setTimeout(() => {
            this._tableRefreshTimer = null;
            this.updateTable();
        }, 140);
    }

    ingestMeasurement(rawMeasurement, bootstrap) {
        const rawSampleCount = Number(rawMeasurement.sample_count);
        const sampleCount = Number.isFinite(rawSampleCount) && rawSampleCount >= 1
            ? Math.floor(rawSampleCount)
            : 1;
        const measurement = {
            timestamp: Number(rawMeasurement.timestamp) || Date.now() / 1000,
            height: Number(rawMeasurement.height) || 0,
            rotational_drag: Number(rawMeasurement.rotational_drag) || 0,
            torque_percent: Number.isFinite(Number(rawMeasurement.torque_percent))
                ? Number(rawMeasurement.torque_percent)
                : (Number(rawMeasurement.rotational_drag) || 0) * (Number(rawMeasurement.rpm) || 0),
            rpm: Number(rawMeasurement.rpm) || 0,
            cell_id: Number(rawMeasurement.cell_id) || 0,
            is_final_save: Boolean(rawMeasurement.is_final_save) || this.isSavingFinalResults,
            hit_detected: rawMeasurement.hit_detected === true
                ? true
                : (rawMeasurement.hit_detected === false ? false : null),
            sample_count: sampleCount,
            elapsed_time: Number.isFinite(Number(rawMeasurement.elapsed_time))
                ? Number(rawMeasurement.elapsed_time)
                : null,
        };

        if (!measurement.cell_id) {
            return;
        }

        this.measurements.push(measurement);
        this._ingestDwellMeasurement(measurement);

        if (!this.measurementsByCell.has(measurement.cell_id)) {
            this.measurementsByCell.set(measurement.cell_id, []);
        }
        this.measurementsByCell.get(measurement.cell_id).push(measurement);

        this.latestTorqueByCell.set(measurement.cell_id, measurement.torque_percent);

        if (this.currentCell === measurement.cell_id && this.activeTabId === "controls-tab") {
            this.updateTorqueBar(measurement.torque_percent);
            this.updateLiveTorqueDisplay(measurement.torque_percent);
            this.updateLiveRotationalDragDisplay(measurement.rotational_drag);
        }

        const nextTabKey = this.getGraphCellIds().join(",");
        if (nextTabKey !== this._graphTabIdsKey) {
            this._graphTabIdsKey = nextTabKey;
            this.updateGraphCellTabs();
            this.updateCalGraphCellTabs();
            this.updateDiscoveryGraphCellTabs();
        }

        this._schedulePlotRefresh();
        this._scheduleTableRefresh();
        this._scheduleMapVisualSync();
    }

     updateZFilterButtons() {
        if (this.el.zFilterAll) {
            this.el.zFilterAll.classList.toggle("active", !this.zLatestOnly);
        }
        if (this.el.zFilterLatest) {
            this.el.zFilterLatest.classList.toggle("active", this.zLatestOnly);
        }
        if (this.el.zConnectDots) {
            this.el.zConnectDots.textContent = `Connect Dots: ${this.zConnectDots ? "On" : "Off"}`;
            this.el.zConnectDots.classList.toggle("dots-on", this.zConnectDots);
        }
    }

    updateDiscoveryZFilterButtons() {
        if (this.el.discoveryZFilterAll) {
            this.el.discoveryZFilterAll.classList.toggle("active", !this.zDiscoveryLatestOnly);
        }
        if (this.el.discoveryZFilterLatest) {
            this.el.discoveryZFilterLatest.classList.toggle("active", this.zDiscoveryLatestOnly);
        }
        if (this.el.discoveryZConnectDots) {
            this.el.discoveryZConnectDots.textContent = `Connect Dots: ${this.zDiscoveryConnectDots ? "On" : "Off"}`;
            this.el.discoveryZConnectDots.classList.toggle("dots-on", this.zDiscoveryConnectDots);
        }
    }

    getGraphCellIds() {
        const ids = new Set([...this.measurementsByCell.keys()]);
        if (this.currentCell) {
            ids.add(this.currentCell);
        }
        return [...ids].sort((a, b) => a - b);
    }

    getActiveGraphCellId() {
        if (this.selectedGraphCell !== null) {
            return this.selectedGraphCell;
        }
        if (this.currentCell) {
            return this.currentCell;
        }
        const ids = this.getGraphCellIds();
        return ids.length ? ids[ids.length - 1] : null;
    }

    updateGraphCellTabs() {
        if (!this.el.graphCellTabs) {
            return;
        }
        const ids = this.getGraphCellIds();
        this.el.graphCellTabs.innerHTML = "";

        const currentBtn = document.createElement("button");
        currentBtn.className = `cell-tab${this.selectedGraphCell === null ? " active" : ""}`;
        currentBtn.textContent = "Current Cell";
        currentBtn.addEventListener("click", () => {
            this.selectedGraphCell = null;
            this.updateGraphCellTabs();
            this.refreshLivePlots();
            this.refreshDwellTimePlot();
            this.updateLiveTerminationBadge();
        });
        this.el.graphCellTabs.appendChild(currentBtn);

        ids.forEach((cellId) => {
            const btn = document.createElement("button");
            btn.className = `cell-tab${this.selectedGraphCell === cellId ? " active" : ""}`;
            btn.textContent = `Cell ${cellId}`;
            btn.addEventListener("click", () => {
                this.selectedGraphCell = cellId;
                this.updateGraphCellTabs();
                this.refreshLivePlots();
                this.refreshDwellTimePlot();
                this.updateLiveTerminationBadge();
            });
            this.el.graphCellTabs.appendChild(btn);
        });
        this.updateLiveTerminationBadge();
    }

    /** Torque % floor from "First-sample torque floor (%)" — used to tint live Z plots (below = red). */
    _torqueFloorPctForLivePlots() {
        const v = Number(this.el.lowTorqueLiquidContactThresholdPct?.value);
        return Number.isFinite(v) ? v : 20;
    }

    _markerColorsForTorqueFloor(measurements, floorPct) {
        const belowFill = LIVE_PLOT_BELOW_FILL;
        const belowLine = LIVE_PLOT_BELOW_LINE;
        return measurements.map((m) => {
            const tp = Number(m.torque_percent);
            const below = Number.isFinite(tp) && tp < floorPct;
            return { fill: below ? belowFill : null, line: below ? belowLine : null, below };
        });
    }

    getRpmsForCell(cellId) {
        if (!Number.isFinite(cellId)) {
            return [];
        }
        const fromMap = this.cellRpmMap[cellId];
        if (Array.isArray(fromMap) && fromMap.length > 0) {
            return [...fromMap]
                .map((n) => Number(n))
                .filter((n) => Number.isFinite(n) && n > 0)
                .sort((a, b) => a - b);
        }
        const fromSettings = this.latestControlSettings?.test_rpms;
        if (Array.isArray(fromSettings) && fromSettings.length > 0) {
            return [...fromSettings]
                .map((n) => Number(n))
                .filter((n) => Number.isFinite(n) && n > 0)
                .sort((a, b) => a - b);
        }
        const measurements = this.measurementsByCell.get(cellId) || [];
        const seen = new Set();
        const rpms = [];
        measurements.forEach((m) => {
            const r = Number(m.rpm);
            const key = r.toFixed(3);
            if (Number.isFinite(r) && r > 0 && !seen.has(key)) {
                seen.add(key);
                rpms.push(r);
            }
        });
        return rpms.sort((a, b) => a - b);
    }

    expandRpmsWithObserved(orderedRpms, source) {
        const list = [...orderedRpms];
        const seen = new Set(list.map((r) => Number(r).toFixed(3)));
        source.forEach((m) => {
            const r = Number(m.rpm);
            const key = r.toFixed(3);
            if (Number.isFinite(r) && r > 0 && !seen.has(key)) {
                seen.add(key);
                list.push(r);
            }
        });
        return list.sort((a, b) => a - b);
    }

    getRpmColor(rpm, orderedRpms) {
        const key = Number(rpm).toFixed(3);
        const idx = orderedRpms.findIndex((r) => Number(r).toFixed(3) === key);
        const paletteIdx = idx >= 0 ? idx : 0;
        return this.palette[paletteIdx % this.palette.length];
    }

    getLiveRpmColor(rpm, orderedRpms) {
        const key = Number(rpm).toFixed(3);
        const idx = orderedRpms.findIndex((r) => Number(r).toFixed(3) === key);
        const paletteIdx = idx >= 0 ? idx : 0;
        return LIVE_RPM_PASTEL_PALETTE[paletteIdx % LIVE_RPM_PASTEL_PALETTE.length];
    }

    partitionMeasurementsByRpm(source, orderedRpms) {
        const buckets = new Map();
        orderedRpms.forEach((rpm) => {
            buckets.set(Number(rpm).toFixed(3), []);
        });
        source.forEach((m) => {
            const r = Number(m.rpm);
            if (!Number.isFinite(r) || r <= 0) {
                return;
            }
            const key = r.toFixed(3);
            if (!buckets.has(key)) {
                buckets.set(key, []);
            }
            buckets.get(key).push(m);
        });
        return buckets;
    }

    _markerColorsForRpmTrace(measurements, floorPct, rpmColor, skipFloorColoring = false) {
        return measurements.map((m) => {
            if (skipFloorColoring) {
                return { fill: rpmColor, line: this._shadeHexColor(rpmColor, 0.82), below: false };
            }
            const tp = Number(m.torque_percent);
            const below = Number.isFinite(tp) && tp < floorPct;
            const fill = below ? LIVE_PLOT_BELOW_FILL : rpmColor;
            const line = below ? LIVE_PLOT_BELOW_LINE : this._shadeHexColor(rpmColor, 0.82);
            return { fill, line, below };
        });
    }

    _buildDragTraceForRpm(rpm, points, torqueFloor, orderedRpms) {
        const rpmColor = this.getLiveRpmColor(rpm, orderedRpms);
        const sorted = [...points].sort((a, b) => Number(a.height) - Number(b.height));
        const markerPalette = this._markerColorsForRpmTrace(sorted, torqueFloor, rpmColor);
        const rpmLabel = Number(rpm).toFixed(3);
        const trace = {
            x: sorted.map((m) => m.height),
            y: sorted.map((m) => m.rotational_drag),
            mode: this.zConnectDots ? "lines+markers" : "markers",
            type: "scatter",
            name: `RPM ${rpmLabel}`,
            marker: {
                size: 7,
                color: markerPalette.map((p) => p.fill),
                line: {
                    width: 0.75,
                    color: markerPalette.map((p) => p.line),
                },
            },
            hovertemplate: `RPM ${rpmLabel}<br>Z %{x:.3f} mm<br>Drag %{y:.4f}<br>Torque %{customdata:.2f}%<extra></extra>`,
            customdata: sorted.map((m) => Number(m.torque_percent)),
        };
        if (this.zConnectDots) {
            trace.line = { color: rpmColor, width: 1.5, opacity: 0.85 };
        }
        return trace;
    }

    _buildTorqueTraceForRpm(rpm, points, torqueFloor, orderedRpms) {
        const rpmColor = this.getLiveRpmColor(rpm, orderedRpms);
        const sorted = [...points].sort((a, b) => Number(a.height) - Number(b.height));
        const markerPalette = this._markerColorsForRpmTrace(sorted, torqueFloor, rpmColor);
        const rpmLabel = Number(rpm).toFixed(3);
        return {
            x: sorted.map((m) => m.height),
            y: sorted.map((m) => m.torque_percent),
            mode: "markers",
            type: "scatter",
            name: `RPM ${rpmLabel}`,
            marker: {
                size: 7,
                color: markerPalette.map((p) => p.fill),
                line: {
                    width: 0.75,
                    color: markerPalette.map((p) => p.line),
                },
            },
            hovertemplate: `RPM ${rpmLabel}<br>Z %{x:.3f} mm<br>Torque %{y:.2f}%<extra></extra>`,
        };
    }

    _buildDragDatasetForRpm(rpm, points, torqueFloor, orderedRpms, options = {}) {
        const connectDots = options.connectDots != null ? options.connectDots : this.zConnectDots;
        const skipFloorColoring = Boolean(options.skipFloorColoring);
        const rpmColor = this.getLiveRpmColor(rpm, orderedRpms);
        const sorted = [...points].sort((a, b) => Number(a.height) - Number(b.height));
        const markerPalette = this._markerColorsForRpmTrace(sorted, torqueFloor, rpmColor, skipFloorColoring);
        const rpmLabel = Number(rpm).toFixed(3);
        return {
            label: `RPM ${rpmLabel}`,
            data: sorted.map((m) => ({
                x: Number(m.height),
                y: Number(m.rotational_drag),
                torque: Number(m.torque_percent),
            })),
            showLine: connectDots,
            borderColor: connectDots ? rpmColor : "transparent",
            borderWidth: connectDots ? 1.5 : 0,
            pointBackgroundColor: markerPalette.map((p) => p.fill),
            pointBorderColor: markerPalette.map((p) => p.line),
            pointBorderWidth: 1,
            pointRadius: 5,
            pointHoverRadius: 6,
        };
    }

    _buildTorqueDatasetForRpm(rpm, points, torqueFloor, orderedRpms) {
        const rpmColor = this.getLiveRpmColor(rpm, orderedRpms);
        const sorted = [...points].sort((a, b) => Number(a.height) - Number(b.height));
        const markerPalette = this._markerColorsForRpmTrace(sorted, torqueFloor, rpmColor);
        const rpmLabel = Number(rpm).toFixed(3);
        return {
            label: `RPM ${rpmLabel}`,
            data: sorted.map((m) => ({
                x: Number(m.height),
                y: Number(m.torque_percent),
            })),
            showLine: false,
            pointBackgroundColor: markerPalette.map((p) => p.fill),
            pointBorderColor: markerPalette.map((p) => p.line),
            pointBorderWidth: 1,
            pointRadius: 5,
            pointHoverRadius: 6,
        };
    }

    renderDragZRpmLegend(cellId, orderedRpms) {
        const listEl = this.el.dragZRpmLegend;
        if (!listEl) {
            return;
        }
        const floor = this._torqueFloorPctForLivePlots();
        if (this.el.dragZRpmLegendNote) {
            this.el.dragZRpmLegendNote.textContent =
                `Below torque floor (${floor}%): red (all RPMs)`;
        }
        if (!Number.isFinite(cellId) || !orderedRpms.length) {
            listEl.innerHTML = '<div class="rpm-legend-note">No RPMs configured</div>';
            return;
        }
        const statusMap = Number.isFinite(cellId)
            ? this.rpmTorqueStatusByCell.get(cellId)
            : null;
        listEl.innerHTML = orderedRpms.map((rpm) => {
            const color = this.getLiveRpmColor(rpm, orderedRpms);
            const label = Number(rpm).toFixed(3);
            const rpmKey = label;
            const dropped = statusMap?.get(rpmKey) === "dropped";
            const dotClass = dropped ? "rpm-status-dropped" : "rpm-status-active";
            const dotTitle = dropped ? "Dropped (torque limit)" : "Actively testing";
            return (
                `<div class="rpm-legend-row">`
                + `<span class="rpm-legend-swatch" style="background:${color}"></span>`
                + `<span class="rpm-legend-label">RPM ${label}</span>`
                + `<span class="rpm-status-dot ${dotClass}" title="${dotTitle}" aria-hidden="true"></span>`
                + `</div>`
            );
        }).join("");
    }

    refreshLivePlots(options = {}) {
        if (!this._shouldRefreshLiveCharts(options)) {
            if (!options.force) {
                this._liveChartsDirty = true;
            }
            return;
        }
        const activeCell = this.getActiveGraphCellId();
        const source = activeCell ? (this.measurementsByCell.get(activeCell) || []) : [];
        const torqueFloor = this._torqueFloorPctForLivePlots();

        let zData = source;
        if (this.zLatestOnly && source.length > 0) {
            const latestByHeightRpm = new Map();
            source.forEach((m) => {
                const key = `${Number(m.height).toFixed(3)}|${Number(m.rpm).toFixed(3)}`;
                const prev = latestByHeightRpm.get(key);
                if (!prev || (Number(m.timestamp) || 0) >= (Number(prev.timestamp) || 0)) {
                    latestByHeightRpm.set(key, m);
                }
            });
            zData = [...latestByHeightRpm.values()];
        }

        const orderedRpms = activeCell ? this.expandRpmsWithObserved(this.getRpmsForCell(activeCell), zData) : [];
        const buckets = this.partitionMeasurementsByRpm(zData, orderedRpms);

        const dragDatasets = orderedRpms
            .map((rpm) => {
                const key = Number(rpm).toFixed(3);
                const points = buckets.get(key) || [];
                if (points.length === 0) {
                    return null;
                }
                return this._buildDragDatasetForRpm(rpm, points, torqueFloor, orderedRpms);
            })
            .filter(Boolean);

        const torqueDatasets = orderedRpms
            .map((rpm) => {
                const key = Number(rpm).toFixed(3);
                const points = buckets.get(key) || [];
                if (points.length === 0) {
                    return null;
                }
                return this._buildTorqueDatasetForRpm(rpm, points, torqueFloor, orderedRpms);
            })
            .filter(Boolean);

        if (this.zPlotInitialized && this.charts.drag) {
            this.charts.drag.data.datasets = dragDatasets;
            if (this.el.zSparklineEmpty) {
                this.el.zSparklineEmpty.classList.toggle("hidden", dragDatasets.length > 0);
            }
            this.renderDragZRpmLegend(activeCell, orderedRpms);
        }

        if (this.torquePlotInitialized && this.charts.torque) {
            this.charts.torque.data.datasets = torqueDatasets;
            if (this.el.torqueZEmpty) {
                this.el.torqueZEmpty.classList.toggle("hidden", torqueDatasets.length > 0);
            }
        }

        if (this._renderPaused) {
            this._liveChartsDirty = true;
            return;
        }

        if (this.charts.drag) {
            this.charts.drag.update("none");
        }
        if (this.charts.torque) {
            this.charts.torque.update("none");
        }
        this._liveChartsDirty = false;
    }

    getActiveCalGraphCellId() {
        if (this.selectedCalGraphCell !== null) {
            return this.selectedCalGraphCell;
        }
        if (this.currentCell) {
            return this.currentCell;
        }
        const ids = this.getGraphCellIds();
        return ids.length ? ids[ids.length - 1] : null;
    }

    updateCalGraphCellTabs() {
        if (!this.el.calGraphCellTabs) {
            return;
        }
        const ids = this.getGraphCellIds();
        this.el.calGraphCellTabs.innerHTML = "";

        const currentBtn = document.createElement("button");
        currentBtn.className = `cell-tab${this.selectedCalGraphCell === null ? " active" : ""}`;
        currentBtn.textContent = "Current Cell";
        currentBtn.addEventListener("click", () => {
            this.selectedCalGraphCell = null;
            this.updateCalGraphCellTabs();
            this.refreshCalibrationLivePlots();
        });
        this.el.calGraphCellTabs.appendChild(currentBtn);

        ids.forEach((cellId) => {
            const btn = document.createElement("button");
            btn.className = `cell-tab${this.selectedCalGraphCell === cellId ? " active" : ""}`;
            btn.textContent = `Cell ${cellId}`;
            btn.addEventListener("click", () => {
                this.selectedCalGraphCell = cellId;
                this.updateCalGraphCellTabs();
                this.refreshCalibrationLivePlots();
            });
            this.el.calGraphCellTabs.appendChild(btn);
        });
    }

    renderCalDragZRpmLegend(cellId, orderedRpms) {
        const listEl = this.el.calDragZRpmLegend;
        if (!listEl) {
            return;
        }
        if (!Number.isFinite(cellId) || !orderedRpms.length) {
            listEl.innerHTML = '<div class="rpm-legend-note">No RPMs configured</div>';
            return;
        }
        listEl.innerHTML = orderedRpms.map((rpm) => {
            const color = this.getLiveRpmColor(rpm, orderedRpms);
            const label = Number(rpm).toFixed(3);
            return (
                `<div class="rpm-legend-row">`
                + `<span class="rpm-legend-swatch" style="background:${color}"></span>`
                + `<span class="rpm-legend-label">RPM ${label}</span>`
                + `</div>`
            );
        }).join("");
    }

    refreshCalibrationLivePlots(options = {}) {
        if (!this._shouldRefreshCalibrationCharts(options)) {
            if (!options.force) {
                this._liveChartsDirty = true;
            }
            return;
        }
        const activeCell = this.getActiveCalGraphCellId();
        const source = activeCell ? (this.measurementsByCell.get(activeCell) || []) : [];
        const orderedRpms = activeCell ? this.expandRpmsWithObserved(this.getRpmsForCell(activeCell), source) : [];
        const buckets = this.partitionMeasurementsByRpm(source, orderedRpms);

        const dragDatasets = orderedRpms
            .map((rpm) => {
                const key = Number(rpm).toFixed(3);
                const points = buckets.get(key) || [];
                if (points.length === 0) {
                    return null;
                }
                return this._buildDragDatasetForRpm(rpm, points, 0, orderedRpms, {
                    connectDots: this.zCalConnectDots,
                    skipFloorColoring: true,
                });
            })
            .filter(Boolean);

        if (this.calDragPlotInitialized && this.charts.calDrag) {
            this.charts.calDrag.data.datasets = dragDatasets;
            if (this.el.calZSparklineEmpty) {
                this.el.calZSparklineEmpty.classList.toggle("hidden", dragDatasets.length > 0);
            }
            this.renderCalDragZRpmLegend(activeCell, orderedRpms);
        }
        if (this.el.calDragZCellLabel) {
            this.el.calDragZCellLabel.textContent = activeCell ? `Cell ${activeCell}` : "All Cells";
        }

        if (this._renderPaused) {
            this._liveChartsDirty = true;
            return;
        }

        if (this.charts.calDrag) {
            this.charts.calDrag.update("none");
        }
    }

    _gaugeElementsForActiveTab() {
        if (this.activeTabId === "controls-tab" && this.el.gaugeValue && this.el.gaugeNeedle && this.el.gaugeText) {
            return [{
                gaugeValue: this.el.gaugeValue,
                gaugeNeedle: this.el.gaugeNeedle,
                gaugeText: this.el.gaugeText,
            }];
        }
        if (this.activeTabId === "calibrate-tab" && this.el.calGaugeValue && this.el.calGaugeNeedle && this.el.calGaugeText) {
            return [{
                gaugeValue: this.el.calGaugeValue,
                gaugeNeedle: this.el.calGaugeNeedle,
                gaugeText: this.el.calGaugeText,
            }];
        }
        if (this.activeTabId === "discovery-tab" && this.el.discoveryGaugeValue && this.el.discoveryGaugeNeedle && this.el.discoveryGaugeText) {
            return [{
                gaugeValue: this.el.discoveryGaugeValue,
                gaugeNeedle: this.el.discoveryGaugeNeedle,
                gaugeText: this.el.discoveryGaugeText,
            }];
        }
        return [];
    }

    _gaugeElementSets() {
        const sets = [];
        if (this.el.gaugeValue && this.el.gaugeNeedle && this.el.gaugeText) {
            sets.push({
                gaugeValue: this.el.gaugeValue,
                gaugeNeedle: this.el.gaugeNeedle,
                gaugeText: this.el.gaugeText,
            });
        }
        if (this.el.calGaugeValue && this.el.calGaugeNeedle && this.el.calGaugeText) {
            sets.push({
                gaugeValue: this.el.calGaugeValue,
                gaugeNeedle: this.el.calGaugeNeedle,
                gaugeText: this.el.calGaugeText,
            });
        }
        if (this.el.discoveryGaugeValue && this.el.discoveryGaugeNeedle && this.el.discoveryGaugeText) {
            sets.push({
                gaugeValue: this.el.discoveryGaugeValue,
                gaugeNeedle: this.el.discoveryGaugeNeedle,
                gaugeText: this.el.discoveryGaugeText,
            });
        }
        return sets;
    }

    _applyGaugeToElements(value, elements) {
        const pct = value / 200;
        const offset = this.gaugeArcLength * (1 - pct);
        const angle = -135 + 270 * pct;
        elements.gaugeValue.style.strokeDashoffset = String(offset);
        elements.gaugeNeedle.style.transform = `rotate(${angle}deg)`;
        elements.gaugeText.textContent = value.toFixed(1);
    }

    updateGauge(targetRPM, options = {}) {
        const clamped = Math.max(0, Math.min(100, targetRPM));
        const gaugeSets = this._gaugeElementsForActiveTab();
        if (!gaugeSets.length && !options.force) {
            return;
        }
        if (!gaugeSets.length) {
            return;
        }

        if (this.gaugeAnimationFrame) {
            cancelAnimationFrame(this.gaugeAnimationFrame);
        }

        if (this._renderPaused) {
            this.gaugeDisplayRPM = clamped;
            gaugeSets.forEach((elements) => this._applyGaugeToElements(clamped, elements));
            if (this.activeTabId === "controls-tab") {
                this.el.body.classList.toggle("spinning", clamped > 0.5);
            }
            return;
        }

        const start = this.gaugeDisplayRPM;
        const delta = clamped - start;
        const duration = 380;
        const startTime = performance.now();

        const animate = (t) => {
            const elapsed = t - startTime;
            const progress = Math.min(1, elapsed / duration);
            const eased = 1 - Math.pow(1 - progress, 3);
            const value = start + delta * eased;

            this.gaugeDisplayRPM = value;
            gaugeSets.forEach((elements) => this._applyGaugeToElements(value, elements));

            if (progress < 1) {
                this.gaugeAnimationFrame = requestAnimationFrame(animate);
            }
        };

        this.gaugeAnimationFrame = requestAnimationFrame(animate);
        if (this.activeTabId === "controls-tab") {
            this.el.body.classList.toggle("spinning", clamped > 0.5);
        }
    }

    updateTorqueBar(value) {
        const torquePercent = Number(value) || 0;
        const pct = Math.max(0, Math.min(100, torquePercent));
        this.el.torqueFill.style.height = `${pct}%`;
        this.el.torqueValue.textContent = `${torquePercent.toFixed(2)}%`;

        if (pct > 80) {
            this.el.torqueFill.style.background = "linear-gradient(180deg, rgb(255, 59, 48), rgb(185, 28, 18))";
        } else if (pct > 50) {
            this.el.torqueFill.style.background = "linear-gradient(180deg, rgb(255, 159, 10), rgb(148, 88, 0))";
        } else {
            this.el.torqueFill.style.background = "linear-gradient(180deg, rgb(48, 209, 88), rgb(21, 128, 49))";
        }
    }

    updateLiveTorqueDisplay(value) {
        this.currentTorquePercent = Number(value) || 0;
    }

    updateLiveRotationalDragDisplay(value) {
        const drag = Math.max(0, Number(value) || 0);
        if (this.el.rotationalDragDisplay) {
            this.el.rotationalDragDisplay.textContent = drag.toFixed(3);
        }
        if (this.el.dragLiveBox) {
            const intensity = Math.min(1.0, drag / 100);
            const r = Math.round(46 + 209 * intensity);
            const g = Math.round(160 - 150 * intensity);
            const b = Math.round(67 - 50 * intensity);
            this.el.dragLiveBox.style.background = `rgba(${r},${g},${b},0.22)`;
            this.el.dragLiveBox.style.borderColor = `rgba(${r},${g},${b},0.7)`;
        }
    }

    _performDragZSidebarElements() {
        return {
            rpm: this.el.sidebarRpm,
            secondDerivDrag: this.el.sidebarSecondDerivDrag,
            secondDerivCv: this.el.sidebarSecondDerivCv,
            secondDerivSlope: this.el.sidebarSecondDerivSlope,
            r2Drag: this.el.sidebarR2Drag,
            r2Cv: this.el.sidebarR2Cv,
            r2Slope: this.el.sidebarR2Slope,
            method2ndDerivDrag: this.el.sidebarMethod2ndDerivDrag,
            method2ndDerivCv: this.el.sidebarMethod2ndDerivCv,
            method2ndDerivSlope: this.el.sidebarMethod2ndDerivSlope,
            methodR2Drag: this.el.sidebarMethodR2Drag,
            methodR2Cv: this.el.sidebarMethodR2Cv,
            methodR2Slope: this.el.sidebarMethodR2Slope,
            confidence: this.el.sidebarConfidence,
            failSafe: this.el.sidebarFailSafe,
            hit: this.el.sidebarHit,
        };
    }

    _discoveryDragZSidebarElements() {
        return {
            rpm: this.el.discoverySidebarRpm,
            secondDerivDrag: this.el.discoverySidebarSecondDerivDrag,
            secondDerivCv: this.el.discoverySidebarSecondDerivCv,
            secondDerivSlope: this.el.discoverySidebarSecondDerivSlope,
            r2Drag: this.el.discoverySidebarR2Drag,
            r2Cv: this.el.discoverySidebarR2Cv,
            r2Slope: this.el.discoverySidebarR2Slope,
            method2ndDerivDrag: this.el.discoverySidebarMethod2ndDerivDrag,
            method2ndDerivCv: this.el.discoverySidebarMethod2ndDerivCv,
            method2ndDerivSlope: this.el.discoverySidebarMethod2ndDerivSlope,
            methodR2Drag: this.el.discoverySidebarMethodR2Drag,
            methodR2Cv: this.el.discoverySidebarMethodR2Cv,
            methodR2Slope: this.el.discoverySidebarMethodR2Slope,
            confidence: this.el.discoverySidebarConfidence,
            failSafe: this.el.discoverySidebarFailSafe,
            hit: this.el.discoverySidebarHit,
        };
    }

    _resetDragZSidebarElements(elements) {
        if (!elements) {
            return;
        }
        if (elements.rpm) elements.rpm.textContent = "-";
        if (elements.secondDerivDrag) elements.secondDerivDrag.textContent = "-";
        if (elements.secondDerivCv) elements.secondDerivCv.textContent = "-";
        if (elements.secondDerivSlope) elements.secondDerivSlope.textContent = "-";
        if (elements.r2Drag) elements.r2Drag.textContent = "-";
        if (elements.r2Cv) elements.r2Cv.textContent = "-";
        if (elements.r2Slope) elements.r2Slope.textContent = "-";
        if (elements.confidence) {
            elements.confidence.textContent = "-";
            elements.confidence.className = "sidebar-value mono";
        }
        if (elements.failSafe) {
            elements.failSafe.textContent = "No";
            elements.failSafe.className = "sidebar-value mono fail-safe-no";
        }
        if (elements.hit) {
            elements.hit.textContent = "No";
            elements.hit.className = "sidebar-value mono hit-no";
        }
    }

    _applyDragZSidebar(data, elements) {
        if (!data || !elements) {
            return;
        }
        if (elements.rpm) {
            elements.rpm.textContent = data.rpm != null ? `${Number(data.rpm).toFixed(2)} RPM` : "-";
        }
        const fmt = (v) => v != null && !Number.isNaN(Number(v)) ? Number(v).toFixed(4) : "-";
        const r2DragThreshold = Number(this.el.r2DragMin?.value ?? 0.975);
        const r2CvThreshold = Number(this.el.r2CvMin?.value ?? 0.975);
        const r2SlopeThreshold = Number(this.el.r2SlopeMin?.value ?? 0.975);
        if (elements.secondDerivDrag) elements.secondDerivDrag.textContent = fmt(data.second_derivative_drag);
        if (elements.secondDerivCv) elements.secondDerivCv.textContent = fmt(data.second_derivative_cv);
        if (elements.secondDerivSlope) elements.secondDerivSlope.textContent = fmt(data.second_derivative_slope);
        if (elements.r2Drag) elements.r2Drag.textContent = fmt(data.trend_r_squared);
        if (elements.r2Cv) elements.r2Cv.textContent = fmt(data.moving_r2_cv);
        if (elements.r2Slope) elements.r2Slope.textContent = fmt(data.moving_r2_slope);
        if (elements.methodR2Drag) elements.methodR2Drag.textContent = `Threshold ≥ ${r2DragThreshold.toFixed(3)}`;
        if (elements.methodR2Cv) elements.methodR2Cv.textContent = `Threshold ≥ ${r2CvThreshold.toFixed(3)}`;
        if (elements.methodR2Slope) elements.methodR2Slope.textContent = `Threshold ≥ ${r2SlopeThreshold.toFixed(3)}`;
        if (elements.method2ndDerivDrag) this.updateCalibrationBadge(elements.method2ndDerivDrag, Boolean(data.drag_sd2_calibrated));
        if (elements.method2ndDerivCv) this.updateCalibrationBadge(elements.method2ndDerivCv, Boolean(data.cv_sd2_calibrated));
        if (elements.method2ndDerivSlope) this.updateCalibrationBadge(elements.method2ndDerivSlope, Boolean(data.slope_sd2_calibrated));
        const hitThreshold = Number(this.el.hitPointConfidenceThreshold?.value ?? 0.8);
        const failSafeFloor = hitThreshold * 0.75;
        const confidenceRaw = Number(data.hit_confidence);
        const confidenceValid = Number.isFinite(confidenceRaw);
        const confidenceAboveFailSafeFloor = confidenceValid && confidenceRaw >= failSafeFloor;

        if (elements.confidence) {
            elements.confidence.textContent = fmt(data.hit_confidence);
            if (confidenceValid && confidenceRaw >= hitThreshold) {
                elements.confidence.className = "sidebar-value mono confidence-hit";
            } else if (confidenceAboveFailSafeFloor) {
                elements.confidence.className = "sidebar-value mono confidence-failsafe";
            } else {
                elements.confidence.className = "sidebar-value mono";
            }
        }

        if (elements.failSafe) {
            const isFailSafe = Boolean(data.fail_safe_active);
            elements.failSafe.textContent = isFailSafe ? "Yes" : "No";
            elements.failSafe.className = `sidebar-value mono ${isFailSafe ? "fail-safe-yes" : "fail-safe-no"}`;
        }

        if (elements.hit) {
            const isHit = Boolean(data.hit_detected);
            elements.hit.textContent = isHit ? "YES ⚠" : "No";
            elements.hit.className = `sidebar-value mono ${isHit ? "hit-yes" : "hit-no"}`;
        }
    }

    updateDragZSidebar(data) {
        if (this.activeTabId !== "controls-tab" || this._isDiscoveryRunActive()) {
            return;
        }
        this._applyDragZSidebar(data, this._performDragZSidebarElements());
    }

    updateDiscoveryDragZSidebar(data) {
        if (!this._isDiscoveryRunActive()) {
            return;
        }
        this._applyDragZSidebar(data, this._discoveryDragZSidebarElements());
    }

    setUiState(state) {
        this.uiState = state;

        const applyBtn = this.el.applySettings;
        const startBtn = this.el.startRun;
        const stopBtn = this.el.stopRun;
        const discApply = this.el.discoveryApplySettings;
        const discStart = this.el.discoveryStartRun;
        const discStop = this.el.discoveryStopRun;

        [applyBtn, startBtn, stopBtn, discApply, discStart, discStop].forEach((btn) => {
            if (btn) btn.classList.remove("is-active", "is-idle");
        });

        if (state === "idle") {
            if (applyBtn) { applyBtn.classList.add("is-active"); applyBtn.disabled = false; }
            if (startBtn) { startBtn.classList.add("is-idle"); startBtn.disabled = true; }
            if (stopBtn) { stopBtn.classList.add("is-idle"); stopBtn.disabled = true; }
            if (discApply) { discApply.classList.add("is-active"); discApply.disabled = false; }
            if (discStart) { discStart.classList.add("is-idle"); discStart.disabled = true; }
            if (discStop) { discStop.classList.add("is-idle"); discStop.disabled = true; }
            this.updateCalibrationReviewStartGuard();
            this.updateDiscoveryStartGuard();
        } else if (state === "ready") {
            if (applyBtn) { applyBtn.classList.add("is-idle"); applyBtn.disabled = false; }
            if (startBtn) { startBtn.classList.add("is-active"); startBtn.disabled = false; }
            if (stopBtn) { stopBtn.classList.add("is-idle"); stopBtn.disabled = true; }
            if (discApply) { discApply.classList.add("is-idle"); discApply.disabled = false; }
            if (discStart) { discStart.classList.add("is-active"); }
            if (discStop) { discStop.classList.add("is-idle"); discStop.disabled = true; }
            this.updateCalibrationReviewStartGuard();
            this.updateDiscoveryStartGuard();
        } else if (state === "running") {
            if (applyBtn) { applyBtn.classList.add("is-idle"); applyBtn.disabled = true; }
            if (startBtn) { startBtn.classList.add("is-idle"); startBtn.disabled = true; }
            if (stopBtn) { stopBtn.classList.add("is-active"); stopBtn.disabled = false; }
            if (discApply) { discApply.classList.add("is-idle"); discApply.disabled = true; }
            if (discStart) { discStart.classList.add("is-idle"); discStart.disabled = true; }
            if (discStop) { discStop.classList.add("is-active"); discStop.disabled = false; }
        }
        this.updateRunControlButtons();
    }

    _terminationDisplayMeta(reason) {
        const normalized = String(reason || "normal");
        if (normalized === "manual_terminate") {
            return { text: "Manual Termination", cls: "termination-manual" };
        }
        if (normalized === "hit_detected") {
            return { text: "Hitpoint Termination", cls: "termination-hitpoint" };
        }
        if (normalized === "fail_safe") {
            return { text: "Fail Safe Termination", cls: "termination-failsafe" };
        }
        if (normalized === "torque_limit") {
            return { text: "Torque Limit Termination", cls: "termination-manual" };
        }
        if (normalized === "user_stop") {
            return { text: "Experiment Stop", cls: "termination-hitpoint" };
        }
        return { text: "Completed", cls: "termination-normal" };
    }

    updateManualTerminateControl() {
        const isRegularRunning = this.isRunning && !this.calibrationModeActive && !this.recalibrationModeActive;
        const label = this.manualTerminateQueued
            ? "Stop Measurement in current cell (queued)"
            : "Stop Measurement in current cell";
        [this.el.terminateCurrentCell, this.el.discoveryTerminateCurrentCell].forEach((btn) => {
            if (!btn) return;
            btn.classList.toggle("hidden", !isRegularRunning);
            btn.disabled = !isRegularRunning || this.manualTerminateQueued;
            btn.textContent = label;
            btn.classList.toggle("is-active", isRegularRunning && !this.manualTerminateQueued);
            btn.classList.toggle("is-idle", !isRegularRunning || this.manualTerminateQueued);
        });
    }

    updateCalibrationStopControls() {
        const isCalRun = this.isRunning && this._isCalibrationLikeProtocolMode();
        const isRecal = Boolean(this.recalibrationModeActive);
        const stopLabel = isRecal ? "Stop Recalibration" : "Stop Calibration";
        const cellStopLabel = isRecal
            ? "Stop recalibration in this cell"
            : "Stop calibration in this cell";
        const cellStopQueuedLabel = isRecal
            ? "Stop recalibration in this cell (queued)"
            : "Stop calibration in this cell (queued)";

        if (this.el.calStopBtn) {
            this.el.calStopBtn.classList.toggle("hidden", !isCalRun);
            this.el.calStopBtn.disabled = !isCalRun;
            this.el.calStopBtn.textContent = stopLabel;
            this.el.calStopBtn.classList.toggle("is-active", isCalRun);
            this.el.calStopBtn.classList.toggle("is-idle", !isCalRun);
        }
        if (this.el.calTerminateCurrentCell) {
            this.el.calTerminateCurrentCell.classList.toggle("hidden", !isCalRun);
            this.el.calTerminateCurrentCell.disabled = !isCalRun || this.manualTerminateQueued;
            this.el.calTerminateCurrentCell.textContent = this.manualTerminateQueued
                ? cellStopQueuedLabel
                : cellStopLabel;
            this.el.calTerminateCurrentCell.classList.toggle("is-active", isCalRun && !this.manualTerminateQueued);
            this.el.calTerminateCurrentCell.classList.toggle("is-idle", !isCalRun || this.manualTerminateQueued);
        }
        const blocked = Boolean(this.calibrationReviewPending || this.experimentReviewPending);
        if (this.el.calStartBtn) {
            this.el.calStartBtn.disabled = this.isRunning || !this.calChecksComplete || blocked;
        }
        this.updateRecalibrationButtonState();
    }

    updateRunControlButtons() {
        this.updateManualTerminateControl();
        this.updateCalibrationStopControls();
    }

    updateLiveTerminationBadge() {
        const pill = this.el.liveTerminationPill;
        if (!pill) return;
        const candidateCell = Number.isInteger(this.selectedGraphCell)
            ? this.selectedGraphCell
            : (this.completedCells.size > 0 ? Math.max(...Array.from(this.completedCells)) : null);
        if (!candidateCell || !this.cellTerminationReasons.has(candidateCell)) {
            pill.classList.add("hidden");
            return;
        }
        const meta = this._terminationDisplayMeta(this.cellTerminationReasons.get(candidateCell));
        pill.className = `live-termination-pill ${meta.cls}`;
        pill.textContent = meta.text;
    }

    toggleCalibrationPanel(forceOpen = null) {
        if (forceOpen === true) {
            this.switchTab("calibrate-tab", { force: true });
        }
        this.calibrationPanelOpen = true;
    }

    _snapshotPreCalibrationSettings() {
        this._preCalibrationSettingsSnapshot = this.readControlSettings();
    }

    _applyCalibrationRunSettingsToDom() {
        if (this.el.feedbackEnabled) {
            this.el.feedbackEnabled.checked = true;
        }
        if (this.el.smartEarlyExitEnabled) {
            this.el.smartEarlyExitEnabled.checked = false;
        }
        if (this.el.failSafeEnabled) {
            this.el.failSafeEnabled.checked = false;
        }
        if (this.el.lowTorqueLiquidContactSkipEnabled) {
            this.el.lowTorqueLiquidContactSkipEnabled.checked = false;
        }
        this._setViscosityPredictionModeUI("off");
        this._updatePredictedViscosityChartsCardVisibility(false);
    }

    _buildCalibrationRunSettings() {
        this._snapshotPreCalibrationSettings();
        this._applyCalibrationRunSettingsToDom();
        const settings = this.readControlSettings();
        settings.feedback_control_enabled = true;
        settings.smart_early_exit_enabled = false;
        settings.fail_safe_enabled = false;
        settings.low_torque_liquid_contact_skip_enabled = false;
        settings.viscosity_prediction_mode = "off";
        settings.predicted_viscosity_enabled = false;
        return settings;
    }

    restorePreCalibrationSettings() {
        if (!this._preCalibrationSettingsSnapshot) {
            return Promise.resolve();
        }
        const snapshot = this._preCalibrationSettingsSnapshot;
        this._preCalibrationSettingsSnapshot = null;
        this.populateControlSettings(snapshot);
        if (this.uiState === "ready") {
            return this.applyControlSettings(true).catch(() => undefined);
        }
        return Promise.resolve();
    }

    updateCalibrationCellsStatusPill(summary) {
        const pill = this.el.calibrationCellsStatusPill;
        const text = this.el.calibrationCellsStatusText;
        if (!pill || !text) {
            return;
        }
        const count = Number(summary?.cell_count) || 0;
        text.textContent = `${count}/18 cells calibrated`;
        pill.classList.remove("cal-cells-status-all", "cal-cells-status-partial", "cal-cells-status-none");
        if (count >= 18) {
            pill.classList.add("cal-cells-status-all");
        } else if (count > 0) {
            pill.classList.add("cal-cells-status-partial");
        } else {
            pill.classList.add("cal-cells-status-none");
        }
    }

    validateCalibrationChecklist() {
        const empty = this.el.calCheckEmpty?.checked || false;
        this.calChecksComplete = empty;

        if (this.el.calActionHint) {
            this.el.calActionHint.textContent = this.calChecksComplete
                ? "Ready to calibrate all 18 cells"
                : "Complete the checklist above to enable calibration";
        }
        this.updateCalibrationStopControls();
    }

    applyCalibrationStatus(summary) {
        if (!summary) return;
        this.calibrationSummary = summary;
        this.updateCalibrationCellsStatusPill(summary);
        this.updateDiscoveryCalibrationPill(summary);
        this.updateZStartOffsetAvailability();
        if (this.activeTabId === "discovery-tab") {
            this.validateDiscoveryCells();
            this.rebuildDiscoveryEtaTable();
        }
        const isOk = Boolean(summary.is_calibrated);
        const section = this.el.calPanelSection;
        const pill = this.el.calStatusPill;
        const text = this.el.calStatusText;

        // Section glow
        if (section) {
            section.classList.toggle("cal-ok", isOk);
            section.classList.toggle("cal-none", !isOk);
        }

        // Pill style
        if (pill) {
            pill.classList.toggle("cal-status-ok", isOk);
            pill.classList.toggle("cal-status-none", !isOk);
        }
        if (text) {
            text.textContent = isOk
                ? `Per-Cell Z-Height Calibrated — ${summary.cell_count} cells`
                : "No Z-Height Per-Cell Calibration Performed";
        }

        // Existing calibration info block (column always visible)
        const detail = this.el.calExistingDetail;
        if (this.el.calExistingEmpty) {
            this.el.calExistingEmpty.classList.toggle("hidden", isOk);
        }
        if (this.el.calExistingContent) {
            this.el.calExistingContent.classList.toggle("hidden", !isOk);
        }
        if (isOk && summary.cells) {
            this.renderCalibrationDropdown(summary);
            this.renderSelectedCalibrationCellDetail();
        } else {
            if (this.el.calExistingSelect) this.el.calExistingSelect.innerHTML = "";
            if (detail) detail.textContent = "";
        }

        // Re-validate checklist (running state may have changed)
        this.validateCalibrationChecklist();
        this.updateCalibrationStopControls();
    }

    renderCalibrationDropdown(summary) {
        const select = this.el.calExistingSelect;
        if (!select || !summary) return;
        const allCellIds = Array.from({ length: 18 }, (_, idx) => idx + 1);
        const perCellTimes = summary.cell_calibrated_at || {};
        const globalTime = summary.calibrated_at;
        const previousValue = Number(select.value) || 1;
        const options = allCellIds.map((cellId) => {
            const rough = summary.cells?.[String(cellId)];
            const hasData = Number.isFinite(Number(rough));
            const calibratedAt = perCellTimes[String(cellId)] || globalTime;
            const timeLabel = calibratedAt ? new Date(calibratedAt).toLocaleString() : "N/A";
            const statusLabel = hasData ? "calibrated" : "not calibrated";
            return `<option value="${cellId}">Cell ${cellId} | ${statusLabel} | ${timeLabel}</option>`;
        });
        select.innerHTML = options.join("");
        const nextValue = allCellIds.includes(previousValue) ? previousValue : 1;
        select.value = String(nextValue);
    }

    renderSelectedCalibrationCellDetail() {
        const select = this.el.calExistingSelect;
        const detail = this.el.calExistingDetail;
        const summary = this.calibrationSummary;
        if (!select || !detail || !summary) return;
        const cellId = String(Number(select.value) || 1);
        const rough = summary.cells?.[cellId];
        const roughNum = Number(rough);
        const perCellTimes = summary.cell_calibrated_at || {};
        const calibratedAt = perCellTimes[cellId] || summary.calibrated_at;
        const timeLabel = calibratedAt ? new Date(calibratedAt).toLocaleString() : "N/A";
        if (!Number.isFinite(roughNum)) {
            detail.innerHTML = `Cell ${cellId}: no calibration saved yet<br>Calibrated at: ${timeLabel}`;
            return;
        }
        const safeZ = roughNum + 0.4;
        detail.innerHTML = `Cell ${cellId}: rough hitpoint ${roughNum.toFixed(3)} mm -> safe_z ${safeZ.toFixed(3)} mm<br>Calibrated at: ${timeLabel}`;
    }

    startCalibrationRun() {
        if (this.calibrationReviewPending || this.experimentReviewPending) {
            this.pushStatusMessage("Finish the data save review before starting a new run");
            return;
        }
        if (!this.calChecksComplete) {
            this.pushStatusMessage("Complete the calibration checklist before starting");
            return;
        }
        if (this.isRunning) {
            this.pushStatusMessage("A run is already in progress");
            return;
        }

        const settings = this._buildCalibrationRunSettings();
        settings.calibration_mode = true;
        settings.testing_mode = "full";  // Always all 18 cells

        this.isCalibrationRun = true;
        this._wasCalibrationLikeRun = true;
        this.setUiState("running");
        fetch("/api/run/start_calibration", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(settings)
        })
            .then((r) => r.json())
            .then((result) => {
                this.pushStatusMessage(result.status_message || "Calibration run started");
            })
            .catch(() => {
                this.isCalibrationRun = false;
                this._wasCalibrationLikeRun = false;
                this.restorePreCalibrationSettings();
                this.setUiState("idle");
                this.pushStatusMessage("Failed to start calibration run");
            });
    }

    handleRecalibrateToggle() {
        const isEnabled = this.el.calRecalibrateIndividual?.checked || false;
        if (isEnabled) {
            this.el.calCellSelectorContainer?.classList.remove("hidden");
            this.el.calStartBtn?.classList.add("hidden");
            this.el.calStartRecalibrationBtn?.classList.remove("hidden");
        } else {
            this.el.calCellSelectorContainer?.classList.add("hidden");
            this.el.calStartBtn?.classList.remove("hidden");
            this.el.calStartRecalibrationBtn?.classList.add("hidden");
            // Uncheck all cells and clear inputs
            this.el.calCellChecks.forEach((checkbox) => {
                checkbox.checked = false;
            });
            this.el.calCellZInputs.innerHTML = "";
            if (this.el.calRecalibrationIgnoreMaxZ) {
                this.el.calRecalibrationIgnoreMaxZ.checked = false;
            }
            this.updateRecalibrationButtonState();
        }
    }

    updateRecalibrationCellInputs() {
        // Get selected cells
        const selectedCells = [];
        this.el.calCellChecks.forEach((checkbox) => {
            if (checkbox.checked) {
                selectedCells.push(parseInt(checkbox.value));
            }
        });
        selectedCells.sort((a, b) => a - b);

        // Generate input fields for selected cells
        const container = this.el.calCellZInputs;
        container.innerHTML = "";
        selectedCells.forEach((cellId) => {
            const row = document.createElement("div");
            row.className = "cal-cell-z-input-row";
            row.innerHTML = `
                <label class="cal-cell-z-label">Cell ${cellId}</label>
                <input 
                    type="number" 
                    step="0.001" 
                    placeholder="Auto-detect" 
                    data-cell="${cellId}"
                    class="cal-cell-z-input"
                    title="Optional: custom starting Z-height for this cell"
                >
            `;
            container.appendChild(row);
        });
    }

    updateRecalibrationButtonState() {
        const selectedCells = [];
        this.el.calCellChecks.forEach((checkbox) => {
            if (checkbox.checked) {
                selectedCells.push(true);
            }
        });
        const hasSelected = selectedCells.length > 0;
        const blocked = Boolean(this.calibrationReviewPending || this.experimentReviewPending);
        if (this.el.calStartRecalibrationBtn) {
            this.el.calStartRecalibrationBtn.disabled =
                !hasSelected || this.isRunning || !this.calChecksComplete || blocked;
        }
    }

    startRecalibrationRun() {
        if (this.calibrationReviewPending || this.experimentReviewPending) {
            this.pushStatusMessage("Finish the data save review before starting a new run");
            return;
        }
        if (!this.calChecksComplete) {
            this.pushStatusMessage("Complete the calibration checklist before starting");
            return;
        }
        const selectedCells = [];
        this.el.calCellChecks.forEach((checkbox) => {
            if (checkbox.checked) {
                selectedCells.push(parseInt(checkbox.value));
            }
        });

        if (selectedCells.length === 0) {
            this.pushStatusMessage("Select at least one cell to recalibrate");
            return;
        }

        if (this.isRunning) {
            this.pushStatusMessage("A run is already in progress");
            return;
        }

        // Collect custom Z-heights for selected cells
        const recalibrationCells = {};
        selectedCells.forEach((cellId) => {
            const input = document.querySelector(`.cal-cell-z-input[data-cell="${cellId}"]`);
            const customZ = input?.value ? parseFloat(input.value) : null;
            recalibrationCells[cellId] = customZ;  // null means auto-detect
        });

        const settings = this._buildCalibrationRunSettings();
        settings.recalibrate_individual_cells = true;
        settings.recalibration_cells = recalibrationCells;
        settings.recalibration_ignore_max_z_travel = Boolean(
            this.el.calRecalibrationIgnoreMaxZ?.checked
        );
        settings.calibration_mode = false;  // Not full calibration mode
        settings.testing_mode = "custom";
        settings.selected_cells = selectedCells;

        this.isCalibrationRun = true;
        this._wasCalibrationLikeRun = true;
        this.setUiState("running");
        fetch("/api/run/start_recalibration", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(settings)
        })
            .then((r) => r.json())
            .then((result) => {
                this.pushStatusMessage(result.status_message || "Individual cell recalibration started");
            })
            .catch(() => {
                this.isCalibrationRun = false;
                this._wasCalibrationLikeRun = false;
                this.restorePreCalibrationSettings();
                this.setUiState("idle");
                this.pushStatusMessage("Failed to start recalibration run");
            });
    }

    updateCalibrationBadge(node, isCalibrated) {
        if (!node) return;
        node.textContent = isCalibrated ? "AUTO Z-SCORE (active)" : "AUTO Z-SCORE (calibrating...)";
        node.classList.toggle("calibrated", isCalibrated);
        node.classList.toggle("calibrating", !isCalibrated);
    }

    updateMeasuringZDisplay(value) {
        this.currentMeasuringZ = value;
        const text = `${value.toFixed(3)} mm`;
        if (this.el.zMeasuringDisplay) {
            this.el.zMeasuringDisplay.textContent = text;
        }
        if (this.el.calZMeasuringDisplay) {
            this.el.calZMeasuringDisplay.textContent = text;
        }
        if (this.el.discoveryZMeasuringDisplay) {
            this.el.discoveryZMeasuringDisplay.textContent = text;
        }
    }

    setInstrumentStatus(name, connected) {
        const map = {
            cnc: this.el.cncStatus,
            viscometer: this.el.viscometerStatus,
            pump: this.el.pumpStatus
        };
        const node = map[name];
        if (!node) {
            return;
        }
        node.classList.toggle("connected", connected);
        node.classList.toggle("disconnected", !connected);
        const stateEl = node.querySelector(".instrument-state");
        if (stateEl) {
            stateEl.textContent = connected ? "initialized" : "not yet initialized";
        }
    }

    addPointToChart(cellId, height, rotationalDrag, rpm, timestamp, hitDetected = null) {
        this.ingestMeasurement({
            cell_id: cellId,
            height,
            rotational_drag: rotationalDrag,
            rpm,
            timestamp,
            hit_detected: hitDetected,
        }, false);
    }

    computeSummaryHitPointHeight(points) {
        if (!Array.isArray(points) || points.length < 4) {
            return null;
        }
        const ordered = [...points].sort((a, b) => Number(b.height) - Number(a.height));
        let hitHeight = null;
        for (let i = 0; i <= ordered.length - 4; i += 1) {
            const isNo = ordered[i]?.hit_detected === false;
            const nextThreeYes = ordered[i + 1]?.hit_detected === true
                && ordered[i + 2]?.hit_detected === true
                && ordered[i + 3]?.hit_detected === true;
            if (isNo && nextThreeYes) {
                hitHeight = Number(ordered[i].height);
            }
        }
        return Number.isFinite(hitHeight) ? hitHeight : null;
    }

    setRunningState(isRunning, previousOverride = null) {
        const previous = typeof previousOverride === "boolean" ? previousOverride : this.isRunning;
        this.isRunning = isRunning;

        this.el.runPill.textContent = isRunning ? "RUNNING" : "IDLE";
        this.el.runPill.classList.toggle("running", isRunning);
        this.el.runPill.classList.toggle("idle", !isRunning);
        this.el.body.classList.toggle("running", isRunning);

        if (isRunning && !previous) {
            const snapshot = this._getRunSettingsForHistorySave();
            this.runSaveAllSampleData = Boolean(snapshot.save_all_sample_data);
            this.dwellSeriesByCell.clear();
            this.dwellZVisibility.clear();
            this._updateSaveAllSampleDataUI(this.runSaveAllSampleData);
            this.cellStart = Date.now();
            this.isSavingFinalResults = false;
            this.measuredCells.clear();
            this.completedCells.clear();
            this.cellTerminationReasons.clear();
            this.washingCell = null;
            this._pendingCompletedCell = null;
            this.protocolCurrentStepId = "init";
            this.protocolLastStatusMessage = "";
            this._protocolRenderedMode = null;
            this.currentPhase = 0;
            this.updateTimeline();
            this.updateCompletionBar();
            this._hideExperimentCompleteMessage();
            this._hideExperimentTerminatedMessage();
            if (this.el.elapsed) {
                this.el.elapsed.textContent = "00:00:00";
            }
            if (this.el.calElapsed) {
                this.el.calElapsed.textContent = "00:00:00";
            }
            this.setControlStatus("Run active");
            this.manualTerminateQueued = false;
            this.updateRunControlButtons();
        }

        if (isRunning && this.uiState !== "running") {
            this.setUiState("running");
        }
        this.updateTestingTabAvailability();
        this.updateRunTabAvailability();
        this.updateZStartOffsetAvailability();
        if (isRunning && !previous) {
            this.warnAndStopTestingForRunTransition();
            if (!this._isDiscoveryRunActive()) {
                this._cancelDiscoveryPlotRefresh();
            }
            const mode = this.getProtocolRunMode();
            if (mode === "calibration" || mode === "recalibration") {
                this.switchTab("calibrate-tab", { force: true });
            } else if (mode === "discovery") {
                this.switchTab("discovery-tab", { force: true });
            } else if (mode === "regular") {
                this.switchTab("controls-tab", { force: true });
            }
        }

        if (!isRunning && previous) {
            this.discoveryModeActive = false;
            this.updateDiscoveryStartGuard();
        }

        if (!isRunning) {
            this.runSaveAllSampleData = false;
            this._updateSaveAllSampleDataUI(Boolean(this.el.saveAllSampleData?.checked));
            this.washingCell = null;
            this.manualTerminateQueued = false;
            this.updateRunControlButtons();
            if (previous) {
                this.playChime(720, 0.14);
                this.setControlStatus("Run stopped");
                this.protocolCurrentStepId = "done";
                this.currentPhase = 6;
                this.updateTimeline();
                setTimeout(() => {
                    this.protocolCurrentStepId = "idle";
                    this.protocolLastStatusMessage = "";
                    this._protocolRenderedMode = null;
                    this.currentPhase = 0;
                    this.washingCell = null;
                    this._finalizePendingCompletedCell();
                    this.updateTimeline();
                    this.updateCellVisuals();
                }, 3000);
            }
            this.updateCompletionBar();
            if (this.uiState === "running") {
                this.setUiState("idle");
            }
            if (this._wasCalibrationLikeRun) {
                this.restorePreCalibrationSettings();
                this._wasCalibrationLikeRun = false;
            }
            this.isCalibrationRun = false;
        }

        this.updateCalibrationStopControls();
        this.updateLiveTerminationBadge();
    }

    bindTestingControls() {
        if (!this.el.testingActionButtons) {
            return;
        }
        this.el.testingActionButtons.forEach((btn) => {
            btn.addEventListener("click", () => {
                const device = btn.dataset.testingDevice;
                const action = btn.dataset.testingAction;
                this.handleTestingAction(device, action);
            });
        });
        this.updateTestingUi();
        this.updateTestingTabAvailability();
    }

    fetchTestingStatus() {
        fetch("/api/testing/status")
            .then((response) => response.json())
            .then((status) => this.applyTestingStatus(status))
            .catch(() => this.pushStatusMessage("Failed to fetch testing status"));
    }

    applyTestingStatus(status) {
        if (!status || typeof status !== "object") {
            return;
        }
        this.testingBackendBusy = Boolean(status.busy);
        this.testingSessionConnected = Boolean(status.connected);
        this.testingSessionLastError = status.last_error || null;
        if (status.devices && typeof status.devices === "object") {
            this.testingDeviceStates = {
                ...this.testingDeviceStates,
                ...status.devices,
            };
        }
        if (this.el.testingRunLockPill && !this.isRunning) {
            this.el.testingRunLockPill.textContent = this.testingSessionConnected
                ? "Idle - Testing connected"
                : "Idle - Testing ready (auto-connect on action)";
        }
        this.updateTestingUi();
    }

    updateTestingTabAvailability() {
        if (this.el.testingTabButton) {
            this.el.testingTabButton.classList.toggle("is-disabled", this.isRunning);
            this.el.testingTabButton.disabled = this.isRunning;
        }
        if (this.el.testingRunLockPill) {
            this.el.testingRunLockPill.classList.toggle("idle", !this.isRunning);
            this.el.testingRunLockPill.classList.toggle("running", this.isRunning);
            this.el.testingRunLockPill.textContent = this.isRunning
                ? "Run active - Testing locked"
                : "Idle - Testing enabled";
        }
        if (this.isRunning) {
            this.el.testingActionButtons?.forEach((btn) => {
                btn.disabled = true;
                btn.classList.remove("is-active");
                btn.classList.add("is-idle");
            });
        } else {
            this.updateTestingUi();
        }
    }

    async handleTestingAction(device, action) {
        if (!device || !action) {
            return;
        }
        if (this.isRunning) {
            this.pushStatusMessage("Testing is unavailable during an active run");
            return;
        }
        const requestKey = `${device}:${action}`;
        if (this.testingRequestInFlight.has(requestKey)) {
            return;
        }
        this.testingRequestInFlight.add(requestKey);
        const optimisticState = action === "start" ? "pending" : "idle";
        this.testingDeviceStates[device] = optimisticState;
        this.updateTestingUi();
        try {
            const response = await fetch(`/api/testing/${action}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ device }),
            });
            const payload = await response.json();
            if (!response.ok || !payload.ok) {
                this.testingDeviceStates[device] = "error";
                this.updateTestingUi();
                const fallback = `Testing ${action} failed for ${device.replace(/_/g, " ")}`;
                this.pushStatusMessage(payload.error || this.testingSessionLastError || fallback);
                return;
            }
            this.applyTestingStatus(payload.testing_status);
            this.pushStatusMessage(`Testing: ${action} ${device.replace(/_/g, " ")}`);
        } catch {
            this.testingDeviceStates[device] = "error";
            this.updateTestingUi();
            this.pushStatusMessage(`Testing request failed for ${device.replace(/_/g, " ")}`);
        } finally {
            this.testingRequestInFlight.delete(requestKey);
            this.updateTestingUi();
        }
    }

    async warnAndStopTestingForRunTransition() {
        if (this.testingGateInProgress) {
            return;
        }
        const activeTab = document.querySelector(".tab-button.active")?.dataset?.tab;
        const hasActiveTestingDevice = Object.values(this.testingDeviceStates).some((state) =>
            state === "running" || state === "pending" || state === "error"
        );
        if (activeTab !== "testing-tab" && !hasActiveTestingDevice) {
            return;
        }
        this.testingGateInProgress = true;
        window.confirm("A viscometry run has started. Testing controls will now stop all test hardware and exit the Testing tab.");
        this.pushStatusMessage("Run started - stopping all testing devices");
        try {
            const response = await fetch("/api/testing/stop_all", { method: "POST" });
            const payload = await response.json();
            this.applyTestingStatus(payload.testing_status);
            if (!payload.ok) {
                this.pushStatusMessage("Warning: some testing devices did not stop cleanly");
            }
        } catch {
            this.pushStatusMessage("Warning: failed to stop testing devices automatically");
        } finally {
            if (activeTab === "testing-tab") {
                this.switchTab("layout-tab");
            }
            this.testingGateInProgress = false;
        }
    }

    updateTestingUi() {
        const stateToLabel = {
            idle: "Idle",
            pending: "Switching...",
            running: "Running",
            error: "Error",
        };
        const statusMap = {
            washing_rotor: this.el.testingStatusWashingRotor,
            drying_rotor: this.el.testingStatusDryingRotor,
            filling_pump: this.el.testingStatusFillingPump,
            draining_pump: this.el.testingStatusDrainingPump,
        };

        this.el.testingDevices?.forEach((card) => {
            const device = card.dataset.device;
            const state = this.testingDeviceStates[device] || "idle";
            card.classList.toggle("is-running", state === "running");
            card.classList.toggle("is-pending", state === "pending");
            card.classList.toggle("is-error", state === "error");
        });

        Object.entries(statusMap).forEach(([device, node]) => {
            if (!node) return;
            const state = this.testingDeviceStates[device] || "idle";
            node.textContent = stateToLabel[state] || "Idle";
        });

        this.el.testingActionButtons?.forEach((btn) => {
            const device = btn.dataset.testingDevice;
            const action = btn.dataset.testingAction;
            const state = this.testingDeviceStates[device] || "idle";
            const isRequestActive = this.testingRequestInFlight.has(`${device}:start`) || this.testingRequestInFlight.has(`${device}:stop`);
            btn.disabled = this.isRunning || isRequestActive;
            const isActiveAction =
                (action === "start" && state === "idle") ||
                (action === "stop" && state === "running");
            btn.classList.toggle("is-active", isActiveAction);
            btn.classList.toggle("is-idle", !isActiveAction);
        });
    }

    initSummaryPlot() {
        if (!this.el.summaryPlot) {
            return;
        }
        const summaryBase = this._buildLivePlotLayout({
            yTitle: "Rotational Drag (torque / RPM)",
            showLegend: true,
        });
        this.summaryPlotLayout = {
            ...summaryBase,
            showlegend: true,
            xaxis: {
                ...summaryBase.xaxis,
                title: "Z-Height (mm) - descent ->",
                autorange: true,
                tickformat: ".3f",
            },
            yaxis: {
                ...summaryBase.yaxis,
                rangemode: "tozero",
            },
            margin: { t: 20, r: 16, b: 56, l: 64 },
            legend: { ...summaryBase.legend, orientation: "h", y: -0.22 },
        };
        Plotly.newPlot(this.el.summaryPlot, [], this.summaryPlotLayout,
            { responsive: true, displayModeBar: false });
        this.summaryPlotInitialized = true;
    }

    loadExperimentHistory() {
        fetch("/api/experiment_history")
            .then((response) => response.json())
            .then((history) => {
                const loaded = Array.isArray(history) ? history : [];
                this.experimentHistory = this._dedupeExperimentHistoryList(loaded);
                this.renderExperimentCards();
                this.renderLoadOldExperimentList();
            })
            .catch(() => {
                this.experimentHistory = [];
                this.renderExperimentCards();
                this.renderLoadOldExperimentList();
            });
    }

    _setLoadOldExperimentStatus(message, type = "") {
        const el = this.el.loadOldExperimentStatus;
        if (!el) {
            return;
        }
        el.textContent = message || "";
        el.classList.remove("is-error", "is-success");
        if (type === "error") {
            el.classList.add("is-error");
        } else if (type === "success") {
            el.classList.add("is-success");
        }
    }

    _sanitizeSettingsFromHistory(raw) {
        if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
            return null;
        }
        let cloned;
        try {
            cloned = JSON.parse(JSON.stringify(raw));
        } catch {
            return null;
        }

        const whitelist = new Set([
            "experiment_name",
            "testing_mode",
            "test_rpms",
            "selected_rows",
            "selected_cells",
            "z_step_size",
            "measurement_duration",
            "sample_interval",
            "dwell_seconds",
            "inter_rpm_pause",
            "torque_break_threshold",
            "feedback_control_enabled",
            "smart_early_exit_enabled",
            "fail_safe_enabled",
            "smart_cv_threshold",
            "smart_window_size",
            "low_torque_liquid_contact_skip_enabled",
            "low_torque_liquid_contact_threshold_pct",
            "r2_drag_min",
            "r2_cv_min",
            "r2_slope_min",
            "hit_point_confidence_threshold",
            "weight_2nd_deriv_drag",
            "weight_2nd_deriv_cv",
            "weight_2nd_deriv_slope",
            "weight_r2_drag",
            "weight_r2_cv",
            "weight_r2_slope",
            "baseline_n_calibration",
            "baseline_z_threshold",
            "min_data_points_for_trend",
            "viscosity_prediction_mode",
            "predicted_viscosity_enabled",
            "save_all_sample_data",
            "z_start_offset_mm",
            "cell_rpm_map",
            "cell_content_map",
        ]);

        const out = {};
        whitelist.forEach((key) => {
            if (Object.prototype.hasOwnProperty.call(cloned, key)) {
                out[key] = cloned[key];
            }
        });

        const parseNumList = (value) => {
            if (Array.isArray(value)) {
                return value.map((v) => Number(v)).filter((n) => Number.isFinite(n));
            }
            if (typeof value === "string") {
                return value.split(",")
                    .map((s) => Number(s.trim()))
                    .filter((n) => Number.isFinite(n));
            }
            return [];
        };

        const parseIntList = (value) => {
            if (Array.isArray(value)) {
                return value.map((v) => Number.parseInt(v, 10)).filter((n) => Number.isFinite(n));
            }
            if (typeof value === "string") {
                return value.split(",")
                    .map((s) => Number.parseInt(s.trim(), 10))
                    .filter((n) => Number.isFinite(n));
            }
            return [];
        };

        if (out.test_rpms != null) {
            const rpms = parseNumList(out.test_rpms);
            if (rpms.length > 0) {
                out.test_rpms = rpms;
            } else {
                delete out.test_rpms;
            }
        }
        if (out.selected_rows != null) {
            const rows = parseIntList(out.selected_rows);
            if (rows.length > 0) {
                out.selected_rows = rows;
            } else {
                delete out.selected_rows;
            }
        }
        if (out.selected_cells != null) {
            const cells = parseIntList(out.selected_cells);
            if (cells.length > 0) {
                out.selected_cells = cells;
            } else {
                delete out.selected_cells;
            }
        }

        if (out.cell_rpm_map != null && typeof out.cell_rpm_map === "object" && !Array.isArray(out.cell_rpm_map)) {
            const parsed = {};
            Object.entries(out.cell_rpm_map).forEach(([cellKey, rpmVal]) => {
                const rpms = parseNumList(rpmVal);
                if (rpms.length > 0) {
                    parsed[String(cellKey)] = rpms;
                }
            });
            out.cell_rpm_map = parsed;
        } else {
            delete out.cell_rpm_map;
        }

        if (out.cell_content_map != null && typeof out.cell_content_map === "object" && !Array.isArray(out.cell_content_map)) {
            const parsed = {};
            Object.entries(out.cell_content_map).forEach(([cellKey, label]) => {
                const text = String(label ?? "").trim();
                if (text.length > 0) {
                    parsed[String(cellKey)] = text;
                }
            });
            out.cell_content_map = parsed;
        } else {
            delete out.cell_content_map;
        }

        const floatKeys = [
            "z_step_size", "measurement_duration", "sample_interval", "dwell_seconds",
            "inter_rpm_pause", "torque_break_threshold", "smart_cv_threshold",
            "r2_drag_min", "r2_cv_min", "r2_slope_min", "hit_point_confidence_threshold",
            "weight_2nd_deriv_drag", "weight_2nd_deriv_cv", "weight_2nd_deriv_slope",
            "weight_r2_drag", "weight_r2_cv", "weight_r2_slope", "baseline_z_threshold",
            "low_torque_liquid_contact_threshold_pct",
        ];
        floatKeys.forEach((key) => {
            if (out[key] != null && out[key] !== "") {
                const n = Number(out[key]);
                if (Number.isFinite(n)) {
                    out[key] = n;
                } else {
                    delete out[key];
                }
            }
        });

        const intKeys = ["smart_window_size", "baseline_n_calibration", "min_data_points_for_trend"];
        intKeys.forEach((key) => {
            if (out[key] != null && out[key] !== "") {
                const n = Number.parseInt(out[key], 10);
                if (Number.isFinite(n)) {
                    out[key] = n;
                } else {
                    delete out[key];
                }
            }
        });

        const boolKeys = [
            "feedback_control_enabled",
            "smart_early_exit_enabled",
            "fail_safe_enabled",
            "low_torque_liquid_contact_skip_enabled",
        ];
        boolKeys.forEach((key) => {
            if (out[key] != null) {
                out[key] = Boolean(out[key]);
            }
        });

        if (typeof out.experiment_name === "string") {
            out.experiment_name = out.experiment_name.trim();
        }
        if (out.testing_mode != null) {
            out.testing_mode = String(out.testing_mode);
        }

        const hasCore =
            (out.experiment_name && out.experiment_name.length > 0)
            || (Array.isArray(out.selected_cells) && out.selected_cells.length > 0)
            || (Array.isArray(out.test_rpms) && out.test_rpms.length > 0)
            || (out.cell_rpm_map && Object.keys(out.cell_rpm_map).length > 0)
            || (out.cell_content_map && Object.keys(out.cell_content_map).length > 0)
            || out.testing_mode != null;

        return hasCore ? out : null;
    }

    renderLoadOldExperimentList() {
        const listEl = this.el.loadOldExperimentList;
        const btn = this.el.loadOldExperimentBtn;
        if (!listEl) {
            return;
        }

        if (!Array.isArray(this.experimentHistory) || this.experimentHistory.length === 0) {
            listEl.innerHTML = "<p class=\"load-old-experiment-empty\">No saved experiments yet.</p>";
            this.selectedLoadExperimentId = null;
            if (btn) {
                btn.disabled = true;
            }
            return;
        }

        const selectedStillExists = this.experimentHistory.some(
            (e) => e.id === this.selectedLoadExperimentId
        );
        if (!selectedStillExists) {
            this.selectedLoadExperimentId = null;
        }

        listEl.innerHTML = "";
        this.experimentHistory.forEach((exp) => {
            const card = document.createElement("div");
            card.className = `experiment-card${exp.id === this.selectedLoadExperimentId ? " active" : ""}`;
            card.dataset.experimentId = exp.id;
            card.innerHTML = this._buildExperimentCardInnerHtml(exp);
            card.addEventListener("click", () => {
                this.selectedLoadExperimentId = exp.id;
                this.renderLoadOldExperimentList();
                this._setLoadOldExperimentStatus("");
            });
            listEl.appendChild(card);
        });

        if (btn) {
            btn.disabled = !this.selectedLoadExperimentId;
        }
    }

    _escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = String(text ?? "");
        return div.innerHTML;
    }

    loadSelectedExperimentIntoDesign() {
        if (this.isRunning) {
            this._setLoadOldExperimentStatus("Cannot load while a run is active.", "error");
            return;
        }
        if (!this.selectedLoadExperimentId) {
            return;
        }

        const applyFromEntry = (exp) => {
            if (!exp || !exp.settings) {
                this._setLoadOldExperimentStatus("Unable to load experiment", "error");
                return;
            }
            const settings = this._sanitizeSettingsFromHistory(exp.settings);
            if (!settings) {
                this._setLoadOldExperimentStatus("Unable to load experiment", "error");
                return;
            }
            try {
                this.populateControlSettings(settings);
            } catch {
                this._setLoadOldExperimentStatus("Unable to load experiment", "error");
                return;
            }
            const name = settings.experiment_name || "(unnamed)";
            const dateStr = exp.created_at
                ? new Date(exp.created_at).toLocaleString()
                : "";
            this._setLoadOldExperimentStatus(
                `Loaded "${name}"${dateStr ? ` (${dateStr})` : ""} — edit if needed, then Apply Settings.`,
                "success"
            );
            this.setControlStatus("Experiment settings loaded from history (not applied yet)");
        };

        let exp = this.experimentHistory.find((e) => e.id === this.selectedLoadExperimentId);
        if (exp) {
            applyFromEntry(exp);
            return;
        }

        fetch("/api/experiment_history")
            .then((response) => response.json())
            .then((history) => {
                this.experimentHistory = Array.isArray(history) ? history : [];
                this.renderExperimentCards();
                this.renderLoadOldExperimentList();
                exp = this.experimentHistory.find((e) => e.id === this.selectedLoadExperimentId);
                if (!exp) {
                    this._setLoadOldExperimentStatus("Unable to load experiment", "error");
                    return;
                }
                applyFromEntry(exp);
            })
            .catch(() => {
                this._setLoadOldExperimentStatus("Unable to load experiment", "error");
            });
    }

    saveExperimentHistoryEntry(entry) {
        return fetch("/api/experiment_history", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(entry)
        });
    }

    _captureRunSettingsSnapshot() {
        if (!this.readControlSettings) {
            return;
        }
        try {
            this.runSettingsSnapshot = JSON.parse(JSON.stringify(this.readControlSettings()));
        } catch {
            this.runSettingsSnapshot = this.readControlSettings();
        }
    }

    _getRunSettingsForHistorySave() {
        if (this.runSettingsSnapshot && typeof this.runSettingsSnapshot === "object") {
            try {
                return JSON.parse(JSON.stringify(this.runSettingsSnapshot));
            } catch {
                return this.runSettingsSnapshot;
            }
        }
        if (this.latestControlSettings && Object.keys(this.latestControlSettings).length > 0) {
            try {
                return JSON.parse(JSON.stringify(this.latestControlSettings));
            } catch {
                return this.latestControlSettings;
            }
        }
        return this.readControlSettings ? this.readControlSettings() : {};
    }

    _predictedViscosityEntryHasData(predData) {
        if (!predData || typeof predData !== "object") {
            return false;
        }
        return Object.entries(predData).some(([cellKey, rpmMap]) => {
            if (!rpmMap || typeof rpmMap !== "object") {
                return false;
            }
            return Object.keys(rpmMap).some((k) => this._isPredictedViscosityRpmKey(k));
        });
    }

    _isPredictedViscosityRpmKey(key) {
        return key !== this.predictedViscositySummaryKey && Number.isFinite(Number(key));
    }

    _getPredictedViscositySummary(cellId) {
        const rpmMap = this.predictedViscosityData[cellId];
        if (!rpmMap || typeof rpmMap !== "object") {
            return null;
        }
        const summary = rpmMap[this.predictedViscositySummaryKey];
        return summary && typeof summary === "object" ? summary : null;
    }

    _buildRegimeBadgeHtml(regime) {
        if (!regime) {
            return "";
        }
        const slug = String(regime).toLowerCase().replace(/\s+/g, "-");
        const label = String(regime).replace(/-/g, " ");
        return `<span class="rheology-regime-badge regime-${slug}">${label}</span>`;
    }

    _experimentHistoryIdForRun(runStartTsSec) {
        const ts = Number(runStartTsSec);
        if (Number.isFinite(ts) && ts > 0) {
            return `exp-${Math.floor(ts * 1000)}`;
        }
        return `exp-${Date.now()}`;
    }

    _runStartTsMatches(a, b, eps = 0.001) {
        const fa = Number(a);
        const fb = Number(b);
        return Number.isFinite(fa) && Number.isFinite(fb) && fa > 0 && fb > 0 && Math.abs(fa - fb) < eps;
    }

    _experimentHistoryEntryRank(entry) {
        const hasCsv = entry?.csv_filename ? 1 : 0;
        const count = Number(entry?.measurement_count) || 0;
        const created = Number(entry?.created_at) || 0;
        return [hasCsv, count, created];
    }

    _dedupeExperimentHistoryList(entries) {
        if (!Array.isArray(entries)) {
            return [];
        }
        const noRunKey = [];
        const byRunStart = new Map();
        entries.forEach((entry) => {
            if (!entry || typeof entry !== "object") {
                return;
            }
            const runStart = Number(entry.runStartTsSec);
            if (!Number.isFinite(runStart) || runStart <= 0) {
                noRunKey.push(entry);
                return;
            }
            const key = runStart.toFixed(3);
            const existing = byRunStart.get(key);
            if (!existing) {
                byRunStart.set(key, entry);
                return;
            }
            const rankNew = this._experimentHistoryEntryRank(entry);
            const rankOld = this._experimentHistoryEntryRank(existing);
            if (rankNew[0] > rankOld[0]
                || (rankNew[0] === rankOld[0] && rankNew[1] > rankOld[1])
                || (rankNew[0] === rankOld[0] && rankNew[1] === rankOld[1] && rankNew[2] > rankOld[2])) {
                byRunStart.set(key, entry);
            }
        });
        const merged = [...byRunStart.values(), ...noRunKey];
        merged.sort((a, b) => (Number(b.created_at) || 0) - (Number(a.created_at) || 0));
        return merged.slice(0, 40);
    }

    _upsertExperimentHistoryEntry(entry) {
        const id = entry?.id;
        const runStart = Number(entry?.runStartTsSec);
        this.experimentHistory = this.experimentHistory.filter((e) => {
            if (id && e.id === id) {
                return false;
            }
            if (Number.isFinite(runStart) && runStart > 0
                && this._runStartTsMatches(e.runStartTsSec, runStart)) {
                return false;
            }
            return true;
        });
        this.experimentHistory.unshift(entry);
        this.experimentHistory = this.experimentHistory.slice(0, 40);
    }

    saveCompletedExperiment() {
        if (this.completedSaveLock) {
            return;
        }
        this.completedSaveLock = true;

        const runStartTsSec = Number.isFinite(this.lastRunStartTsSec)
            ? this.lastRunStartTsSec
            : (Number.isFinite(this.experimentStart) ? this.experimentStart / 1000 : null);
        let runData = this.measurements.slice(this.runMeasurementStartIndex);
        if (Number.isFinite(runStartTsSec)) {
            runData = runData.filter((m) => Number(m.timestamp) >= runStartTsSec);
        }
        if (runData.length === 0) {
            this.completedSaveLock = false;
            return;
        }

        const latestByKey = new Map();
        runData.forEach((m) => {
            const k = `${m.cell_id}|${Number(m.height).toFixed(3)}|${m.rpm}`;
            latestByKey.set(k, m);
        });

        const cells = [...new Set(runData.map((m) => m.cell_id))].sort((a, b) => a - b);
        const rpms = [...new Set(runData.map((m) => Number(m.rpm.toFixed(3))))].sort((a, b) => a - b);
        const cellDurations = {};
        cells.forEach((cellId) => {
            const pts = runData
                .filter((m) => !m.is_final_save)
                .filter((m) => Number(m.cell_id) === Number(cellId))
                .sort((a, b) => Number(a.timestamp) - Number(b.timestamp));
            if (pts.length >= 2) {
                const startTs = Number(pts[0].timestamp);
                const endTs = Number(pts[pts.length - 1].timestamp);
                const durMs = Math.max(0, (endTs - startTs) * 1000);
                cellDurations[cellId] = durMs;
            }
        });

        const csvHeader = "timestamp,cell_id,height_mm,torque_percent,rotational_drag,rpm,cell_termination_method\n";
        const csvBody = runData.map((m) => {
            const iso = new Date(m.timestamp * 1000).toISOString();
            const termination = this.cellTerminationReasons.get(Number(m.cell_id)) || "normal";
            return `${iso},${m.cell_id},${m.height},${m.torque_percent},${m.rotational_drag},${m.rpm},${termination}`;
        }).join("\n");

        const settingsSnapshot = this._getRunSettingsForHistorySave();
        const predictedViscosity = JSON.parse(JSON.stringify(this.predictedViscosityData || {}));
        const hasPredictedViscosityData = this._predictedViscosityEntryHasData(predictedViscosity);

        const exp = {
            id: this._experimentHistoryIdForRun(runStartTsSec),
            created_at: Date.now(),
            measurement_count: runData.length,
            cells,
            rpms,
            settings: settingsSnapshot,
            latestPerZ: [...latestByKey.values()],
            cellDurations,
            runStartTsSec: Number.isFinite(runStartTsSec) ? runStartTsSec : null,
            runEndTsSec: Number(runData[runData.length - 1]?.timestamp) || null,
            csv: csvHeader + csvBody,
            cell_termination_reasons: Object.fromEntries(this.cellTerminationReasons),
            viscosity_prediction_mode:
                settingsSnapshot.viscosity_prediction_mode
                || (hasPredictedViscosityData ? "on" : "off"),
            predicted_viscosity: predictedViscosity,
            run_type: settingsSnapshot.discovery_mode_enabled ? "discovery" : "regular",
            discovery_results: settingsSnapshot.discovery_mode_enabled
                ? JSON.parse(JSON.stringify(this.discoveryResultsByCell || {}))
                : {},
        };

        this.runSettingsSnapshot = null;
        this._upsertExperimentHistoryEntry(exp);
        this.saveExperimentHistoryEntry(exp).catch(() => {
            this.pushStatusMessage("Warning: failed to sync experiment history to server");
        });
        this.renderExperimentCards();
    }

    _buildExperimentCardInnerHtml(exp) {
        const experimentName = (exp.settings && exp.settings.experiment_name)
            ? exp.settings.experiment_name
            : "(unnamed)";
        const dateStr = exp.created_at
            ? new Date(exp.created_at).toLocaleString()
            : "";
        const isDiscovery = exp.run_type === "discovery"
            || Boolean(exp.settings && exp.settings.discovery_mode_enabled);
        const discoveryBadge = isDiscovery
            ? '<span class="experiment-card-badge mode-discovery">Discovery</span>'
            : "";
        return `
            <strong class="experiment-card-title">${this._escapeHtml(experimentName)}${discoveryBadge}</strong>
            <div class="experiment-card-date">${this._escapeHtml(dateStr)}</div>
            <div class="experiment-card-row">
                <span>Cells</span><span>${(exp.cells || []).join(", ") || "-"}</span>
            </div>
            <div class="experiment-card-row">
                <span>RPMs</span><span>${(exp.rpms || []).join(", ") || "-"}</span>
            </div>`;
    }

    _attachExperimentDeleteButton(card, expId) {
        const del = document.createElement("button");
        del.type = "button";
        del.className = "btn subtle experiment-delete";
        del.setAttribute("aria-label", "Delete experiment");
        del.innerHTML = "&times;";
        del.addEventListener("click", (e) => {
            e.stopPropagation();
            this.deleteExperiment(expId);
        });
        card.appendChild(del);
    }

    _buildSummaryFeatureTiles(s) {
        const predMode = this._normalizeViscosityPredictionMode(
            s.viscosity_prediction_mode,
            s.predicted_viscosity_enabled
        );
        const torqueFloorOn = s.low_torque_liquid_contact_skip_enabled === true;
        const smartExitOn = s.smart_early_exit_enabled === true;
        const feedbackOn = Boolean(s.feedback_control_enabled);

        const feedbackDetail = feedbackOn
            ? [
                `R² drag ≥ ${s.r2_drag_min ?? "-"}`,
                `R² CV ≥ ${s.r2_cv_min ?? "-"}`,
                `R² slope ≥ ${s.r2_slope_min ?? "-"}`,
                `Hit confidence ≥ ${s.hit_point_confidence_threshold ?? "-"}`,
            ].join("<br>")
            : "Disabled for this run";

        const smartDetail = smartExitOn
            ? `CV threshold ${s.smart_cv_threshold ?? "-"} · window ${s.smart_window_size ?? "-"}`
            : "Disabled for this run";

        const torqueDetail = torqueFloorOn
            ? `Skip Z-rows when first sample &lt; ${s.low_torque_liquid_contact_threshold_pct ?? "-"}%`
            : "Disabled for this run";

        const viscosityDetail = predMode !== "off"
            ? "Unified rheology fit after each cell"
            : "Disabled for this run";

        const tile = (title, on, status, detail) => `
            <article class="summary-feature-tile ${on ? "is-on" : "is-off"}">
                <h4>${title}</h4>
                <div class="tile-status">${status}</div>
                <div class="tile-detail">${detail}</div>
            </article>`;

        const saveAllOn = Boolean(s.save_all_sample_data);
        const saveAllDetail = saveAllOn
            ? "All dwell samples saved to timeseries CSV"
            : "Summary CSV uses final point per Z×RPM";

        const zOffset = Number(s.z_start_offset_mm);
        const zOffsetDetail = Number.isFinite(zOffset)
            ? `Start Z = rough hitpoint + ${zOffset.toFixed(3)} mm (calibrated cells)`
            : "Default 0.4 mm above rough hitpoint";

        return [
            tile("Feedback", feedbackOn, feedbackOn ? "On" : "Off", feedbackDetail),
            tile("Smart Early Exit", smartExitOn, smartExitOn ? "On" : "Off", smartDetail),
            tile("1st Sample Torque Floor", torqueFloorOn, torqueFloorOn ? "On" : "Off", torqueDetail),
            tile("Viscosity Prediction", predMode !== "off", predMode !== "off" ? "On" : "Off", viscosityDetail),
            tile("Save All Sample Data", saveAllOn, saveAllOn ? "On" : "Off", saveAllDetail),
            tile("Z-Start Offset", Number.isFinite(zOffset), Number.isFinite(zOffset) ? `${zOffset.toFixed(3)} mm` : "0.4 mm", zOffsetDetail),
        ].join("");
    }

    _buildPredictedViscosityTableHtml(exp, s) {
        const predData = exp.predicted_viscosity || {};
        const hasPredData = this._predictedViscosityEntryHasData(predData);
        const predMode = this._normalizeViscosityPredictionMode(
            exp.viscosity_prediction_mode ?? s.viscosity_prediction_mode,
            exp.predicted_viscosity_enabled ?? s.predicted_viscosity_enabled
        );
        if (predMode === "off" && !hasPredData) {
            return "<p class=\"summary-empty\"><em>Viscosity predictions were off for this run.</em></p>";
        }
        const summaryBlocks = [];
        const rows = [];
        Object.keys(predData).forEach((cellKey) => {
            const cellId = Number(cellKey);
            const rpmMap = predData[cellKey];
            if (!rpmMap || typeof rpmMap !== "object") {
                return;
            }
            const summary = rpmMap[this.predictedViscositySummaryKey];
            if (summary && typeof summary === "object") {
                const cellEta = summary.success && summary.viscosity_kcp != null
                    ? Number(summary.viscosity_kcp).toFixed(3)
                    : "—";
                const nVal = summary.n != null && Number.isFinite(Number(summary.n))
                    ? Number(summary.n).toFixed(3)
                    : "—";
                summaryBlocks.push(
                    `<div class="predicted-viscosity-cell-meta">`
                    + `<strong>Cell ${cellId}</strong> `
                    + this._buildRegimeBadgeHtml(summary.regime || (summary.success ? summary.mode : "failed"))
                    + `<span class="cell-eta-label">η = ${cellEta} kCp · n = ${nVal}</span>`
                    + `</div>`
                );
            }
            Object.keys(rpmMap).forEach((rpmKey) => {
                if (!this._isPredictedViscosityRpmKey(rpmKey)) {
                    return;
                }
                const result = rpmMap[rpmKey];
                const label = s.cell_content_map?.[cellId] ?? s.cell_content_map?.[String(cellId)] ?? "";
                const visc = result?.success && result?.viscosity_kcp != null
                    ? Number(result.viscosity_kcp).toFixed(3)
                    : "—";
                const r2 = result?.R2 != null && Number.isFinite(Number(result.R2))
                    ? Number(result.R2).toFixed(3)
                    : "—";
                const regime = summary?.regime
                    ?? (result?.success ? "per-RPM" : "failed");
                rows.push(
                    `<tr><td>${cellId}</td><td>${label || "—"}</td><td>${rpmKey}</td>`
                    + `<td>${visc}</td><td>${r2}</td>`
                    + `<td>${this._buildRegimeBadgeHtml(regime)}</td></tr>`
                );
            });
        });
        if (rows.length === 0) {
            return "<p class=\"summary-empty\"><em>No predicted viscosity results were recorded.</em></p>";
        }
        return `
            <h3 class="summary-table-heading">Predicted viscosity</h3>
            ${summaryBlocks.join("")}
            <table class="duration-table predicted-viscosity-summary-table">
                <thead><tr><th>Cell No.</th><th>Cell Label</th><th>RPM</th><th>Predicted Viscosity (kCp)</th><th>R²</th><th>Regime</th></tr></thead>
                <tbody>${rows.join("")}</tbody>
            </table>`;
    }

    renderExperimentCards() {
        if (!this.el.summaryCards) {
            return;
        }

        if (this.experimentHistory.length === 0) {
            this.el.summaryCards.innerHTML = "<p class=\"summary-empty\">No experiments recorded yet.</p>";
            if (this.el.summaryDetail) {
                this.el.summaryDetail.classList.add("hidden");
            }
            return;
        }

        this.el.summaryCards.innerHTML = "";
        this.experimentHistory.forEach((exp) => {
            const card = document.createElement("div");
            card.className = `experiment-card${exp.id === this.selectedExperimentId ? " active" : ""}`;
            card.innerHTML = this._buildExperimentCardInnerHtml(exp);
            this._attachExperimentDeleteButton(card, exp.id);
            card.addEventListener("click", () => this.selectExperiment(exp.id));
            this.el.summaryCards.appendChild(card);
        });
    }

    selectExperiment(id) {
        const exp = this.experimentHistory.find((e) => e.id === id);
        if (!exp) {
            return;
        }

        this.selectedExperimentId = id;
        this.renderExperimentCards();

        if (this.el.summaryDetail) {
            this.el.summaryDetail.classList.remove("hidden");
        }

        const s = exp.settings || {};
        const cellLabelsSummary = s.cell_content_map && typeof s.cell_content_map === "object"
            ? (exp.cells || [])
                .map((cellId) => {
                    const label = s.cell_content_map[cellId] ?? s.cell_content_map[String(cellId)];
                    return label ? `C${cellId}: ${label}` : null;
                })
                .filter(Boolean)
                .join(" | ")
            : "";
        const torqueFloorOn = s.low_torque_liquid_contact_skip_enabled === true;
        const torqueFloorStatus = torqueFloorOn
            ? `On — ${s.low_torque_liquid_contact_threshold_pct ?? "-"}%`
            : "Off";

        const terminationMap = exp.cell_termination_reasons || {};
        const durationRows = exp.cells.map((cellId) => {
            const dur = exp.cellDurations?.[cellId];
            const label = s.cell_content_map?.[cellId] ? ` (${s.cell_content_map[cellId]})` : "";
            const timeStr = dur != null ? this.formatDuration(dur) : "—";
            const tMeta = this._terminationDisplayMeta(terminationMap[cellId] || terminationMap[String(cellId)] || "normal");
            return `<tr><td>Cell ${cellId}${label}</td><td>${timeStr}</td><td><span class="summary-termination-chip ${tMeta.cls}">${tMeta.text}</span></td></tr>`;
        }).join("");
        const allTimestamps = (exp.latestPerZ || [])
            .map((p) => Number(p.timestamp))
            .filter((ts) => Number.isFinite(ts));
        const explicitStart = Number(exp.runStartTsSec);
        const explicitEnd = Number(exp.runEndTsSec);
        const earliestTsSec = Number.isFinite(explicitStart)
            ? explicitStart
            : (allTimestamps.length ? Math.min(...allTimestamps) : null);
        const latestTsSec = Number.isFinite(explicitEnd)
            ? explicitEnd
            : (allTimestamps.length ? Math.max(...allTimestamps) : null);
        const totalDurationMs = (Number.isFinite(earliestTsSec) && Number.isFinite(latestTsSec))
            ? Math.max(0, (latestTsSec - earliestTsSec) * 1000)
            : null;
        const durationTable = `
<table class="duration-table">
  <thead><tr><th>Cell</th><th>Duration</th><th>Termination</th></tr></thead>
  <tbody>${durationRows}</tbody>
</table>
<div><strong>Total Time:</strong> ${totalDurationMs != null ? this.formatDuration(totalDurationMs) : "—"}</div>`;
        const leftLines = [
            `<strong>Date:</strong> ${new Date(exp.created_at).toLocaleString()}`,
            `<strong>Experiment name:</strong> ${s.experiment_name || "(unnamed)"}`,
            (exp.run_type === "discovery" || s.discovery_mode_enabled)
                ? '<strong>Run type:</strong> <span class="experiment-card-badge mode-discovery">Discovery</span>'
                : "<strong>Run type:</strong> Regular",
            `<strong>Cells tested:</strong> ${exp.cells.join(", ") || "-"}`,
            `<strong>RPMs:</strong> ${exp.rpms.join(", ") || "-"}`,
            `<strong>Cell labels:</strong> ${cellLabelsSummary || "-"}`,
            `<strong>Z step:</strong> ${s.z_step_size ?? "-"} mm`,
            `<strong>Measurement duration:</strong> ${s.measurement_duration ?? "-"} s`,
            `<strong>Sample interval:</strong> ${s.sample_interval ?? "-"} s`,
            `<strong>1st Sample Torque Floor:</strong> ${torqueFloorStatus}`,
            durationTable,
        ];

        const leftEl = this.el.summaryMetaLeft;
        const rightEl = this.el.summaryMetaRight;
        const predEl = this.el.summaryPredictedViscosity;
        if (leftEl) {
            leftEl.innerHTML = leftLines.map((line) => line.startsWith("<table") ? line : `<div>${line}</div>`).join("");
        }
        if (rightEl) {
            rightEl.innerHTML = this._buildSummaryFeatureTiles(s);
        }
        if (predEl) {
            predEl.innerHTML = this._buildPredictedViscosityTableHtml(exp, s);
        }

        const discoveryResults = exp.discovery_results || {};
        const discoveryBlocks = (exp.cells || []).map((cellId) => {
            const entry = discoveryResults[String(cellId)] || discoveryResults[cellId];
            return this._buildDiscoverySummaryBlockHtml(cellId, entry);
        }).filter(Boolean).join("");
        if (discoveryBlocks && leftEl) {
            leftEl.insertAdjacentHTML("beforeend", discoveryBlocks);
        }

        const byCellRpm = {};
        (exp.latestPerZ || []).forEach((p) => {
            const cellId = Number(p.cell_id);
            const rpm = Number(p.rpm);
            if (!Number.isFinite(cellId) || !Number.isFinite(rpm)) {
                return;
            }
            const k = `${cellId}|${rpm.toFixed(3)}`;
            if (!byCellRpm[k]) byCellRpm[k] = [];
            byCellRpm[k].push(p);
        });
        const alignToHit = Boolean(this.el.summaryAlignHitpoint?.checked);

        const traces = Object.entries(byCellRpm)
            .sort((a, b) => {
                const [cellA, rpmA] = a[0].split("|");
                const [cellB, rpmB] = b[0].split("|");
                const cellDiff = Number(cellA) - Number(cellB);
                if (cellDiff !== 0) return cellDiff;
                return Number(rpmA) - Number(rpmB);
            })
            .map(([key, pts]) => {
            const [cellIdStr, rpmStr] = key.split("|");
            const cellId = Number(cellIdStr);
            const rpm = Number(rpmStr);
            pts.sort((a, b) => a.height - b.height);
            const timeOrdered = [...pts].sort((a, b) => Number(a.timestamp) - Number(b.timestamp));
            const trimmed = timeOrdered.length > 3 ? timeOrdered.slice(0, -3) : [...timeOrdered];
            const plotPoints = alignToHit
                ? (trimmed.length > 0 ? trimmed : [...timeOrdered])
                : [...timeOrdered];
            const alignReference = plotPoints.length > 0
                ? Number(plotPoints[plotPoints.length - 1].height)
                : null;
            const rawX = plotPoints.map((p) => Number(p.height));
            const xSeries = (alignToHit && Number.isFinite(alignReference))
                ? rawX.map((x) => x - alignReference)
                : rawX;
            const cellLabel = s.cell_content_map?.[cellId]
                ? `Cell ${cellId} — ${s.cell_content_map[cellId]}`
                : `Cell ${cellId}`;
            const label = `${cellLabel} @ ${rpm.toFixed(3)} RPM`;
            const refText = Number.isFinite(alignReference) ? alignReference.toFixed(3) : "N/A";
            return {
                x: xSeries,
                y: plotPoints.map((p) => p.rotational_drag),
                mode: "lines+markers",
                type: "scatter",
                name: label,
                marker: { size: 6 },
                line: { width: 2 },
                hovertemplate: alignToHit
                    ? `Rel. height %{x:.3f} mm<br>Drag %{y:.4f}<br>Alignment ref ${refText} mm<extra>${label}</extra>`
                    : `Z %{x:.3f} mm<br>Drag %{y:.4f}<br>Alignment ref ${refText} mm<extra>${label}</extra>`
            };
        });

        if (this.summaryPlotInitialized && this.el.summaryPlot) {
            const layout = {
                ...this.summaryPlotLayout,
                xaxis: {
                    ...this.summaryPlotLayout.xaxis,
                    title: alignToHit
                        ? "Height Relative to Alignment Reference (mm, reference = 0)"
                        : "Z-Height (mm) - descent ->",
                    tickformat: ".3f",
                },
                shapes: [],
            };
            Plotly.react(this.el.summaryPlot, traces, layout,
                { responsive: true, displayModeBar: false });
        }
    }

    deleteExperiment(id) {
        this.experimentHistory = this.experimentHistory.filter((e) => e.id !== id);
        if (this.selectedExperimentId === id) {
            this.selectedExperimentId = null;
            if (this.el.summaryDetail) {
                this.el.summaryDetail.classList.add("hidden");
            }
        }
        fetch(`/api/experiment_history/${encodeURIComponent(id)}`, {
            method: "DELETE"
        }).catch(() => {
            this.pushStatusMessage("Warning: failed to delete experiment history on server");
        });
        this.renderExperimentCards();
    }

    downloadSelectedCSV() {
        const exp = this.experimentHistory.find((e) => e.id === this.selectedExperimentId);
        if (!exp) {
            return;
        }
        const blob = new Blob([exp.csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `viscometry_${exp.id}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    updateTimers() {
        const now = Date.now();

        if (this.experimentStart !== null && this.isRunning) {
            const elapsedText = this.formatDuration(now - this.experimentStart);
            if (this.el.elapsed) {
                this.el.elapsed.textContent = elapsedText;
            }
            if (this.el.calElapsed) {
                this.el.calElapsed.textContent = elapsedText;
            }
            if (this.el.discoveryElapsed) {
                this.el.discoveryElapsed.textContent = elapsedText;
            }
        }

        if (this.cellStart !== null && this.isRunning) {
            const cellElapsedText = `Cell ${this.formatDuration(now - this.cellStart)}`;
            if (this.el.elapsedCell) {
                this.el.elapsedCell.textContent = cellElapsedText;
            }
            if (this.el.calElapsedCell) {
                this.el.calElapsedCell.textContent = cellElapsedText;
            }
            if (this.el.discoveryElapsedCell) {
                this.el.discoveryElapsedCell.textContent = cellElapsedText;
            }
        }
    }

    formatDuration(ms) {
        const total = Math.max(0, Math.floor(ms / 1000));
        const h = String(Math.floor(total / 3600)).padStart(2, "0");
        const m = String(Math.floor((total % 3600) / 60)).padStart(2, "0");
        const s = String(total % 60).padStart(2, "0");
        return `${h}:${m}:${s}`;
    }

    updateCompletionBar() {

        // Use server's calibration mode state which persists across page reloads
        const isCalibrating = this.calibrationModeActive;
        
        const isRecalibrating = isCalibrating && this.recalibrationModeActive;
        // During full calibration, show 18 total. During recalibration, use selected total.
        const total = isRecalibrating
            ? (this.recalibrationTargetCount || this.plannedCells.length || 18)
            : (isCalibrating ? 18 : (this.plannedCells.length || 18));
        const done = this.measuredCells.size;
        const ratio = total > 0 ? done / total : 0;

        if (this.el.completionBar) {
            this.el.completionBar.style.width = `${(ratio * 100).toFixed(1)}%`;
        }
        
        const isAllDone = done >= total && total > 0;
        // Determine display text based on server's calibration mode
        let chipText;
        if (isRecalibrating) {
            chipText = `${done}/${total} cells recalibrating`;
        } else if (isCalibrating) {
            chipText = `Calibrating ${done} / ${total} cells`;
        } else if (isAllDone) {
            // Keep the top status bar clean; the popup bubble is shown separately.
            chipText = `${done} / ${total} cells completed`;
        } else {
            chipText = `${done} / ${total} cells completed`;
        }
        
        if (this.el.completionText) {
            this.el.completionText.textContent = chipText;
        }
        if (this.el.completionChip) {
            this.el.completionChip.textContent = chipText;
        }

        if (!this.isRunning && !isCalibrating && !isRecalibrating) {
            if (isAllDone) {
                this._showExperimentCompleteMessage();
                this._hideExperimentTerminatedMessage();
            } else if (done > 0) {
                this._showExperimentTerminatedMessage();
                this._hideExperimentCompleteMessage();
            } else {
                this._hideExperimentCompleteMessage();
                this._hideExperimentTerminatedMessage();
            }
        }
    }

    updateCompletionChip() {
        this.updateCompletionBar();
    }

    _showExperimentCompleteMessage() {
        if (this.el.experimentCompleteBanner) {
            this.el.experimentCompleteBanner.classList.remove("hidden");
        }
    }

    _hideExperimentCompleteMessage() {
        if (this.el.experimentCompleteBanner) {
            this.el.experimentCompleteBanner.classList.add("hidden");
        }
    }

    _showExperimentTerminatedMessage() {
        if (this.el.experimentTerminatedBanner) {
            this.el.experimentTerminatedBanner.classList.remove("hidden");
        }
    }

    _hideExperimentTerminatedMessage() {
        if (this.el.experimentTerminatedBanner) {
            this.el.experimentTerminatedBanner.classList.add("hidden");
        }
    }

    _syncPlannedCells(settings) {
        const mode = settings.testing_mode || "custom";
        if (mode === "full") {
            this.plannedCells = Array.from({ length: 18 }, (_, i) => i + 1);
        } else if (mode === "row") {
            const rows = Array.isArray(settings.selected_rows) ? settings.selected_rows : [];
            this.plannedCells = rows.flatMap((r) =>
                Array.from({ length: 6 }, (_, i) => (r - 1) * 6 + i + 1)
            );
        } else {
            this.plannedCells = Array.isArray(settings.selected_cells) ? settings.selected_cells : [];
        }
        this.updateZStartOffsetAvailability();
    }

    _finalizePendingCompletedCell() {
        if (this._pendingCompletedCell !== null && this._pendingCompletedCell !== undefined) {
            this.completedCells.add(this._pendingCompletedCell);
            this.cellStates.set(this._pendingCompletedCell, "completed");
            this.washingCell = null;
            this._pendingCompletedCell = null;
            this.updateCompletionBar();
            this.syncMapVisuals({ force: true });
        }
    }

    _updatePredictedViscosityChartsCardVisibility(enabled) {
        if (!this.el.predictedViscosityChartsCard) {
            return;
        }
        const show = Boolean(enabled);
        this.el.predictedViscosityChartsCard.classList.toggle("hidden", !show);
        if (show) {
            this.renderPredictedViscosityCharts();
        }
    }

    _hydratePredictedViscosityFromServer(serverData) {
        if (!serverData || typeof serverData !== "object") {
            return;
        }
        this.predictedViscosityData = {};
        Object.entries(serverData).forEach(([cellKey, rpmMap]) => {
            const cellId = Number(cellKey);
            if (!Number.isFinite(cellId)) {
                return;
            }
            this.predictedViscosityData[cellId] = {};
            if (rpmMap && typeof rpmMap === "object") {
                Object.entries(rpmMap).forEach(([rpmKey, result]) => {
                    if (rpmKey === this.predictedViscositySummaryKey) {
                        if (result) {
                            this.predictedViscosityData[cellId][this.predictedViscositySummaryKey] = result;
                        }
                        return;
                    }
                    const rpm = Number(rpmKey);
                    if (Number.isFinite(rpm) && result) {
                        this.predictedViscosityData[cellId][rpm] = result;
                    }
                });
            }
        });
        this.renderPredictedViscosityCharts();
        this.renderLiveViscosityPredictionsTable();
    }

    _ingestPredictedViscosityUpdate(payload) {
        if (!payload || typeof payload !== "object") {
            return;
        }
        const cellId = Number(payload.cell_id);
        const rpm = Number(payload.rpm);
        if (!Number.isFinite(cellId) || !Number.isFinite(rpm)) {
            return;
        }
        if (!this.predictedViscosityData[cellId]) {
            this.predictedViscosityData[cellId] = {};
        }
        this.predictedViscosityData[cellId][rpm] = payload;
        if (payload.cell_summary && typeof payload.cell_summary === "object") {
            this.predictedViscosityData[cellId][this.predictedViscositySummaryKey] = payload.cell_summary;
        }
        this._refreshPredictedViscosityViews();
    }

    _ingestPredictedViscositySummaryUpdate(payload) {
        if (!payload || typeof payload !== "object") {
            return;
        }
        const cellId = Number(payload.cell_id);
        if (!Number.isFinite(cellId)) {
            return;
        }
        if (!this.predictedViscosityData[cellId]) {
            this.predictedViscosityData[cellId] = {};
        }
        this.predictedViscosityData[cellId][this.predictedViscositySummaryKey] = payload;
        this._refreshPredictedViscosityViews();
    }

    _refreshPredictedViscosityViews() {
        if (this.activeTabId === "data-processing-tab") {
            this.renderPredictedViscosityCharts();
        }
        if (this.activeTabId === "controls-tab") {
            this.renderLiveViscosityPredictionsTable();
        }
    }

    _fmtPredictedViscosity3(value) {
        const n = Number(value);
        return Number.isFinite(n) ? n.toFixed(3) : "—";
    }

    renderLiveViscosityPredictionsTable() {
        if (this.activeTabId !== "controls-tab" || this._isDiscoveryRunActive()) {
            return;
        }
        const tbody = this.el.liveViscosityTableBody;
        if (!tbody) {
            return;
        }

        const contentMap = this.latestControlSettings?.cell_content_map
            || this.readControlSettings().cell_content_map
            || {};
        const rows = [];

        Object.keys(this.predictedViscosityData)
            .map((k) => Number(k))
            .filter((id) => Number.isFinite(id))
            .sort((a, b) => a - b)
            .forEach((cellId) => {
                const rpmMap = this.predictedViscosityData[cellId];
                if (!rpmMap || typeof rpmMap !== "object") {
                    return;
                }
                const summary = this._getPredictedViscositySummary(cellId);
                Object.keys(rpmMap)
                    .filter((k) => this._isPredictedViscosityRpmKey(k))
                    .map((k) => Number(k))
                    .sort((a, b) => a - b)
                    .forEach((rpm) => {
                        const result = rpmMap[rpm];
                        const label = contentMap[cellId]
                            ?? contentMap[String(cellId)]
                            ?? "";
                        const visc = summary?.success && summary?.viscosity_kcp != null
                            ? this._fmtPredictedViscosity3(summary.viscosity_kcp)
                            : (result?.success && result?.viscosity_kcp != null
                                ? this._fmtPredictedViscosity3(result.viscosity_kcp)
                                : "—");
                        const r2 = result?.R2 != null && Number.isFinite(Number(result.R2))
                            ? Number(result.R2).toFixed(3)
                            : "—";
                        const status = result?.success
                            ? "OK"
                            : (result?.error ? String(result.error) : "—");
                        const rpmLabel = Number(rpm).toFixed(3);
                        rows.push(
                            `<tr><td>${cellId}</td><td>${label || "—"}</td><td class="mono">${rpmLabel}</td>`
                            + `<td class="mono">${visc}</td><td class="mono">${r2}</td>`
                            + `<td class="pv-status-cell">${status}</td></tr>`
                        );
                    });
            });

        tbody.innerHTML = rows.join("");
        if (this.el.liveViscosityEmpty) {
            this.el.liveViscosityEmpty.classList.toggle("hidden", rows.length > 0);
        }
        const table = tbody.closest(".live-viscosity-table");
        if (table) {
            table.classList.toggle("hidden", rows.length === 0);
        }
    }

    _normalizeViscosityPredictionMode(mode, legacyEnabled) {
        if (mode === "on" || mode === "off") {
            return mode;
        }
        if (mode === "Newtonian" || mode === "Non-Newtonian") {
            return "on";
        }
        if (legacyEnabled === true || legacyEnabled === "true") {
            return "on";
        }
        return "off";
    }

    _getViscosityPredictionMode() {
        return this._normalizeViscosityPredictionMode(this.viscosityPredictionMode);
    }

    _setViscosityPredictionModeUI(mode, legacyEnabled) {
        const normalized = this._normalizeViscosityPredictionMode(mode, legacyEnabled);
        this.viscosityPredictionMode = normalized;
        if (this.el.viscosityPredictionToggleRow) {
            this.el.viscosityPredictionToggleRow.dataset.mode = normalized;
        }
        if (this.el.viscosityPredictionEnabled) {
            this.el.viscosityPredictionEnabled.checked = normalized === "on";
        }
    }

    _plannedCellsHaveCalibration() {
        const cells = this.calibrationSummary?.cells || {};
        const planned = this.plannedCells || [];
        if (!planned.length) {
            return false;
        }
        return planned.some((cellId) => {
            const key = String(cellId);
            return Object.prototype.hasOwnProperty.call(cells, key);
        });
    }

    updateZStartOffsetAvailability() {
        const row = this.el.zStartOffsetRow;
        const input = this.el.zStartOffsetMm;
        if (!row || !input) {
            return;
        }
        const calibrationRun = this.isCalibrationRun
            || this.calibrationModeActive
            || this.recalibrationModeActive;
        const enabled = !this.isRunning
            && !calibrationRun
            && Boolean(this.calibrationSummary?.is_calibrated)
            && this._plannedCellsHaveCalibration();
        row.classList.toggle("is-disabled", !enabled);
        input.disabled = !enabled;
    }

    _updateSaveAllSampleDataUI(enabled) {
        const active = Boolean(enabled);
        if (this.el.controlsChartsDwellRow) {
            this.el.controlsChartsDwellRow.classList.toggle("is-save-all-active", active);
        }
        if (this.el.dwellTimeDragCard) {
            this.el.dwellTimeDragCard.classList.toggle("hidden", !active);
        }
        if (!active && this.charts.dwell) {
            this.charts.dwell.data.datasets = [];
            this.charts.dwell.update("none");
        }
    }

    _isSaveAllSampleDataActive() {
        if (this.isRunning) {
            return Boolean(this.runSaveAllSampleData);
        }
        return Boolean(this.el.saveAllSampleData?.checked);
    }

    _dwellZVisibilityKey(cellId, zHeight) {
        return `${Number(cellId)}|${Number(zHeight).toFixed(3)}`;
    }

    _ingestDwellMeasurement(measurement) {
        if (!this._isSaveAllSampleDataActive()) {
            return;
        }
        const elapsed = Number(measurement.elapsed_time);
        if (!Number.isFinite(elapsed)) {
            return;
        }
        const cellId = Number(measurement.cell_id);
        const zHeight = Number(measurement.height);
        const drag = Number(measurement.rotational_drag);
        if (!Number.isFinite(cellId) || !Number.isFinite(zHeight) || !Number.isFinite(drag)) {
            return;
        }
        if (!this.dwellSeriesByCell.has(cellId)) {
            this.dwellSeriesByCell.set(cellId, new Map());
        }
        const byZ = this.dwellSeriesByCell.get(cellId);
        const zKey = zHeight.toFixed(3);
        if (!byZ.has(zKey)) {
            byZ.set(zKey, []);
            const visKey = this._dwellZVisibilityKey(cellId, zHeight);
            if (!this.dwellZVisibility.has(visKey)) {
                this.dwellZVisibility.set(visKey, true);
            }
        }
        byZ.get(zKey).push({
            x: elapsed,
            y: drag,
            rpm: Number(measurement.rpm) || 0,
        });
        this._scheduleDwellPlotRefresh();
    }

    _scheduleDwellPlotRefresh() {
        if (!this._isSaveAllSampleDataActive() || this.activeTabId !== "controls-tab") {
            return;
        }
        if (this._dwellPlotRefreshTimer) {
            window.clearTimeout(this._dwellPlotRefreshTimer);
        }
        this._dwellPlotRefreshTimer = window.setTimeout(() => {
            this._dwellPlotRefreshTimer = null;
            this.refreshDwellTimePlot();
        }, 110);
    }

    _buildDwellChartOptions(theme) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                legend: { display: true, labels: { color: theme.text, boxWidth: 12 } },
                tooltip: {
                    callbacks: {
                        label(context) {
                            const y = Number(context.parsed.y);
                            const x = Number(context.parsed.x);
                            return `Z ${context.dataset.label}: ${y.toFixed(4)} drag @ ${x.toFixed(1)} s`;
                        },
                    },
                },
            },
            scales: {
                x: {
                    type: "linear",
                    title: {
                        display: true,
                        text: "Elapsed time (s)",
                        color: theme.text,
                    },
                    ticks: { color: theme.tick },
                    grid: { color: theme.grid },
                    border: { color: theme.border },
                },
                y: {
                    title: {
                        display: true,
                        text: "Rotational Drag (torque / RPM)",
                        color: theme.text,
                    },
                    ticks: { color: theme.tick },
                    grid: { color: theme.grid },
                    border: { color: theme.border },
                },
            },
        };
    }

    refreshDwellTimePlot(options = {}) {
        if (!this._shouldRefreshLiveCharts(options)) {
            if (!options.force) {
                this._dwellChartsDirty = true;
            }
            return;
        }
        if (!this._isSaveAllSampleDataActive() || !this.dwellPlotInitialized || !this.charts.dwell) {
            return;
        }
        const activeCell = this.getActiveGraphCellId();
        if (!Number.isFinite(activeCell)) {
            return;
        }
        if (this.el.dwellTimeCellLabel) {
            this.el.dwellTimeCellLabel.textContent = `Cell ${activeCell}`;
        }
        const byZ = this.dwellSeriesByCell.get(activeCell) || new Map();
        const zKeys = [...byZ.keys()].sort((a, b) => Number(b) - Number(a));
        const palette = LIVE_RPM_PASTEL_PALETTE;
        const datasets = zKeys.map((zKey, idx) => {
            const points = [...(byZ.get(zKey) || [])].sort((a, b) => a.x - b.x);
            const visKey = this._dwellZVisibilityKey(activeCell, Number(zKey));
            const visible = this.dwellZVisibility.get(visKey) !== false;
            const color = palette[idx % palette.length];
            return {
                label: `Z ${zKey} mm`,
                data: points,
                showLine: true,
                borderColor: color,
                backgroundColor: color,
                pointRadius: 3,
                pointHoverRadius: 5,
                hidden: !visible,
            };
        });
        this.charts.dwell.data.datasets = datasets;
        if (this.el.dwellTimeEmpty) {
            this.el.dwellTimeEmpty.classList.toggle("hidden", datasets.length > 0);
        }
        this._renderDwellZSections(activeCell, zKeys);
        if (this._renderPaused) {
            this._dwellChartsDirty = true;
            return;
        }
        this.charts.dwell.update("none");
        this._dwellChartsDirty = false;
    }

    _renderDwellZSections(cellId, zKeys) {
        const container = this.el.dwellZSections;
        if (!container) {
            return;
        }
        container.innerHTML = zKeys.map((zKey) => {
            const visKey = this._dwellZVisibilityKey(cellId, Number(zKey));
            const checked = this.dwellZVisibility.get(visKey) !== false;
            return (
                `<label class="dwell-z-toggle">`
                + `<input type="checkbox" data-dwell-z-key="${visKey}" ${checked ? "checked" : ""}>`
                + `<span>Z ${zKey} mm</span>`
                + `</label>`
            );
        }).join("");
        container.querySelectorAll("input[data-dwell-z-key]").forEach((input) => {
            input.addEventListener("change", () => {
                const key = input.getAttribute("data-dwell-z-key");
                this.dwellZVisibility.set(key, Boolean(input.checked));
                this.refreshDwellTimePlot();
            });
        });
    }

    renderPredictedViscosityCharts() {
        const mode = this._getViscosityPredictionMode();
        if (mode === "off" || !this.el.predictedViscosityCharts) {
            return;
        }

        const cellIds = Object.keys(this.predictedViscosityData)
            .map((k) => Number(k))
            .filter((id) => Number.isFinite(id))
            .sort((a, b) => a - b);

        const hasData = cellIds.some((cid) => {
            const rpmMap = this.predictedViscosityData[cid];
            return rpmMap && Object.keys(rpmMap).some((k) => this._isPredictedViscosityRpmKey(k));
        });

        if (this.el.predictedViscosityChartsEmpty) {
            this.el.predictedViscosityChartsEmpty.classList.toggle("hidden", hasData);
        }
        if (!hasData) {
            this.el.predictedViscosityCharts.innerHTML = "";
            return;
        }

        cellIds.forEach((cellId) => {
            const rpmMap = this.predictedViscosityData[cellId];
            const rpmKeys = rpmMap
                ? Object.keys(rpmMap).filter((k) => this._isPredictedViscosityRpmKey(k))
                : [];
            if (!rpmMap || rpmKeys.length === 0) {
                return;
            }

            const summary = this._getPredictedViscositySummary(cellId);

            let wrap = this.el.predictedViscosityCharts.querySelector(
                `[data-pv-cell-id="${cellId}"]`
            );
            if (!wrap) {
                wrap = document.createElement("div");
                wrap.className = "predicted-viscosity-plot-wrap";
                wrap.dataset.pvCellId = String(cellId);
                this.el.predictedViscosityCharts.appendChild(wrap);
            }
            if (!wrap.querySelector(`[data-pv-plot="${cellId}"]`)) {
                wrap.innerHTML = `
                    <div class="predicted-viscosity-cell-heading" data-pv-heading="${cellId}">Cell ${cellId}</div>
                    <div class="predicted-viscosity-plot-row">
                        <div class="predicted-viscosity-plot" data-pv-plot="${cellId}"></div>
                        <div class="predicted-viscosity-side-panels">
                            <aside class="predicted-viscosity-params-panel">
                                <table class="predicted-viscosity-params-table" data-pv-params="${cellId}">
                                    <thead>
                                        <tr>
                                            <th>RPM</th>
                                            <th>η (kCp)</th>
                                            <th>A</th>
                                            <th>R²</th>
                                            <th>pts</th>
                                            <th>Status</th>
                                        </tr>
                                    </thead>
                                    <tbody data-pv-params-body="${cellId}"></tbody>
                                </table>
                            </aside>
                            <aside class="discovery-rheology-panel" data-dr-panel="${cellId}"></aside>
                        </div>
                    </div>`;
            }

            const headingEl = wrap.querySelector(`[data-pv-heading="${cellId}"]`);
            const plotEl = wrap.querySelector(`[data-pv-plot="${cellId}"]`);
            const paramsBody = wrap.querySelector(`[data-pv-params-body="${cellId}"]`);
            if (!plotEl) {
                return;
            }
            if (headingEl) {
                const cellEta = summary?.success && summary?.viscosity_kcp != null
                    ? this._fmtPredictedViscosity3(summary.viscosity_kcp)
                    : null;
                const nVal = summary?.n != null && Number.isFinite(Number(summary.n))
                    ? Number(summary.n).toFixed(3)
                    : null;
                const regime = summary?.regime || (summary?.success ? summary?.mode : null);
                let headingHtml = `<strong>Cell ${cellId}</strong>`;
                if (regime) {
                    headingHtml += ` ${this._buildRegimeBadgeHtml(regime)}`;
                }
                if (cellEta != null) {
                    headingHtml += `<span class="cell-eta-label">η = ${cellEta} kCp</span>`;
                }
                if (nVal != null) {
                    headingHtml += `<span class="cell-eta-label">n = ${nVal}</span>`;
                }
                headingEl.className = "predicted-viscosity-cell-heading predicted-viscosity-cell-meta";
                headingEl.innerHTML = headingHtml;
            }

            const rpms = rpmKeys
                .map((k) => Number(k))
                .sort((a, b) => a - b);

            const traces = [];
            const paramRows = [];
            rpms.forEach((rpm, idx) => {
                const result = rpmMap[rpm];
                if (!result) {
                    return;
                }
                const color = this.palette[idx % this.palette.length];
                const preZ = result.pretrim_z || [];
                const preD = result.pretrim_drag || [];
                const fitZ = result.fit_curve_z || [];
                const fitD = result.fit_curve_drag || [];

                if (preZ.length > 0) {
                    traces.push({
                        x: preZ,
                        y: preD,
                        mode: "markers",
                        type: "scatter",
                        name: `RPM ${rpm} data`,
                        legendgroup: `rpm${rpm}`,
                        marker: { size: 7, color, opacity: 0.55 },
                        showlegend: idx === 0,
                    });
                }
                if (fitZ.length > 0) {
                    traces.push({
                        x: fitZ,
                        y: fitD,
                        mode: "lines",
                        type: "scatter",
                        name: `RPM ${rpm} fit`,
                        legendgroup: `rpm${rpm}`,
                        line: { color, width: 2 },
                        showlegend: idx === 0,
                    });
                }

                const eta = result.success && result.viscosity_kcp != null
                    ? this._fmtPredictedViscosity3(result.viscosity_kcp)
                    : "—";
                const r2 = result.R2 != null && Number.isFinite(Number(result.R2))
                    ? Number(result.R2).toFixed(3)
                    : "—";
                const status = result.success
                    ? "OK"
                    : (result.error ? String(result.error) : "—");
                paramRows.push(
                    `<tr>`
                    + `<td class="mono">${Number(rpm).toFixed(3)}</td>`
                    + `<td class="mono">${eta}</td>`
                    + `<td class="mono">${this._fmtPredictedViscosity3(result.A)}</td>`
                    + `<td class="mono">${r2}</td>`
                    + `<td class="mono">${result.n_points_used ?? 0}</td>`
                    + `<td class="pv-status-cell">${status}</td>`
                    + `</tr>`
                );
            });

            if (paramsBody) {
                paramsBody.innerHTML = paramRows.join("");
            }

            const pvBase = this._buildLivePlotLayout({
                yTitle: "Rotational drag",
                showLegend: true,
            });
            const layout = {
                ...pvBase,
                showlegend: true,
                margin: { t: 24, r: 16, b: 40, l: 52 },
                xaxis: { ...pvBase.xaxis, title: "Z (mm)" },
                legend: { ...pvBase.legend, orientation: "h", y: 1.12 },
            };

            Plotly.react(plotEl, traces, layout, { responsive: true, displayModeBar: false });
        });

        // Remove plot wrappers for cells no longer in data
        this.el.predictedViscosityCharts.querySelectorAll("[data-pv-cell-id]").forEach((wrap) => {
            const cid = Number(wrap.dataset.pvCellId);
            if (!cellIds.includes(cid)) {
                wrap.remove();
            }
        });

        this._refreshDiscoveryRheologyPanels();
    }

    updateTable() {
        if (!this.el.tableBody) {
            return;
        }
        const rows = this.measurements.slice(-20).reverse();
        this.el.tableBody.innerHTML = "";

        rows.forEach((m, index) => {
            const tr = document.createElement("tr");
            if (this.currentCell && m.cell_id === this.currentCell) {
                tr.classList.add("active-row");
            }
            tr.style.animationDelay = `${index * 0.02}s`;

            const dt = new Date(m.timestamp * 1000);
            tr.innerHTML = [
                `<td>${m.cell_id}</td>`,
                `<td>${m.height.toFixed(3)}</td>`,
                `<td>${m.rotational_drag.toFixed(2)}</td>`,
                `<td>${m.rpm.toFixed(2)}</td>`,
                `<td>${dt.toLocaleTimeString()}</td>`
            ].join("");

            this.el.tableBody.appendChild(tr);
        });
    }

    pushStatusMessage(message) {
        if (!message) {
            return;
        }

        this.statusLog.unshift(message);
        this.statusLog = this.statusLog.slice(0, 5);

        this.el.statusLog.innerHTML = "";
        this.statusLog.forEach((entry, index) => {
            const li = document.createElement("li");
            li.textContent = entry;
            li.style.animationDelay = `${index * 0.05}s`;
            this.el.statusLog.appendChild(li);
        });

        this._scheduleMapVisualSync();
    }

    showDisconnectedBanner(show) {
        if (show) {
            this.el.disconnectBanner.classList.remove("hidden");
            if (this.disconnectedBannerTimeout) {
                clearTimeout(this.disconnectedBannerTimeout);
                this.disconnectedBannerTimeout = null;
            }
        } else {
            if (this.disconnectedBannerTimeout) {
                clearTimeout(this.disconnectedBannerTimeout);
            }
            this.disconnectedBannerTimeout = setTimeout(() => {
                this.el.disconnectBanner.classList.add("hidden");
            }, 350);
        }
    }

    toggleTheme() {
        if (!this.el.themeToggle) return;
        const isDark = this.el.body.classList.contains("theme-dark");
        if (isDark) {
            this.el.body.classList.remove("theme-dark");
            this.el.body.classList.add("theme-light");
            this.el.themeToggle.textContent = "Dark";
        } else {
            this.el.body.classList.remove("theme-light");
            this.el.body.classList.add("theme-dark");
            this.el.themeToggle.textContent = "Light";
        }
        this.updateLiveChartTheme();
    }

    exportCSV() {
        if (this.measurements.length === 0) {
            this.pushStatusMessage("No measurement data to export yet");
            return;
        }

        const header = "timestamp,cell_id,height_mm,rotational_drag_percent,rpm\n";
        const csv = this.measurements
            .map((m) => {
                const iso = new Date(m.timestamp * 1000).toISOString();
                return `${iso},${m.cell_id},${m.height},${m.rotational_drag},${m.rpm}`;
            })
            .join("\n");

        const blob = new Blob([header + csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `viscometry_export_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        this.pushStatusMessage("CSV export generated");
    }

    updateReviewStartGuard() {
        const blocked = Boolean(this.calibrationReviewPending || this.experimentReviewPending);
        if (this.el.startRun && this.uiState === "ready") {
            this.el.startRun.disabled = blocked;
        }
        this.updateCalibrationStopControls();
    }

    updateCalibrationReviewStartGuard() {
        this.updateReviewStartGuard();
    }

    syncCalibrationReviewSession(session) {
        if (!session || !session.session_id) {
            return;
        }
        this.calibrationReviewSession = session;
        this.calibrationReviewPending = true;
        this.updateReviewStartGuard();
        this.renderCalibrationReviewTabs();
        const pending = this.getPendingReviewCellIds();
        if (!pending.includes(this.calibrationReviewActiveCellId)) {
            this.calibrationReviewActiveCellId = pending[0];
        }
        this.renderCalibrationReviewCellView(this.calibrationReviewActiveCellId);
    }

    openCalibrationReview(session) {
        if (!session || !session.session_id) {
            return;
        }
        this.calibrationReviewSession = session;
        this.calibrationReviewPending = true;
        this.isCalibrationRun = false;
        this.updateReviewStartGuard();

        const pending = this.getPendingReviewCellIds();
        if (pending.length === 0) {
            this.closeCalibrationReviewModal();
            return;
        }
        this.calibrationReviewActiveCellId = pending[0];

        if (this.el.calReviewBackdrop) {
            this.el.calReviewBackdrop.classList.remove("hidden");
            this.el.calReviewBackdrop.setAttribute("aria-hidden", "false");
        }
        this.el.body.classList.add("calibration-review-active");
        this.renderCalibrationReviewTabs();
        this.renderCalibrationReviewCellView(this.calibrationReviewActiveCellId);
        this.pushStatusMessage("Review calibration data — Save or Discard each cell");
    }

    closeCalibrationReviewModal() {
        this.calibrationReviewPending = false;
        this.calibrationReviewSession = null;
        this.calibrationReviewActiveCellId = null;
        this.calibrationReviewPlotState = { initialized: false, layout: null };
        if (this.el.calReviewBackdrop) {
            this.el.calReviewBackdrop.classList.add("hidden");
            this.el.calReviewBackdrop.setAttribute("aria-hidden", "true");
        }
        this.el.body.classList.remove("calibration-review-active");
        this.updateReviewStartGuard();
    }

    getPendingReviewCellIds() {
        const session = this.calibrationReviewSession;
        if (!session) {
            return [];
        }
        const order = session.completion_order || [];
        const cells = session.cells || {};
        return order.filter((cellId) => {
            const key = String(cellId);
            const entry = cells[key];
            return entry && entry.decision === "pending";
        });
    }

    getReviewCellEntry(cellId, session = this.calibrationReviewSession) {
        if (!session) {
            return null;
        }
        return session.cells?.[String(cellId)] || null;
    }

    getMeasurementsForReviewCell(cellId, session = this.calibrationReviewSession) {
        const entry = this.getReviewCellEntry(cellId, session);
        const fromSession = entry?.measurements;
        if (Array.isArray(fromSession) && fromSession.length > 0) {
            return fromSession.map((m) => ({
                height: Number(m.height),
                rotational_drag: Number(m.rotational_drag),
                torque_percent: Number(m.torque_percent),
                rpm: Number(m.rpm),
                timestamp: m.timestamp,
                cell_id: Number(cellId),
            })).filter((m) => Number.isFinite(m.height) && Number.isFinite(m.rpm));
        }
        return (this.measurementsByCell.get(Number(cellId)) || []).slice();
    }

    renderCalibrationReviewTabs() {
        const tabsEl = this.el.calReviewTabs;
        const session = this.calibrationReviewSession;
        if (!tabsEl || !session) {
            return;
        }
        const order = session.completion_order || [];
        const cells = session.cells || {};
        tabsEl.innerHTML = "";
        order.forEach((cellId) => {
            const key = String(cellId);
            const entry = cells[key];
            if (!entry) {
                return;
            }
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "calibration-review-tab";
            if (entry.decision !== "pending") {
                btn.classList.add("resolved");
            }
            if (Number(cellId) === Number(this.calibrationReviewActiveCellId)) {
                btn.classList.add("active");
            }
            btn.textContent = `Cell ${cellId}`;
            if (entry.decision === "pending") {
                btn.addEventListener("click", () => {
                    this.calibrationReviewActiveCellId = Number(cellId);
                    this.renderCalibrationReviewTabs();
                    this.renderCalibrationReviewCellView(this.calibrationReviewActiveCellId);
                });
            }
            tabsEl.appendChild(btn);
        });
    }

    renderCalibrationReviewSummary(cellId) {
        const box = this.el.calReviewSummary;
        const entry = this.getReviewCellEntry(cellId);
        if (!box || !entry) {
            return;
        }
        const offset = Number(this.calibrationReviewSession?.calibration_offset ?? 0.4);
        const rpms = this.getRpmsForCell(cellId);
        const rpmText = rpms.length ? rpms.map((r) => Number(r).toFixed(3)).join(", ") : "—";
        box.innerHTML = `
            <div><strong>Cell ${cellId}</strong></div>
            <div>Rough hitpoint Z: <strong>${Number(entry.rough_z).toFixed(3)} mm</strong></div>
            <div>Saved safe Z (rough + ${offset.toFixed(1)} mm): <strong>${Number(entry.safe_z).toFixed(3)} mm</strong></div>
            <div>RPMs tested: ${rpmText}</div>
        `;
    }

    renderCalibrationReviewCellView(cellId) {
        if (!Number.isFinite(cellId)) {
            return;
        }
        this.renderCalibrationReviewSummary(cellId);
        this.renderCalibrationReviewPlot(cellId);
        const pending = this.getPendingReviewCellIds();
        const isPending = pending.includes(cellId);
        if (this.el.calReviewSave) {
            this.el.calReviewSave.disabled = !isPending || this.calibrationReviewDecisionInFlight;
        }
        if (this.el.calReviewDiscard) {
            this.el.calReviewDiscard.disabled = !isPending || this.calibrationReviewDecisionInFlight;
        }
    }

    renderReviewDragPlot(plotEl, plotState, cellId, measurements, options = {}) {
        if (!plotEl || typeof Plotly === "undefined") {
            return;
        }
        const roughZ = options.roughZ;
        const orderedRpms = this.expandRpmsWithObserved(this.getRpmsForCell(cellId), measurements);
        const floor = this._torqueFloorPctForLivePlots();
        const buckets = this.partitionMeasurementsByRpm(measurements, orderedRpms);
        const traces = orderedRpms
            .map((rpm) => {
                const key = Number(rpm).toFixed(3);
                const points = buckets.get(key) || [];
                if (points.length === 0) {
                    return null;
                }
                return this._buildDragTraceForRpm(rpm, points, floor, orderedRpms);
            })
            .filter(Boolean);

        const baseLayout = {
            margin: { t: 36, r: 20, b: 52, l: 58 },
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(255,255,255,0.35)",
            font: { family: "DM Sans, sans-serif", size: 12, color: "rgb(72, 84, 110)" },
            xaxis: {
                title: "Z-Height (mm)",
                tickformat: ".3f",
                gridcolor: "rgba(180, 200, 230, 0.35)",
                zeroline: false,
            },
            yaxis: {
                title: "Rotational Drag (torque / RPM)",
                gridcolor: "rgba(180, 200, 230, 0.35)",
                zeroline: false,
            },
            showlegend: orderedRpms.length > 1,
            legend: { orientation: "h", y: 1.14, font: { size: 11 } },
        };

        if (!plotState.initialized) {
            plotState.layout = { ...baseLayout };
            Plotly.newPlot(plotEl, traces, plotState.layout, {
                responsive: true,
                displayModeBar: false,
            });
            plotState.initialized = true;
        } else {
            const shapes = Number.isFinite(roughZ)
                ? [{
                    type: "line",
                    x0: roughZ,
                    x1: roughZ,
                    y0: 0,
                    y1: 1,
                    yref: "paper",
                    line: { color: "rgb(255, 59, 48)", width: 2, dash: "dash" },
                }]
                : [];
            plotState.layout = { ...baseLayout, shapes };
            Plotly.react(plotEl, traces, plotState.layout, {
                responsive: true,
                displayModeBar: false,
            });
        }
    }

    renderCalibrationReviewPlot(cellId) {
        const measurements = this.getMeasurementsForReviewCell(cellId);
        const entry = this.getReviewCellEntry(cellId);
        const roughZ = entry ? Number(entry.rough_z) : NaN;
        this.renderReviewDragPlot(
            this.el.calReviewPlot,
            this.calibrationReviewPlotState,
            cellId,
            measurements,
            { roughZ: Number.isFinite(roughZ) ? roughZ : undefined }
        );
    }

    postCalibrationReviewDecision(action) {
        const session = this.calibrationReviewSession;
        const cellId = this.calibrationReviewActiveCellId;
        if (!session || !Number.isFinite(cellId) || this.calibrationReviewDecisionInFlight) {
            return Promise.resolve();
        }
        this.calibrationReviewDecisionInFlight = true;
        if (this.el.calReviewSave) {
            this.el.calReviewSave.disabled = true;
        }
        if (this.el.calReviewDiscard) {
            this.el.calReviewDiscard.disabled = true;
        }
        return fetch("/api/calibration/review/decision", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: session.session_id,
                cell_id: cellId,
                action,
            }),
        })
            .then((r) => r.json())
            .then((result) => {
                if (result.error) {
                    throw new Error(result.error);
                }
                if (result.session) {
                    this.syncCalibrationReviewSession(result.session);
                }
            })
            .catch((err) => {
                this.pushStatusMessage(
                    `Calibration review failed: ${err.message || "unknown error"}`
                );
            })
            .finally(() => {
                this.calibrationReviewDecisionInFlight = false;
                const pending = this.getPendingReviewCellIds();
                if (pending.length === 0) {
                    this.commitCalibrationReview();
                } else {
                    this.renderCalibrationReviewCellView(this.calibrationReviewActiveCellId);
                }
            });
    }

    onCalibrationReviewSave() {
        this.postCalibrationReviewDecision("save");
    }

    onCalibrationReviewDiscard() {
        this.postCalibrationReviewDecision("discard");
    }

    commitCalibrationReview() {
        const session = this.calibrationReviewSession;
        if (!session?.session_id || this.calibrationReviewCommitInFlight) {
            if (!session?.session_id) {
                this.closeCalibrationReviewModal();
            }
            return;
        }
        this.calibrationReviewCommitInFlight = true;
        fetch("/api/calibration/review/commit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: session.session_id }),
        })
            .then((r) => r.json())
            .then((result) => {
                if (result.error) {
                    throw new Error(result.error);
                }
                this.onCalibrationReviewCommitted(result);
            })
            .catch((err) => {
                this.pushStatusMessage(
                    `Failed to save calibration file: ${err.message || "unknown error"}`
                );
            })
            .finally(() => {
                this.calibrationReviewCommitInFlight = false;
            });
    }

    onCalibrationReviewCommitted(payload) {
        this.closeCalibrationReviewModal();
        const saved = payload?.saved_cells || {};
        const summary = payload?.summary;
        if (summary) {
            this.applyCalibrationStatus(summary);
        }
        const ids = Object.keys(saved)
            .map((k) => Number(k))
            .filter((n) => Number.isInteger(n) && n > 0)
            .sort((a, b) => a - b);
        if (ids.length > 0) {
            this.showCalibrationSavedModal(ids, saved);
            this.pushStatusMessage(`Calibration saved for cell(s): ${ids.join(", ")}`);
            if (!this.calibrationPanelOpen) {
                this.toggleCalibrationPanel(true);
            }
        } else {
            this.pushStatusMessage("Calibration review complete — no cells saved");
        }
        this.isCalibrationRun = false;
    }

    _isDiscoveryReviewSession(session) {
        if (!session) {
            return false;
        }
        if (session.discovery_mode_enabled) {
            return true;
        }
        const settings = this.runSettingsSnapshot || this.readControlSettings();
        return Boolean(settings.discovery_mode_enabled);
    }

    _applyExperimentReviewDiscoveryTheme(session) {
        const isDiscovery = this._isDiscoveryReviewSession(session);
        this.el.body.classList.toggle("discovery-review-active", isDiscovery);
        if (this.el.expReviewModal) {
            this.el.expReviewModal.classList.toggle("discovery-review-modal", isDiscovery);
        }
    }

    _getDiscoveryResultForReviewCell(cellId) {
        const session = this.experimentReviewSession;
        const fromSession = session?.discovery_results_by_cell?.[String(cellId)];
        if (fromSession) {
            return fromSession;
        }
        return this.discoveryResultsByCell[String(cellId)] || null;
    }

    getPendingExperimentReviewCellIds() {
        const session = this.experimentReviewSession;
        if (!session) {
            return [];
        }
        const order = session.completion_order || [];
        const cells = session.cells || {};
        return order.filter((cellId) => {
            const key = String(cellId);
            const entry = cells[key];
            return entry && entry.decision === "pending";
        });
    }

    getExperimentReviewCellEntry(cellId) {
        return this.getReviewCellEntry(cellId, this.experimentReviewSession);
    }

    syncExperimentReviewSession(session) {
        if (!session || !session.session_id) {
            return;
        }
        this.experimentReviewSession = session;
        this.experimentReviewPending = true;
        this.updateReviewStartGuard();
        this.updateExperimentReviewHeader(session);
        this._applyExperimentReviewDiscoveryTheme(session);
        this.renderExperimentReviewTabs();
        const pending = this.getPendingExperimentReviewCellIds();
        if (!pending.includes(this.experimentReviewActiveCellId)) {
            this.experimentReviewActiveCellId = pending[0];
        }
        this.renderExperimentReviewCellView(this.experimentReviewActiveCellId);
    }

    openExperimentReview(session) {
        if (!session || !session.session_id) {
            return;
        }
        this.experimentReviewSession = session;
        this.experimentReviewPending = true;
        this.completedSaveLock = true;
        this.updateReviewStartGuard();

        const pending = this.getPendingExperimentReviewCellIds();
        if (pending.length === 0) {
            this.closeExperimentReviewModal();
            return;
        }
        this.experimentReviewActiveCellId = pending[0];

        if (this.el.expReviewBackdrop) {
            this.el.expReviewBackdrop.classList.remove("hidden");
            this.el.expReviewBackdrop.setAttribute("aria-hidden", "false");
        }
        this.updateExperimentReviewHeader(session);
        this._applyExperimentReviewDiscoveryTheme(session);
        this.el.body.classList.add("experiment-review-active");
        this.renderExperimentReviewTabs();
        this.renderExperimentReviewCellView(this.experimentReviewActiveCellId);
        this.handleWindowResize();
        this.pushStatusMessage("Review experiment data — Save or Discard each cell");
    }

    updateExperimentReviewHeader(session) {
        const runEndedEarly = Boolean(session?.run_ended_early);
        const isDiscovery = this._isDiscoveryReviewSession(session);
        if (this.el.expReviewTitle) {
            if (isDiscovery) {
                this.el.expReviewTitle.innerHTML = runEndedEarly
                    ? 'Save Discovery Experiment <span class="protocol-mode-badge mode-discovery">Discovery</span>'
                    : 'Save Discovery Experiment <span class="protocol-mode-badge mode-discovery">Discovery</span>';
            } else {
                this.el.expReviewTitle.textContent = runEndedEarly
                    ? "Save experiment data"
                    : "Save Data";
            }
        }
        if (this.el.expReviewSubtitle) {
            if (runEndedEarly) {
                this.el.expReviewSubtitle.textContent = isDiscovery
                    ? "Discovery run ended early — saved output uses final point per Z×RPM"
                    : "Run ended early — saved output uses final point per Z×RPM";
                this.el.expReviewSubtitle.classList.remove("hidden");
            } else if (isDiscovery) {
                this.el.expReviewSubtitle.textContent = "Discovery run — RPM probe summary included in saved CSV metadata";
                this.el.expReviewSubtitle.classList.remove("hidden");
            } else {
                this.el.expReviewSubtitle.textContent = "";
                this.el.expReviewSubtitle.classList.add("hidden");
            }
        }
    }

    closeExperimentReviewModal() {
        this.experimentReviewPending = false;
        this.experimentReviewSession = null;
        this.experimentReviewActiveCellId = null;
        this.experimentReviewPlotState = { initialized: false, layout: null };
        if (this.el.expReviewBackdrop) {
            this.el.expReviewBackdrop.classList.add("hidden");
            this.el.expReviewBackdrop.setAttribute("aria-hidden", "true");
        }
        this.el.body.classList.remove("experiment-review-active");
        this.el.body.classList.remove("discovery-review-active");
        if (this.el.expReviewModal) {
            this.el.expReviewModal.classList.remove("discovery-review-modal");
        }
        this.updateReviewStartGuard();
    }

    renderExperimentReviewTabs() {
        const tabsEl = this.el.expReviewTabs;
        const session = this.experimentReviewSession;
        if (!tabsEl || !session) {
            return;
        }
        const order = session.completion_order || [];
        const cells = session.cells || {};
        tabsEl.innerHTML = "";
        order.forEach((cellId) => {
            const key = String(cellId);
            const entry = cells[key];
            if (!entry) {
                return;
            }
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "experiment-review-tab data-review-tab";
            if (entry.decision !== "pending") {
                btn.classList.add("resolved");
            }
            if (Number(cellId) === Number(this.experimentReviewActiveCellId)) {
                btn.classList.add("active");
            }
            btn.textContent = `Cell ${cellId}`;
            if (entry.is_partial) {
                const badge = document.createElement("span");
                badge.className = "review-partial-badge";
                badge.textContent = "Partial results";
                btn.appendChild(badge);
            }
            if (entry.decision === "pending") {
                btn.addEventListener("click", () => {
                    this.experimentReviewActiveCellId = Number(cellId);
                    this.renderExperimentReviewTabs();
                    this.renderExperimentReviewCellView(this.experimentReviewActiveCellId);
                });
            }
            tabsEl.appendChild(btn);
        });
    }

    _formatTerminationReason(reason) {
        const raw = String(reason || "normal").trim();
        if (!raw || raw === "normal") {
            return "Normal completion";
        }
        return raw.replace(/_/g, " ");
    }

    renderExperimentReviewSummary(cellId) {
        const box = this.el.expReviewSummary;
        const entry = this.getExperimentReviewCellEntry(cellId);
        if (!box || !entry) {
            return;
        }
        const settings = this.runSettingsSnapshot || this.readControlSettings();
        const label = settings.cell_content_map?.[cellId]
            ?? settings.cell_content_map?.[String(cellId)]
            ?? "";
        const rpms = this.getRpmsForCell(cellId);
        const rpmText = rpms.length ? rpms.map((r) => Number(r).toFixed(3)).join(", ") : "—";
        const zLevelCount = Number(entry.z_level_count);
        const zLevelsText = Number.isFinite(zLevelCount) && zLevelCount > 0
            ? String(zLevelCount)
            : "—";
        const title = label ? `Cell ${cellId} — ${label}` : `Cell ${cellId}`;
        const tMeta = this._terminationDisplayMeta(entry.termination_reason);
        const partialBadge = entry.is_partial
            ? '<span class="review-partial-badge">Partial results</span>'
            : "";
        const runEndedNote = this.experimentReviewSession?.run_ended_early
            ? '<div class="experiment-review-early-note">Run ended early</div>'
            : "";
        const discoveryEntry = this._getDiscoveryResultForReviewCell(cellId);
        let discoveryBlock = "";
        if (discoveryEntry && Array.isArray(discoveryEntry.probes) && discoveryEntry.probes.length > 0) {
            const dEta = discoveryEntry.eta_estimate != null
                ? Number(discoveryEntry.eta_estimate).toLocaleString(undefined, { maximumFractionDigits: 0 })
                : "—";
            discoveryBlock = `
                <div class="summary-discovery-cell-block">
                    <div><strong>RPM discovery</strong> <span class="protocol-mode-badge mode-discovery">Discovery</span></div>
                    <div>Status: ${this._escapeHtml(String(discoveryEntry.status || "—"))} · Discovered RPM: ${discoveryEntry.rpm != null ? Number(discoveryEntry.rpm).toFixed(2) : "—"} · η est: ${dEta} cP</div>
                    ${this._buildDiscoveryStage2SummaryHtml(discoveryEntry)}
                    ${this._buildDiscoveryProbeTableHtml(discoveryEntry.probes, { review: true })}
                </div>`;
        }
        box.innerHTML = `
            <div><strong>${title}</strong> ${partialBadge}</div>
            ${runEndedNote}
            ${discoveryBlock}
            <div>RPMs tested: ${rpmText}</div>
            <div>Termination: <span class="review-termination-chip summary-termination-chip ${tMeta.cls}">${tMeta.text}</span></div>
            <div>Z levels collected: <strong>${zLevelsText}</strong></div>
            ${settings.save_all_sample_data ? "<div>Save all sample data: <strong>enabled</strong> (timeseries CSV written on commit)</div>" : ""}
        `;
    }

    renderExperimentReviewCellView(cellId) {
        if (!Number.isFinite(cellId)) {
            return;
        }
        this.renderExperimentReviewSummary(cellId);
        this.renderExperimentReviewPlot(cellId);
        const pending = this.getPendingExperimentReviewCellIds();
        const isPending = pending.includes(cellId);
        if (this.el.expReviewSave) {
            this.el.expReviewSave.disabled = !isPending || this.experimentReviewDecisionInFlight;
        }
        if (this.el.expReviewDiscard) {
            this.el.expReviewDiscard.disabled = !isPending || this.experimentReviewDecisionInFlight;
        }
    }

    renderExperimentReviewPlot(cellId) {
        const measurements = this.getMeasurementsForReviewCell(cellId, this.experimentReviewSession);
        this.renderReviewDragPlot(
            this.el.expReviewPlot,
            this.experimentReviewPlotState,
            cellId,
            measurements,
            {}
        );
    }

    postExperimentReviewDecision(action) {
        const session = this.experimentReviewSession;
        const cellId = this.experimentReviewActiveCellId;
        if (!session || !Number.isFinite(cellId) || this.experimentReviewDecisionInFlight) {
            return Promise.resolve();
        }
        this.experimentReviewDecisionInFlight = true;
        if (this.el.expReviewSave) {
            this.el.expReviewSave.disabled = true;
        }
        if (this.el.expReviewDiscard) {
            this.el.expReviewDiscard.disabled = true;
        }
        return fetch("/api/experiment/review/decision", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: session.session_id,
                cell_id: cellId,
                action,
            }),
        })
            .then((r) => r.json())
            .then((result) => {
                if (result.error) {
                    throw new Error(result.error);
                }
                if (result.session) {
                    this.syncExperimentReviewSession(result.session);
                }
            })
            .catch((err) => {
                this.pushStatusMessage(
                    `Experiment review failed: ${err.message || "unknown error"}`
                );
            })
            .finally(() => {
                this.experimentReviewDecisionInFlight = false;
                const pending = this.getPendingExperimentReviewCellIds();
                if (pending.length === 0) {
                    this.commitExperimentReview();
                } else {
                    this.experimentReviewActiveCellId = pending[0];
                    this.renderExperimentReviewTabs();
                    this.renderExperimentReviewCellView(this.experimentReviewActiveCellId);
                }
            });
    }

    onExperimentReviewSave() {
        this.postExperimentReviewDecision("save");
    }

    onExperimentReviewDiscard() {
        this.postExperimentReviewDecision("discard");
    }

    commitExperimentReview() {
        const session = this.experimentReviewSession;
        if (!session?.session_id || this.experimentReviewCommitInFlight) {
            if (!session?.session_id) {
                this.closeExperimentReviewModal();
            }
            return;
        }
        this.experimentReviewCommitInFlight = true;
        fetch("/api/experiment/review/commit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: session.session_id }),
        })
            .then((r) => r.json())
            .then((result) => {
                if (result.error) {
                    throw new Error(result.error);
                }
                this.onExperimentReviewCommitted(result);
            })
            .catch((err) => {
                this.pushStatusMessage(
                    `Failed to save experiment data: ${err.message || "unknown error"}`
                );
                if (Number.isFinite(this.experimentReviewActiveCellId)) {
                    this.renderExperimentReviewCellView(this.experimentReviewActiveCellId);
                }
            })
            .finally(() => {
                this.experimentReviewCommitInFlight = false;
            });
    }

    onExperimentReviewCommitted(payload) {
        this.closeExperimentReviewModal();
        this.completedSaveLock = true;
        const entry = payload?.experiment;
        const savedIds = (payload?.saved_cells || [])
            .map((n) => Number(n))
            .filter((n) => Number.isInteger(n) && n > 0)
            .sort((a, b) => a - b);
        if (entry) {
            const previousSelectedId = this.selectedExperimentId;
            this._upsertExperimentHistoryEntry(entry);
            this.renderExperimentCards();
            const selectId = entry.id || (this.experimentHistory[0] && this.experimentHistory[0].id);
            if (selectId && (previousSelectedId === selectId || this.experimentHistory.length > 0)) {
                this.selectExperiment(selectId);
            }
            if (savedIds.length > 0) {
                this.showExperimentSavedModal(savedIds, entry, payload?.csv_filename);
                this.pushStatusMessage(`Experiment data saved for cell(s): ${savedIds.join(", ")}`);
            } else {
                this.pushStatusMessage("Experiment data saved to summary");
            }
        } else {
            this.pushStatusMessage("Experiment review complete — no cells saved");
        }
        this.runSettingsSnapshot = null;
    }

    showExperimentSavedModal(cellIds, experiment, csvFilename) {
        if (!this.el.expSavedBackdrop || !this.el.expSavedBody) {
            return;
        }
        const settings = experiment?.settings || {};
        const labelMap = settings.cell_content_map || {};
        const rpms = Array.isArray(experiment?.rpms) ? experiment.rpms : [];
        const rpmText = rpms.length
            ? rpms.map((r) => Number(r).toFixed(3)).join(", ")
            : null;
        const partialFlags = experiment?.cell_partial_flags || {};
        const items = cellIds
            .map((id) => {
                const label = labelMap[id] ?? labelMap[String(id)] ?? "";
                const labelPart = label ? ` — ${this._escapeHtml(label)}` : "";
                const partialNote = partialFlags[id] || partialFlags[String(id)]
                    ? ' <span class="review-partial-badge">partial results</span>'
                    : "";
                return `<li>Cell ${id}${labelPart}${partialNote}</li>`;
            })
            .join("");
        const csvNote = csvFilename
            ? `<p class="experiment-saved-csv-note">CSV: <code>${this._escapeHtml(String(csvFilename))}</code></p>`
            : "";
        const rpmNote = rpmText
            ? `<p>RPMs in saved run: ${this._escapeHtml(rpmText)}</p>`
            : "";
        this.el.expSavedBody.innerHTML = `
            <p>The following cells were saved to the experiment summary and CSV:</p>
            <ul>${items}</ul>
            ${rpmNote}
            ${csvNote}
        `;
        this.el.expSavedBackdrop.classList.remove("hidden");
        this.el.expSavedBackdrop.setAttribute("aria-hidden", "false");
    }

    hideExperimentSavedModal() {
        if (this.el.expSavedBackdrop) {
            this.el.expSavedBackdrop.classList.add("hidden");
            this.el.expSavedBackdrop.setAttribute("aria-hidden", "true");
        }
    }

    showCalibrationSavedModal(cellIds, savedCells) {
        if (!this.el.calSavedBackdrop || !this.el.calSavedBody) {
            return;
        }
        const items = cellIds
            .map((id) => {
                const z = savedCells[String(id)];
                const zText = Number.isFinite(Number(z)) ? `${Number(z).toFixed(3)} mm` : "—";
                return `<li>Cell ${id}: rough hitpoint ${zText}</li>`;
            })
            .join("");
        this.el.calSavedBody.innerHTML = `
            <p>The following cells were written to the calibration file:</p>
            <ul>${items}</ul>
        `;
        this.el.calSavedBackdrop.classList.remove("hidden");
        this.el.calSavedBackdrop.setAttribute("aria-hidden", "false");
    }

    hideCalibrationSavedModal() {
        if (this.el.calSavedBackdrop) {
            this.el.calSavedBackdrop.classList.add("hidden");
            this.el.calSavedBackdrop.setAttribute("aria-hidden", "true");
        }
    }

    playChime(frequency, duration) {
        try {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (!AudioCtx) {
                return;
            }
            const context = new AudioCtx();
            const oscillator = context.createOscillator();
            const gainNode = context.createGain();

            oscillator.type = "sine";
            oscillator.frequency.value = frequency;
            gainNode.gain.setValueAtTime(0.0001, context.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.08, context.currentTime + 0.02);
            gainNode.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + duration);

            oscillator.connect(gainNode);
            gainNode.connect(context.destination);
            oscillator.start(context.currentTime);
            oscillator.stop(context.currentTime + duration + 0.02);
            oscillator.onended = () => context.close();
        } catch (_err) {
            // Ignore audio failures in restricted browsers.
        }
    }
}

document.addEventListener("DOMContentLoaded", () => {
    window.viscometryDashboard = new ViscometryDashboard();
});

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
        this.currentPhase = 0;
        this.gaugeDisplayRPM = 0;
        this.gaugeAnimationFrame = null;
        this.zPlotInitialized = false;
        this.torquePlotInitialized = false;
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
        this.runMeasurementStartIndex = 0;
        this.lastRunStartTsSec = null;
        this.completedSaveLock = false;
        this.summaryPlotInitialized = false;
        this._summaryHistoryPollIntervalId = null;
        this._summaryHistoryPollMs = 8000;
        /** Debounce heavy Plotly / table DOM work during streaming measurements (remote viewers). */
        this._plotRefreshTimer = null;
        this._tableRefreshTimer = null;
        this._graphTabIdsKey = "";
        this.customHitpointSelectedCellId = null;
        this.isSavingFinalResults = false;
        this.cellRpmMap = {};   // { cellId (number): [rpm, ...] }
        this.cellContentMap = {}; // { cellId (number): "sample label" }
        this.latestControlSettings = {};
        this.predictedViscosityData = {};
        this.calibrationSummary = { is_calibrated: false, cell_count: 0, cells: {}, calibrated_at: null };
        this.calibrationPanelOpen = false;
        this.calChecksComplete = false;
        this.isCalibrationRun = false;

        this.palette = [
            "#5EA1FF", "#F5A623", "#39C5BB", "#2EA043", "#E25A5A", "#9BB5FF",
            "#B6E388", "#FFC47E", "#8FDDE5", "#EA9CB9", "#B9A0FF", "#8FD66B",
            "#73B0F9", "#FFD36A", "#69D5C7", "#86E0A8", "#EFA17C", "#BFC7D5"
        ];

    this.calibrationModeActive = false;  // Server's calibration mode state (persists across page reloads)
    this.recalibrationModeActive = false;
    this.recalibrationTargetCount = 0;

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
        this.loadExperimentHistory();

        // Restore active tab from localStorage
        let activeTab = localStorage.getItem("activeTab") || "layout-tab";
        if (activeTab === "data-tab") {
            activeTab = "data-processing-tab";
        }
        this.switchTab(activeTab);
        this.connectSocket();
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
            map: document.getElementById("platform-map"),
            armDot: document.getElementById("arm-dot"),
            timeline: document.getElementById("timeline"),
            timelineFill: document.getElementById("timeline-fill"),
            statusLog: document.getElementById("status-log"),
            zSparklinePlot: document.getElementById("z-sparkline-plot"),
            zSparklineEmpty: document.getElementById("z-sparkline-empty"),
            torqueZPlot: document.getElementById("torque-z-plot"),
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
            predictedViscosityEnabled: document.getElementById("predicted-viscosity-enabled"),
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
            controlStatus: document.getElementById("control-status"),
            cellFlip: document.getElementById("cell-flip"),
            cellMeta: document.getElementById("cell-meta"),
            gaugeValue: document.getElementById("gauge-value"),
            gaugeNeedle: document.getElementById("gauge-needle"),
            gaugeText: document.getElementById("gauge-rpm"),
            xyzX: document.getElementById("xyz-x"),
            xyzY: document.getElementById("xyz-y"),
            xyzZ: document.getElementById("xyz-z"),
            torqueFill: document.getElementById("torque-fill"),
            torqueValue: document.getElementById("torque-value"),
            torqueDisplay: document.getElementById("torque-display"),
            rotationalDragDisplay: document.getElementById("rotational-drag-display"),
            dragLiveBox: document.getElementById("drag-live-box"),
            zMeasuringDisplay: document.getElementById("z-measuring-display"),
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
            sidebarHit: document.getElementById("sidebar-hit"),
            dragZRpmLegend: document.getElementById("drag-z-rpm-legend"),
            dragZRpmLegendNote: document.getElementById("drag-z-rpm-legend-note"),
            elapsed: document.getElementById("elapsed"),
            elapsedCell: document.getElementById("elapsed-cell"),
            tableBody: document.getElementById("measurement-table"),
            zFilterAll: document.getElementById("z-filter-all"),
            zFilterLatest: document.getElementById("z-filter-latest"),
            zConnectDots: document.getElementById("z-connect-dots"),
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
            summaryShowHitLine: document.getElementById("summary-show-hit-line"),
            summaryAlignHitpoint: document.getElementById("summary-align-hitpoint"),
            summaryCustomHitpointCell: document.getElementById("summary-custom-hitpoint-cell"),
            summaryCustomHitpointZ: document.getElementById("summary-custom-hitpoint-z"),
            summaryMakeCustomHitpoint: document.getElementById("summary-make-custom-hitpoint"),
            summaryUndoCustomHitpoint: document.getElementById("summary-undo-custom-hitpoint"),
            summaryCustomHitpointStatus: document.getElementById("summary-custom-hitpoint-status"),
            summaryPlot: document.getElementById("summary-plot"),
            tabButtons: document.querySelectorAll(".tab-button"),
            tabPanels: document.querySelectorAll(".tab-panel"),
            calPanelSection: document.getElementById("calibration-panel-section"),
            calStatusPill: document.getElementById("cal-status-pill"),
            calStatusText: document.getElementById("cal-status-text"),
            calPanelDetails: document.getElementById("cal-panel-details"),
            calPanelBody: document.getElementById("cal-panel-body"),
            calCheckEmpty: document.getElementById("cal-check-empty"),
            calCheckFeedback: document.getElementById("cal-check-feedback"),
            calCheckSmartExit: document.getElementById("cal-check-smart-exit"),
            calApplyZStep: document.getElementById("cal-apply-z-step"),
            calApplyDuration: document.getElementById("cal-apply-duration"),
            calApplyInterval: document.getElementById("cal-apply-interval"),
            calApplyAll: document.getElementById("cal-apply-all-recommended"),
            calExistingInfo: document.getElementById("cal-existing-info"),
            calExistingSelect: document.getElementById("cal-existing-select"),
            calExistingDetail: document.getElementById("cal-existing-detail"),
            calClearBtn: document.getElementById("cal-clear-btn"),
            calStartBtn: document.getElementById("cal-start-btn"),
            calStartRecalibrationBtn: document.getElementById("cal-start-recalibration-btn"),
            calRecalibrateIndividual: document.getElementById("cal-recalibrate-individual"),
            calCellSelectorContainer: document.getElementById("cal-cell-selector-container"),
            calCellChecks: document.querySelectorAll(".cal-cell-check"),
            calCellZInputs: document.getElementById("cal-cell-z-inputs"),
            calActionHint: document.getElementById("cal-action-hint")
        };
    }

    bindUI() {
        if (this.el.exportTable) {
            this.el.exportTable.addEventListener("click", () => this.exportCSV());
        }
        const onPredictedViscosityToggleChange = () => {
            const checked = Boolean(this.el.predictedViscosityEnabled?.checked);
            this._updatePredictedViscosityChartsCardVisibility(checked);
            this.applyControlSettings(true);
        };
        if (this.el.predictedViscosityEnabled) {
            this.el.predictedViscosityEnabled.addEventListener("change", onPredictedViscosityToggleChange);
        }
        this.el.applySettings.addEventListener("click", () => this.applyControlSettings());
        this.el.startRun.addEventListener("click", () => this.startRunFromUI());
        this.el.stopRun.addEventListener("click", () => this.stopRunFromUI());
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
        if (this.el.summaryShowHitLine) {
            this.el.summaryShowHitLine.addEventListener("change", () => {
                if (this.selectedExperimentId) this.selectExperiment(this.selectedExperimentId);
            });
        }
        if (this.el.summaryAlignHitpoint) {
            this.el.summaryAlignHitpoint.addEventListener("change", () => {
                if (this.selectedExperimentId) this.selectExperiment(this.selectedExperimentId);
            });
        }

        if (this.el.summaryCustomHitpointCell) {
            this.el.summaryCustomHitpointCell.addEventListener("change", () => {
                this.customHitpointSelectedCellId = this.el.summaryCustomHitpointCell.value
                    ? Number(this.el.summaryCustomHitpointCell.value)
                    : null;
                if (this.selectedExperimentId) this.updateCustomHitpointControlsUI();
            });
        }

        if (this.el.summaryMakeCustomHitpoint) {
            this.el.summaryMakeCustomHitpoint.addEventListener("click", () => this.applyCustomHitpointOverrideFromUI());
        }

        if (this.el.summaryUndoCustomHitpoint) {
            this.el.summaryUndoCustomHitpoint.addEventListener("click", () => this.undoCustomHitpointOverrideFromUI());
        }

        document.addEventListener("keydown", (event) => {
            if (event.key.toLowerCase() === "e") {
                this.exportCSV();
            }
        });

        window.addEventListener("resize", () => this.applyArmPosition());

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

        // Calibration panel (compact details dropdown)
        if (this.el.calPanelDetails) {
            this.el.calPanelDetails.open = false;
            this.el.calPanelDetails.addEventListener("toggle", () => {
                this.calibrationPanelOpen = this.el.calPanelDetails.open;
            });
        }

        // Checklist validation
        [this.el.calCheckEmpty, this.el.calCheckFeedback, this.el.calCheckSmartExit].forEach((cb) => {
            if (cb) cb.addEventListener("change", () => this.validateCalibrationChecklist());
        });

        // Apply recommended settings buttons
        if (this.el.calApplyZStep) {
            this.el.calApplyZStep.addEventListener("click", () => {
                if (this.el.zStepSize) this.el.zStepSize.value = "-0.02";
                this.setUiState("idle");
            });
        }
        if (this.el.calApplyDuration) {
            this.el.calApplyDuration.addEventListener("click", () => {
                if (this.el.measurementDuration) this.el.measurementDuration.value = "5";
                this.setUiState("idle");
            });
        }
        if (this.el.calApplyInterval) {
            this.el.calApplyInterval.addEventListener("click", () => {
                if (this.el.sampleInterval) this.el.sampleInterval.value = "4";
                this.setUiState("idle");
            });
        }
        if (this.el.calApplyAll) {
            this.el.calApplyAll.addEventListener("click", () => {
                if (this.el.zStepSize) this.el.zStepSize.value = "-0.02";
                if (this.el.measurementDuration) this.el.measurementDuration.value = "5";
                if (this.el.sampleInterval) this.el.sampleInterval.value = "4";
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
    }

    switchTab(tabId) {
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

        // Store active tab in localStorage
        localStorage.setItem("activeTab", tabId);

        if (tabId === "summary-tab") {
            this.startSummaryHistoryPolling();
        } else {
            this.stopSummaryHistoryPolling();
        }
    }

    startSummaryHistoryPolling() {
        if (this._summaryHistoryPollIntervalId) {
            return;
        }
        this._summaryHistoryPollIntervalId = window.setInterval(() => {
            this.pollExperimentHistoryForCustomHitpoints();
        }, this._summaryHistoryPollMs);
        // Do an immediate sync so another device's changes show up quickly.
        this.pollExperimentHistoryForCustomHitpoints();
    }

    stopSummaryHistoryPolling() {
        if (!this._summaryHistoryPollIntervalId) {
            return;
        }
        window.clearInterval(this._summaryHistoryPollIntervalId);
        this._summaryHistoryPollIntervalId = null;
    }

    pollExperimentHistoryForCustomHitpoints() {
        if (!this.selectedExperimentId) {
            return;
        }
        if (!this.el.summaryDetail || this.el.summaryDetail.classList.contains("hidden")) {
            return;
        }

        const selectedId = this.selectedExperimentId;
        const prevExp = this.experimentHistory.find((e) => e.id === selectedId);
        const prevCustom = JSON.stringify(prevExp?.custom_hitpoints || {});

        fetch("/api/experiment_history")
            .then((r) => r.json())
            .then((history) => {
                if (!Array.isArray(history)) return;
                const nextExp = history.find((e) => e.id === selectedId);
                if (!nextExp) return;
                const nextCustom = JSON.stringify(nextExp?.custom_hitpoints || {});
                if (nextCustom === prevCustom) {
                    return;
                }
                this.experimentHistory = history;
                // Re-render the plot/controls with the synced overrides.
                this.selectExperiment(selectedId);
            })
            .catch(() => {
                // Polling is best-effort; ignore failures to avoid noisy status messages.
            });
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
    }

    updateCellNode(cellId) {
        const node = document.getElementById(`cell-node-${cellId}`);
        if (!node) {
            return;
        }
        const state = this.cellStates.get(cellId) || "pending";
        node.className = `pg-cell state-${state}`;
    }

    applyArmPosition() {
        const xPct = (this.position.x / 450) * 100;
        const yPct = (this.position.y / 400) * 100;
        if (this.el.armDot) {
            this.el.armDot.style.left = `${xPct}%`;
            this.el.armDot.style.top = `${yPct}%`;
        }
    }

    initPlot() {
        const zLayout = {
            paper_bgcolor: "transparent",
            plot_bgcolor: "rgba(255,255,255,0.03)",
            font: { family: "DM Mono", color: "#C9D1D9", size: 12 },
            xaxis: {
                title: "Z-Height (mm)",
                gridcolor: "#21262D",
                zeroline: false,
                autorange: true
            },
            yaxis: {
                title: "Rotational Drag (torque / RPM)",
                gridcolor: "#21262D",
                zeroline: false
            },
            margin: { t: 16, r: 16, b: 45, l: 58 },
            showlegend: false,
        };
        this.zSparklineLayout = zLayout;

        const torqueLayout = {
            paper_bgcolor: "transparent",
            plot_bgcolor: "rgba(255,255,255,0.03)",
            font: { family: "DM Mono", color: "#C9D1D9", size: 12 },
            xaxis: {
                title: "Z-Height (mm)",
                gridcolor: "#21262D",
                zeroline: false,
                autorange: "reversed"
            },
            yaxis: {
                title: "Torque (%)",
                gridcolor: "#21262D",
                zeroline: false
            },
            margin: { t: 16, r: 16, b: 45, l: 58 },
            legend: { bgcolor: "transparent", bordercolor: "#30363D" }
        };

        const config = {
            responsive: true,
            displaylogo: false,
            modeBarButtonsToAdd: [
                {
                    name: "Export CSV",
                    icon: Plotly.Icons.disk,
                    click: () => this.exportCSV()
                }
            ],
            modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"]
        };

        if (this.el.zSparklinePlot) {
            Plotly.newPlot(this.el.zSparklinePlot, [], zLayout, config).then(() => {
                this.zPlotInitialized = true;
                this.refreshLivePlots();
            });
        }

        if (this.el.torqueZPlot) {
            Plotly.newPlot(this.el.torqueZPlot, [], torqueLayout, config).then(() => {
                this.torquePlotInitialized = true;
                this.refreshLivePlots();
            });
        }
    }

    initGauge() {
        const circumference = 2 * Math.PI * 72;
        this.gaugeArcLength = circumference * 0.75;
        this.el.gaugeValue.style.strokeDasharray = `${this.gaugeArcLength} ${circumference}`;
        this.el.gaugeValue.style.strokeDashoffset = `${this.gaugeArcLength}`;
        this.updateGauge(0);
    }

    startTimerLoop() {
        this.timerInterval = window.setInterval(() => {
            this.updateTimers();
        }, 1000);
    }

    fetchInitialData() {
        Promise.all([
            fetch("/api/status").then((r) => r.json()),
            fetch("/api/measurement_data").then((r) => r.json()),
            fetch("/api/calibration/status").then((r) => r.json()),
            fetch("/api/predicted_viscosity").then((r) => r.json()).catch(() => ({})),
        ])
            .then(([status, measurementData, calSummary, predictedViscosity]) => {
                this.applyStatusSnapshot(status);
                if (Array.isArray(measurementData)) {
                    measurementData.forEach((m) => this.ingestMeasurement(m, true));
                    this.refreshLivePlots();
                }
                this._hydratePredictedViscosityFromServer(
                    predictedViscosity || status.predicted_viscosity_results
                );
                this.applyCalibrationStatus(calSummary);
                this.el.body.classList.remove("loading");
                this.pushStatusMessage(status.status_message || "Connected and ready");
            })
            .catch(() => {
                this.statusError = true;
                this.pushStatusMessage("Status bootstrap failed, waiting for live socket updates");
                this.showDisconnectedBanner(true);
            });
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
        const predEnabled = Boolean(settings.predicted_viscosity_enabled);
        if (this.el.predictedViscosityEnabled) {
            this.el.predictedViscosityEnabled.checked = predEnabled;
        }
        this._updatePredictedViscosityChartsCardVisibility(predEnabled);
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
        this.latestControlSettings = JSON.parse(JSON.stringify(settings));

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
            predicted_viscosity_enabled: Boolean(this.el.predictedViscosityEnabled?.checked),
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
        if (this.uiState !== "ready") {
            this.setControlStatus("Apply settings before starting");
            return;
        }
        this.setUiState("running");
        this.applyControlSettings(true)
            .then((settings) => {
                this._syncPlannedCells(this.readControlSettings());
                return fetch("/api/run/start", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(settings)
                });
            })
            .then((response) => response.json())
            .then((result) => {
                this.setControlStatus(result.status_message || "Run started");
            })
            .catch(() => {
                this.setUiState("idle");
                this.setControlStatus("Failed to start run");
            });
    }

    stopRunFromUI() {
        this.setUiState("idle");
        fetch("/api/run/stop", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({})
        })
            .then((response) => response.json())
            .then((result) => {
                this.setControlStatus(result.status_message || "Stop requested");
            })
            .catch(() => {
                this.setControlStatus("Failed to stop run");
            });
    }

    connectSocket() {
        this.socket = io({ reconnectionAttempts: 5 });

        this.socket.on("connect", () => {
            this.isConnected = true;
            this.el.connectionDot.classList.remove("disconnected");
            this.el.connectionDot.classList.add("connected");
            this.showDisconnectedBanner(false);
            this.pushStatusMessage("Socket connection established");
        });

        this.socket.on("disconnect", () => {
            this.isConnected = false;
            this.el.connectionDot.classList.remove("connected");
            this.el.connectionDot.classList.add("disconnected");
            this.showDisconnectedBanner(true);
        });

        this.socket.on("status_update", (data) => {
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
        });

        this.socket.on("new_measurement", (data) => {
            this.addPointToChart(
                data.cell_id,
                data.height,
                data.rotational_drag,
                data.rpm,
                data.timestamp,
                data.hit_detected
            );
            const torquePercent = Number.isFinite(Number(data.torque_percent))
                ? Number(data.torque_percent)
                : (Number(data.rotational_drag) || 0) * (Number(data.rpm) || 0);
            this.updateTorqueBar(torquePercent);
            this.updateLiveTorqueDisplay(torquePercent);
            this.updateLiveRotationalDragDisplay(data.rotational_drag);
        });

        this.socket.on("torque_update", (data) => {
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
            const wasRunning = this.isRunning;
            if (data.is_running && !this.isRunning) {
                this.runMeasurementStartIndex = this.measurements.length;
                this.completedSaveLock = false;
            }
            if (!data.is_running && wasRunning) {
                this.isRunning = false;
                this.saveCompletedExperiment();
            }
            this.setRunningState(Boolean(data.is_running), wasRunning);
        });

        this.socket.on("experiment_start", (data) => {
            const startTs = Number(data?.start_ts);
            this.experimentStart = Number.isFinite(startTs) ? startTs * 1000 : Date.now();
            this.lastRunStartTsSec = Number.isFinite(startTs) ? startTs : (this.experimentStart / 1000);
            this.cellStart = Date.now();
            this._hideExperimentCompleteMessage();
            if (this.el.elapsed) {
                this.el.elapsed.textContent = "00:00:00";
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
            this.recalibrationModeActive = Boolean(data?.recalibration_mode_active);
            this.recalibrationTargetCount = Number(data?.recalibration_target_count) || 0;
            this.updateCompletionBar();
            this.updateCellVisuals();
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
            }
        });

        this.socket.on("feedback_metrics_update", (data) => {
            if (data) {
                this.updateDragZSidebar(data);
            }
        });

        this.socket.on("clear_dashboard", () => {
            this.clearDashboard();
        });

        this.socket.on("predicted_viscosity_update", (payload) => {
            this._ingestPredictedViscosityUpdate(payload);
        });

        this.socket.on("calibration_status_update", (summary) => {
            this.applyCalibrationStatus(summary);
        });

        this.socket.on("calibration_complete", (summary) => {
            this.applyCalibrationStatus(summary);
            this.pushStatusMessage("✓ Calibration complete — Z-height data saved for all cells");
            // Auto-open panel so user sees the green confirmation
            if (!this.calibrationPanelOpen) {
                this.toggleCalibrationPanel(true);
            }
            this.isCalibrationRun = false;
        });

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
        this.cellStates.forEach((_, cellId) => this.cellStates.set(cellId, "pending"));
        this.washingCell = null;
        this._pendingCompletedCell = null;
        this.selectedGraphCell = null;
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
        this.currentPhase = 0;
        this._graphTabIdsKey = "";
        if (this._plotRefreshTimer) {
            window.clearTimeout(this._plotRefreshTimer);
            this._plotRefreshTimer = null;
        }
        if (this._tableRefreshTimer) {
            window.clearTimeout(this._tableRefreshTimer);
            this._tableRefreshTimer = null;
        }

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
        if (this.el.elapsedCell) {
            this.el.elapsedCell.textContent = "Cell 00:00:00";
        }
        if (this.el.zMeasuringDisplay) {
            this.el.zMeasuringDisplay.textContent = "-";
        }
        if (this.el.rotationalDragDisplay) {
            this.el.rotationalDragDisplay.textContent = "0.000";
        }
        if (this.el.torqueDisplay) {
            this.el.torqueDisplay.textContent = "0.00 %";
        }
        if (this.el.torqueValue) {
            this.el.torqueValue.textContent = "0.00";
        }
        if (this.el.sidebarRpm) this.el.sidebarRpm.textContent = "-";
        if (this.el.sidebarSecondDerivDrag) this.el.sidebarSecondDerivDrag.textContent = "-";
        if (this.el.sidebarSecondDerivCv) this.el.sidebarSecondDerivCv.textContent = "-";
        if (this.el.sidebarSecondDerivSlope) this.el.sidebarSecondDerivSlope.textContent = "-";
        if (this.el.sidebarR2Drag) this.el.sidebarR2Drag.textContent = "-";
        if (this.el.sidebarR2Cv) this.el.sidebarR2Cv.textContent = "-";
        if (this.el.sidebarR2Slope) this.el.sidebarR2Slope.textContent = "-";
        if (this.el.sidebarConfidence) this.el.sidebarConfidence.textContent = "-";
        if (this.el.sidebarHit) {
            this.el.sidebarHit.textContent = "No";
            this.el.sidebarHit.className = "sidebar-value mono hit-no";
        }
        this.renderDragZRpmLegend(null, []);

        this.platform.cells.forEach((cell) => this.cellStates.set(cell.id, "pending"));
        this.renderMap();
        this.updateCellDisplay();
        this.updateCellVisuals();
        this.updateCompletionBar();
        this.updateGauge(0);
        this.updateTorqueBar(0);
        this.updateLiveTorqueDisplay(0);
        this.updateLiveRotationalDragDisplay(0);
        if (this.el.zMeasuringDisplay) {
            this.el.zMeasuringDisplay.textContent = "-";
        }
        this.updateGraphCellTabs();
        this.refreshLivePlots();
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
            this.updateCompletionBar();
            this.updateCellVisuals();
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
            this.refreshLivePlots();
        }

        if (status.predicted_viscosity_results) {
            this._hydratePredictedViscosityFromServer(status.predicted_viscosity_results);
        }

        if (status.status_message) {
            this.consumeStatusForPhase(status.status_message);
        }
    }

    queueRender() {
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

        if (previousCell && this.currentCell !== previousCell) {
            this.measuredCells.add(previousCell);
            this._pendingCompletedCell = previousCell;
            this.cellStates.set(previousCell, "washing");
            this.playChime(660, 0.08);
            this.updateCompletionBar();
        }

        // Reset timeline to phase 1 when a new cell starts
        if (this.currentCell && this.currentCell !== previousCell) {
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
        this.refreshLivePlots();
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
        const statusLower = (this.statusLog[0] || "").toLowerCase();
        const hasErrorStatus = statusLower.includes("error") || statusLower.includes("fail") || statusLower.includes("critical");
        let activeStation = null;
        if (statusLower.includes("wash station 1") || statusLower.includes("motor 1") || statusLower.includes("pump 1")) {
            activeStation = "WASH";
        } else if (statusLower.includes("wash station 2") || statusLower.includes("motor 2") || statusLower.includes("pump 2")) {
            activeStation = "DRY";
        }

        this.platform.cells.forEach((cell) => {
            const overrideState = this.cellStates.get(cell.id);
            let state = overrideState || "pending";

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
        });

        this.renderMap();

        ["WASH", "DRY"].forEach((id) => {
            const node = document.getElementById(`station-${id}`);
            if (!node) {
                return;
            }
            node.classList.toggle("station-active", activeStation === id);
        });
    }

    consumeStatusForPhase(message) {
        const normalized = (message || "").toLowerCase();
        let phase = 0;

        // Phase 1 — moving to cell
        if (
            normalized.includes("moving to cell") ||
            normalized.includes("auto-zeroing") ||
            normalized.includes("initializing")
        ) {
            phase = 1;
        }
        // Phase 2 — auto-zero
        else if (
            normalized.includes("zeroing") ||
            normalized.includes("auto-zero")
        ) {
            phase = 2;
        }
        // Phase 3 — Z-descent and measurement
        else if (
            normalized.includes("descending") ||
            normalized.includes("measuring") ||
            normalized.includes("z-step") ||
            normalized.includes("testing cell") ||
            normalized.includes("at rpm") ||
            normalized.includes("rotational drag")
        ) {
            phase = 3;
        }
        // Phase 4 — raising Z / returning / saving
        else if (
            normalized.includes("returning") ||
            normalized.includes("raising") ||
            normalized.includes("safe z") ||
            normalized.includes("saving")
        ) {
            phase = 4;
        }
        // Phase 5 — wash station 1
        else if (
            normalized.includes("wash station 1") ||
            normalized.includes("washing after") ||
            normalized.includes("pump 1") ||
            normalized.includes("motor 1")
        ) {
            phase = 5;
            // Capture which cell is being washed from messages like "Washing after Cell 3"
            const washMatch = message.match(/washing after cell\s+(\d+)/i);
            if (washMatch) {
                this.washingCell = Number(washMatch[1]);
            }
        }
        // Phase 6 — wash station 2
        else if (
            normalized.includes("wash station 2") ||
            normalized.includes("pump 2") ||
            normalized.includes("motor 2") ||
            normalized.includes("wash sequence completed")
        ) {
            phase = 6;
            if (
                normalized.includes("completed") ||
                normalized.includes("stopping motor 2") ||
                normalized.includes("wash sequence completed")
            ) {
                this._finalizePendingCompletedCell();
            }
        }

        if (phase !== 0) {
            this.currentPhase = phase;
            this.updateTimeline();
            this.updateCellVisuals();
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
        const nodes = this.el.timeline.querySelectorAll("li");
        nodes.forEach((node) => {
            const phase = Number(node.dataset.phase);
            node.classList.remove("current", "done");
            if (phase < this.currentPhase) {
                node.classList.add("done");
            } else if (phase === this.currentPhase) {
                node.classList.add("current");
            }
        });

        const fillPct = this.currentPhase > 0 ? this.currentPhase / 6 : 0;
        this.el.timelineFill.style.transform = `scaleX(${fillPct})`;
    }

    _schedulePlotRefresh() {
        if (this._plotRefreshTimer) {
            window.clearTimeout(this._plotRefreshTimer);
        }
        this._plotRefreshTimer = window.setTimeout(() => {
            this._plotRefreshTimer = null;
            this.refreshLivePlots();
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
        };

        if (!measurement.cell_id) {
            return;
        }

        this.measurements.push(measurement);

        if (!this.measurementsByCell.has(measurement.cell_id)) {
            this.measurementsByCell.set(measurement.cell_id, []);
        }
        this.measurementsByCell.get(measurement.cell_id).push(measurement);

        this.latestTorqueByCell.set(measurement.cell_id, measurement.torque_percent);

        if (this.currentCell === measurement.cell_id) {
            this.updateTorqueBar(measurement.torque_percent);
            this.updateLiveTorqueDisplay(measurement.torque_percent);
            this.updateLiveRotationalDragDisplay(measurement.rotational_drag);
        }

        const nextTabKey = this.getGraphCellIds().join(",");
        if (nextTabKey !== this._graphTabIdsKey) {
            this._graphTabIdsKey = nextTabKey;
            this.updateGraphCellTabs();
        }

        this._schedulePlotRefresh();
        this._scheduleTableRefresh();
        this.updateCellVisuals();
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
            });
            this.el.graphCellTabs.appendChild(btn);
        });
    }

    /** Torque % floor from "First-sample torque floor (%)" — used to tint live Z plots (below = red). */
    _torqueFloorPctForLivePlots() {
        const v = Number(this.el.lowTorqueLiquidContactThresholdPct?.value);
        return Number.isFinite(v) ? v : 20;
    }

    _markerColorsForTorqueFloor(measurements, floorPct) {
        const belowFill = "#f85149";
        const belowLine = "#ffb4a6";
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

    _markerColorsForRpmTrace(measurements, floorPct, rpmColor) {
        const belowFill = "#f85149";
        const belowLine = "#ffb4a6";
        return measurements.map((m) => {
            const tp = Number(m.torque_percent);
            const below = Number.isFinite(tp) && tp < floorPct;
            return {
                fill: below ? belowFill : rpmColor,
                line: below ? belowLine : rpmColor,
                below,
            };
        });
    }

    _buildDragTraceForRpm(rpm, points, torqueFloor, orderedRpms) {
        const rpmColor = this.getRpmColor(rpm, orderedRpms);
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
                size: 8,
                color: markerPalette.map((p) => p.fill),
                line: {
                    width: 1,
                    color: markerPalette.map((p) => p.line),
                },
            },
            hovertemplate: `RPM ${rpmLabel}<br>Z %{x:.3f} mm<br>Drag %{y:.4f}<br>Torque %{customdata:.2f}%<extra></extra>`,
            customdata: sorted.map((m) => Number(m.torque_percent)),
        };
        if (this.zConnectDots) {
            trace.line = { color: rpmColor, width: 2 };
        }
        return trace;
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
        listEl.innerHTML = orderedRpms.map((rpm) => {
            const color = this.getRpmColor(rpm, orderedRpms);
            const label = Number(rpm).toFixed(3);
            return (
                `<div class="rpm-legend-row">`
                + `<span class="rpm-legend-swatch" style="background:${color}"></span>`
                + `<span class="rpm-legend-label">RPM ${label}</span>`
                + `</div>`
            );
        }).join("");
    }

    refreshLivePlots() {
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

        let orderedRpms = activeCell ? this.expandRpmsWithObserved(this.getRpmsForCell(activeCell), zData) : [];
        const buckets = this.partitionMeasurementsByRpm(zData, orderedRpms);

        if (this.zPlotInitialized && this.el.zSparklinePlot) {
            const zTraces = orderedRpms
                .map((rpm) => {
                    const key = Number(rpm).toFixed(3);
                    const points = buckets.get(key) || [];
                    if (points.length === 0) {
                        return null;
                    }
                    return this._buildDragTraceForRpm(rpm, points, torqueFloor, orderedRpms);
                })
                .filter(Boolean);

            const layout = this.zSparklineLayout || undefined;
            Plotly.react(this.el.zSparklinePlot, zTraces, layout, { responsive: true, displayModeBar: false });
            if (this.el.zSparklineEmpty) {
                this.el.zSparklineEmpty.classList.toggle("hidden", zTraces.length > 0);
            }
            this.renderDragZRpmLegend(activeCell, orderedRpms);
        }

        const torqueData = [...source].sort((a, b) => a.height - b.height);
        if (this.torquePlotInitialized && this.el.torqueZPlot) {
            const torqueDefault = "#F5A623";
            const torqueLineDefault = "#ffd37a";
            const tPalette = torqueData.length ? this._markerColorsForTorqueFloor(torqueData, torqueFloor) : [];
            const torqueTrace = torqueData.length ? [{
                x: torqueData.map((m) => m.height),
                y: torqueData.map((m) => m.torque_percent),
                mode: "markers",
                type: "scatter",
                name: activeCell ? `Cell ${activeCell}` : "No Cell",
                marker: {
                    size: 8,
                    color: tPalette.map((p) => p.fill || torqueDefault),
                    line: {
                        width: 1,
                        color: tPalette.map((p) => p.line || torqueLineDefault),
                    },
                },
                hovertemplate: "Z %{x:.3f} mm<br>Torque %{y:.3f}%<extra></extra>"
            }] : [];

            Plotly.react(this.el.torqueZPlot, torqueTrace, undefined, { responsive: true, displayModeBar: false });
            if (this.el.torqueZEmpty) {
                this.el.torqueZEmpty.classList.toggle("hidden", torqueTrace.length > 0);
            }
        }
    }

    updateGauge(targetRPM) {
        const clamped = Math.max(0, Math.min(100, targetRPM));
        if (this.gaugeAnimationFrame) {
            cancelAnimationFrame(this.gaugeAnimationFrame);
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
            const pct = value / 200;
            const offset = this.gaugeArcLength * (1 - pct);
            const angle = -135 + 270 * pct;

            this.el.gaugeValue.style.strokeDashoffset = String(offset);
            this.el.gaugeNeedle.style.transform = `rotate(${angle}deg)`;
            this.el.gaugeText.textContent = value.toFixed(1);

            if (progress < 1) {
                this.gaugeAnimationFrame = requestAnimationFrame(animate);
            }
        };

        this.gaugeAnimationFrame = requestAnimationFrame(animate);
        this.el.body.classList.toggle("spinning", clamped > 0.5);
    }

    updateTorqueBar(value) {
        const torquePercent = Number(value) || 0;
        const pct = Math.max(0, Math.min(100, torquePercent));
        this.el.torqueFill.style.height = `${pct}%`;
        this.el.torqueValue.textContent = `${torquePercent.toFixed(2)}%`;

        if (pct > 80) {
            this.el.torqueFill.style.background = "linear-gradient(180deg, #f85149, #c2322b)";
        } else if (pct > 50) {
            this.el.torqueFill.style.background = "linear-gradient(180deg, #f5a623, #d5891d)";
        } else {
            this.el.torqueFill.style.background = "linear-gradient(180deg, #2ea043, #1a7431)";
        }
    }

    updateLiveTorqueDisplay(value) {
        const torque = Number(value) || 0;
        this.currentTorquePercent = torque;
        if (this.el.torqueDisplay) {
            this.el.torqueDisplay.textContent = `${torque.toFixed(2)} %`;
        }
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

    updateDragZSidebar(data) {
        if (this.el.sidebarRpm) {
            this.el.sidebarRpm.textContent = data.rpm != null ? `${Number(data.rpm).toFixed(2)} RPM` : "-";
        }
        const fmt = (v) => v != null && !Number.isNaN(Number(v)) ? Number(v).toFixed(4) : "-";
        const r2DragThreshold = Number(this.el.r2DragMin?.value ?? 0.975);
        const r2CvThreshold = Number(this.el.r2CvMin?.value ?? 0.975);
        const r2SlopeThreshold = Number(this.el.r2SlopeMin?.value ?? 0.975);
        if (this.el.sidebarSecondDerivDrag) this.el.sidebarSecondDerivDrag.textContent = fmt(data.second_derivative_drag);
        if (this.el.sidebarSecondDerivCv) this.el.sidebarSecondDerivCv.textContent = fmt(data.second_derivative_cv);
        if (this.el.sidebarSecondDerivSlope) this.el.sidebarSecondDerivSlope.textContent = fmt(data.second_derivative_slope);
        if (this.el.sidebarR2Drag) this.el.sidebarR2Drag.textContent = fmt(data.trend_r_squared);
        if (this.el.sidebarR2Cv) this.el.sidebarR2Cv.textContent = fmt(data.moving_r2_cv);
        if (this.el.sidebarR2Slope) this.el.sidebarR2Slope.textContent = fmt(data.moving_r2_slope);
        if (this.el.sidebarMethodR2Drag) this.el.sidebarMethodR2Drag.textContent = `Threshold ≥ ${r2DragThreshold.toFixed(3)}`;
        if (this.el.sidebarMethodR2Cv) this.el.sidebarMethodR2Cv.textContent = `Threshold ≥ ${r2CvThreshold.toFixed(3)}`;
        if (this.el.sidebarMethodR2Slope) this.el.sidebarMethodR2Slope.textContent = `Threshold ≥ ${r2SlopeThreshold.toFixed(3)}`;
        if (this.el.sidebarMethod2ndDerivDrag) this.updateCalibrationBadge(this.el.sidebarMethod2ndDerivDrag, Boolean(data.drag_sd2_calibrated));
        if (this.el.sidebarMethod2ndDerivCv) this.updateCalibrationBadge(this.el.sidebarMethod2ndDerivCv, Boolean(data.cv_sd2_calibrated));
        if (this.el.sidebarMethod2ndDerivSlope) this.updateCalibrationBadge(this.el.sidebarMethod2ndDerivSlope, Boolean(data.slope_sd2_calibrated));
        if (this.el.sidebarConfidence) this.el.sidebarConfidence.textContent = fmt(data.hit_confidence);

        if (this.el.sidebarHit) {
            const isHit = Boolean(data.hit_detected);
            this.el.sidebarHit.textContent = isHit ? "YES ⚠" : "No";
            this.el.sidebarHit.className = `sidebar-value mono ${isHit ? "hit-yes" : "hit-no"}`;
        }
    }

    setUiState(state) {
        this.uiState = state;

        const applyBtn = this.el.applySettings;
        const startBtn = this.el.startRun;
        const stopBtn = this.el.stopRun;

        [applyBtn, startBtn, stopBtn].forEach((btn) => {
            btn.classList.remove("is-active", "is-idle");
        });

        if (state === "idle") {
            applyBtn.classList.add("is-active");
            startBtn.classList.add("is-idle");
            stopBtn.classList.add("is-idle");
            startBtn.disabled = true;
            stopBtn.disabled = true;
            applyBtn.disabled = false;
        } else if (state === "ready") {
            applyBtn.classList.add("is-idle");
            startBtn.classList.add("is-active");
            stopBtn.classList.add("is-idle");
            applyBtn.disabled = false;
            startBtn.disabled = false;
            stopBtn.disabled = true;
        } else if (state === "running") {
            applyBtn.classList.add("is-idle");
            startBtn.classList.add("is-idle");
            stopBtn.classList.add("is-active");
            applyBtn.disabled = true;
            startBtn.disabled = true;
            stopBtn.disabled = false;
        }
    }

    toggleCalibrationPanel(forceOpen = null) {
        if (!this.el.calPanelDetails) return;

        if (forceOpen === true) {
            this.el.calPanelDetails.open = true;
        } else if (forceOpen === false) {
            this.el.calPanelDetails.open = false;
        } else {
            this.el.calPanelDetails.open = !this.el.calPanelDetails.open;
        }

        this.calibrationPanelOpen = this.el.calPanelDetails.open;
    }

    validateCalibrationChecklist() {
        const empty = this.el.calCheckEmpty?.checked || false;
        const feedback = this.el.calCheckFeedback?.checked || false;
        const noSmartExit = this.el.calCheckSmartExit?.checked || false;
        this.calChecksComplete = empty && feedback && noSmartExit;

        if (this.el.calStartBtn) {
            this.el.calStartBtn.disabled = !this.calChecksComplete || this.isRunning;
        }
        if (this.el.calActionHint) {
            this.el.calActionHint.textContent = this.calChecksComplete
                ? "Ready to calibrate all 18 cells"
                : "Complete the checklist above to enable calibration";
        }
    }

    applyCalibrationStatus(summary) {
        if (!summary) return;
        this.calibrationSummary = summary;
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

        // Existing calibration info block
        const infoBlock = this.el.calExistingInfo;
        const detail = this.el.calExistingDetail;
        if (infoBlock) {
            infoBlock.classList.toggle("hidden", !isOk);
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
        if (!this.calChecksComplete) {
            this.pushStatusMessage("Complete the calibration checklist before starting");
            return;
        }
        if (this.isRunning) {
            this.pushStatusMessage("A run is already in progress");
            return;
        }

        // Build settings — apply recommended values if not already set
        const settings = this.readControlSettings();
        settings.calibration_mode = true;
        settings.testing_mode = "full";  // Always all 18 cells

        this.isCalibrationRun = true;
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
        if (this.el.calStartRecalibrationBtn) {
            this.el.calStartRecalibrationBtn.disabled = !hasSelected || this.isRunning;
        }
    }

    startRecalibrationRun() {
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

        // Build settings
        const settings = this.readControlSettings();
        settings.recalibrate_individual_cells = true;
        settings.recalibration_cells = recalibrationCells;
        settings.calibration_mode = false;  // Not full calibration mode
        settings.testing_mode = "custom";
        settings.selected_cells = selectedCells;

        this.isCalibrationRun = true;
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
        if (this.el.zMeasuringDisplay) {
            this.el.zMeasuringDisplay.textContent = `${value.toFixed(3)} mm`;
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
            this.cellStart = Date.now();
            this.isSavingFinalResults = false;
            this.measuredCells.clear();
            this.completedCells.clear();
            this.washingCell = null;
            this._pendingCompletedCell = null;
            this.currentPhase = 0;
            this.updateTimeline();
            this.updateCompletionBar();
            this._hideExperimentCompleteMessage();
            if (this.el.elapsed) {
                this.el.elapsed.textContent = "00:00:00";
            }
            this.setControlStatus("Run active");
        }

        if (isRunning && this.uiState !== "running") {
            this.setUiState("running");
        }

        if (!isRunning) {
            this.washingCell = null;
            if (previous) {
                this.playChime(720, 0.14);
                this.setControlStatus("Run stopped");
                // Mark timeline as fully complete when run stops
                this.currentPhase = 6;
                this.updateTimeline();
                // Then immediately reset for next run after a brief visual pause
                setTimeout(() => {
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
        }

        if (this.el.calStartBtn) {
            this.el.calStartBtn.disabled = isRunning || !this.calChecksComplete;
        }

        // Update recalibration button state based on running status
        if (this.el.calStartRecalibrationBtn) {
            this.updateRecalibrationButtonState();
        }
    }

    initSummaryPlot() {
        if (!this.el.summaryPlot) {
            return;
        }
        this.summaryPlotLayout = {
            xaxis: {
                title: "Z-Height (mm) - descent ->",
                autorange: true,
                tickformat: ".3f",
            },
            yaxis: { title: "Rotational Drag (torque / RPM)", rangemode: "tozero" },
            margin: { t: 20, r: 16, b: 56, l: 64 },
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            font: { color: "#c9d1d9" },
            legend: { orientation: "h", y: -0.22 }
        };
        Plotly.newPlot(this.el.summaryPlot, [], this.summaryPlotLayout,
            { responsive: true, displayModeBar: false });
        this.summaryPlotInitialized = true;
    }

    loadExperimentHistory() {
        fetch("/api/experiment_history")
            .then((response) => response.json())
            .then((history) => {
                this.experimentHistory = Array.isArray(history) ? history : [];
                this.renderExperimentCards();
            })
            .catch(() => {
                this.experimentHistory = [];
                this.renderExperimentCards();
            });
    }

    saveExperimentHistoryEntry(entry) {
        return fetch("/api/experiment_history", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(entry)
        });
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

        const csvHeader = "timestamp,cell_id,height_mm,torque_percent,rotational_drag,rpm\n";
        const csvBody = runData.map((m) => {
            const iso = new Date(m.timestamp * 1000).toISOString();
            return `${iso},${m.cell_id},${m.height},${m.torque_percent},${m.rotational_drag},${m.rpm}`;
        }).join("\n");

        const settingsSnapshot = this.latestControlSettings && Object.keys(this.latestControlSettings).length > 0
            ? this.latestControlSettings
            : (this.readControlSettings ? this.readControlSettings() : {});

        const exp = {
            id: `exp-${Date.now()}`,
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
            predicted_viscosity_enabled: Boolean(settingsSnapshot.predicted_viscosity_enabled),
            predicted_viscosity: JSON.parse(JSON.stringify(this.predictedViscosityData || {})),
        };

        this.experimentHistory.unshift(exp);
        this.experimentHistory = this.experimentHistory.slice(0, 40);
        this.saveExperimentHistoryEntry(exp).catch(() => {
            this.pushStatusMessage("Warning: failed to sync experiment history to server");
        });
        this.renderExperimentCards();
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
            const experimentName = (exp.settings && exp.settings.experiment_name) ? exp.settings.experiment_name : "(unnamed)";
            const card = document.createElement("div");
            card.className = `experiment-card${exp.id === this.selectedExperimentId ? " active" : ""}`;
            card.innerHTML = `
            <div class="experiment-card-row">
                <strong>${new Date(exp.created_at).toLocaleString()}</strong>
            </div>
            <div class="experiment-card-row">
                <span>Name</span><span>${experimentName}</span>
            </div>
            <div class="experiment-card-row">
                <span>Cells</span><span>${exp.cells.join(", ") || "-"}</span>
            </div>
            <div class="experiment-card-row">
                <span>RPMs</span><span>${exp.rpms.join(", ") || "-"}</span>
            </div>`;

            const del = document.createElement("button");
            del.className = "experiment-delete";
            del.textContent = "x";
            del.addEventListener("click", (e) => {
                e.stopPropagation();
                this.deleteExperiment(exp.id);
            });
            card.appendChild(del);
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
            ? Object.entries(s.cell_content_map).map(([cellId, label]) => `C${cellId}: ${label}`).join(" | ")
            : "";
        const feedbackRows = s.feedback_control_enabled ? [
            `<strong>Feedback enabled:</strong> Yes`,
            `<strong>R_2 Drag threshold:</strong> ${s.r2_drag_min ?? "-"}`,
            `<strong>R_2 CV threshold:</strong> ${s.r2_cv_min ?? "-"}`,
            `<strong>R_2 Slope threshold:</strong> ${s.r2_slope_min ?? "-"}`,
            `<strong>Hit Confidence threshold:</strong> ${s.hit_point_confidence_threshold ?? "-"}`,
            `<strong>w (2nd Deriv Drag/CV/Slope):</strong> ${s.weight_2nd_deriv_drag ?? "-"}/${s.weight_2nd_deriv_cv ?? "-"}/${s.weight_2nd_deriv_slope ?? "-"}`,
            `<strong>w (R_2 Drag/CV/Slope):</strong> ${s.weight_r2_drag ?? "-"}/${s.weight_r2_cv ?? "-"}/${s.weight_r2_slope ?? "-"}`,
        ] : ["<strong>Feedback enabled:</strong> No"];

        const durationRows = exp.cells.map((cellId) => {
            const dur = exp.cellDurations?.[cellId];
            const label = s.cell_content_map?.[cellId] ? ` (${s.cell_content_map[cellId]})` : "";
            const timeStr = dur != null ? this.formatDuration(dur) : "—";
            return `<tr><td>Cell ${cellId}${label}</td><td>${timeStr}</td></tr>`;
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
  <thead><tr><th>Cell</th><th>Duration</th></tr></thead>
  <tbody>${durationRows}</tbody>
</table>
<div><strong>Total Time:</strong> ${totalDurationMs != null ? this.formatDuration(totalDurationMs) : "—"}</div>`;
        const leftLines = [
            `<strong>Date:</strong> ${new Date(exp.created_at).toLocaleString()}`,
            `<strong>Experiment name:</strong> ${s.experiment_name || "(unnamed)"}`,
            `<strong>Cells tested:</strong> ${exp.cells.join(", ") || "-"}`,
            `<strong>RPMs:</strong> ${exp.rpms.join(", ") || "-"}`,
            `<strong>Cell labels:</strong> ${cellLabelsSummary || "-"}`,
            `<strong>Z step:</strong> ${s.z_step_size ?? "-"} mm`,
            `<strong>Measurement duration:</strong> ${s.measurement_duration ?? "-"} s`,
            `<strong>Sample interval:</strong> ${s.sample_interval ?? "-"} s`,
            durationTable,
        ];
        const rightLines = [
            ...feedbackRows,
            `<strong>Smart early exit:</strong> ${
                s.smart_early_exit_enabled === true
                    ? "Yes"
                    : (s.smart_early_exit_enabled === false ? "No" : "-")
            }`,
            `<strong>Smart CV threshold:</strong> ${s.smart_cv_threshold ?? "-"}`,
            `<strong>Smart window size:</strong> ${s.smart_window_size ?? "-"}`,
        ];

        let predictedViscosityBlock;
        const predEnabled = Boolean(
            exp.predicted_viscosity_enabled ?? s.predicted_viscosity_enabled
        );
        if (!predEnabled) {
            predictedViscosityBlock = "<p><em>Predicted viscosity was not enabled for this run.</em></p>";
        } else {
            const predData = exp.predicted_viscosity || {};
            const rows = [];
            Object.keys(predData).forEach((cellKey) => {
                const cellId = Number(cellKey);
                const rpmMap = predData[cellKey];
                if (!rpmMap || typeof rpmMap !== "object") {
                    return;
                }
                Object.keys(rpmMap).forEach((rpmKey) => {
                    const result = rpmMap[rpmKey];
                    const label = s.cell_content_map?.[cellId] ?? s.cell_content_map?.[String(cellId)] ?? "";
                    const visc = result?.success && result?.viscosity_kcp != null
                        ? Number(result.viscosity_kcp).toFixed(3)
                        : "—";
                    rows.push(
                        `<tr><td>${cellId}</td><td>${label || "—"}</td><td>${rpmKey}</td><td>${visc}</td></tr>`
                    );
                });
            });
            if (rows.length === 0) {
                predictedViscosityBlock = "<p><em>No predicted viscosity results were recorded.</em></p>";
            } else {
                predictedViscosityBlock = `
<table class="duration-table predicted-viscosity-summary-table">
  <thead><tr><th>Cell No.</th><th>Cell Label</th><th>RPM</th><th>Predicted Viscosity (kCp)</th></tr></thead>
  <tbody>${rows.join("")}</tbody>
</table>`;
            }
        }

        const leftEl = this.el.summaryMetaLeft;
        const rightEl = this.el.summaryMetaRight;
        if (leftEl) {
            leftEl.innerHTML = leftLines.map((line) => line.startsWith("<table") ? line : `<div>${line}</div>`).join("");
        }
        if (rightEl) {
            rightEl.innerHTML = [
                ...rightLines.map((line) => `<div>${line}</div>`),
                "<div><strong>Predicted viscosity</strong></div>",
                predictedViscosityBlock,
            ].join("");
        }

        this.syncCustomHitpointControlsForExperiment(exp);

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
        const showHitLine = Boolean(this.el.summaryShowHitLine?.checked);
        const alignToHit = Boolean(this.el.summaryAlignHitpoint?.checked);
        const customHitpoints = this._getCustomHitpointsForExperiment(exp);
        const getCustomHitZForCell = (cellId) => this._getCustomHitZForCell(customHitpoints, cellId);

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
            const customHitZ = Number.isFinite(getCustomHitZForCell(cellId))
                ? getCustomHitZForCell(cellId)
                : null;

            let plotPoints;
            let alignReference;

            if (customHitZ != null) {
                // Drop points before (hit − 3 samples); keep 3 points before hit + rest through end.
                // With "align traces": keep only those 3 + hit, then shift so hit = 0 (same as auto logic).
                const hitIdx = this._closestMeasurementIndexByZ(timeOrdered, customHitZ);
                const startIdx = Math.max(0, hitIdx - 3);
                const hitZMeasured = Number(timeOrdered[hitIdx].height);
                plotPoints = alignToHit
                    ? timeOrdered.slice(startIdx, hitIdx + 1)
                    : timeOrdered.slice(startIdx);
                alignReference = Number.isFinite(hitZMeasured) ? hitZMeasured : customHitZ;
            } else {
                plotPoints = alignToHit
                    ? (trimmed.length > 0 ? trimmed : [...timeOrdered])
                    : [...timeOrdered];
                alignReference = plotPoints.length > 0 ? Number(plotPoints[plotPoints.length - 1].height) : null;
            }
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
            const referenceXs = [];
            Object.entries(byCellRpm).forEach(([key, pts]) => {
                const [cellIdStr] = key.split("|");
                const cellId = Number(cellIdStr);
                const customHitZ = getCustomHitZForCell(cellId);

                let reference = null;
                if (Number.isFinite(customHitZ)) {
                    const timeOrdered = [...pts].sort((a, b) => Number(a.timestamp) - Number(b.timestamp));
                    const hitIdx = this._closestMeasurementIndexByZ(timeOrdered, customHitZ);
                    reference = Number(timeOrdered[hitIdx]?.height);
                } else {
                    const timeOrdered = [...pts].sort((a, b) => Number(a.timestamp) - Number(b.timestamp));
                    const trimmed = timeOrdered.length > 3 ? timeOrdered.slice(0, -3) : [...timeOrdered];
                    const plotPoints = alignToHit
                        ? (trimmed.length > 0 ? trimmed : [...timeOrdered])
                        : [...timeOrdered];
                    reference = plotPoints.length > 0 ? Number(plotPoints[plotPoints.length - 1].height) : null;
                }

                if (Number.isFinite(reference)) {
                    referenceXs.push(alignToHit ? 0 : reference);
                }
            });
            const uniqueRefXs = [...new Set(referenceXs.map((v) => Number(v.toFixed(6))))];
            const shapes = showHitLine
                ? uniqueRefXs.map((xVal) => ({
                    type: "line",
                    x0: xVal,
                    x1: xVal,
                    y0: 0,
                    y1: 1,
                    yref: "paper",
                    line: { color: "#ff4d4f", width: 2, dash: "dash" },
                }))
                : [];
            const layout = {
                ...this.summaryPlotLayout,
                xaxis: {
                    ...this.summaryPlotLayout.xaxis,
                    title: alignToHit
                        ? "Height Relative to Alignment Reference (mm, reference = 0)"
                        : "Z-Height (mm) - descent ->",
                    tickformat: ".3f",
                },
                shapes,
            };
            Plotly.react(this.el.summaryPlot, traces, layout,
                { responsive: true, displayModeBar: false });
        }
    }

    _closestMeasurementIndexByZ(timeOrdered, targetZ) {
        if (!Array.isArray(timeOrdered) || timeOrdered.length === 0) {
            return 0;
        }
        const z = Number(targetZ);
        if (!Number.isFinite(z)) {
            return 0;
        }
        let bestIdx = 0;
        let bestDist = Math.abs(Number(timeOrdered[0].height) - z);
        for (let i = 1; i < timeOrdered.length; i += 1) {
            const d = Math.abs(Number(timeOrdered[i].height) - z);
            if (d < bestDist) {
                bestDist = d;
                bestIdx = i;
            }
        }
        return bestIdx;
    }

    _getCustomHitpointsForExperiment(exp) {
        const ch = exp?.custom_hitpoints;
        if (ch && typeof ch === "object") return ch;
        return {};
    }

    _getCustomHitZForCell(customHitpoints, cellId) {
        const key = String(cellId);
        const raw = customHitpoints?.[key];
        const num = typeof raw === "number"
            ? raw
            : (raw && typeof raw === "object" ? Number(raw.hit_z) : Number(raw));
        return Number.isFinite(num) ? num : null;
    }

    syncCustomHitpointControlsForExperiment(exp) {
        if (!this.el.summaryCustomHitpointCell) return;
        const cells = Array.isArray(exp?.cells) ? exp.cells : [];
        const select = this.el.summaryCustomHitpointCell;
        if (!select) return;

        select.innerHTML = "";
        cells.forEach((cellId) => {
            const opt = document.createElement("option");
            opt.value = String(cellId);
            opt.textContent = `Cell ${cellId}`;
            select.appendChild(opt);
        });

        const desired = cells.includes(this.customHitpointSelectedCellId)
            ? this.customHitpointSelectedCellId
            : (cells.length ? cells[0] : null);
        this.customHitpointSelectedCellId = desired;
        select.value = desired != null ? String(desired) : "";

        this.updateCustomHitpointControlsUI(exp, desired);
    }

    updateCustomHitpointControlsUI(exp = null, selectedCellId = null) {
        if (!this.el.summaryCustomHitpointZ || !this.el.summaryUndoCustomHitpoint || !this.el.summaryCustomHitpointStatus) {
            return;
        }

        if (!exp) {
            exp = this.experimentHistory.find((e) => e.id === this.selectedExperimentId);
        }
        if (!exp) return;

        const cells = Array.isArray(exp.cells) ? exp.cells : [];
        if (selectedCellId == null) {
            selectedCellId = this.customHitpointSelectedCellId;
        }
        if (selectedCellId == null || !cells.includes(selectedCellId)) {
            selectedCellId = cells.length ? cells[0] : null;
        }

        const customHitpoints = this._getCustomHitpointsForExperiment(exp);
        const hitZ = selectedCellId != null
            ? this._getCustomHitZForCell(customHitpoints, selectedCellId)
            : null;

        this.el.summaryCustomHitpointZ.value = Number.isFinite(hitZ) ? String(hitZ.toFixed(3)) : "";
        const hasOverride = Number.isFinite(hitZ);

        this.el.summaryUndoCustomHitpoint.disabled = !hasOverride;
        this.el.summaryCustomHitpointStatus.textContent = hasOverride
            ? `Custom hitpoint: Cell ${selectedCellId} @ ${hitZ.toFixed(3)} mm`
            : "Using auto hitpoint for this cell";
    }

    applyCustomHitpointOverrideFromUI() {
        if (!this.selectedExperimentId) return;
        const exp = this.experimentHistory.find((e) => e.id === this.selectedExperimentId);
        if (!exp) return;
        if (!this.el.summaryCustomHitpointCell || !this.el.summaryCustomHitpointZ) return;

        const cellId = Number(this.el.summaryCustomHitpointCell.value);
        const hitZ = Number(this.el.summaryCustomHitpointZ.value);
        if (!Number.isFinite(cellId) || !Number.isFinite(hitZ)) {
            this.pushStatusMessage("Enter a valid cell and Hitpoint Z value first");
            return;
        }

        const overrides = { ...this._getCustomHitpointsForExperiment(exp) };
        overrides[String(cellId)] = hitZ;
        const updatedExp = { ...exp, custom_hitpoints: overrides };

        const idx = this.experimentHistory.findIndex((e) => e.id === updatedExp.id);
        if (idx >= 0) this.experimentHistory[idx] = updatedExp;
        else this.experimentHistory.unshift(updatedExp);

        // Persist to server so other devices get the override.
        this.saveExperimentHistoryEntry(updatedExp).catch(() => {
            this.pushStatusMessage("Warning: failed to sync custom hitpoint to server");
        });

        this.customHitpointSelectedCellId = cellId;
        this.selectExperiment(updatedExp.id);
    }

    undoCustomHitpointOverrideFromUI() {
        if (!this.selectedExperimentId) return;
        const exp = this.experimentHistory.find((e) => e.id === this.selectedExperimentId);
        if (!exp) return;
        if (!this.el.summaryCustomHitpointCell) return;

        const cellId = Number(this.el.summaryCustomHitpointCell.value);
        if (!Number.isFinite(cellId)) return;

        const overrides = { ...this._getCustomHitpointsForExperiment(exp) };
        const key = String(cellId);
        if (!(key in overrides)) {
            return;
        }

        delete overrides[key];
        const updatedExp = { ...exp };
        if (Object.keys(overrides).length > 0) {
            updatedExp.custom_hitpoints = overrides;
        } else {
            delete updatedExp.custom_hitpoints;
        }

        const idx = this.experimentHistory.findIndex((e) => e.id === updatedExp.id);
        if (idx >= 0) this.experimentHistory[idx] = updatedExp;
        else this.experimentHistory.unshift(updatedExp);

        this.saveExperimentHistoryEntry(updatedExp).catch(() => {
            this.pushStatusMessage("Warning: failed to sync undo to server");
        });

        this.selectExperiment(updatedExp.id);
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
            this.el.elapsed.textContent = this.formatDuration(now - this.experimentStart);
        }

        if (this.cellStart !== null && this.isRunning) {
            this.el.elapsedCell.textContent = `Cell ${this.formatDuration(now - this.cellStart)}`;
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

        if (isAllDone && !this.isRunning) {
            this._showExperimentCompleteMessage();
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
    }

    _finalizePendingCompletedCell() {
        if (this._pendingCompletedCell !== null && this._pendingCompletedCell !== undefined) {
            this.completedCells.add(this._pendingCompletedCell);
            this.cellStates.set(this._pendingCompletedCell, "completed");
            this.washingCell = null;
            this._pendingCompletedCell = null;
            this.updateCompletionBar();
            this.renderMap();
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
        this.renderPredictedViscosityCharts();
        this.renderLiveViscosityPredictionsTable();
    }

    _fmtPredictedViscosity3(value) {
        const n = Number(value);
        return Number.isFinite(n) ? n.toFixed(3) : "—";
    }

    renderLiveViscosityPredictionsTable() {
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
                Object.keys(rpmMap)
                    .map((k) => Number(k))
                    .filter((r) => Number.isFinite(r))
                    .sort((a, b) => a - b)
                    .forEach((rpm) => {
                        const result = rpmMap[rpm];
                        const label = contentMap[cellId]
                            ?? contentMap[String(cellId)]
                            ?? "";
                        const visc = result?.success && result?.viscosity_kcp != null
                            ? this._fmtPredictedViscosity3(result.viscosity_kcp)
                            : "—";
                        rows.push(
                            `<tr><td>${cellId}</td><td>${label || "—"}</td><td class="mono">${visc}</td></tr>`
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

    renderPredictedViscosityCharts() {
        const enabled = Boolean(
            this.el.predictedViscosityEnabled?.checked
            ?? this.latestControlSettings?.predicted_viscosity_enabled
        );
        if (!enabled || !this.el.predictedViscosityCharts) {
            return;
        }

        const cellIds = Object.keys(this.predictedViscosityData)
            .map((k) => Number(k))
            .filter((id) => Number.isFinite(id))
            .sort((a, b) => a - b);

        const hasData = cellIds.some((cid) => {
            const rpmMap = this.predictedViscosityData[cid];
            return rpmMap && Object.keys(rpmMap).length > 0;
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
            if (!rpmMap || Object.keys(rpmMap).length === 0) {
                return;
            }

            let wrap = this.el.predictedViscosityCharts.querySelector(
                `[data-pv-cell-id="${cellId}"]`
            );
            if (!wrap) {
                wrap = document.createElement("div");
                wrap.className = "predicted-viscosity-plot-wrap";
                wrap.dataset.pvCellId = String(cellId);
                wrap.innerHTML = `
                    <div class="predicted-viscosity-plot-title" data-pv-title="${cellId}"></div>
                    <div class="predicted-viscosity-plot" data-pv-plot="${cellId}"></div>`;
                this.el.predictedViscosityCharts.appendChild(wrap);
            }

            const titleEl = wrap.querySelector(`[data-pv-title="${cellId}"]`);
            const plotEl = wrap.querySelector(`[data-pv-plot="${cellId}"]`);
            if (!plotEl) {
                return;
            }

            const rpms = Object.keys(rpmMap)
                .map((k) => Number(k))
                .filter((r) => Number.isFinite(r))
                .sort((a, b) => a - b);

            const traces = [];
            const subtitles = [];
            rpms.forEach((rpm, idx) => {
                const result = rpmMap[rpm];
                if (!result) {
                    return;
                }
                const color = this.palette[idx % this.palette.length];
                const preZ = result.pretrim_z || [];
                const preD = result.pretrim_drag || [];
                const trimZ = result.trimmed_z || [];
                const trimD = result.trimmed_drag || [];
                const fitZ = result.fit_curve_z || [];
                const fitD = result.fit_curve_drag || [];

                if (preZ.length > 0) {
                    traces.push({
                        x: preZ,
                        y: preD,
                        mode: "markers",
                        type: "scatter",
                        name: `RPM ${rpm} raw`,
                        legendgroup: `rpm${rpm}`,
                        marker: { size: 7, color, opacity: 0.45 },
                        showlegend: idx === 0,
                    });
                }
                if (trimZ.length > 0) {
                    traces.push({
                        x: trimZ,
                        y: trimD,
                        mode: "markers",
                        type: "scatter",
                        name: `RPM ${rpm} trimmed`,
                        legendgroup: `rpm${rpm}`,
                        marker: { size: 9, color, line: { width: 1, color: "#1a1a1a" } },
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
                subtitles.push(
                    `RPM ${rpm} | η = ${eta} kCp | a = ${this._fmtPredictedViscosity3(result.a)} | b = ${this._fmtPredictedViscosity3(result.b)} | n = ${result.n_points_used ?? 0}`
                );
            });

            if (titleEl) {
                titleEl.textContent = `Cell ${cellId} — ${subtitles.join(" · ")}`;
            }

            const layout = {
                margin: { t: 24, r: 16, b: 40, l: 52 },
                xaxis: { title: "Z (mm)" },
                yaxis: { title: "Rotational drag" },
                showlegend: true,
                legend: { orientation: "h", y: 1.12 },
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

        this.updateCellVisuals();
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

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
        this.summaryPlotInitialized = false;
        this.timingStorageKey = "viscometryTimingState";
        this.cellRpmMap = {};   // { cellId (number): [rpm, ...] }
        this.cellContentMap = {}; // { cellId (number): "sample label" }

        this.palette = [
            "#5EA1FF", "#F5A623", "#39C5BB", "#2EA043", "#E25A5A", "#9BB5FF",
            "#B6E388", "#FFC47E", "#8FDDE5", "#EA9CB9", "#B9A0FF", "#8FD66B",
            "#73B0F9", "#FFD36A", "#69D5C7", "#86E0A8", "#EFA17C", "#BFC7D5"
        ];

        this.initElements();
        this.bindUI();
        this.handleLogoFallback();
        this.initStaticLayout();
        this.initPlot();
        this.initGauge();
        this.initSummaryPlot();
        this.restoreTimingState();
        this.startTimerLoop();
        this.fetchInitialData();
        this.loadControlSettings();
        this.rebuildCellRpmTable();
        this.rebuildCellContentTable();
        this.loadExperimentHistory();

        // Restore active tab from localStorage
        const activeTab = localStorage.getItem("activeTab") || "layout-tab";
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
            secondDerivativeThreshold: document.getElementById("second-derivative-threshold"),
            cvJumpThreshold: document.getElementById("cv-jump-threshold"),
            trendRSquaredMin: document.getElementById("trend-r-squared-min"),
            hitPointConfidenceThreshold: document.getElementById("hit-point-confidence-threshold"),
            weightSecondDerivative: document.getElementById("weight-second-derivative"),
            weightPlateauCv: document.getElementById("weight-plateau-cv"),
            weightTrendBreakdown: document.getElementById("weight-trend-breakdown"),
            weightWrongDirection: document.getElementById("weight-wrong-direction"),
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
            sidebarSecondDeriv: document.getElementById("sidebar-2nd-deriv"),
            sidebarCv: document.getElementById("sidebar-cv"),
            sidebarR2: document.getElementById("sidebar-r2"),
            sidebarConfidence: document.getElementById("sidebar-confidence"),
            sidebarHit: document.getElementById("sidebar-hit"),
            elapsed: document.getElementById("elapsed"),
            elapsedCell: document.getElementById("elapsed-cell"),
            tableBody: document.getElementById("measurement-table"),
            zFilterAll: document.getElementById("z-filter-all"),
            zFilterLatest: document.getElementById("z-filter-latest"),
            zConnectDots: document.getElementById("z-connect-dots"),
            exportPlot: document.getElementById("plot-export"),
            exportTable: document.getElementById("table-export"),
            themeToggle: document.getElementById("theme-toggle"),
            cncStatus: document.getElementById("cnc-status"),
            viscometerStatus: document.getElementById("viscometer-status"),
            pumpStatus: document.getElementById("pump-status"),
            summaryCards: document.getElementById("experiment-cards"),
            summaryEmpty: document.getElementById("summary-empty"),
            summaryDetail: document.getElementById("summary-detail"),
            summaryMeta: document.getElementById("summary-meta"),
            summaryDownload: document.getElementById("summary-download"),
            summaryPlot: document.getElementById("summary-plot"),
            tabButtons: document.querySelectorAll(".tab-button"),
            tabPanels: document.querySelectorAll(".tab-panel")
        };
    }

    bindUI() {
        this.el.exportPlot.addEventListener("click", () => this.exportCSV());
        this.el.exportTable.addEventListener("click", () => this.exportCSV());
        this.el.applySettings.addEventListener("click", () => this.applyControlSettings());
        this.el.startRun.addEventListener("click", () => this.startRunFromUI());
        this.el.stopRun.addEventListener("click", () => this.stopRunFromUI());
        this.el.themeToggle.addEventListener("click", () => this.toggleTheme());
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
                this.refreshLivePlots();
            });
        }
        if (this.el.summaryDownload) {
            this.el.summaryDownload.addEventListener("click", () => this.downloadSelectedCSV());
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
                title: "Z-Height (mm) - descent ->",
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
            legend: { bgcolor: "transparent", bordercolor: "#30363D" }
        };

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
            fetch("/api/measurement_data").then((r) => r.json())
        ])
            .then(([status, measurementData]) => {
                this.applyStatusSnapshot(status);
                if (Array.isArray(measurementData)) {
                    measurementData.forEach((m) => this.ingestMeasurement(m, true));
                    this.refreshLivePlots();
                }
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
        this.el.sampleInterval.value = settings.sample_interval ?? 10;
        this.el.dwellSeconds.value = settings.dwell_seconds ?? 2;
        this.el.interRpmPause.value = settings.inter_rpm_pause ?? 2;
        this.el.torqueBreakThreshold.value = settings.torque_break_threshold ?? 100;
        this.el.feedbackEnabled.checked = Boolean(settings.feedback_control_enabled);
        if (this.el.secondDerivativeThreshold) this.el.secondDerivativeThreshold.value = settings.second_derivative_threshold ?? -2.0;
        if (this.el.cvJumpThreshold) this.el.cvJumpThreshold.value = settings.cv_jump_threshold ?? 0.4;
        if (this.el.trendRSquaredMin) this.el.trendRSquaredMin.value = settings.trend_r_squared_min ?? 0.5;
        if (this.el.hitPointConfidenceThreshold) this.el.hitPointConfidenceThreshold.value = settings.hit_point_confidence_threshold ?? 0.8;
        if (this.el.weightSecondDerivative) this.el.weightSecondDerivative.value = settings.weight_second_derivative ?? 0.5;
        if (this.el.weightPlateauCv) this.el.weightPlateauCv.value = settings.weight_plateau_cv ?? 0.4;
        if (this.el.weightTrendBreakdown) this.el.weightTrendBreakdown.value = settings.weight_trend_breakdown ?? 0.3;
        if (this.el.weightWrongDirection) this.el.weightWrongDirection.value = settings.weight_wrong_direction ?? 0.2;

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

        this.setControlStatus("Settings loaded");
        this.updateCompletionBar();
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
            second_derivative_threshold: Number(this.el.secondDerivativeThreshold?.value ?? -2.0),
            cv_jump_threshold: Number(this.el.cvJumpThreshold?.value ?? 0.4),
            trend_r_squared_min: Number(this.el.trendRSquaredMin?.value ?? 0.5),
            hit_point_confidence_threshold: Number(this.el.hitPointConfidenceThreshold?.value ?? 0.8),
            weight_second_derivative: Number(this.el.weightSecondDerivative?.value ?? 0.5),
            weight_plateau_cv: Number(this.el.weightPlateauCv?.value ?? 0.4),
            weight_trend_breakdown: Number(this.el.weightTrendBreakdown?.value ?? 0.3),
            weight_wrong_direction: Number(this.el.weightWrongDirection?.value ?? 0.2),
            feedback_control_enabled: this.el.feedbackEnabled.checked,
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
            this.addPointToChart(data.cell_id, data.height, data.rotational_drag, data.rpm, data.timestamp);
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
            if (data.is_running && !this.isRunning) {
                this.runMeasurementStartIndex = this.measurements.length;
            }
            if (!data.is_running && this.isRunning) {
                this.saveCompletedExperiment();
            }
            this.setRunningState(Boolean(data.is_running));
        });

        this.socket.on("instrument_status_update", (status) => {
            if (!status) {
                return;
            }
            this.setInstrumentStatus("cnc", Boolean(status.cnc));
            this.setInstrumentStatus("viscometer", Boolean(status.viscometer));
            this.setInstrumentStatus("pump", Boolean(status.pump));
        });

        this.socket.on("feedback_metrics_update", (data) => {
            if (data) {
                this.updateDragZSidebar(data);
            }
        });

        this.socket.on("clear_dashboard", () => {
            this.clearDashboard();
        });

    }

    clearDashboard() {
        this.measurements = [];
        this.measurementsByCell.clear();
        this.latestTorqueByCell.clear();
        this.hitPoints.clear();
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
        this.runMeasurementStartIndex = 0;
        this.currentPhase = 0;

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
        if (this.el.sidebarSecondDeriv) this.el.sidebarSecondDeriv.textContent = "-";
        if (this.el.sidebarCv) this.el.sidebarCv.textContent = "-";
        if (this.el.sidebarR2) this.el.sidebarR2.textContent = "-";
        if (this.el.sidebarConfidence) this.el.sidebarConfidence.textContent = "-";
        if (this.el.sidebarHit) {
            this.el.sidebarHit.textContent = "No";
            this.el.sidebarHit.className = "sidebar-value mono hit-no";
        }

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

        if (Array.isArray(status.measurement_data) && status.measurement_data.length > 0) {
            status.measurement_data.forEach((m) => this.ingestMeasurement(m, true));
            this.refreshLivePlots();
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
            // Don't mark completed immediately — washing may still be in progress.
            // The cell will be marked completed when washing finalizes or on safe fallback.
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
            if (this.isRunning) {
                this.saveTimingState();
            }
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
        let activeStation = null;
        if (statusLower.includes("wash station 1") || statusLower.includes("motor 1") || statusLower.includes("pump 1")) {
            activeStation = "WASH";
        } else if (statusLower.includes("wash station 2") || statusLower.includes("motor 2") || statusLower.includes("pump 2")) {
            activeStation = "DRY";
        }

        this.platform.cells.forEach((cell) => {
            let state;

            if (this.washingCell === cell.id) {
                // Cell is actively being washed — show washing regardless of completed state.
                state = "washing";
            } else if (this.completedCells.has(cell.id)) {
                state = "completed";
            } else if (this.currentCell === cell.id) {
                if (
                    this.currentRPM > 0 ||
                    statusLower.includes("descending") ||
                    statusLower.includes("measuring") ||
                    statusLower.includes("z-step")
                ) {
                    state = "measuring";
                } else if (statusLower.includes("error") || statusLower.includes("fail")) {
                    state = "error";
                } else {
                    state = "active";
                }
            } else {
                state = this.cellStates.get(cell.id) || "pending";
            }

            this.cellStates.set(cell.id, state);
        });

        this.renderMap();

        ["WASH", "DRY"].forEach((id) => {
            const node = document.getElementById(`station-${id}`);
            if (!node) {
                return;
            }
            node.classList.toggle("active", activeStation === id);
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

    ingestMeasurement(rawMeasurement, bootstrap) {
        const measurement = {
            timestamp: Number(rawMeasurement.timestamp) || Date.now() / 1000,
            height: Number(rawMeasurement.height) || 0,
            rotational_drag: Number(rawMeasurement.rotational_drag) || 0,
            torque_percent: Number.isFinite(Number(rawMeasurement.torque_percent))
                ? Number(rawMeasurement.torque_percent)
                : (Number(rawMeasurement.rotational_drag) || 0) * (Number(rawMeasurement.rpm) || 0),
            rpm: Number(rawMeasurement.rpm) || 0,
            cell_id: Number(rawMeasurement.cell_id) || 0
        };

        if (!measurement.cell_id) {
            return;
        }

        this.measurements.push(measurement);
        if (this.measurements.length > 4000) {
            this.measurements = this.measurements.slice(-4000);
        }

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

        this.updateGraphCellTabs();
        this.refreshLivePlots();
        this.updateTable();
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

    refreshLivePlots() {
        const activeCell = this.getActiveGraphCellId();
        const source = activeCell ? (this.measurementsByCell.get(activeCell) || []) : [];

        let zData = source;
        if (this.zLatestOnly && source.length > 0) {
            const latestByHeight = new Map();
            source.forEach((m) => {
                const key = Number(m.height).toFixed(3);
                const prev = latestByHeight.get(key);
                if (!prev || (Number(m.timestamp) || 0) >= (Number(prev.timestamp) || 0)) {
                    latestByHeight.set(key, m);
                }
            });
            zData = [...latestByHeight.values()];
        }
        zData = [...zData].sort((a, b) => a.height - b.height);

        if (this.zPlotInitialized && this.el.zSparklinePlot) {
            const zTrace = zData.length ? [{
                x: zData.map((m) => m.height),
                y: zData.map((m) => m.rotational_drag),
                mode: this.zConnectDots ? "lines+markers" : "markers",
                type: "scatter",
                name: activeCell ? `Cell ${activeCell}` : "No Cell",
                marker: { size: 8, color: "#39C5BB", line: { color: "#8ff5ee", width: 1 } },
                line: { color: "#39C5BB", width: 2 },
                hovertemplate: "Z %{x:.3f} mm<br>Drag %{y:.4f}<extra></extra>"
            }] : [];

            Plotly.react(this.el.zSparklinePlot, zTrace, undefined, { responsive: true, displayModeBar: false });
            if (this.el.zSparklineEmpty) {
                this.el.zSparklineEmpty.classList.toggle("hidden", zTrace.length > 0);
            }
        }

        const torqueData = [...source].sort((a, b) => a.height - b.height);
        if (this.torquePlotInitialized && this.el.torqueZPlot) {
            const torqueTrace = torqueData.length ? [{
                x: torqueData.map((m) => m.height),
                y: torqueData.map((m) => m.torque_percent),
                mode: "markers",
                type: "scatter",
                name: activeCell ? `Cell ${activeCell}` : "No Cell",
                marker: { size: 8, color: "#F5A623", line: { color: "#ffd37a", width: 1 } },
                hovertemplate: "Z %{x:.3f} mm<br>Torque %{y:.3f}%<extra></extra>"
            }] : [];

            Plotly.react(this.el.torqueZPlot, torqueTrace, undefined, { responsive: true, displayModeBar: false });
            if (this.el.torqueZEmpty) {
                this.el.torqueZEmpty.classList.toggle("hidden", torqueTrace.length > 0);
            }
        }
    }

    updateGauge(targetRPM) {
        const clamped = Math.max(0, Math.min(200, targetRPM));
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
        if (this.el.sidebarSecondDeriv) this.el.sidebarSecondDeriv.textContent = fmt(data.second_derivative);
        if (this.el.sidebarCv) this.el.sidebarCv.textContent = fmt(data.plateau_score);
        if (this.el.sidebarR2) this.el.sidebarR2.textContent = fmt(data.trend_r_squared);
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

    addPointToChart(cellId, height, rotationalDrag, rpm, timestamp) {
        this.ingestMeasurement({
            cell_id: cellId,
            height,
            rotational_drag: rotationalDrag,
            rpm,
            timestamp
        }, false);
    }

    setRunningState(isRunning) {
        const previous = this.isRunning;
        this.isRunning = isRunning;

        this.el.runPill.textContent = isRunning ? "RUNNING" : "IDLE";
        this.el.runPill.classList.toggle("running", isRunning);
        this.el.runPill.classList.toggle("idle", !isRunning);
        this.el.body.classList.toggle("running", isRunning);

        if (isRunning && !this.experimentStart) {
            this.experimentStart = Date.now();
            this.cellStart = Date.now();
            this.completedCells.clear();
            this.washingCell = null;
            this._pendingCompletedCell = null;
            this.currentPhase = 0;
            this.updateTimeline();
            this.updateCompletionBar();
            this._hideExperimentCompleteMessage();
            this.saveTimingState();
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
            this.experimentStart = null;
            this.cellStart = null;
            this.clearTimingState();
            this.updateCompletionBar();
            if (this.uiState === "running") {
                this.setUiState("idle");
            }
        }
    }

    saveTimingState() {
        const payload = {
            experimentStart: this.experimentStart,
            cellStart: this.cellStart,
            currentCell: this.currentCell,
            isRunning: this.isRunning
        };
        localStorage.setItem(this.timingStorageKey, JSON.stringify(payload));
    }

    restoreTimingState() {
        try {
            const raw = localStorage.getItem(this.timingStorageKey);
            if (!raw) {
                return;
            }
            const parsed = JSON.parse(raw);
            this.experimentStart = Number(parsed.experimentStart) || null;
            this.cellStart = Number(parsed.cellStart) || null;
        } catch (_error) {
            this.experimentStart = null;
            this.cellStart = null;
        }
    }

    clearTimingState() {
        localStorage.removeItem(this.timingStorageKey);
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
        try {
            const raw = localStorage.getItem("viscometryExperimentHistory");
            this.experimentHistory = raw ? JSON.parse(raw) : [];
        } catch (_error) {
            this.experimentHistory = [];
        }
        this.renderExperimentCards();
    }

    saveExperimentHistory() {
        localStorage.setItem("viscometryExperimentHistory", JSON.stringify(this.experimentHistory));
    }

    saveCompletedExperiment() {
        const runData = this.measurements.slice(this.runMeasurementStartIndex);
        if (runData.length === 0) {
            return;
        }

        const latestByKey = new Map();
        runData.forEach((m) => {
            const k = `${m.cell_id}|${Number(m.height).toFixed(3)}|${m.rpm}`;
            latestByKey.set(k, m);
        });

        const cells = [...new Set(runData.map((m) => m.cell_id))].sort((a, b) => a - b);
        const rpms = [...new Set(runData.map((m) => Number(m.rpm.toFixed(3))))].sort((a, b) => a - b);

        const csvHeader = "timestamp,cell_id,height_mm,torque_percent,rotational_drag,rpm\n";
        const csvBody = runData.map((m) => {
            const iso = new Date(m.timestamp * 1000).toISOString();
            return `${iso},${m.cell_id},${m.height},${m.torque_percent},${m.rotational_drag},${m.rpm}`;
        }).join("\n");

        const exp = {
            id: `exp-${Date.now()}`,
            created_at: Date.now(),
            measurement_count: runData.length,
            cells,
            rpms,
            settings: this.readControlSettings ? this.readControlSettings() : {},
            latestPerZ: [...latestByKey.values()],
            csv: csvHeader + csvBody
        };

        this.experimentHistory.unshift(exp);
        this.experimentHistory = this.experimentHistory.slice(0, 40);
        this.saveExperimentHistory();
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
                <span>${exp.measurement_count} pts</span>
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
            `<strong>2nd Derivative threshold:</strong> ${s.second_derivative_threshold ?? "-"}`,
            `<strong>CV Jump threshold:</strong> ${s.cv_jump_threshold ?? "-"}`,
            `<strong>Min R²:</strong> ${s.trend_r_squared_min ?? "-"}`,
            `<strong>Hit Confidence threshold:</strong> ${s.hit_point_confidence_threshold ?? "-"}`,
            `<strong>w (2nd Derivative):</strong> ${s.weight_second_derivative ?? "-"}`,
            `<strong>w (Plateau/CV):</strong> ${s.weight_plateau_cv ?? "-"}`,
            `<strong>w (Trend Breakdown):</strong> ${s.weight_trend_breakdown ?? "-"}`,
            `<strong>w (Wrong Direction):</strong> ${s.weight_wrong_direction ?? "-"}`,
        ] : ["<strong>Feedback enabled:</strong> No"];

        this.el.summaryMeta.innerHTML = [
            `<strong>Date:</strong> ${new Date(exp.created_at).toLocaleString()}`,
            `<strong>Experiment name:</strong> ${s.experiment_name || "(unnamed)"}`,
            `<strong>Cells tested:</strong> ${exp.cells.join(", ") || "-"}`,
            `<strong>RPMs:</strong> ${exp.rpms.join(", ") || "-"}`,
            `<strong>Cell labels:</strong> ${cellLabelsSummary || "-"}`,
            `<strong>Z step:</strong> ${s.z_step_size ?? "-"} mm`,
            `<strong>Measurement duration:</strong> ${s.measurement_duration ?? "-"} s`,
            `<strong>Sample interval:</strong> ${s.sample_interval ?? "-"} s`,
            `<strong>Points collected:</strong> ${exp.measurement_count}`,
            `<hr class="meta-divider">`,
            ...feedbackRows,
        ].map((line) => line.startsWith("<hr") ? line : `<div>${line}</div>`).join("");

        const byRpm = {};
        (exp.latestPerZ || []).forEach((p) => {
            const k = String(Number(p.rpm).toFixed(3));
            if (!byRpm[k]) {
                byRpm[k] = [];
            }
            byRpm[k].push(p);
        });

        const traces = Object.entries(byRpm).map(([rpm, pts]) => {
            pts.sort((a, b) => a.height - b.height);
            return {
                x: pts.map((p) => p.height),
                y: pts.map((p) => p.rotational_drag),
                mode: "lines+markers",
                type: "scatter",
                name: `${rpm} RPM`,
                marker: { size: 7 },
                line: { width: 2 }
            };
        });

        if (this.summaryPlotInitialized && this.el.summaryPlot) {
            Plotly.react(this.el.summaryPlot, traces, this.summaryPlotLayout,
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
        this.saveExperimentHistory();
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

        if (this.experimentStart && this.isRunning) {
            this.el.elapsed.textContent = this.formatDuration(now - this.experimentStart);
        }

        if (this.cellStart && this.isRunning) {
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
        const total = this.plannedCells.length || 18;
        const done = this.completedCells.size;
        const ratio = total > 0 ? done / total : 0;

        if (this.el.completionBar) {
            this.el.completionBar.style.width = `${(ratio * 100).toFixed(1)}%`;
        }
        if (this.el.completionText) {
            this.el.completionText.textContent = `${done} / ${total} cells complete`;
        }
        if (this.el.completionChip) {
            this.el.completionChip.textContent = `${done} / ${total} cells completed`;
        }

        if (done >= total && total > 0 && !this.isRunning) {
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

    updateTable() {
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

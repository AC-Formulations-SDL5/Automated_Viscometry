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
        this.currentRotationalDrag = 0;
        this.currentMeasuringZ = null;
        this.position = { x: 0, y: 0, z: 0 };
        this.statusLog = [];
        this.measurements = [];
        this.measurementsByCell = new Map();
        this.latestTorqueByCell = new Map();
        this.completedCells = new Set();
        this.cellStates = new Map();
        this.hitPoints = new Map();
        this.plotMode = "all";
        this.currentPhase = 0;
        this.gaugeDisplayRPM = 0;
        this.gaugeAnimationFrame = null;
        this.plotInitialized = false;
        this.dragZPlotInitialized = false;
        this.timerInterval = null;
        this.experimentStart = null;
        this.cellStart = null;
        this.serverClockOffset = 0;
        this.runStartTime = null;
        this.trendlineVisible = false;
        this.latestZVisible = false;
        this.latestZLineVisible = false;
        this.latestPerZ = new Map();
        this.settingsApplied = false;
        this.runMeasurementStartIndex = 0;
        this.experimentHistory = [];
        this.selectedExperimentId = null;
        this.pendingRender = false;
        this.disconnectedBannerTimeout = null;
        this.statusError = false;
        this.sparklineData = [];

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
        this.initDragZChart();
        this.initGauge();
        this.updateDragZSubtitle();
        this.initSummaryPlot();
        this.loadExperimentHistory();
        this.updateControlButtons();
        this.startTimerLoop();
        this.fetchInitialData();
        this.loadControlSettings();

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
            cncStatus: document.getElementById("cnc-status"),
            viscometerStatus: document.getElementById("viscometer-status"),
            pumpStatus: document.getElementById("pump-status"),
            completionBar: document.getElementById("completion-bar"),
            completionText: document.getElementById("completion-text"),
            map: document.getElementById("platform-map"),
            cellLayer: document.getElementById("cell-layer"),
            washLayer: document.getElementById("wash-layer"),
            armDot: document.getElementById("arm-dot"),
            timeline: document.getElementById("timeline"),
            timelineFill: document.getElementById("timeline-fill"),
            statusLog: document.getElementById("status-log"),
            plot: document.getElementById("scatter-plot"),
            plotEmpty: document.getElementById("plot-empty"),
            trendlineToggle: document.getElementById("btn-trendline"),
            latestZToggle: document.getElementById("btn-latest-z"),
            latestZLineToggle: document.getElementById("btn-latest-z-line"),
            dragZChart: document.getElementById("drag-z-chart"),
            dragZCellLabel: document.getElementById("drag-z-cell-label"),
            testingMode: document.getElementById("testing-mode"),
            testRpms: document.getElementById("test-rpms"),
            selectedRows: document.getElementById("selected-rows"),
            selectedCells: document.getElementById("selected-cells"),
            zStepSize: document.getElementById("z-step-size"),
            measurementDuration: document.getElementById("measurement-duration"),
            sampleInterval: document.getElementById("sample-interval"),
            dwellSeconds: document.getElementById("dwell-seconds"),
            interRpmPause: document.getElementById("inter-rpm-pause"),
            torqueBreakThreshold: document.getElementById("torque-break-threshold"),
            feedbackEnabled: document.getElementById("feedback-control-enabled"),
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
            elapsed: document.getElementById("elapsed"),
            elapsedCell: document.getElementById("elapsed-cell"),
            sparklineLine: document.getElementById("sparkline-line"),
            tableBody: document.getElementById("measurement-table"),
            toggleAll: document.getElementById("toggle-all"),
            toggleCurrent: document.getElementById("toggle-current"),
            exportPlot: document.getElementById("plot-export"),
            exportTable: document.getElementById("table-export"),
            themeToggle: document.getElementById("theme-toggle"),
            tabButtons: document.querySelectorAll(".tab-button"),
            tabPanels: document.querySelectorAll(".tab-panel"),
            summaryCards: document.getElementById("experiment-cards"),
            summaryEmpty: document.getElementById("summary-empty"),
            summaryDetail: document.getElementById("summary-detail"),
            summaryMeta: document.getElementById("summary-meta"),
            summaryDownload: document.getElementById("summary-download"),
            summaryPlot: document.getElementById("summary-plot")
        };
    }

    bindUI() {
        this.el.toggleAll.addEventListener("click", () => this.setPlotMode("all"));
        this.el.toggleCurrent.addEventListener("click", () => this.setPlotMode("current"));
        this.el.exportPlot.addEventListener("click", () => this.exportCSV());
        this.el.exportTable.addEventListener("click", () => this.exportCSV());
        this.el.applySettings.addEventListener("click", () => this.applyControlSettings());
        this.el.startRun.addEventListener("click", () => this.startRunFromUI());
        this.el.stopRun.addEventListener("click", () => this.stopRunFromUI());
        this.el.themeToggle.addEventListener("click", () => this.toggleTheme());
        this.el.trendlineToggle.addEventListener("click", () => this.toggleTrendline());
        this.el.latestZToggle.addEventListener("click", () => this.toggleLatestZ());
        this.el.latestZLineToggle.addEventListener("click", () => this.toggleLatestZLine());
        this.el.summaryDownload.addEventListener("click", () => this.downloadSelectedSummaryCSV());

        const settingsForm = document.getElementById("run-settings-form");
        if (settingsForm) {
            settingsForm.addEventListener("input", () => {
                if (this.settingsApplied && !this.isRunning) {
                    this.settingsApplied = false;
                    this.updateControlButtons();
                }
            });
        }

        document.addEventListener("keydown", (event) => {
            if (event.key.toLowerCase() === "e") {
                this.exportCSV();
            }
        });

        window.addEventListener("resize", () => this.renderMap());

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
            this.gridToMachinePoint(7, 1, "WASH", "Washing Station"),
            this.gridToMachinePoint(7, 2, "DRY", "Drying Station")
        ];

        this.platform.cells.forEach((cell) => {
            this.cellStates.set(cell.id, "pending");
        });

        this.renderMap();
        this.updateCompletionBar();
    }

    buildCells() {
        const cells = [];

        let cellId = 1;
        for (let row = 1; row <= 6; row += 1) {
            cells.push(this.gridToMachinePoint(2, row, cellId, `Cell ${cellId}`));
            cellId += 1;
        }
        for (let row = 1; row <= 6; row += 1) {
            cells.push(this.gridToMachinePoint(3, row, cellId, `Cell ${cellId}`));
            cellId += 1;
        }
        for (let row = 1; row <= 6; row += 1) {
            cells.push(this.gridToMachinePoint(6, row, cellId, `Cell ${cellId}`));
            cellId += 1;
        }

        return cells;
    }

    gridToMachinePoint(col, row, id, label) {
        const x = ((col - 0.5) / 8) * this.platform.width;
        const y = ((row - 0.5) / 7) * this.platform.height;
        return { id, label, col, row, x, y };
    }

    mmToPct(x, y) {
        return {
            x: (x / this.platform.width) * 100,
            y: (y / this.platform.height) * 100
        };
    }

    renderMap() {
        this.el.cellLayer.innerHTML = "";
        this.el.washLayer.innerHTML = "";

        this.platform.cells.forEach((cell) => {
            const pct = this.mmToPct(cell.x, cell.y);
            const node = document.createElement("div");
            const state = this.cellStates.get(cell.id) || "pending";
            const torque = this.latestTorqueByCell.has(cell.id)
                ? `, last torque ${this.latestTorqueByCell.get(cell.id).toFixed(2)}%`
                : "";

            node.className = `map-node cell-node ${state}`;
            node.dataset.cellId = String(cell.id);
            node.dataset.tip = `${cell.label}, Row ${cell.row}, Column ${cell.col}${torque}`;
            node.style.left = `${pct.x}%`;
            node.style.top = `${pct.y}%`;
            node.textContent = cell.label;
            this.el.cellLayer.appendChild(node);
        });

        this.platform.washStations.forEach((station) => {
            const pct = this.mmToPct(station.x, station.y);
            const node = document.createElement("div");
            node.className = "map-node wash-node";
            node.dataset.station = station.id;
            node.dataset.tip = `${station.label}, column ${station.col}, row ${station.row}`;
            node.style.left = `${pct.x}%`;
            node.style.top = `${pct.y}%`;
            node.textContent = station.id;
            this.el.washLayer.appendChild(node);
        });

        this.applyArmPosition();
    }

    applyArmPosition() {
        const pct = this.mmToPct(this.position.x, this.position.y);
        this.el.armDot.style.left = `${pct.x}%`;
        this.el.armDot.style.top = `${pct.y}%`;
    }

    initPlot() {
        this.plotLayout = {
            paper_bgcolor: "transparent",
            plot_bgcolor: "rgba(255,255,255,0.03)",
            font: { family: "DM Mono", color: "#C9D1D9", size: 12 },
            xaxis: {
                title: "Height (mm)",
                gridcolor: "#21262D",
                zeroline: false
            },
            yaxis: {
                title: "Rotational Drag (%)",
                gridcolor: "#21262D",
                zeroline: false
            },
            margin: { t: 16, r: 16, b: 45, l: 58 },
            legend: { bgcolor: "transparent", bordercolor: "#30363D" },
            shapes: []
        };

        this.plotConfig = {
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

        Plotly.newPlot(this.el.plot, [], this.plotLayout, this.plotConfig).then(() => {
            this.plotInitialized = true;
            this.updatePlotEmptyState();
        });
    }

    initDragZChart() {
        this.dragZLayout = {
            xaxis: {
                title: "Z-Height (mm)",
                autorange: "reversed",
                tickformat: ".3f"
            },
            yaxis: {
                title: "Rotational Drag (Nm per RPM)",
                rangemode: "tozero"
            },
            legend: { orientation: "h", y: -0.2 },
            margin: { t: 20, r: 20, b: 80, l: 70 },
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            font: { color: "#cdd6f4" }
        };

        this.dragZConfig = {
            responsive: true,
            displayModeBar: false
        };

        Plotly.newPlot(this.el.dragZChart, [], this.dragZLayout, this.dragZConfig).then(() => {
            this.dragZPlotInitialized = true;
        });
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
        fetch("/api/status")
            .then((r) => r.json())
            .then((status) => {
                this.applyStatusSnapshot(status);
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
        this.settingsApplied = false;
        this.updateControlButtons();
        this.setControlStatus("Settings loaded");
    }

    readControlSettings() {
        const parseList = (value) => value.split(",").map((item) => item.trim()).filter(Boolean);

        return {
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
            feedback_control_enabled: this.el.feedbackEnabled.checked
        };
    }

    setControlStatus(message) {
        this.el.controlStatus.textContent = message;
    }

    updateControlButtons() {
        const applyActive = !this.settingsApplied;
        const startActive = this.settingsApplied && !this.isRunning;
        const stopActive = this.isRunning;

        this.el.applySettings.classList.toggle("is-active", applyActive);
        this.el.applySettings.classList.toggle("is-idle", !applyActive);
        this.el.startRun.classList.toggle("is-active", startActive);
        this.el.startRun.classList.toggle("is-idle", !startActive);
        this.el.stopRun.classList.toggle("is-active", stopActive);
        this.el.stopRun.classList.toggle("is-idle", !stopActive);

        this.el.startRun.disabled = !startActive;
        this.el.stopRun.disabled = !stopActive;
    }

    setInstrumentStatus(name, connected) {
        const lookup = {
            cnc: this.el.cncStatus,
            viscometer: this.el.viscometerStatus,
            pump: this.el.pumpStatus
        };
        const node = lookup[name];
        if (!node) {
            return;
        }
        node.classList.toggle("connected", connected);
        node.classList.toggle("disconnected", !connected);
        node.textContent = `${name.charAt(0).toUpperCase() + name.slice(1)}: ${connected ? "connected" : "disconnected"}`;
    }

    setAllInstrumentStatus(connected) {
        this.setInstrumentStatus("cnc", connected);
        this.setInstrumentStatus("viscometer", connected);
        this.setInstrumentStatus("pump", connected);
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
                this.settingsApplied = true;
                this.updateControlButtons();
                if (!silent) {
                    this.setControlStatus("Settings applied");
                }
                return saved;
            })
            .catch((error) => {
                this.settingsApplied = false;
                this.updateControlButtons();
                this.setControlStatus("Failed to apply settings");
                throw error;
            });
    }

    startRunFromUI() {
        this.applyControlSettings(true)
            .then((settings) => fetch("/api/run/start", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(settings)
            }))
            .then((response) => response.json())
            .then((result) => {
                this.setControlStatus(result.status_message || "Run started");
                this.updateControlButtons();
            })
            .catch(() => {
                this.setControlStatus("Failed to start run");
            });
    }

    stopRunFromUI() {
        fetch("/api/run/stop", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({})
        })
            .then((response) => response.json())
            .then((result) => {
                this.setControlStatus(result.status_message || "Stop requested");
                this.updateControlButtons();
            })
            .catch(() => {
                this.setControlStatus("Failed to stop run");
            });
    }

    connectSocket() {
        this.socket = io({ transports: ["websocket"], reconnectionAttempts: 5 });

        this.socket.on("connect", () => {
            this.isConnected = true;
            this.el.connectionDot.classList.remove("disconnected");
            this.el.connectionDot.classList.add("connected");
            this.setAllInstrumentStatus(true);
            this.showDisconnectedBanner(false);
            this.pushStatusMessage("Socket connection established");
            this.socket.emit("request_full_history");
        });

        this.socket.on("disconnect", () => {
            this.isConnected = false;
            this.el.connectionDot.classList.remove("connected");
            this.el.connectionDot.classList.add("disconnected");
            this.setAllInstrumentStatus(false);
            this.showDisconnectedBanner(true);
        });

        this.socket.on("status_update", (data) => {
            if (data && typeof data === "object") {
                this.applyTimeSync(data.server_time, data.run_start_time);
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

        this.socket.on("instrument_status_update", (status) => {
            if (!status || typeof status !== "object") {
                return;
            }
            this.setInstrumentStatus("cnc", Boolean(status.cnc));
            this.setInstrumentStatus("viscometer", Boolean(status.viscometer));
            this.setInstrumentStatus("pump", Boolean(status.pump));
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
            this.addPointToChart(data.cell_id, data.height, data.rotational_drag, data.rpm, data.timestamp, data.torque_percent);
        });

        this.socket.on("full_history", (data) => {
            this.applyTimeSync(data.server_time, data.run_start_time);
            this.bulkLoadScatterPoints(Array.isArray(data.measurement_data) ? data.measurement_data : []);
            this.bulkLoadLatestPerZ(Array.isArray(data.latest_per_z) ? data.latest_per_z : []);
        });

        this.socket.on("latest_per_z_update", (data) => {
            const key = this.latestPerZKey(data.cell_id, data.height, data.rpm);
            this.latestPerZ.set(key, {
                timestamp: Number(data.timestamp) || Date.now() / 1000,
                height: Number(data.height) || 0,
                rotational_drag: Number(data.rotational_drag) || 0,
                torque_percent: Number(data.torque_percent),
                rpm: Number(data.rpm) || 0,
                cell_id: Number(data.cell_id) || 0
            });
            if (this.latestZVisible) {
                this.renderLatestZTrace();
            }
            this.updateDragZChart();
        });

        this.socket.on("torque_update", (data) => {
            const torquePercent = Number(data.torque_percent);
            const rpm = Number(data.rpm) || 0;
            const rotationalDrag = Number(data.rotational_drag);
            if (!Number.isNaN(torquePercent)) {
                this.updateLiveTorqueDisplay(torquePercent);
                this.updateTorqueBar(torquePercent);
                if (!Number.isNaN(rotationalDrag)) {
                    this.updateLiveRotationalDragDisplay(rotationalDrag);
                } else if (rpm > 0) {
                    this.updateLiveRotationalDragDisplay(Math.abs(torquePercent) / rpm);
                }
            }
        });

        this.socket.on("z_update", (data) => {
            const currentZ = Number(data.current_z);
            if (!Number.isNaN(currentZ)) {
                this.updateMeasuringZDisplay(currentZ);
            }
        });

        this.socket.on("running_state_update", (data) => {
            this.applyTimeSync(data.server_time, data.run_start_time);
            this.setRunningState(Boolean(data.is_running), data.run_start_time ?? null);
        });
    }

    applyStatusSnapshot(status) {
        this.applyTimeSync(status.server_time, status.run_start_time);

        if (status.position) {
            this.position = {
                x: Number(status.position.x) || 0,
                y: Number(status.position.y) || 0,
                z: Number(status.position.z) || 0
            };
            this.queueRender();
        }

        // Keep map layout pinned to the template geometry configured in initStaticLayout().

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
                this.updateLiveTorqueDisplay(torquePercent);
                this.updateTorqueBar(torquePercent);
            }
        }

        if (status.instrument_status && typeof status.instrument_status === "object") {
            this.setInstrumentStatus("cnc", Boolean(status.instrument_status.cnc));
            this.setInstrumentStatus("viscometer", Boolean(status.instrument_status.viscometer));
            this.setInstrumentStatus("pump", Boolean(status.instrument_status.pump));
        }

        if (status.current_z_measuring !== undefined && status.current_z_measuring !== null) {
            const currentZ = Number(status.current_z_measuring);
            if (!Number.isNaN(currentZ)) {
                this.updateMeasuringZDisplay(currentZ);
            }
        }

        if (status.is_running !== undefined) {
            this.setRunningState(Boolean(status.is_running), status.run_start_time ?? null);
        }

        if (Array.isArray(status.measurement_data) && status.measurement_data.length > 0 && this.measurements.length === 0) {
            status.measurement_data.forEach((m) => this.ingestMeasurement(m, true));
            this.rebuildPlot();
        }

        if (status.status_message) {
            this.consumeStatusForPhase(status.status_message);
        }
    }

    applyTimeSync(serverTime, runStart) {
        if (typeof serverTime === "number" && Number.isFinite(serverTime)) {
            this.serverClockOffset = serverTime * 1000 - Date.now();
        }
        this.runStartTime = typeof runStart === "number" && Number.isFinite(runStart) ? runStart : null;
    }

    getElapsedSeconds() {
        if (!this.runStartTime) {
            return 0;
        }
        const correctedNow = (Date.now() + this.serverClockOffset) / 1000;
        return Math.max(0, correctedNow - this.runStartTime);
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
            this.completedCells.add(previousCell);
            this.cellStates.set(previousCell, "completed");
            this.playChime(660, 0.08);
            this.updateCompletionBar();
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
        this.updateSparkline();
        this.updateDragZSubtitle();
        if (this.latestZVisible) {
            this.renderLatestZTrace();
        }
        this.updateDragZChart();
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
        let washStation = null;

        if (statusLower.includes("wash station 1")) {
            washStation = "WASH";
        } else if (statusLower.includes("wash station 2")) {
            washStation = "DRY";
        }

        this.platform.cells.forEach((cell) => {
            let state = this.cellStates.get(cell.id) || "pending";

            if (this.completedCells.has(cell.id)) {
                state = "completed";
            }

            if (this.currentCell === cell.id) {
                if (statusLower.includes("descending") || statusLower.includes("measuring")) {
                    state = "measuring";
                } else if (statusLower.includes("error") || statusLower.includes("fail")) {
                    state = "error";
                } else if (statusLower.includes("wash station")) {
                    state = "washing";
                } else {
                    state = "active";
                }
            }

            this.cellStates.set(cell.id, state);
        });

        this.renderMap();

        const stationNodes = this.el.washLayer.querySelectorAll(".wash-node");
        stationNodes.forEach((node) => {
            if (washStation && node.dataset.station === washStation) {
                node.classList.add("active");
            } else {
                node.classList.remove("active");
            }
        });
    }

    consumeStatusForPhase(message) {
        const normalized = (message || "").toLowerCase();
        let phase = 0;

        if (normalized.includes("moving to cell")) {
            phase = 1;
        } else if (normalized.includes("zeroing") || normalized.includes("auto-zero")) {
            phase = 2;
        } else if (normalized.includes("descending") || normalized.includes("measuring")) {
            phase = 3;
        } else if (normalized.includes("returning")) {
            phase = 4;
        } else if (normalized.includes("wash station 1")) {
            phase = 5;
        } else if (normalized.includes("wash station 2")) {
            phase = 6;
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
                    this.updatePlotShapes();
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
        const rpm = Number(rawMeasurement.rpm) || 0;
        const rotationalDrag = Number(rawMeasurement.rotational_drag) || 0;
        const rawTorque = Number(rawMeasurement.torque_percent);
        const measurement = {
            timestamp: Number(rawMeasurement.timestamp) || Date.now() / 1000,
            height: Number(rawMeasurement.height) || 0,
            rotational_drag: rotationalDrag,
            torque_percent: Number.isNaN(rawTorque) ? rotationalDrag * rpm : rawTorque,
            rpm,
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
            this.sparklineData.push({
                x: measurement.height,
                y: measurement.rotational_drag
            });
            if (this.sparklineData.length > 60) {
                this.sparklineData = this.sparklineData.slice(-60);
            }
            this.updateSparkline();
        }

        if (!bootstrap && this.plotInitialized) {
            if (this.trendlineVisible || this.latestZVisible) {
                this.rebuildPlot();
            } else {
                this.appendPointToPlot(measurement);
            }
        }

        this.updatePlotEmptyState();
        this.updateTable();
        this.updateCellVisuals();
    }

    setPlotMode(mode) {
        this.plotMode = mode;
        this.el.toggleAll.classList.toggle("active", mode === "all");
        this.el.toggleCurrent.classList.toggle("active", mode === "current");
        this.rebuildPlot();
        this.updateDragZSubtitle();
        this.updateDragZChart();
    }

    isPointVisible(point) {
        if (this.plotMode !== "current") {
            return true;
        }
        if (!this.currentCell) {
            return false;
        }
        return Number(point.cell_id) === Number(this.currentCell);
    }

    getVisibleScatterPoints() {
        const points = [];
        this.measurementsByCell.forEach((arr, cellId) => {
            if (this.plotMode === "current" && this.currentCell && cellId !== this.currentCell) {
                return;
            }
            arr.forEach((p) => points.push(p));
        });
        return points;
    }

    computeOLS(points) {
        const n = points.length;
        if (n < 2) {
            return null;
        }

        const sumX = points.reduce((sum, p) => sum + p.x, 0);
        const sumY = points.reduce((sum, p) => sum + p.y, 0);
        const sumXY = points.reduce((sum, p) => sum + p.x * p.y, 0);
        const sumX2 = points.reduce((sum, p) => sum + p.x * p.x, 0);
        const denominator = n * sumX2 - sumX * sumX;
        if (Math.abs(denominator) < 1e-12) {
            return null;
        }

        const slope = (n * sumXY - sumX * sumY) / denominator;
        const intercept = (sumY - slope * sumX) / n;
        return { slope, intercept };
    }

    buildTrendlineTrace() {
        if (!this.trendlineVisible) {
            return null;
        }

        const visiblePoints = this.getVisibleScatterPoints();
        if (visiblePoints.length < 2) {
            return null;
        }

        const reg = this.computeOLS(visiblePoints.map((p) => ({ x: p.height, y: p.rotational_drag })));
        if (!reg) {
            return null;
        }

        const heights = visiblePoints.map((p) => p.height);
        const xMin = Math.min(...heights);
        const xMax = Math.max(...heights);

        return {
            x: [xMin, xMax],
            y: [reg.slope * xMin + reg.intercept, reg.slope * xMax + reg.intercept],
            mode: "lines",
            type: "scatter",
            name: "Trendline",
            line: { color: "rgba(255,200,0,0.85)", width: 2, dash: "dash" },
            hoverinfo: "skip"
        };
    }

    buildTracesForMode() {
        const traces = [];
        const selectedCell = this.plotMode === "current" ? this.currentCell : null;

        this.measurementsByCell.forEach((arr, cellId) => {
            if (selectedCell && cellId !== selectedCell) {
                return;
            }

            traces.push({
                x: arr.map((m) => m.height),
                y: arr.map((m) => m.rotational_drag),
                mode: "markers",
                type: "scatter",
                name: `Cell ${cellId}`,
                marker: {
                    color: this.palette[(cellId - 1) % this.palette.length],
                    size: arr.map(() => 8),
                    opacity: 0.88
                },
                hovertemplate: "Cell %{text}<br>Height %{x:.3f} mm<br>Drag %{y:.2f}%<extra></extra>",
                text: arr.map(() => String(cellId))
            });
        });

        return traces;
    }

    rebuildPlot() {
        if (!this.plotInitialized) {
            return;
        }

        const traces = this.buildTracesForMode();
        const trendlineTrace = this.buildTrendlineTrace();
        if (trendlineTrace) {
            traces.push(trendlineTrace);
        }

        Plotly.react(this.el.plot, traces, this.plotLayout, { responsive: true });
        this.updatePlotShapes();
        this.renderLatestZTrace();
        this.updatePlotEmptyState();
    }

    toggleTrendline() {
        this.trendlineVisible = !this.trendlineVisible;
        this.el.trendlineToggle.textContent = this.trendlineVisible ? "Trendline: ON" : "Trendline: OFF";
        this.el.trendlineToggle.dataset.active = this.trendlineVisible ? "true" : "false";
        this.rebuildPlot();
    }

    toggleLatestZ() {
        this.latestZVisible = !this.latestZVisible;
        this.el.latestZToggle.textContent = this.latestZVisible ? "Final Z-Points: ON" : "Final Z-Points: OFF";
        this.el.latestZToggle.dataset.active = this.latestZVisible ? "true" : "false";
        this.el.latestZLineToggle.disabled = !this.latestZVisible;
        if (!this.latestZVisible) {
            this.latestZLineVisible = false;
            this.el.latestZLineToggle.textContent = "Connect Finals: OFF";
            this.el.latestZLineToggle.dataset.active = "false";
        }
        this.renderLatestZTrace();
        this.updateDragZChart();
    }

    toggleLatestZLine() {
        if (!this.latestZVisible) {
            return;
        }
        this.latestZLineVisible = !this.latestZLineVisible;
        this.el.latestZLineToggle.textContent = this.latestZLineVisible ? "Connect Finals: ON" : "Connect Finals: OFF";
        this.el.latestZLineToggle.dataset.active = this.latestZLineVisible ? "true" : "false";
        this.renderLatestZTrace();
    }

    removeTracesByNamePrefix(prefix) {
        if (!this.plotInitialized || !this.el.plot.data) {
            return;
        }

        const deleteIndices = [];
        this.el.plot.data.forEach((trace, index) => {
            if (typeof trace.name === "string" && trace.name.startsWith(prefix)) {
                deleteIndices.push(index);
            }
        });

        if (deleteIndices.length > 0) {
            Plotly.deleteTraces(this.el.plot, deleteIndices);
        }
    }

    renderLatestZTrace() {
        if (!this.plotInitialized) {
            return;
        }

        this.removeTracesByNamePrefix("Final @");

        if (!this.latestZVisible) {
            return;
        }

        const byRpm = {};
        this.latestPerZ.forEach((point) => {
            if (!this.isPointVisible(point)) {
                return;
            }
            const rpmKey = String(point.rpm);
            if (!byRpm[rpmKey]) {
                byRpm[rpmKey] = [];
            }
            byRpm[rpmKey].push(point);
        });

        const traces = Object.entries(byRpm).map(([rpm, pts]) => {
            pts.sort((a, b) => a.height - b.height);
            return {
                x: pts.map((p) => p.height),
                y: pts.map((p) => p.rotational_drag),
                mode: this.latestZLineVisible ? "lines+markers+text" : "markers+text",
                type: "scatter",
                name: `Final @ ${rpm} RPM`,
                text: pts.map((p) => p.rotational_drag.toFixed(3)),
                textposition: "top center",
                textfont: { size: 10 },
                marker: { size: 10, symbol: "diamond", line: { width: 2 } },
                line: this.latestZLineVisible ? { width: 2, dash: "dot" } : undefined
            };
        });

        if (traces.length > 0) {
            Plotly.addTraces(this.el.plot, traces);
        }
    }

    latestPerZKey(cellId, height, rpm) {
        return `${Number(cellId)}|${Number(height).toFixed(3)}|${Number(rpm)}`;
    }

    resetMeasurementStore() {
        this.measurements = [];
        this.measurementsByCell = new Map();
        this.latestTorqueByCell = new Map();
        this.sparklineData = [];
    }

    bulkLoadScatterPoints(points) {
        this.resetMeasurementStore();

        points.forEach((rawPoint) => {
            const rpm = Number(rawPoint.rpm) || 0;
            const rotationalDrag = Number(rawPoint.rotational_drag) || 0;
            const rawTorque = Number(rawPoint.torque_percent);
            const measurement = {
                timestamp: Number(rawPoint.timestamp) || Date.now() / 1000,
                height: Number(rawPoint.height) || 0,
                rotational_drag: rotationalDrag,
                torque_percent: Number.isNaN(rawTorque) ? rotationalDrag * rpm : rawTorque,
                rpm,
                cell_id: Number(rawPoint.cell_id) || 0
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
        });

        if (this.measurements.length > 4000) {
            this.measurements = this.measurements.slice(-4000);
        }

        if (this.currentCell && this.measurementsByCell.has(this.currentCell)) {
            const currentCellPoints = this.measurementsByCell.get(this.currentCell);
            const latestCurrent = currentCellPoints[currentCellPoints.length - 1];
            if (latestCurrent) {
                this.updateTorqueBar(latestCurrent.torque_percent);
                this.updateLiveTorqueDisplay(latestCurrent.torque_percent);
                this.updateLiveRotationalDragDisplay(latestCurrent.rotational_drag);
            }
        }

        this.updateSparkline();
        this.rebuildPlot();
        this.updatePlotEmptyState();
        this.updateTable();
        this.updateCellVisuals();
    }

    bulkLoadLatestPerZ(points) {
        this.latestPerZ = new Map();
        points.forEach((point) => {
            const key = this.latestPerZKey(point.cell_id, point.height, point.rpm);
            this.latestPerZ.set(key, {
                timestamp: Number(point.timestamp) || Date.now() / 1000,
                height: Number(point.height) || 0,
                rotational_drag: Number(point.rotational_drag) || 0,
                torque_percent: Number(point.torque_percent),
                rpm: Number(point.rpm) || 0,
                cell_id: Number(point.cell_id) || 0
            });
        });
        if (this.latestZVisible) {
            this.renderLatestZTrace();
        }
        this.updateDragZChart();
    }

    updateDragZSubtitle() {
        const label = this.plotMode === "current" && this.currentCell ? `Cell ${this.currentCell}` : "All Cells";
        this.el.dragZCellLabel.textContent = label;
    }

    updateDragZChart() {
        if (!this.dragZPlotInitialized) {
            return;
        }

        const byRpm = {};
        this.latestPerZ.forEach((point) => {
            if (!this.isPointVisible(point)) {
                return;
            }
            const rpmKey = String(point.rpm);
            if (!byRpm[rpmKey]) {
                byRpm[rpmKey] = [];
            }
            byRpm[rpmKey].push(point);
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

        Plotly.react(this.el.dragZChart, traces, this.dragZLayout, this.dragZConfig);
    }

    appendPointToPlot(measurement) {
        if (this.plotMode === "current" && this.currentCell && measurement.cell_id !== this.currentCell) {
            return;
        }

        const existingTraces = this.el.plot.data || [];
        let traceIndex = existingTraces.findIndex((trace) => trace.name === `Cell ${measurement.cell_id}`);

        if (traceIndex === -1) {
            this.rebuildPlot();
            return;
        }

        const trace = existingTraces[traceIndex];
        const markerSizes = Array.isArray(trace.marker.size)
            ? [...trace.marker.size, 0]
            : [0];

        Plotly.extendTraces(this.el.plot, {
            x: [[measurement.height]],
            y: [[measurement.rotational_drag]],
            text: [[String(measurement.cell_id)]],
            "marker.size": [[0]]
        }, [traceIndex]);

        requestAnimationFrame(() => {
            markerSizes[markerSizes.length - 1] = 8;
            Plotly.restyle(this.el.plot, { "marker.size": [markerSizes] }, [traceIndex]);
        });
    }

    updatePlotShapes() {
        if (!this.plotInitialized) {
            return;
        }

        const shapes = [];
        const selectedCell = this.plotMode === "current" ? this.currentCell : null;

        this.hitPoints.forEach((height, cellId) => {
            if (selectedCell && selectedCell !== cellId) {
                return;
            }

            shapes.push({
                type: "line",
                x0: height,
                x1: height,
                y0: 0,
                y1: 1,
                yref: "paper",
                line: {
                    color: this.palette[(cellId - 1) % this.palette.length],
                    width: 2,
                    dash: "dash"
                }
            });
        });

        Plotly.relayout(this.el.plot, { shapes });
    }

    updatePlotEmptyState() {
        const hasData = this.measurements.length > 0;
        this.el.plotEmpty.classList.toggle("hidden", hasData);
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
        const rawValue = Number(value) || 0;
        const pct = Math.max(0, Math.min(100, rawValue));
        this.el.torqueFill.style.height = `${pct}%`;
        this.el.torqueValue.textContent = `${rawValue.toFixed(2)}%`;

        if (pct > 80) {
            this.el.torqueFill.style.background = "linear-gradient(180deg, #f85149, #c2322b)";
            this.el.torqueFill.style.filter = "drop-shadow(0 0 8px rgba(248,81,73,0.6))";
        } else if (pct > 50) {
            this.el.torqueFill.style.background = "linear-gradient(180deg, #f5a623, #d5891d)";
            this.el.torqueFill.style.filter = "drop-shadow(0 0 8px rgba(245,166,35,0.5))";
        } else {
            this.el.torqueFill.style.background = "linear-gradient(180deg, #39c5bb, #2ea043)";
            this.el.torqueFill.style.filter = "drop-shadow(0 0 8px rgba(57,197,187,0.42))";
        }
    }

    updateLiveTorqueDisplay(value) {
        this.currentTorquePercent = Number(value) || 0;
        if (this.el.torqueDisplay) {
            this.el.torqueDisplay.textContent = `${this.currentTorquePercent.toFixed(2)}%`;
        }
    }

    updateLiveRotationalDragDisplay(value) {
        this.currentRotationalDrag = Number(value) || 0;
        if (this.el.rotationalDragDisplay) {
            this.el.rotationalDragDisplay.textContent = `${this.currentRotationalDrag.toFixed(2)}%`;
        }
        if (this.el.dragLiveBox) {
            const intensity = Math.min(1.2, this.currentRotationalDrag / 100);
            const red = Math.min(255, Math.round(70 + 180 * intensity));
            const green = Math.max(50, Math.round(180 - 110 * intensity));
            const blue = Math.max(40, Math.round(120 - 90 * intensity));
            this.el.dragLiveBox.style.background = `rgba(${red}, ${green}, ${blue}, 0.28)`;
            this.el.dragLiveBox.style.borderColor = `rgba(${red}, ${Math.max(40, green - 20)}, ${Math.max(35, blue - 20)}, 0.75)`;
            this.el.dragLiveBox.style.boxShadow = intensity >= 1
                ? "0 0 14px rgba(248,81,73,0.55)"
                : "0 0 10px rgba(245,166,35,0.35)";
        }
    }

    updateMeasuringZDisplay(value) {
        this.currentMeasuringZ = value;
        if (this.el.zMeasuringDisplay) {
            this.el.zMeasuringDisplay.textContent = `${value.toFixed(3)} mm`;
        }
    }

    addPointToChart(cellId, height, rotationalDrag, rpm, timestamp, torquePercent = null) {
        this.ingestMeasurement({
            cell_id: cellId,
            height,
            rotational_drag: rotationalDrag,
            rpm,
            timestamp,
            torque_percent: torquePercent
        }, false);
    }

    updateSparkline() {
        if (this.currentCell && this.measurementsByCell.has(this.currentCell)) {
            const src = this.measurementsByCell.get(this.currentCell);
            this.sparklineData = src.slice(-40).map((p) => ({ x: p.height, y: p.rotational_drag }));
        }

        if (this.sparklineData.length < 2) {
            this.el.sparklineLine.setAttribute("points", "");
            return;
        }

        const xs = this.sparklineData.map((d) => d.x);
        const ys = this.sparklineData.map((d) => d.y);
        const minX = Math.min(...xs);
        const maxX = Math.max(...xs);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);

        const spreadX = maxX - minX || 1;
        const spreadY = maxY - minY || 1;

        const points = this.sparklineData.map((d, idx) => {
            const x = (idx / (this.sparklineData.length - 1)) * 216 + 2;
            const y = 56 - ((d.y - minY) / spreadY) * 52;
            return `${x.toFixed(2)},${y.toFixed(2)}`;
        });

        this.el.sparklineLine.setAttribute("points", points.join(" "));
    }

    setRunningState(isRunning, runStartTime = this.runStartTime) {
        const previous = this.isRunning;
        this.isRunning = isRunning;
        this.runStartTime = isRunning ? runStartTime : null;

        this.el.runPill.textContent = isRunning ? "RUNNING" : "IDLE";
        this.el.runPill.classList.toggle("running", isRunning);
        this.el.runPill.classList.toggle("idle", !isRunning);
        this.el.body.classList.toggle("running", isRunning);
        if (isRunning && !this.experimentStart) {
            this.experimentStart = Date.now();
            this.cellStart = Date.now();
            this.runMeasurementStartIndex = this.measurements.length;
            this.setControlStatus("Run active");
        }

        if (!isRunning && previous) {
            this.playChime(720, 0.14);
            this.setControlStatus("Run stopped");
            this.saveCompletedExperiment();
        }

        this.updateControlButtons();
    }

    updateTimers() {
        const now = Date.now();

        if (this.isRunning && this.runStartTime) {
            this.el.elapsed.textContent = this.formatDuration(this.getElapsedSeconds() * 1000);
        } else {
            this.el.elapsed.textContent = "00:00:00";
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
        const ratio = this.completedCells.size / 18;
        this.el.completionBar.style.width = `${(ratio * 100).toFixed(1)}%`;
        this.el.completionText.textContent = `${this.completedCells.size} / 18 cells complete`;
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
                `<td>${m.torque_percent.toFixed(2)}</td>`,
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

        const header = "timestamp,cell_id,height_mm,torque_percent,rotational_drag,rpm\n";
        const csv = this.measurements
            .map((m) => {
                const iso = new Date(m.timestamp * 1000).toISOString();
                return `${iso},${m.cell_id},${m.height},${m.torque_percent},${m.rotational_drag},${m.rpm}`;
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

    initSummaryPlot() {
        this.summaryPlotLayout = {
            xaxis: { title: "Z-Height (mm)", autorange: "reversed", tickformat: ".3f" },
            yaxis: { title: "Rotational Drag", rangemode: "tozero" },
            margin: { t: 24, r: 16, b: 56, l: 64 },
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            font: { color: "#cdd6f4" },
            legend: { orientation: "h", y: -0.24 }
        };
        this.summaryPlotConfig = { responsive: true, displayModeBar: false };
        Plotly.newPlot(this.el.summaryPlot, [], this.summaryPlotLayout, this.summaryPlotConfig);
    }

    loadExperimentHistory() {
        try {
            const raw = localStorage.getItem("viscometryExperimentHistory");
            this.experimentHistory = raw ? JSON.parse(raw) : [];
        } catch (_error) {
            this.experimentHistory = [];
        }
        this.renderExperimentHistoryCards();
    }

    persistExperimentHistory() {
        localStorage.setItem("viscometryExperimentHistory", JSON.stringify(this.experimentHistory));
    }

    buildSummaryCSV(rows) {
        const header = "timestamp,cell_id,height_mm,torque_percent,rotational_drag,rpm\n";
        const body = rows.map((row) => {
            const iso = new Date(row.timestamp * 1000).toISOString();
            return `${iso},${row.cell_id},${row.height},${row.torque_percent},${row.rotational_drag},${row.rpm}`;
        }).join("\n");
        return header + body;
    }

    saveCompletedExperiment() {
        const runData = this.measurements.slice(this.runMeasurementStartIndex);
        if (runData.length === 0) {
            return;
        }

        const settings = this.readControlSettings();
        const cells = [...new Set(runData.map((m) => m.cell_id))].sort((a, b) => a - b);
        const rpms = [...new Set(runData.map((m) => Number(m.rpm.toFixed(3))))].sort((a, b) => a - b);
        const summary = {
            id: `exp-${Date.now()}`,
            created_at: Date.now(),
            measurement_count: runData.length,
            cells,
            rpms,
            settings,
            rows: runData,
            csv: this.buildSummaryCSV(runData)
        };

        this.experimentHistory.unshift(summary);
        this.experimentHistory = this.experimentHistory.slice(0, 40);
        this.persistExperimentHistory();
        this.renderExperimentHistoryCards();
        this.selectExperimentSummary(summary.id);
    }

    renderExperimentHistoryCards() {
        this.el.summaryCards.innerHTML = "";

        if (this.experimentHistory.length === 0) {
            this.el.summaryCards.innerHTML = '<div class="summary-empty">No experiments recorded yet.</div>';
            this.el.summaryDetail.classList.add("hidden");
            this.el.summaryEmpty.classList.remove("hidden");
            return;
        }

        this.experimentHistory.forEach((exp) => {
            const card = document.createElement("div");
            card.className = "experiment-card";
            if (exp.id === this.selectedExperimentId) {
                card.classList.add("active");
            }
            card.innerHTML = [
                `<div class="experiment-card-row"><strong>${new Date(exp.created_at).toLocaleString()}</strong><span>${exp.measurement_count} pts</span></div>`,
                `<div class="experiment-card-row"><span>Cells</span><span>${exp.cells.join(", ") || "-"}</span></div>`,
                `<div class="experiment-card-row"><span>RPMs</span><span>${exp.rpms.join(", ") || "-"}</span></div>`
            ].join("");

            const deleteBtn = document.createElement("button");
            deleteBtn.className = "experiment-delete";
            deleteBtn.textContent = "Delete";
            deleteBtn.addEventListener("click", (event) => {
                event.stopPropagation();
                this.deleteExperimentSummary(exp.id);
            });

            card.appendChild(deleteBtn);
            card.addEventListener("click", () => this.selectExperimentSummary(exp.id));
            this.el.summaryCards.appendChild(card);
        });
    }

    deleteExperimentSummary(expId) {
        this.experimentHistory = this.experimentHistory.filter((item) => item.id !== expId);
        if (this.selectedExperimentId === expId) {
            this.selectedExperimentId = null;
        }
        this.persistExperimentHistory();
        this.renderExperimentHistoryCards();
        if (!this.selectedExperimentId) {
            this.el.summaryDetail.classList.add("hidden");
            this.el.summaryEmpty.classList.remove("hidden");
            Plotly.react(this.el.summaryPlot, [], this.summaryPlotLayout, this.summaryPlotConfig);
        }
    }

    selectExperimentSummary(expId) {
        const summary = this.experimentHistory.find((item) => item.id === expId);
        if (!summary) {
            return;
        }

        this.selectedExperimentId = expId;
        this.el.summaryEmpty.classList.add("hidden");
        this.el.summaryDetail.classList.remove("hidden");
        this.el.summaryMeta.innerHTML = [
            `<strong>Timestamp:</strong> ${new Date(summary.created_at).toLocaleString()}<br>`,
            `<strong>Cells:</strong> ${summary.cells.join(", ") || "-"}<br>`,
            `<strong>RPMs:</strong> ${summary.rpms.join(", ") || "-"}<br>`,
            `<strong>Rows:</strong> ${summary.settings.selected_rows?.join(", ") || "-"}<br>`,
            `<strong>Z Step:</strong> ${summary.settings.z_step_size}<br>`,
            `<strong>Measurement Duration:</strong> ${summary.settings.measurement_duration} s`
        ].join("");
        this.renderSummaryPlot(summary);
        this.renderExperimentHistoryCards();
    }

    renderSummaryPlot(summary) {
        const latestByKey = new Map();
        summary.rows.forEach((row) => {
            const key = `${row.cell_id}|${Number(row.height).toFixed(3)}|${row.rpm}`;
            latestByKey.set(key, row);
        });

        const byRpm = {};
        latestByKey.forEach((row) => {
            const rpmKey = String(row.rpm);
            if (!byRpm[rpmKey]) {
                byRpm[rpmKey] = [];
            }
            byRpm[rpmKey].push(row);
        });

        const traces = Object.entries(byRpm).map(([rpm, points]) => {
            points.sort((a, b) => a.height - b.height);
            return {
                x: points.map((p) => p.height),
                y: points.map((p) => p.rotational_drag),
                mode: "lines+markers",
                type: "scatter",
                name: `${rpm} RPM`,
                marker: { size: 7 },
                line: { width: 2 }
            };
        });

        Plotly.react(this.el.summaryPlot, traces, this.summaryPlotLayout, this.summaryPlotConfig);
    }

    downloadSelectedSummaryCSV() {
        const summary = this.experimentHistory.find((item) => item.id === this.selectedExperimentId);
        if (!summary) {
            return;
        }

        const blob = new Blob([summary.csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `viscometry_summary_${summary.id}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
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

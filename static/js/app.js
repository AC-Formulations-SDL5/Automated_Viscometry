// Viscometry Platform Web Interface JavaScript

class ViscometryInterface {
    constructor() {
        this.socket = io();
        this.measurementData = [];
        this.currentCell = null;
        this.cellPositions = [];
        this.washStations = [];
        this.bounds = {};
        this.viscometer = { x: 0, y: 0, z: 0 };
        
        // Initialize cell state tracking
        this.testedCells = new Set();
        this.currentTestingCell = null;
        
        this.initializeInterface();
        this.setupSocketHandlers();
        this.setupEventHandlers();
    }

    initializeInterface() {
        // Initialize the scatter plot
        this.initializePlot();
        
        // Load initial data
        this.loadInitialData();
    }

    loadInitialData() {
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                this.cellPositions = data.cell_positions;
                this.washStations = data.wash_stations;
                this.bounds = data.bounds;
                this.viscometer = data.position;
                this.updatePlatformMap();
                this.updateViscometer();
                this.updateStatusDisplay(data);
            })
            .catch(error => console.error('Error loading initial data:', error));

        fetch('/api/measurement_data')
            .then(response => response.json())
            .then(data => {
                this.measurementData = data;
                this.updatePlot();
            })
            .catch(error => console.error('Error loading measurement data:', error));
    }

    setupSocketHandlers() {
        this.socket.on('connect', () => {
            console.log('Connected to server');
        });

        this.socket.on('position_update', (data) => {
            this.viscometer = data;
            this.updateViscometer();
            this.updatePositionDisplay(data);
        });

        this.socket.on('status_update', (data) => {
            this.updateStatusDisplay(data);
        });

        this.socket.on('cell_update', (data) => {
            // Update current testing cell
            if (data.current_cell !== this.currentTestingCell) {
                // Mark previous cell as tested if it was being tested
                if (this.currentTestingCell !== null) {
                    this.testedCells.add(this.currentTestingCell);
                }
                this.currentTestingCell = data.current_cell;
                this.currentCell = data.current_cell;
                this.updateCellStates();
            }
        });

        this.socket.on('rpm_update', (data) => {
            document.getElementById('current-rpm').textContent = data.current_rpm.toFixed(1);
        });

        this.socket.on('new_measurement', (measurement) => {
            this.measurementData.push(measurement);
            // Keep only last 1000 points for performance
            if (this.measurementData.length > 1000) {
                this.measurementData = this.measurementData.slice(-1000);
            }
            this.updatePlot();
            this.updateDataSummary();
        });

        this.socket.on('running_state_update', (data) => {
            this.updateRunningState(data.is_running);
        });
    }

    setupEventHandlers() {
        // Plot control handlers
        document.getElementById('show-all-cells').addEventListener('change', () => {
            this.updatePlot();
        });

        document.getElementById('show-current-only').addEventListener('change', () => {
            this.updatePlot();
        });

        document.getElementById('clear-data').addEventListener('click', () => {
            if (confirm('Clear all measurement data?')) {
                this.measurementData = [];
                this.updatePlot();
                this.updateDataSummary();
            }
        });

        document.getElementById('export-data').addEventListener('click', () => {
            this.exportData();
        });

        // Fixed control handlers
        document.getElementById('start-experiment').addEventListener('click', () => {
            this.startExperiment();
        });

        document.getElementById('stop-experiment').addEventListener('click', () => {
            this.stopExperiment();
        });

        document.getElementById('export-results').addEventListener('click', () => {
            this.exportResults();
        });
    }

    updatePlatformMap() {
        const svg = document.getElementById('platform-map');
        const cellsGroup = document.getElementById('cells-group');
        const washStationsGroup = document.getElementById('wash-stations-group');

        // Clear existing elements
        cellsGroup.innerHTML = '';
        washStationsGroup.innerHTML = '';

        // Add cells with enhanced visualization
        this.cellPositions.forEach(cell => {
            const svgX = this.mapToSvgX(cell.x);
            const svgY = this.mapToSvgY(cell.y);

            // Create cell circle (larger size)
            const cellCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            cellCircle.setAttribute('cx', svgX);
            cellCircle.setAttribute('cy', svgY);
            cellCircle.setAttribute('r', '18'); // Increased from 12 to 18
            cellCircle.setAttribute('class', this.getCellClass(cell.id));
            cellCircle.setAttribute('data-cell-id', cell.id);
            cellCircle.innerHTML = `<title>Cell ${cell.id} (Row ${cell.row}) - ${this.getCellStatus(cell.id)}</title>`;

            // Create cell label
            const cellLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            cellLabel.setAttribute('x', svgX);
            cellLabel.setAttribute('y', svgY);
            cellLabel.setAttribute('class', 'cell-label');
            cellLabel.textContent = cell.id;

            cellsGroup.appendChild(cellCircle);
            cellsGroup.appendChild(cellLabel);
        });

        // Add wash stations with enhanced styling
        this.washStations.forEach(station => {
            const svgX = this.mapToSvgX(station.x);
            const svgY = this.mapToSvgY(station.y);

            const stationCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            stationCircle.setAttribute('cx', svgX);
            stationCircle.setAttribute('cy', svgY);
            stationCircle.setAttribute('r', '20'); // Increased from 15 to 20
            stationCircle.setAttribute('class', 'wash-station');
            stationCircle.innerHTML = `<title>Wash Station ${station.id}</title>`;

            // Create wash station label
            const stationLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            stationLabel.setAttribute('x', svgX);
            stationLabel.setAttribute('y', svgY);
            stationLabel.setAttribute('class', 'cell-label');
            stationLabel.textContent = `W${station.id}`;

            washStationsGroup.appendChild(stationCircle);
            washStationsGroup.appendChild(stationLabel);
        });
    }

    updateViscometer() {
        const viscometer = document.getElementById('viscometer');
        const viscometer_glow = document.getElementById('viscometer-glow');
        const svgX = this.mapToSvgX(this.viscometer.x);
        const svgY = this.mapToSvgY(this.viscometer.y);

        // Update main viscometer position
        viscometer.setAttribute('cx', svgX);
        viscometer.setAttribute('cy', svgY);
        
        // Update glow effect
        if (viscometer_glow) {
            viscometer_glow.setAttribute('cx', svgX);
            viscometer_glow.setAttribute('cy', svgY);
        }
        
        // Update tooltip
        viscometer.innerHTML = `<title>Viscometer at (${this.viscometer.x.toFixed(1)}, ${this.viscometer.y.toFixed(1)}, ${this.viscometer.z.toFixed(2)})</title>`;
    }

    getCellClass(cellId) {
        let baseClass = 'cell';
        
        if (this.currentTestingCell === cellId) {
            baseClass += ' current';
        } else if (this.testedCells.has(cellId)) {
            baseClass += ' tested';
        } else {
            baseClass += ' empty';
        }
        
        return baseClass;
    }

    getCellStatus(cellId) {
        if (this.currentTestingCell === cellId) {
            return 'Testing Now';
        } else if (this.testedCells.has(cellId)) {
            return 'Tested';
        } else {
            return 'Empty';
        }
    }

    updateCellStates() {
        // Update all cell classes based on current state
        this.cellPositions.forEach(cell => {
            const cellElement = document.querySelector(`[data-cell-id="${cell.id}"]`);
            if (cellElement) {
                cellElement.setAttribute('class', this.getCellClass(cell.id));
                cellElement.innerHTML = `<title>Cell ${cell.id} (Row ${cell.row}) - ${this.getCellStatus(cell.id)}</title>`;
            }
        });
    }

    mapToSvgX(x) {
        // Map platform coordinates to SVG coordinates (CNC bed layout)
        const svgWidth = 420; // Working area width (435-15)
        const svgOffset = 15; // Working area offset
        return (x / this.bounds.x_max) * svgWidth + svgOffset;
    }

    mapToSvgY(y) {
        // Map platform coordinates to SVG coordinates (Y is flipped, CNC bed layout)
        const svgHeight = 370; // Working area height (385-15)
        const svgOffset = 15; // Working area offset
        return svgHeight - (y / this.bounds.y_max) * svgHeight + svgOffset;
    }

    initializePlot() {
        const layout = {
            title: {
                text: 'Rotational Drag vs Height',
                font: { size: 16, color: '#ffffff' }
            },
            xaxis: {
                title: { 
                    text: 'Height (mm)',
                    font: { color: '#ffffff' }
                },
                showgrid: true,
                gridcolor: '#333333',
                zeroline: true,
                zerolinecolor: '#666666',
                tickfont: { color: '#cccccc' }
            },
            yaxis: {
                title: { 
                    text: 'Rotational Drag (Nm)',
                    font: { color: '#ffffff' }
                },
                showgrid: true,
                gridcolor: '#333333',
                zeroline: true,
                zerolinecolor: '#666666',
                tickfont: { color: '#cccccc' }
            },
            showlegend: true,
            legend: {
                font: { color: '#ffffff' }
            },
            hovermode: 'closest',
            margin: { l: 60, r: 30, t: 60, b: 60 },
            plot_bgcolor: '#0a0a0a',
            paper_bgcolor: '#0a0a0a'
        };

        const config = {
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['pan2d', 'select2d', 'lasso2d']
        };

        Plotly.newPlot('scatter-plot', [], layout, config);
    }

    updatePlot() {
        const showAllCells = document.getElementById('show-all-cells').checked;
        const showCurrentOnly = document.getElementById('show-current-only').checked;

        let dataToPlot = this.measurementData;

        if (showCurrentOnly && this.currentCell) {
            dataToPlot = this.measurementData.filter(d => d.cell_id === this.currentCell);
        }

        // Group data by cell
        const cellData = {};
        dataToPlot.forEach(point => {
            if (!cellData[point.cell_id]) {
                cellData[point.cell_id] = {
                    x: [],
                    y: [],
                    text: [],
                    name: `Cell ${point.cell_id}`,
                    mode: 'markers',
                    type: 'scatter',
                    marker: {
                        size: 6,
                        opacity: 0.7
                    }
                };
            }
            cellData[point.cell_id].x.push(point.height);
            cellData[point.cell_id].y.push(point.rotational_drag);
            cellData[point.cell_id].text.push(
                `Cell: ${point.cell_id}<br>` +
                `Height: ${point.height.toFixed(3)} mm<br>` +
                `Drag: ${point.rotational_drag.toFixed(3)} Nm<br>` +
                `RPM: ${point.rpm.toFixed(1)}<br>` +
                `Time: ${new Date(point.timestamp * 1000).toLocaleTimeString()}`
            );
        });

        // Convert to array of traces
        const traces = Object.values(cellData);

        // Color scheme for different cells
        const colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b',
            '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#aec7e8', '#ffbb78',
            '#98df8a', '#ff9896', '#c5b0d5', '#c49c94', '#f7b6d3', '#c7c7c7',
        ];

        traces.forEach((trace, index) => {
            trace.marker.color = colors[index % colors.length];
        });

        Plotly.react('scatter-plot', traces);
        this.updateDataSummary();
    }

    updateStatusDisplay(data) {
        if (data.status_message) {
            document.getElementById('status-message').textContent = data.status_message;
        }
        if (data.current_cell !== undefined) {
            document.getElementById('current-cell').textContent = data.current_cell || '-';
            // Update current testing cell
            if (data.current_cell !== this.currentTestingCell) {
                // Mark previous cell as tested if it was being tested
                if (this.currentTestingCell !== null) {
                    this.testedCells.add(this.currentTestingCell);
                }
                this.currentTestingCell = data.current_cell;
                this.currentCell = data.current_cell;
                this.updateCellStates();
            }
        }
        if (data.current_rpm !== undefined) {
            document.getElementById('current-rpm').textContent = data.current_rpm.toFixed(1);
        }
        if (data.position) {
            this.updatePositionDisplay(data.position);
        }
        if (data.is_running !== undefined) {
            this.updateRunningState(data.is_running);
        }
    }

    updatePositionDisplay(position) {
        const positionText = `X: ${position.x.toFixed(1)}, Y: ${position.y.toFixed(1)}, Z: ${position.z.toFixed(2)}`;
        document.getElementById('position').textContent = positionText;
    }

    updateRunningState(isRunning) {
        const indicator = document.getElementById('running-indicator');
        if (isRunning) {
            indicator.textContent = 'RUNNING';
            indicator.className = 'value status-running';
        } else {
            indicator.textContent = 'STOPPED';
            indicator.className = 'value status-stopped';
        }
    }

    updateDataSummary() {
        document.getElementById('total-points').textContent = this.measurementData.length;
        
        if (this.measurementData.length > 0) {
            const latestPoint = this.measurementData[this.measurementData.length - 1];
            document.getElementById('current-height').textContent = latestPoint.height.toFixed(3) + ' mm';
            document.getElementById('current-drag').textContent = latestPoint.rotational_drag.toFixed(3) + ' Nm';
        } else {
            document.getElementById('current-height').textContent = '-';
            document.getElementById('current-drag').textContent = '-';
        }
    }

    exportData() {
        if (this.measurementData.length === 0) {
            alert('No data to export');
            return;
        }

        // Convert data to CSV
        const header = 'Timestamp,Cell_ID,Height_mm,Rotational_Drag_Nm,RPM\n';
        const csv = this.measurementData.map(point => {
            const timestamp = new Date(point.timestamp * 1000).toISOString();
            return `${timestamp},${point.cell_id},${point.height},${point.rotational_drag},${point.rpm}`;
        }).join('\n');

        // Download file
        const blob = new Blob([header + csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `viscometry_data_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    startExperiment() {
        // Send start command via Socket.IO
        this.socket.emit('start_experiment');
        
        // Update button states
        document.getElementById('start-experiment').disabled = true;
        document.getElementById('stop-experiment').disabled = false;
        document.getElementById('export-results').style.display = 'none';
        document.getElementById('recording-dot').classList.remove('hidden');
    }

    stopExperiment() {
        // Send stop command via Socket.IO
        this.socket.emit('stop_experiment');
        
        // Update button states
        document.getElementById('start-experiment').disabled = false;
        document.getElementById('stop-experiment').disabled = true;
        document.getElementById('export-results').style.display = 'inline-block';
        document.getElementById('recording-dot').classList.add('hidden');
    }

    exportResults() {
        // Use existing export functionality
        this.exportData();
    }
}

// Initialize the interface when the page loads
document.addEventListener('DOMContentLoaded', () => {
    const interface = new ViscometryInterface();
    
    // Make it globally accessible for debugging
    window.viscometryInterface = interface;
});
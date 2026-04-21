"""
Web Interface for Automated Viscometry Platform
Provides real-time monitoring and control interface
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import time
import os
from typing import Dict, List, Tuple, Optional
import json

class ViscometryWebInterface:
    def __init__(self, port=5001):
        # Set template and static folder paths relative to project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        template_folder = os.path.join(project_root, 'templates')
        static_folder = os.path.join(project_root, 'static')
        
        self.app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
        self.app.config['SECRET_KEY'] = 'viscometry_secret_key'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        self.port = port
        
        # Current state
        self.current_position = {'x': 0, 'y': 0, 'z': 0}
        self.measurement_data = []
        self.current_cell = None
        self.current_rpm = 0
        self.current_torque_percent = 0.0
        self.current_z_measuring = None
        self.instrument_status = {'cnc': False, 'viscometer': False, 'pump': False}
        self.is_running = False
        self.status_message = "Ready"
        self.control_lock = threading.Lock()
        self.start_requested_event = threading.Event()
        self.stop_requested_event = threading.Event()
        self.runtime_settings = {
            'testing_mode': 'custom',
            'selected_rows': [2],
            'selected_cells': [1],
            'test_rpms': [0.8],
            'cell_rpm_map': {},
            'z_step_size': -0.02,
            'measurement_duration': 40.0,
            'sample_interval': 10.0,
            'dwell_seconds': 2.0,
            'inter_rpm_pause': 2.0,
            'feedback_control_enabled': True,
            'min_data_points_for_trend': 8,
            'second_derivative_threshold': -2.0,
            'cv_jump_threshold': 0.4,
            'trend_r_squared_min': 0.5,
            'hit_point_confidence_threshold': 0.8,
            'torque_break_threshold': 100.0,
        }
        
        # Platform configuration from your code
        self.X_LOW_BOUND = 0
        self.X_HIGH_BOUND = 450
        self.Y_LOW_BOUND = 0
        self.Y_HIGH_BOUND = 400
        
        # Cell configuration
        self.BASE_Y = 62
        self.Y_OFFSET = 67
        self.ROWS = [
            {'row_number': 1, 'base_x': 10, 'safe_z': -65.5, 'max_z_travel': -66.500},
            {'row_number': 2, 'base_x': 85, 'safe_z': -65.5, 'max_z_travel': -66.500},
            {'row_number': 3, 'base_x': 309, 'safe_z': -64.5, 'max_z_travel': -65.500}
        ]
        
        # Wash stations
        self.WASH_STATION1_X = 383
        self.WASH_STATION1_Y = 68
        self.WASH_STATION2_X = 383
        self.WASH_STATION2_Y = 147
        
        self.setup_routes()
        
        # Create templates and static directories
        self.create_directories()
        
    def create_directories(self):
        """Create necessary directories for web interface"""
        os.makedirs('templates', exist_ok=True)
        os.makedirs('static/css', exist_ok=True)
        os.makedirs('static/js', exist_ok=True)
        os.makedirs('static/images', exist_ok=True)
        
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            return render_template('index.html')
            
        @self.app.route('/api/status')
        def get_status():
            return jsonify({
                'position': self.current_position,
                'current_cell': self.current_cell,
                'current_rpm': self.current_rpm,
                'current_torque_percent': self.current_torque_percent,
                'current_z_measuring': self.current_z_measuring,
                'instrument_status': self.instrument_status,
                'is_running': self.is_running,
                'status_message': self.status_message,
                'cell_positions': self.get_cell_positions(),
                'wash_stations': [
                    {'id': 1, 'x': self.WASH_STATION1_X, 'y': self.WASH_STATION1_Y},
                    {'id': 2, 'x': self.WASH_STATION2_X, 'y': self.WASH_STATION2_Y}
                ],
                'bounds': {
                    'x_min': self.X_LOW_BOUND, 'x_max': self.X_HIGH_BOUND,
                    'y_min': self.Y_LOW_BOUND, 'y_max': self.Y_HIGH_BOUND
                }
            })
            
        @self.app.route('/api/measurement_data')
        def get_measurement_data():
            return jsonify(self.measurement_data)

        @self.app.route('/api/control_settings', methods=['GET', 'POST'])
        def control_settings():
            if request.method == 'GET':
                return jsonify(self.get_runtime_settings())

            payload = request.get_json(silent=True) or {}
            settings = self.update_runtime_settings(payload)
            return jsonify(settings)

        @self.app.route('/api/run/start', methods=['POST'])
        def api_run_start():
            payload = request.get_json(silent=True) or {}
            if payload:
                self.update_runtime_settings(payload)
            self.request_start()
            self.update_status('Start command received from web interface')
            return jsonify({'ok': True, 'status_message': self.status_message})

        @self.app.route('/api/run/stop', methods=['POST'])
        def api_run_stop():
            self.request_stop()
            self.update_status('Stop command received from web interface')
            return jsonify({'ok': True, 'status_message': self.status_message})
            
        @self.socketio.on('connect')
        def handle_connect():
            emit('status_update', self.get_status_dict())
            emit('control_settings_update', self.get_runtime_settings())

        @self.socketio.on('update_control_settings')
        def handle_update_control_settings(payload):
            settings = self.update_runtime_settings(payload or {})
            emit('control_settings_update', settings, broadcast=True)

        @self.socketio.on('start_run')
        def handle_start_run(payload=None):
            if isinstance(payload, dict) and payload:
                self.update_runtime_settings(payload)
            self.request_start()
            emit('status_update', {'status_message': 'Start command received from web interface'}, broadcast=True)

        @self.socketio.on('stop_run')
        def handle_stop_run():
            self.request_stop()
            emit('status_update', {'status_message': 'Stop command received from web interface'}, broadcast=True)
            
    def get_cell_positions(self) -> List[Dict]:
        """Calculate positions for all 18 cells"""
        cells = []
        for row_idx, row in enumerate(self.ROWS):
            for cell_idx in range(6):  # 6 cells per row
                global_cell_num = row_idx * 6 + cell_idx + 1
                x = row['base_x']
                y = self.BASE_Y + cell_idx * self.Y_OFFSET
                cells.append({
                    'id': global_cell_num,
                    'x': x,
                    'y': y,
                    'row': row_idx + 1,
                    'local_cell': cell_idx + 1
                })
        return cells
        
    def get_status_dict(self) -> Dict:
        """Get current status as dictionary"""
        return {
            'position': self.current_position,
            'current_cell': self.current_cell,
            'current_rpm': self.current_rpm,
            'current_torque_percent': self.current_torque_percent,
            'current_z_measuring': self.current_z_measuring,
            'instrument_status': self.instrument_status,
            'is_running': self.is_running,
            'status_message': self.status_message,
            'measurement_data': self.measurement_data[-100:],  # Last 100 points
            'control_settings': self.get_runtime_settings()
        }

    def get_runtime_settings(self) -> Dict:
        """Get a copy of the current runtime settings."""
        with self.control_lock:
            settings = {}
            for key, value in self.runtime_settings.items():
                settings[key] = value[:] if isinstance(value, list) else value
            return settings

    def update_runtime_settings(self, settings: Dict) -> Dict:
        """Update runtime settings from UI input."""
        normalized = self.get_runtime_settings()

        def parse_float_list(value):
            if isinstance(value, list):
                return [float(item) for item in value]
            if isinstance(value, str):
                items = [part.strip() for part in value.split(',') if part.strip()]
                return [float(item) for item in items]
            return normalized.get('test_rpms', [0.8])

        def parse_int_list(value):
            if isinstance(value, list):
                return [int(item) for item in value]
            if isinstance(value, str):
                items = [part.strip() for part in value.split(',') if part.strip()]
                return [int(item) for item in items]
            return []

        with self.control_lock:
            if 'testing_mode' in settings and settings['testing_mode']:
                normalized['testing_mode'] = str(settings['testing_mode'])
            if 'selected_rows' in settings:
                rows = parse_int_list(settings['selected_rows'])
                normalized['selected_rows'] = rows or normalized['selected_rows']
            if 'selected_cells' in settings:
                cells = parse_int_list(settings['selected_cells'])
                normalized['selected_cells'] = cells or normalized['selected_cells']
            if 'test_rpms' in settings:
                rpms = parse_float_list(settings['test_rpms'])
                if rpms:
                    normalized['test_rpms'] = rpms
            if 'cell_rpm_map' in settings:
                raw_map = settings['cell_rpm_map']
                if isinstance(raw_map, dict):
                    parsed_map = {}
                    for cell_key, rpm_val in raw_map.items():
                        # Normalise key to string
                        str_key = str(cell_key)
                        # rpm_val may be a list, a comma-string, or a single number
                        if isinstance(rpm_val, list):
                            rpms = [float(r) for r in rpm_val if str(r).strip()]
                        elif isinstance(rpm_val, str):
                            rpms = [float(r.strip()) for r in rpm_val.split(',') if r.strip()]
                        else:
                            rpms = [float(rpm_val)]
                        if rpms:
                            parsed_map[str_key] = rpms
                    normalized['cell_rpm_map'] = parsed_map
                else:
                    normalized['cell_rpm_map'] = {}
            float_keys = {'z_step_size', 'measurement_duration', 'sample_interval', 'dwell_seconds', 'inter_rpm_pause', 'second_derivative_threshold', 'cv_jump_threshold', 'trend_r_squared_min', 'hit_point_confidence_threshold', 'torque_break_threshold'}
            int_keys = {'min_data_points_for_trend'}
            for key in ['z_step_size', 'measurement_duration', 'sample_interval', 'dwell_seconds', 'inter_rpm_pause', 'min_data_points_for_trend', 'second_derivative_threshold', 'cv_jump_threshold', 'trend_r_squared_min', 'hit_point_confidence_threshold', 'torque_break_threshold']:
                if key in settings and settings[key] not in (None, ''):
                    if key in float_keys:
                        normalized[key] = float(settings[key])
                    else:
                        normalized[key] = int(settings[key])
            if 'feedback_control_enabled' in settings:
                normalized['feedback_control_enabled'] = bool(settings['feedback_control_enabled'])

            self.runtime_settings = normalized

        return self.get_runtime_settings()

    def request_start(self):
        """Mark that the experiment should start."""
        self.stop_requested_event.clear()
        self.start_requested_event.set()

    def request_stop(self):
        """Mark that the experiment should stop."""
        self.stop_requested_event.set()
        self.is_running = False
        self.socketio.emit('running_state_update', {'is_running': False})

    def wait_for_start_command(self, poll_interval=0.2):
        """Block until a start request is received from the web UI."""
        while not self.start_requested_event.is_set():
            if self.stop_requested_event.is_set():
                return False
            time.sleep(poll_interval)
        return True

    def consume_start_command(self):
        """Clear the start request after the run begins."""
        self.start_requested_event.clear()

    def should_stop(self) -> bool:
        """Return True when the UI has requested shutdown."""
        return self.stop_requested_event.is_set()

    def clear_stop_request(self):
        """Clear any pending stop request."""
        self.stop_requested_event.clear()
        
    def update_position(self, x: Optional[float] = None, y: Optional[float] = None, z: Optional[float] = None):
        """Update viscometer position"""
        if x is not None:
            self.current_position['x'] = x
        if y is not None:
            self.current_position['y'] = y
        if z is not None:
            self.current_position['z'] = z
            
        # Emit update to connected clients
        self.socketio.emit('position_update', self.current_position)
        
    def update_status(self, message: str):
        """Update status message"""
        self.status_message = message
        self.socketio.emit('status_update', {'status_message': message})
        
    def set_current_cell(self, cell_id: int):
        """Set the currently active cell"""
        self.current_cell = cell_id
        self.socketio.emit('cell_update', {'current_cell': cell_id})
        
    def set_current_rpm(self, rpm: float):
        """Set current RPM"""
        self.current_rpm = rpm
        self.socketio.emit('rpm_update', {'current_rpm': rpm})

    def set_instrument_status(self, cnc=None, viscometer=None, pump=None):
        if cnc is not None:
            self.instrument_status['cnc'] = bool(cnc)
        if viscometer is not None:
            self.instrument_status['viscometer'] = bool(viscometer)
        if pump is not None:
            self.instrument_status['pump'] = bool(pump)
        self.socketio.emit('instrument_status_update', self.instrument_status)

    def update_live_torque(self, torque_percent: float, rpm: float, elapsed: float):
        """Broadcast the most recent raw torque reading to connected clients."""
        self.current_torque_percent = torque_percent
        self.socketio.emit('torque_update', {
            'torque_percent': torque_percent,
            'rpm': rpm,
            'elapsed': elapsed,
        })

    def set_current_z(self, z: float):
        """Broadcast the Z-height currently under active measurement."""
        self.current_z_measuring = z
        self.socketio.emit('z_update', {'current_z': z})
        
    def add_measurement_point(self, height: float, rotational_drag: float, rpm: float, cell_id: int):
        """Add a new measurement point"""
        measurement = {
            'timestamp': time.time(),
            'height': height,
            'rotational_drag': rotational_drag,
            'torque_percent': rotational_drag * rpm,
            'rpm': rpm,
            'cell_id': cell_id
        }
        self.measurement_data.append(measurement)
        
        # Keep only last 1000 measurements
        if len(self.measurement_data) > 1000:
            self.measurement_data = self.measurement_data[-1000:]
            
        # Emit to connected clients
        self.socketio.emit('new_measurement', measurement)
        
    def set_running_state(self, is_running: bool):
        """Set running state"""
        self.is_running = is_running
        self.socketio.emit('running_state_update', {'is_running': is_running})
        
    def start_server(self, debug=False):
        """Start the web server"""
        print(f"Starting Viscometry Web Interface on http://localhost:{self.port}")
        self.socketio.run(self.app, host='0.0.0.0', port=self.port, debug=debug, allow_unsafe_werkzeug=True)
        
    def start_in_thread(self, debug=False):
        """Start web server in background thread"""
        thread = threading.Thread(target=self.start_server, args=(debug,), daemon=True)
        thread.start()
        return thread

# Global instance for easy access
web_interface = ViscometryWebInterface(port=5001)

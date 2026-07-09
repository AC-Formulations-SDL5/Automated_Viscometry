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
    def __init__(self, port=5000):
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
        self.is_running = False
        self.status_message = "Ready"
        
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
            
        @self.socketio.on('connect')
        def handle_connect():
            emit('status_update', self.get_status_dict())
            
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
            'is_running': self.is_running,
            'status_message': self.status_message,
            'measurement_data': self.measurement_data[-100:]  # Last 100 points
        }
        
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
        
    def add_measurement_point(self, height: float, rotational_drag: float, rpm: float, cell_id: int):
        """Add a new measurement point"""
        measurement = {
            'timestamp': time.time(),
            'height': height,
            'rotational_drag': rotational_drag,
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
web_interface = ViscometryWebInterface()
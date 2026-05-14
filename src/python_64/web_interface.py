"""
Web Interface for Automated Viscometry Platform
Provides real-time monitoring and control interface
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import time
import os
import math
from typing import Dict, List, Tuple, Optional
import json
from calibration_store import is_calibrated, get_calibration_summary, clear_calibration

class ViscometryWebInterface:
    def __init__(self, port=5001):
        # Set template and static folder paths relative to project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.project_root = project_root
        template_folder = os.path.join(project_root, 'templates')
        static_folder = os.path.join(project_root, 'static')
        
        self.app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
        self.app.config['SECRET_KEY'] = 'viscometry_secret_key'
        # Disable static-file caching in this dev/lab server so refreshes always
        # pull the latest app.js / style.css. Browsers were holding onto stale
        # JS that prevented persisted state from being restored after refresh.
        self.app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

        # Compute a per-process asset version (mtime of app.js) so templates can
        # append ?v=<version> for cache-busting in case a proxy still caches.
        try:
            _js_path = os.path.join(static_folder, 'js', 'app.js')
            self._asset_version = str(int(os.path.getmtime(_js_path)))
        except Exception:
            self._asset_version = str(int(time.time()))
        self.socketio = SocketIO(
            self.app,
            cors_allowed_origins="*",
            async_mode="threading",
            ping_timeout=60,
            ping_interval=25,
            logger=True,
            engineio_logger=True,
        )
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
        self.experiment_start_ts: Optional[float] = None
        self.current_cell_start_ts: Optional[float] = None
        self.completed_cells: List[int] = []
        self.status_message = "Ready"
        self.control_lock = threading.Lock()
        self.start_requested_event = threading.Event()
        self.stop_requested_event = threading.Event()
        self.experiment_history_path = os.path.join(self.project_root, 'results', 'web_experiment_history.json')
        self.experiment_history = []
        self._load_experiment_history()
        # Predicted viscosity results for current run (persisted in-memory so clients see them on refresh)
        # Structure: { cell_id (int): { rpm (float): { 'viscosity_kcP': float|None, 'h0': float|None, 'heights': list, 'drags': list } } }
        self.predicted_viscosity_results: Dict[int, Dict[float, Dict]] = {}
        self.runtime_settings = {
            'experiment_name': '',
            'testing_mode': 'custom',
            'selected_rows': [2],
            'selected_cells': [1],
            'test_rpms': [0.8],
            'cell_rpm_map': {},
            'cell_content_map': {},
            'z_step_size': -0.02,
            'measurement_duration': 40.0,
            'sample_interval': 5.0,
            'dwell_seconds': 2.0,
            'inter_rpm_pause': 2.0,
            'feedback_control_enabled': True,
            'smart_early_exit_enabled': True,
            'smart_cv_threshold': 0.005,
            'smart_window_size': 3,
            'min_data_points_for_trend': 8,
            'r2_drag_min': 0.975,
            'r2_cv_min': 0.975,
            'r2_slope_min': 0.975,
            'hit_point_confidence_threshold': 0.8,
            'weight_2nd_deriv_drag': 0.2,
            'weight_2nd_deriv_cv': 0.2,
            'weight_2nd_deriv_slope': 0.2,
            'weight_r2_drag': 0.2,
            'weight_r2_cv': 0.2,
            'weight_r2_slope': 0.2,
            'baseline_n_calibration': 10,
            'baseline_z_threshold': 5.0,
            'torque_break_threshold': 100.0,
            'calibration_mode': False,
            'recalibrate_individual_cells': False,
            'recalibration_cells': {},
            # Regular runs only: skip Z-levels when torque (first sample at elapsed >= SAMPLE_INTERVAL) is below threshold.
            'low_torque_liquid_contact_skip_enabled': True,
            'low_torque_liquid_contact_threshold_pct': 25.0,
            # Feature toggles
            'predicted_viscosity_enabled': False,
        }
        # ========== Calibration state ==========
        self.calibration_mode = False         # True when a calibration run is active
        self._calibration_summary = {}        # Cached summary from last calibration check
        self._refresh_calibration_summary()   # Populate on startup

        # ========== State heartbeat ==========
        # Periodically broadcast the FULL status dict to all connected clients.
        # During an active run, the server emits many incremental events
        # (new_measurement, torque_update, rpm_update, position_update, etc.)
        # but no single periodic full-state snapshot — so a client that misses
        # an event (refresh mid-run, remote viewer joining late, transient
        # websocket buffer drop under GIL pressure) could drift out of sync.
        # This heartbeat guarantees every client reconverges within ~2 seconds.
        self._heartbeat_interval_s = 2.0
        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread: Optional[threading.Thread] = None
        
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
            return render_template('index.html', asset_version=self._asset_version)

        @self.app.after_request
        def _no_cache_static(response):
            # Force-revalidate all /static/* responses so refreshes can never
            # render with a stale app.js or style.css.
            try:
                if request.path.startswith('/static/'):
                    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                    response.headers['Pragma'] = 'no-cache'
                    response.headers['Expires'] = '0'
            except Exception:
                pass
            return response
            
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
                'experiment_start_ts': self.experiment_start_ts,
                'current_cell_start_ts': self.current_cell_start_ts,
                'completed_cells': self.completed_cells,
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
            try:
                return jsonify(self.measurement_data)
            except Exception as e:
                print(f"Error in get_measurement_data: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/predicted_viscosity_results', methods=['GET'])
        def api_predicted_viscosity_results():
            try:
                return jsonify(self._serialize_viscosity_results())
            except Exception as e:
                print(f"Error in api_predicted_viscosity_results: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/control_settings', methods=['GET', 'POST'])
        def control_settings():
            try:
                if request.method == 'GET':
                    return jsonify(self.get_runtime_settings())

                payload = request.get_json(silent=True) or {}
                settings = self.update_runtime_settings(payload)
                return jsonify(settings)
            except Exception as e:
                print(f"Error in control_settings: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/run/start', methods=['POST'])
        def api_run_start():
            try:
                payload = request.get_json(silent=True) or {}
                if payload:
                    self.update_runtime_settings(payload)
                self.request_start()
                self.update_status('Start command received from web interface')
                return jsonify({'ok': True, 'status_message': self.status_message})
            except Exception as e:
                print(f"Error in api_run_start: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/run/stop', methods=['POST'])
        def api_run_stop():
            try:
                self.request_stop()
                self.update_status('Stop command received from web interface')
                return jsonify({'ok': True, 'status_message': self.status_message})
            except Exception as e:
                print(f"Error in api_run_stop: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/experiment_history', methods=['GET', 'POST'])
        def experiment_history():
            try:
                if request.method == 'GET':
                    return jsonify(self.get_experiment_history())

                payload = request.get_json(silent=True) or {}
                self.add_experiment_history_entry(payload)
                return jsonify({'ok': True})
            except Exception as e:
                print(f"Error in experiment_history: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/experiment_history/<experiment_id>', methods=['DELETE'])
        def experiment_history_delete(experiment_id):
            try:
                removed = self.delete_experiment_history_entry(experiment_id)
                return jsonify({'ok': removed})
            except Exception as e:
                print(f"Error in experiment_history_delete: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/calibration/status', methods=['GET'])
        def calibration_status():
            try:
                self._refresh_calibration_summary()
                return jsonify(self._calibration_summary)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/calibration/clear', methods=['POST'])
        def calibration_clear():
            try:
                clear_calibration()
                self._refresh_calibration_summary()
                self.socketio.emit('calibration_status_update', self._calibration_summary)
                return jsonify({'ok': True})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/run/start_calibration', methods=['POST'])
        def api_run_start_calibration():
            try:
                payload = request.get_json(silent=True) or {}
                # Force calibration_mode flag into settings before starting
                payload['calibration_mode'] = True
                self.update_runtime_settings(payload)
                self.calibration_mode = True
                self.request_start()
                self.update_status('Calibration run started')
                return jsonify({'ok': True, 'status_message': self.status_message})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/run/start_recalibration', methods=['POST'])
        def api_run_start_recalibration():
            try:
                payload = request.get_json(silent=True) or {}
                # Force individual cell recalibration flags
                payload['recalibrate_individual_cells'] = True
                payload['calibration_mode'] = False  # Not full calibration, individual only
                self.update_runtime_settings(payload)
                self.calibration_mode = True  # Mark as in calibration-like mode for UI purposes
                self.request_start()
                self.broadcast_calibration_mode()
                self.update_status('Individual cell recalibration run started')
                return jsonify({'ok': True, 'status_message': self.status_message})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
            
        @self.socketio.on('connect')
        def handle_connect():
            try:
                emit('status_update', self.get_status_dict())
                emit('control_settings_update', self.get_runtime_settings())
                # Send current predicted viscosity snapshot so clients can populate persisted plots
                try:
                    emit('predicted_viscosity_results_snapshot', self._serialize_viscosity_results())
                except Exception:
                    pass
                # Send current calibration status
                try:
                    self._refresh_calibration_summary()
                    emit('calibration_status_update', self._calibration_summary)
                except Exception:
                    pass
            except Exception as e:
                print(f"Error in handle_connect: {e}")
                try:
                    emit('error', {'message': str(e)})
                except:
                    pass

        @self.socketio.on('update_control_settings')
        def handle_update_control_settings(payload):
            try:
                settings = self.update_runtime_settings(payload or {})
                emit('control_settings_update', settings, broadcast=True)
            except Exception as e:
                print(f"Error in handle_update_control_settings: {e}")
                try:
                    emit('error', {'message': str(e)})
                except:
                    pass

        @self.socketio.on('start_run')
        def handle_start_run(payload=None):
            try:
                if isinstance(payload, dict) and payload:
                    self.update_runtime_settings(payload)
                self.request_start()
                emit('status_update', {'status_message': 'Start command received from web interface'}, broadcast=True)
            except Exception as e:
                print(f"Error in handle_start_run: {e}")
                try:
                    emit('error', {'message': str(e)})
                except:
                    pass

        @self.socketio.on('stop_run')
        def handle_stop_run():
            try:
                self.request_stop()
                emit('status_update', {'status_message': 'Stop command received from web interface'}, broadcast=True)
            except Exception as e:
                print(f"Error in handle_stop_run: {e}")
                try:
                    emit('error', {'message': str(e)})
                except:
                    pass
            
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
        """Get current status as dictionary.

        Returns shallow *snapshot* copies of mutable containers (measurement_data,
        instrument_status, completed_cells, calibration_summary) so the run loop
        can keep mutating them while SocketIO/Flask serialize this dict to JSON.
        Without this, an occasional 'dict changed size during iteration' inside
        the JSON serializer would silently drop the heartbeat broadcast, which is
        what was causing the calibration pill and live-history to fail to persist
        across refresh during an active run.
        """
        try:
            runtime = self.get_runtime_settings()
            recalibration_cells = runtime.get('recalibration_cells') if isinstance(runtime, dict) else {}
            recalibration_target_count = len(recalibration_cells) if isinstance(recalibration_cells, dict) else 0
            recalibration_mode_active = bool(self.calibration_mode and runtime.get('recalibrate_individual_cells', False))

            # Take snapshots of mutable structures under the lock where possible.
            try:
                instrument_status_snap = dict(self.instrument_status)
            except Exception:
                instrument_status_snap = {'cnc': False, 'viscometer': False, 'pump': False}
            try:
                with self.control_lock:
                    measurement_snap = list(self.measurement_data)
                    completed_cells_snap = list(self.completed_cells)
            except Exception:
                measurement_snap = []
                completed_cells_snap = []
            try:
                calibration_summary_snap = dict(self._calibration_summary) if isinstance(self._calibration_summary, dict) else {}
            except Exception:
                calibration_summary_snap = {}

            return {
                'position': dict(self.current_position) if isinstance(self.current_position, dict) else self.current_position,
                'current_cell': self.current_cell,
                'current_rpm': self.current_rpm,
                'current_torque_percent': self.current_torque_percent,
                'current_z_measuring': self.current_z_measuring,
                'instrument_status': instrument_status_snap,
                'is_running': self.is_running,
                'experiment_start_ts': self.experiment_start_ts,
                'current_cell_start_ts': self.current_cell_start_ts,
                'completed_cells': completed_cells_snap,
                'status_message': self.status_message,
                'measurement_data': measurement_snap,
                'control_settings': runtime
                ,
                'calibration_summary': calibration_summary_snap,
                'calibration_mode': self.calibration_mode,
                'recalibration_mode_active': recalibration_mode_active,
                'recalibration_target_count': recalibration_target_count,
                'predicted_viscosity_results': self._serialize_viscosity_results(),
            }
        except Exception as e:
            print(f"Error in get_status_dict: {e}")
            # IMPORTANT: never zero-blank calibration_summary / measurement_data /
            # instrument_status in the fallback. Doing so causes the periodic
            # heartbeat broadcast to push a 'not calibrated, no measurements'
            # snapshot to every client, blanking their UI state. Return cached
            # snapshots instead so clients keep displaying real state.
            try:
                cached_instr = dict(self.instrument_status)
            except Exception:
                cached_instr = {'cnc': False, 'viscometer': False, 'pump': False}
            try:
                cached_cal = dict(self._calibration_summary) if isinstance(self._calibration_summary, dict) else {
                    'is_calibrated': False, 'calibrated_at': None, 'cell_count': 0,
                    'cell_calibrated_at': {}, 'cells': {}
                }
            except Exception:
                cached_cal = {'is_calibrated': False, 'calibrated_at': None, 'cell_count': 0, 'cell_calibrated_at': {}, 'cells': {}}
            try:
                cached_measurements = list(self.measurement_data)
            except Exception:
                cached_measurements = []
            try:
                cached_completed = list(self.completed_cells)
            except Exception:
                cached_completed = []
            return {
                'position': self.current_position,
                'current_cell': self.current_cell,
                'current_rpm': self.current_rpm,
                'current_torque_percent': self.current_torque_percent,
                'current_z_measuring': self.current_z_measuring,
                'instrument_status': cached_instr,
                'is_running': self.is_running,
                'experiment_start_ts': self.experiment_start_ts,
                'current_cell_start_ts': self.current_cell_start_ts,
                'completed_cells': cached_completed,
                'status_message': f"Error building status: {str(e)[:100]}",
                'measurement_data': cached_measurements,
                'control_settings': {}
                ,
                'calibration_summary': cached_cal,
                'calibration_mode': self.calibration_mode,
                'recalibration_mode_active': False,
                'recalibration_target_count': 0,
                'predicted_viscosity_results': {},
            }

    def _serialize_viscosity_results(self) -> Dict:
        """Return a JSON-safe copy of predicted viscosity results with string keys.

        Converts int cell ids and float RPM keys to strings so they serialize cleanly.
        """
        try:
            with self.control_lock:
                out = {}
                for cell_id, rpm_map in (self.predicted_viscosity_results or {}).items():
                    try:
                        cell_key = str(int(cell_id))
                    except Exception:
                        cell_key = str(cell_id)
                    out[cell_key] = {}
                    for rpm_key, vals in (rpm_map or {}).items():
                        try:
                            rpm_str = str(float(rpm_key))
                        except Exception:
                            rpm_str = str(rpm_key)
                        out[cell_key][rpm_str] = {
                            'viscosity_kcP': None if vals.get('viscosity_kcP') is None else float(vals.get('viscosity_kcP')),
                            'h0': None if vals.get('h0') is None else float(vals.get('h0')),
                            'heights': list(vals.get('heights') or []),
                            'drags': list(vals.get('drags') or []),
                        }
                return out
        except Exception:
            return {}

    def get_runtime_settings(self) -> Dict:
        """Get a copy of the current runtime settings."""
        with self.control_lock:
            settings = {}
            for key, value in self.runtime_settings.items():
                try:
                    if isinstance(value, list):
                        settings[key] = value[:]  # Shallow copy of list
                    elif isinstance(value, dict):
                        settings[key] = dict(value)  # Shallow copy of dict
                    else:
                        settings[key] = value  # Direct assignment for primitives
                except Exception as e:
                    print(f"Warning: Failed to copy runtime setting '{key}': {e}")
                    settings[key] = value  # Fallback to direct assignment
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
            if 'experiment_name' in settings:
                normalized['experiment_name'] = str(settings.get('experiment_name') or '').strip()
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
            if 'cell_content_map' in settings:
                raw_content_map = settings['cell_content_map']
                if isinstance(raw_content_map, dict):
                    parsed_content_map = {}
                    for cell_key, content_value in raw_content_map.items():
                        str_key = str(cell_key)
                        label = str(content_value or '').strip()
                        if label:
                            parsed_content_map[str_key] = label
                    normalized['cell_content_map'] = parsed_content_map
                else:
                    normalized['cell_content_map'] = {}
            float_keys = {
                'z_step_size', 'measurement_duration', 'sample_interval', 'dwell_seconds',
                'inter_rpm_pause', 'hit_point_confidence_threshold', 'torque_break_threshold',
                'smart_cv_threshold',
                'r2_drag_min', 'r2_cv_min', 'r2_slope_min',
                'weight_2nd_deriv_drag', 'weight_2nd_deriv_cv', 'weight_2nd_deriv_slope',
                'weight_r2_drag', 'weight_r2_cv', 'weight_r2_slope',
                'baseline_z_threshold',
            }
            int_keys = {'min_data_points_for_trend', 'baseline_n_calibration', 'smart_window_size'}
            for key in [
                'z_step_size', 'measurement_duration', 'sample_interval', 'dwell_seconds',
                'inter_rpm_pause', 'min_data_points_for_trend',
                'smart_cv_threshold', 'smart_window_size',
                'r2_drag_min', 'r2_cv_min', 'r2_slope_min', 'hit_point_confidence_threshold',
                'torque_break_threshold',
                'weight_2nd_deriv_drag', 'weight_2nd_deriv_cv', 'weight_2nd_deriv_slope',
                'weight_r2_drag', 'weight_r2_cv', 'weight_r2_slope',
                'baseline_n_calibration', 'baseline_z_threshold',
            ]:
                if key in settings and settings[key] not in (None, ''):
                    if key in float_keys:
                        normalized[key] = float(settings[key])
                    else:
                        normalized[key] = int(settings[key])
            if 'feedback_control_enabled' in settings:
                normalized['feedback_control_enabled'] = bool(settings['feedback_control_enabled'])
            if 'smart_early_exit_enabled' in settings:
                normalized['smart_early_exit_enabled'] = bool(settings['smart_early_exit_enabled'])
            if 'predicted_viscosity_enabled' in settings:
                normalized['predicted_viscosity_enabled'] = bool(settings['predicted_viscosity_enabled'])
            if 'low_torque_liquid_contact_skip_enabled' in settings:
                normalized['low_torque_liquid_contact_skip_enabled'] = bool(
                    settings['low_torque_liquid_contact_skip_enabled']
                )
            if 'low_torque_liquid_contact_threshold_pct' in settings and settings['low_torque_liquid_contact_threshold_pct'] not in (None, ''):
                normalized['low_torque_liquid_contact_threshold_pct'] = float(
                    settings['low_torque_liquid_contact_threshold_pct']
                )
            if 'calibration_mode' in settings:
                normalized['calibration_mode'] = bool(settings['calibration_mode'])
            if 'recalibrate_individual_cells' in settings:
                normalized['recalibrate_individual_cells'] = bool(settings['recalibrate_individual_cells'])
            if 'recalibration_cells' in settings:
                raw_cells = settings['recalibration_cells']
                if isinstance(raw_cells, dict):
                    parsed_cells = {}
                    for cell_key, starting_z in raw_cells.items():
                        try:
                            normalized_key = str(int(cell_key))
                        except Exception:
                            continue
                        if starting_z in (None, ''):
                            parsed_cells[normalized_key] = None
                        else:
                            try:
                                parsed_cells[normalized_key] = float(starting_z)
                            except Exception:
                                parsed_cells[normalized_key] = None
                    normalized['recalibration_cells'] = parsed_cells
                else:
                    normalized['recalibration_cells'] = {}

            self.runtime_settings = normalized
            # Mirror calibration_mode into instance state
            try:
                self.calibration_mode = bool(normalized.get('calibration_mode', False))
            except Exception:
                self.calibration_mode = False

        return self.get_runtime_settings()

    def _refresh_calibration_summary(self):
        """Re-read calibration file and cache the summary."""
        try:
            self._calibration_summary = get_calibration_summary()
        except Exception as e:
            print(f"Warning: failed to read calibration summary: {e}")
            self._calibration_summary = {
                "is_calibrated": False,
                "calibrated_at": None,
                "cell_count": 0,
                "cell_calibrated_at": {},
                "cells": {}
            }

    def emit_calibration_complete(self, summary: dict):
        """Broadcast calibration completion to all connected clients."""
        try:
            self._calibration_summary = summary
            self.socketio.emit('calibration_complete', summary)
        except Exception as e:
            print(f"Warning: failed to emit calibration complete: {e}")

    def request_start(self):
        """Mark that the experiment should start."""
        self.stop_requested_event.clear()
        self.experiment_start_ts = time.time()
        self.current_cell_start_ts = None
        self.completed_cells = []
        self.start_requested_event.set()
        self.socketio.emit('experiment_start', {'start_ts': self.experiment_start_ts})
        self.broadcast_calibration_mode()

    def broadcast_calibration_mode(self):
        """Broadcast current calibration mode to all connected clients."""
        runtime = self.get_runtime_settings()
        recalibration_cells = runtime.get('recalibration_cells') if isinstance(runtime, dict) else {}
        recalibration_target_count = len(recalibration_cells) if isinstance(recalibration_cells, dict) else 0
        recalibration_mode_active = bool(self.calibration_mode and runtime.get('recalibrate_individual_cells', False))
        self.socketio.emit('calibration_mode_update', {
            'calibration_mode': self.calibration_mode,
            'completed_cells': self.completed_cells,
            'recalibration_mode_active': recalibration_mode_active,
            'recalibration_target_count': recalibration_target_count,
        })

    def request_stop(self):
        """Mark that the experiment should stop."""
        self.stop_requested_event.set()
        self.set_running_state(False)
        self.calibration_mode = False
        self.broadcast_calibration_mode()

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
        self.current_cell_start_ts = time.time() if cell_id is not None else None
        self.socketio.emit('cell_update', {'current_cell': cell_id})

    def add_completed_cell(self, cell_id: int):
        """Track a cell as fully completed (including wash) for refresh-safe progress."""
        try:
            normalized = int(cell_id)
        except (TypeError, ValueError):
            return
        if normalized not in self.completed_cells:
            self.completed_cells.append(normalized)
        runtime = self.get_runtime_settings()
        recalibration_cells = runtime.get('recalibration_cells') if isinstance(runtime, dict) else {}
        recalibration_target_count = len(recalibration_cells) if isinstance(recalibration_cells, dict) else 0
        recalibration_mode_active = bool(self.calibration_mode and runtime.get('recalibrate_individual_cells', False))
        self.socketio.emit('completed_cells_update', {
            'completed_cells': self.completed_cells,
            'recalibration_mode_active': recalibration_mode_active,
            'recalibration_target_count': recalibration_target_count,
        })
        
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

    def emit_feedback_metrics(
        self, rpm: float,
        second_derivative_drag, second_derivative_cv, second_derivative_slope,
        trend_r_squared: float,
        moving_r2_cv, moving_r2_slope,
        hit_confidence: float, hit_detected: bool,
        drag_sd2_calibrated: bool, cv_sd2_calibrated: bool, slope_sd2_calibrated: bool
        , predicted_viscosity: Optional[float] = None, predicted_viscosity_h0: Optional[float] = None
    ):
        """Emit latest feedback controller metrics for a single RPM to the sidebar."""
        self.socketio.emit('feedback_metrics_update', {
            'rpm': rpm,
            'second_derivative_drag': second_derivative_drag,
            'second_derivative_cv': second_derivative_cv,
            'second_derivative_slope': second_derivative_slope,
            'trend_r_squared': trend_r_squared,
            'moving_r2_cv': moving_r2_cv,
            'moving_r2_slope': moving_r2_slope,
            'hit_confidence': hit_confidence,
            'hit_detected': hit_detected,
            'drag_sd2_calibrated': drag_sd2_calibrated,
            'cv_sd2_calibrated': cv_sd2_calibrated,
            'slope_sd2_calibrated': slope_sd2_calibrated,
            'predicted_viscosity': predicted_viscosity,
            'predicted_viscosity_h0': predicted_viscosity_h0,
        })

    def emit_predicted_viscosity_plot(
        self, cell_id: int, rpm: float, viscosity_kcP: float, 
        heights: List[float], drags: List[float], h0: Optional[float] = None
    ):
        """Emit plot data for predicted viscosity visualization."""
        self.socketio.emit('predicted_viscosity_plot_data', {
            'cell_id': cell_id,
            'rpm': rpm,
            'viscosity_kcP': viscosity_kcP,
            'h0': h0,
            'heights': heights,
            'drags': drags,
        })
        # Store result in in-memory state so it survives page refresh and is available to all clients
        try:
            cell_key = int(cell_id)
        except Exception:
            try:
                cell_key = int(float(cell_id))
            except Exception:
                return
        try:
            rpm_key = float(rpm)
        except Exception:
            try:
                rpm_key = float(str(rpm))
            except Exception:
                rpm_key = rpm

        with self.control_lock:
            if cell_key not in self.predicted_viscosity_results:
                self.predicted_viscosity_results[cell_key] = {}
            self.predicted_viscosity_results[cell_key][rpm_key] = {
                'viscosity_kcP': None if viscosity_kcP is None else float(viscosity_kcP),
                'h0': None if h0 is None else float(h0),
                'heights': list(heights) if heights is not None else [],
                'drags': list(drags) if drags is not None else [],
            }

    def clear_run_data(self):
        """Clear the current run's dashboard data and notify connected clients."""
        with self.control_lock:
            self.measurement_data = []
            self.current_cell = None
            self.current_rpm = 0
            self.current_torque_percent = 0.0
            self.current_z_measuring = None
            self.current_cell_start_ts = None
            self.completed_cells = []
            # Clear predicted viscosity state for the run
            self.predicted_viscosity_results = {}
        self.socketio.emit('clear_dashboard')
        # Notify clients that predicted viscosity results have been cleared
        try:
            self.socketio.emit('clear_predicted_viscosity')
        except Exception:
            pass

    def _load_experiment_history(self):
        """Load shared experiment history from disk if available."""
        try:
            os.makedirs(os.path.dirname(self.experiment_history_path), exist_ok=True)
            if os.path.exists(self.experiment_history_path):
                with open(self.experiment_history_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.experiment_history = data if isinstance(data, list) else []
            else:
                self.experiment_history = []
        except Exception as e:
            print(f"Warning: Failed to load experiment history: {e}")
            self.experiment_history = []

    def _persist_experiment_history(self):
        """Persist shared experiment history to disk."""
        try:
            os.makedirs(os.path.dirname(self.experiment_history_path), exist_ok=True)
            with open(self.experiment_history_path, 'w', encoding='utf-8') as f:
                json.dump(self.experiment_history, f, ensure_ascii=True, indent=2)
        except Exception as e:
            print(f"Warning: Failed to persist experiment history: {e}")

    def get_experiment_history(self):
        """Return a shallow copy of shared experiment history."""
        with self.control_lock:
            return list(self.experiment_history)

    def add_experiment_history_entry(self, entry: Dict):
        """Add or update an experiment history entry and persist it."""
        if not isinstance(entry, dict):
            return
        exp_id = str(entry.get('id') or '').strip()
        if not exp_id:
            return

        with self.control_lock:
            self.experiment_history = [e for e in self.experiment_history if str(e.get('id')) != exp_id]
            self.experiment_history.insert(0, entry)
            self.experiment_history = self.experiment_history[:200]
            self._persist_experiment_history()

    def delete_experiment_history_entry(self, experiment_id: str) -> bool:
        """Delete an experiment history entry by id and persist changes."""
        with self.control_lock:
            before = len(self.experiment_history)
            self.experiment_history = [
                e for e in self.experiment_history
                if str(e.get('id')) != str(experiment_id)
            ]
            removed = len(self.experiment_history) != before
            if removed:
                self._persist_experiment_history()
            return removed
        
    def add_measurement_point(
        self,
        height: float,
        rotational_drag: float,
        rpm: float,
        cell_id: int,
        hit_detected: Optional[bool] = None,
        sample_count: int = 1,
    ):
        """Add a new measurement point.

        sample_count: viscometer torque samples represented by this point (e.g. one live
        stream row = 1; a single summary row for an RPM dwell = number of reads in that dwell).
        """
        try:
            # Sanitize rotational_drag: replace inf with None for JSON serialization
            safe_drag = None if (isinstance(rotational_drag, float) and math.isinf(rotational_drag)) else rotational_drag
            
            # Sanitize torque calculation to handle potential inf
            torque_calc = safe_drag * rpm if safe_drag is not None else None
            
            try:
                sc = int(sample_count)
            except (TypeError, ValueError):
                sc = 1
            if sc < 1:
                sc = 1

            measurement = {
                'timestamp': time.time(),
                'height': height,
                'rotational_drag': safe_drag,
                'torque_percent': torque_calc,
                'rpm': rpm,
                'cell_id': cell_id,
                'hit_detected': bool(hit_detected) if hit_detected is not None else None,
                'sample_count': sc,
            }
            self.measurement_data.append(measurement)
            
            # Emit to connected clients
            try:
                self.socketio.emit('new_measurement', measurement)
            except Exception as emit_error:
                print(f"Warning: Failed to emit measurement: {emit_error}")
        except Exception as e:
            print(f"Error in add_measurement_point: {e}")

    def calculate_predicted_viscosity(self, measurements, hitpoint_z=None, torque_floor=25.0, m_hyp=2.330):
        """Calculate predicted viscosity using hyperbola fitting.
        
        Matches the logic from viscosity_pipeline_helper.py

        Parameters:
            measurements: iterable of measurement dicts with 'height', 'rotational_drag', 'torque_percent'
            hitpoint_z: Z-height where liquid contact is detected (if None, uses oldest measurement as reference)
            torque_floor: Minimum torque percentage threshold for inclusion (default 25.0)
            m_hyp: Scaling factor for converting hyperbola parameter a to viscosity (kcP) - default 2.330

        Returns:
            (viscosity_kcP, offset_b, (trimmed_heights, trimmed_drags)) on success, or
            (None, None, ([], [])) on failure
        """
        try:
            import numpy as _np
            from scipy.optimize import curve_fit as _curve_fit
        except Exception:
            return None, None, ([], [])

        if not measurements or len(measurements) < 3:
            return None, None, ([], [])

        # Filter: only pre-hitpoint with sufficient torque
        filtered = []
        for m in measurements:
            try:
                z = float(m.get('height', 0))
                drag = float(m.get('rotational_drag', 0))
                torque = float(m.get('torque_percent', 0))
            except (ValueError, TypeError):
                continue

            # Must pass torque floor
            if torque <= torque_floor:
                continue

            # If hitpoint_z is specified, only include pre-hitpoint (z < hitpoint_z)
            if hitpoint_z is not None and z >= hitpoint_z:
                continue

            filtered.append((z, drag))

        if len(filtered) < 3:
            return None, None, ([], [])

        heights = _np.array([f[0] for f in filtered], dtype=float)
        drags = _np.array([f[1] for f in filtered], dtype=float)

        # If hitpoint_z specified, check Z-span and potentially trim to 0.3mm window
        if hitpoint_z is not None:
            z_max = _np.max(heights)
            z_min = _np.min(heights)
            z_span = z_max - z_min

            if z_span > 0.3:
                # Trim to only points within 0.3mm above hitpoint
                cutoff_z = hitpoint_z + 0.3
                mask = heights <= cutoff_z
                if _np.sum(mask) >= 3:
                    heights = heights[mask]
                    drags = drags[mask]

        if len(heights) < 3:
            return None, None, ([], [])

        # Fit hyperbola: y = a / (x - b) from viscosity_pipeline_helper
        def _hyperbola(x, a, b):
            return a / (x - b)

        try:
            # Initial guesses matching viscosity_pipeline_helper
            x_min = float(_np.min(heights))
            x_range = float(_np.ptp(heights))
            b_guess = x_min - 0.5 * max(x_range, 1e-6)
            a_guess = float((drags[0] - drags[-1]) * max(x_range, 1e-6))

            lower_b = x_min - 5.0 * max(x_range, 1e-6)
            upper_b = x_min - 1e-6

            popt, pcov = _curve_fit(
                _hyperbola,
                heights,
                drags,
                p0=[a_guess, b_guess],
                bounds=([-_np.inf, lower_b], [_np.inf, upper_b]),
                maxfev=5000,
            )

            a, b = float(popt[0]), float(popt[1])
            viscosity_kcP = abs(a) * m_hyp

            return viscosity_kcP, b, (list(heights), list(drags))

        except RuntimeError:
            return None, None, (list(heights), list(drags))
        except Exception:
            return None, None, ([], [])
        
    def set_running_state(self, is_running: bool):
        """Set running state"""
        previous_state = self.is_running
        self.is_running = is_running
        if not is_running:
            self.experiment_start_ts = None
            self.current_cell_start_ts = None
            if previous_state:
                self.socketio.emit('experiment_stop', {})
        if previous_state != is_running:
            self.socketio.emit('running_state_update', {'is_running': is_running})
        # If a calibration run just stopped, clear calibration_mode and refresh status
        if not is_running and self.calibration_mode:
            self.calibration_mode = False
            try:
                self._refresh_calibration_summary()
                self.socketio.emit('calibration_status_update', self._calibration_summary)
            except Exception:
                pass
        
    def _status_heartbeat_loop(self):
        """Background thread: broadcast full status snapshot every N seconds.

        This is intentionally robust: any exception is swallowed so a single
        bad snapshot can't kill the heartbeat. Clients re-converge to the
        authoritative server state on the next tick.
        """
        while not self._heartbeat_stop.is_set():
            try:
                snapshot = self.get_status_dict()
                # Also refresh and include calibration summary so the per-cell
                # Z-height pill never drifts to red on a connected client.
                try:
                    self._refresh_calibration_summary()
                    snapshot['calibration_summary'] = self._calibration_summary
                except Exception:
                    pass
                self.socketio.emit('status_update', snapshot)
                # Also re-broadcast instrument status so pills stay accurate
                # even if the original instrument_status_update was lost.
                try:
                    self.socketio.emit('instrument_status_update', self.instrument_status)
                except Exception:
                    pass
            except Exception as e:
                print(f"Warning: status heartbeat failed: {e}")
            # Sleep on the Event so shutdown is responsive
            self._heartbeat_stop.wait(self._heartbeat_interval_s)

    def start_server(self, debug=False):
        """Start the web server"""
        print(f"Starting Viscometry Web Interface on http://localhost:{self.port}")
        # Launch state heartbeat once, before the server starts blocking.
        if self._heartbeat_thread is None or not self._heartbeat_thread.is_alive():
            self._heartbeat_stop.clear()
            self._heartbeat_thread = threading.Thread(
                target=self._status_heartbeat_loop,
                daemon=True,
                name="status-heartbeat",
            )
            self._heartbeat_thread.start()
        self.socketio.run(self.app, host='0.0.0.0', port=self.port, debug=debug, allow_unsafe_werkzeug=True)
        
    def start_in_thread(self, debug=False):
        """Start web server in background thread"""
        thread = threading.Thread(target=self.start_server, args=(debug,), daemon=True)
        thread.start()
        return thread

# Global instance for easy access
web_interface = ViscometryWebInterface(port=5001)

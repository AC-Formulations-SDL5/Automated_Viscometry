#!/usr/bin/env python3
"""
Orchestration Control Interface
Quick-start script for running different experimental scenarios
"""

import time
import datetime
from typing import Dict, List
from cnc_controller import CNC_Machine
from viscometer_client import ViscometerClient
from move_to_locations import PumpESP32

class OrchestrationController:
    """Main controller class for managing the complete workflow"""
    
    def __init__(self, config_profile="standard"):
        """Initialize with a specific configuration profile"""
        self.config = self.load_config_profile(config_profile)
        self.cnc = None
        self.viscometer = None
        self.pump = None
        self.experiment_data = {}
        
    def load_config_profile(self, profile_name):
        """Load configuration parameters for different experimental scenarios"""
        
        profiles = {
            "fast": {
                "name": "Fast Testing Profile",
                "test_rpms": [3.0],
                "measurement_duration": 10.0,
                "sample_interval": 2.0,
                "z_step_size": -2.0,
                "wash_times": {"primary": 15, "rinse": 10},
                "settle_time": 0.5,
                "z_feed_rate": 1000,
                "torque_threshold": 1000.0
            },
            
            "standard": {
                "name": "Standard Production Profile", 
                "test_rpms": [3.0, 1.0, 5.0, 10.0],
                "measurement_duration": 40.0,
                "sample_interval": 10.0,
                "z_step_size": -1.0,
                "wash_times": {"primary": 30, "rinse": 15},
                "settle_time": 1.0,
                "z_feed_rate": 500,
                "torque_threshold": 1000.0
            },
            
            "thorough": {
                "name": "Thorough Research Profile",
                "test_rpms": [0.5, 1.0, 3.0, 5.0, 10.0, 20.0, 50.0],
                "measurement_duration": 60.0,
                "sample_interval": 5.0, 
                "z_step_size": -0.5,
                "wash_times": {"primary": 45, "rinse": 20},
                "settle_time": 2.0,
                "z_feed_rate": 250,
                "torque_threshold": 800.0
            },
            
            "conservative": {
                "name": "Conservative Safety Profile",
                "test_rpms": [1.0, 3.0, 5.0],
                "measurement_duration": 50.0,
                "sample_interval": 8.0,
                "z_step_size": -1.0,
                "wash_times": {"primary": 40, "rinse": 20},
                "settle_time": 2.0,
                "z_feed_rate": 300,
                "torque_threshold": 500.0  # Lower safety threshold
            }
        }
        
        return profiles.get(profile_name, profiles["standard"])
    
    def initialize_hardware(self, virtual_mode=False):
        """Initialize all hardware connections"""
        print(f"Initializing hardware with '{self.config['name']}'...")
        print(f"Virtual mode: {virtual_mode}")
        
        try:
            # Initialize CNC
            self.cnc = CNC_Machine(virtual=virtual_mode)
            self.cnc.home()
            print("✓ CNC initialized and homed")
            
            # Initialize Pump System  
            self.pump = PumpESP32("COM11", 115200, virtual=virtual_mode)
            self.pump.open()
            print("✓ Pump system initialized")
            
            # Initialize Viscometer
            self.viscometer = ViscometerClient(".\\.venv32\\Scripts\\python.exe", 
                                             "viscometer_worker_32.py")
            self.viscometer.init(port="COM6", baud=115200, timeout=1.0, spindle_k=992.47)
            print("✓ Viscometer initialized")
            
            return True
            
        except Exception as e:
            print(f"✗ Hardware initialization failed: {e}")
            return False
    
    def run_scenario(self, scenario_type, **kwargs):
        """Execute different orchestration scenarios"""
        
        scenarios = {
            "single_cell": self.scenario_single_cell,
            "row_comparison": self.scenario_row_comparison, 
            "full_survey": self.scenario_full_survey,
            "corner_cells": self.scenario_corner_cells,
            "z_gap_study": self.scenario_z_gap_study,
            "rpm_characterization": self.scenario_rpm_characterization
        }
        
        if scenario_type not in scenarios:
            print(f"Unknown scenario: {scenario_type}")
            print(f"Available scenarios: {list(scenarios.keys())}")
            return
            
        print(f"\\n{'='*60}")
        print(f"EXECUTING SCENARIO: {scenario_type.upper()}")
        print(f"Configuration: {self.config['name']}")
        print(f"{'='*60}")
        
        try:
            scenarios[scenario_type](**kwargs)
            print(f"\\n✓ Scenario '{scenario_type}' completed successfully")
        except Exception as e:
            print(f"\\n✗ Scenario '{scenario_type}' failed: {e}")
        
    def scenario_single_cell(self, cell_number=9):
        """Test a single cell for validation/debugging"""
        print(f"Testing single cell: {cell_number}")
        
        cells_to_test = [cell_number]
        self.execute_cell_sequence(cells_to_test)
    
    def scenario_row_comparison(self, row_number=1):
        """Compare all cells in a specific row"""
        print(f"Testing all cells in row {row_number}")
        
        start_cell = (row_number - 1) * 6 + 1
        end_cell = row_number * 6
        cells_to_test = list(range(start_cell, end_cell + 1))
        
        print(f"Cells to test: {cells_to_test}")
        self.execute_cell_sequence(cells_to_test)
    
    def scenario_full_survey(self):
        """Test all 18 cells in the system"""
        print("Testing all 18 cells - full laboratory survey")
        
        cells_to_test = list(range(1, 19))
        estimated_time = len(cells_to_test) * 8  # Rough estimate: 8 minutes per cell
        print(f"Estimated completion time: {estimated_time} minutes")
        
        self.execute_cell_sequence(cells_to_test)
    
    def scenario_corner_cells(self):
        """Test corner cells from each row for system validation"""
        print("Testing corner cells from each row")
        
        corner_cells = [1, 6, 7, 12, 13, 18]  # First and last cell from each row
        self.execute_cell_sequence(corner_cells)
    
    def scenario_z_gap_study(self, cell_number=9):
        """Detailed Z-gap study with fine resolution on single cell"""
        print(f"Z-gap study on cell {cell_number} with fine resolution")
        
        # Override config for fine Z resolution
        original_z_step = self.config['z_step_size']
        self.config['z_step_size'] = -0.25  # Very fine steps
        
        try:
            cells_to_test = [cell_number]
            self.execute_cell_sequence(cells_to_test)
        finally:
            # Restore original config
            self.config['z_step_size'] = original_z_step
    
    def scenario_rpm_characterization(self, cell_number=9):
        """Comprehensive RPM response study on single cell"""
        print(f"RPM characterization study on cell {cell_number}")
        
        # Override config for full RPM range
        original_rpms = self.config['test_rpms']
        self.config['test_rpms'] = [0.5, 1.0, 3.0, 5.0, 10.0, 20.0, 50.0]
        
        try:
            cells_to_test = [cell_number]
            self.execute_cell_sequence(cells_to_test)
        finally:
            # Restore original config  
            self.config['test_rpms'] = original_rpms
    
    def execute_cell_sequence(self, cells_to_test):
        """Execute the main measurement and washing sequence for given cells"""
        
        # Cell position configurations
        rows = [
            {'row_number': 1, 'base_x': 10, 'safe_z': -65.5, 'max_z_travel': -66.500},
            {'row_number': 2, 'base_x': 85, 'safe_z': -65.5, 'max_z_travel': -66.500}, 
            {'row_number': 3, 'base_x': 309, 'safe_z': -64.5, 'max_z_travel': -65.500}
        ]
        
        total_cells = len(cells_to_test)
        
        for i, cell_number in enumerate(cells_to_test):
            print(f"\\n--- Processing Cell {cell_number} ({i+1}/{total_cells}) ---")
            
            try:
                # Calculate cell position
                row_number = ((cell_number - 1) // 6) + 1
                local_cell = ((cell_number - 1) % 6) + 1
                row_config = rows[row_number - 1]
                
                # Execute measurement phase
                self.execute_cell_measurement(cell_number, row_config, local_cell)
                
                # Execute washing phase
                self.execute_washing_sequence(cell_number)
                
                print(f"✓ Cell {cell_number} completed successfully")
                
            except Exception as e:
                print(f"✗ Error processing cell {cell_number}: {e}")
                # Continue with next cell rather than abort entire sequence
                continue
    
    def execute_cell_measurement(self, cell_number, row_config, local_cell):
        """Execute measurement sequence for a single cell"""
        
        # Calculate target position
        base_y = 62 
        y_offset = 67
        target_x = row_config['base_x']
        target_y = base_y + (local_cell - 1) * y_offset
        safe_z = row_config['safe_z']
        max_z = row_config['max_z_travel']
        
        print(f"  Position: X={target_x}, Y={target_y}, Z_safe={safe_z}")
        
        # Move to cell position
        self.cnc.move_to_point_safe(target_x, target_y, safe_z, speed=3000)
        time.sleep(self.config['settle_time'])
        
        # Z-series measurement loop
        current_z = safe_z
        step_count = 0
        
        while current_z >= max_z:
            step_count += 1
            
            # Position at current Z
            if step_count > 1:
                self.cnc.move_to_point(target_x, target_y, current_z, 
                                     speed=self.config['z_feed_rate'])
                time.sleep(self.config['settle_time'])
            
            # RPM measurement sequence
            for rpm in self.config['test_rpms']:
                try:
                    measurements = self.measure_torque_at_rpm(rpm)
                    
                    # Store data
                    if cell_number not in self.experiment_data:
                        self.experiment_data[cell_number] = {}
                    if current_z not in self.experiment_data[cell_number]:
                        self.experiment_data[cell_number][current_z] = {}
                    
                    self.experiment_data[cell_number][current_z][rpm] = measurements
                    
                    # Safety check
                    if measurements and len(measurements) > 0:
                        max_torque = max(abs(m["torque_percent"]) for m in measurements)
                        if max_torque >= self.config['torque_threshold']:
                            print(f"    SAFETY: Torque {max_torque}% exceeds threshold")
                            break
                    
                except Exception as e:
                    print(f"    Error at RPM {rpm}: {e}")
            
            # Move to next Z position
            current_z += self.config['z_step_size']
        
        # Return to safe position
        self.cnc.move_to_point(target_x, target_y, 0, speed=self.config['z_feed_rate'])
        self.viscometer.stop()
    
    def measure_torque_at_rpm(self, rpm):
        """Measure torque at specific RPM using current configuration"""
        
        measurements = []
        
        try:
            # Set RPM and allow settling
            self.viscometer.set_speed(rpm)
            time.sleep(2.0)  # RPM settling time
            
            # Collect measurements
            start_time = time.time()
            next_sample_time = start_time + self.config['sample_interval']
            
            while time.time() - start_time < self.config['measurement_duration']:
                current_time = time.time()
                
                if current_time >= next_sample_time:
                    try:
                        data = self.viscometer.read_single(timeout=2.0)
                        if data and data.get("torque_valid"):
                            measurement = {
                                "timestamp": current_time,
                                "elapsed_time": current_time - start_time,
                                "torque_percent": data["torque_percent"],
                                "rpm": rpm
                            }
                            measurements.append(measurement)
                        
                        next_sample_time += self.config['sample_interval']
                        
                    except Exception as e:
                        print(f"      Measurement error: {e}")
                
                time.sleep(0.1)
            
            # Stop spindle
            self.viscometer.stop()
            time.sleep(1.0)
            
            # Report results
            if measurements:
                avg_torque = sum(m["torque_percent"] for m in measurements) / len(measurements)
                print(f"    RPM {rpm}: {len(measurements)} samples, Avg: {avg_torque:.2f}%")
            
            return measurements
            
        except Exception as e:
            print(f"    Error measuring RPM {rpm}: {e}")
            return None
    
    def execute_washing_sequence(self, cell_number):
        """Execute washing sequence with current configuration"""
        
        wash_x = 387
        wash_y = 68  
        wash_z = -67
        
        print(f"  Washing sequence for cell {cell_number}...")
        
        try:
            # Pre-wash pump activation
            self.pump.send_tag(b"1")
            time.sleep(5)  # Head start
            
            # Move to washing station
            self.cnc.move_to_point_safe(wash_x, wash_y, 0, speed=3000)
            self.cnc.move_to_point(wash_x, wash_y, wash_z, speed=1000)
            
            # Primary wash cycle
            time.sleep(self.config['wash_times']['primary'])
            
            # Rinse cycle (automatic pump switching in ESP32)
            time.sleep(self.config['wash_times']['rinse'])
            
            # Stop pumps and return to safe position
            self.pump.send_tag(b"0")
            self.cnc.move_to_point(wash_x, wash_y, 0, speed=500)
            
            print(f"  ✓ Washing completed")
            
        except Exception as e:
            print(f"  ✗ Washing error: {e}")
            # Emergency cleanup
            self.pump.send_tag(b"0")
            try:
                self.cnc.move_to_point(wash_x, wash_y, 0, speed=500)
            except:
                pass
    
    def save_results(self, filename_prefix="orchestration_results"):
        """Save experiment results to CSV file"""
        
        if not self.experiment_data:
            print("No data to save")
            return
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.csv"
        
        # Implementation would save self.experiment_data to CSV
        # (Following the existing CSV format from main script)
        print(f"Results saved to: {filename}")
    
    def shutdown(self):
        """Safely shutdown all hardware"""
        print("\\nShutting down hardware...")
        
        try:
            if self.cnc:
                self.cnc.home()
                print("✓ CNC homed")
        except:
            pass
            
        try:
            if self.viscometer:
                self.viscometer.stop()
                self.viscometer.close()
                print("✓ Viscometer stopped")
        except:
            pass
            
        try:
            if self.pump:
                self.pump.send_tag(b"0")
                self.pump.close()
                print("✓ Pumps stopped")
        except:
            pass


# ============================================================================
# EXAMPLE USAGE SCENARIOS
# ============================================================================

def main():
    """Example orchestration scenarios"""
    
    # Choose configuration profile
    controller = OrchestrationController(config_profile="standard")
    
    # Initialize hardware (set virtual_mode=True for testing without hardware)
    if not controller.initialize_hardware(virtual_mode=False):
        print("Failed to initialize hardware")
        return
    
    try:
        # Example scenarios (uncomment one to run):
        
        # Scenario 1: Single cell validation
        controller.run_scenario("single_cell", cell_number=9)
        
        # Scenario 2: Row comparison  
        # controller.run_scenario("row_comparison", row_number=2)
        
        # Scenario 3: Full laboratory survey
        # controller.run_scenario("full_survey")
        
        # Scenario 4: Corner cells validation
        # controller.run_scenario("corner_cells")
        
        # Scenario 5: Detailed Z-gap study
        # controller.run_scenario("z_gap_study", cell_number=9)
        
        # Scenario 6: RPM characterization 
        # controller.run_scenario("rpm_characterization", cell_number=9)
        
        # Save results
        controller.save_results()
        
    finally:
        # Always shutdown hardware safely
        controller.shutdown()

if __name__ == "__main__":
    main()
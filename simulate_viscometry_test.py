#!/usr/bin/env python3
"""
Simulation script for Viscometry Platform Web Interface
Simulates the complete experiment workflow without hardware
"""

import time
import random
import threading
import math
from typing import Dict, List, Tuple
import sys
import os
import pathlib

# Add the src/python_64 directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'python_64'))

from web_interface import web_interface

class ViscometrySimulator:
    def __init__(self):
        # Platform configuration (same as real system)
        self.X_LOW_BOUND = 0
        self.X_HIGH_BOUND = 450
        self.Y_LOW_BOUND = 0
        self.Y_HIGH_BOUND = 400
        self.Z_LOW_BOUND = -75
        self.Z_HIGH_BOUND = 0
        
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
        
        # Test parameters
        self.TEST_RPMS = [0.8, 1.0, 2.0, 5.0, 10.0]
        self.Z_STEP_SIZE = -0.02
        
        # Current state
        self.current_position = {'x': 0, 'y': 0, 'z': 0}
        self.is_running = False
        self.simulation_speed = 1.0  # Speed multiplier for simulation
        
    def get_cell_position(self, global_cell: int) -> Tuple[int, int, float, float]:
        """Get row, local cell, x, y for a global cell number"""
        row = ((global_cell - 1) // 6) + 1
        local_cell = ((global_cell - 1) % 6) + 1
        
        # Find row config
        row_config = None
        for r in self.ROWS:
            if r['row_number'] == row:
                row_config = r
                break
        
        x_pos = row_config['base_x']
        y_pos = self.BASE_Y + (local_cell - 1) * self.Y_OFFSET
        
        return row, local_cell, x_pos, y_pos
    
    def simulate_movement(self, target_x: float, target_y: float, target_z: float, speed: int = 3000):
        """Simulate smooth movement from current position to target"""
        start_x, start_y, start_z = self.current_position['x'], self.current_position['y'], self.current_position['z']
        
        # Calculate distance and time
        distance = math.sqrt((target_x - start_x)**2 + (target_y - start_y)**2 + (target_z - start_z)**2)
        move_time = max(distance / 100, 0.5) / self.simulation_speed  # Simulate realistic movement time
        
        # Number of steps for smooth animation
        steps = max(int(move_time * 10), 5)
        
        for i in range(steps + 1):
            progress = i / steps
            
            # Interpolate position
            current_x = start_x + (target_x - start_x) * progress
            current_y = start_y + (target_y - start_y) * progress
            current_z = start_z + (target_z - start_z) * progress
            
            # Update position
            self.current_position = {'x': current_x, 'y': current_y, 'z': current_z}
            web_interface.update_position(current_x, current_y, current_z)
            
            time.sleep(move_time / steps)
    
    def simulate_safe_movement(self, target_x: float, target_y: float, target_z: float):
        """Simulate safe movement (Z up, move XY, Z down)"""
        # Move Z to safe position
        web_interface.update_status(f"Moving to safe Z position")
        self.simulate_movement(self.current_position['x'], self.current_position['y'], self.Z_HIGH_BOUND)
        
        # Move X,Y
        web_interface.update_status(f"Moving to X={target_x:.1f}, Y={target_y:.1f}")
        self.simulate_movement(target_x, target_y, self.Z_HIGH_BOUND)
        
        # Move Z down
        web_interface.update_status(f"Moving to Z={target_z:.3f}")
        self.simulate_movement(target_x, target_y, target_z)
    
    def simulate_measurement_at_rpm(self, rpm: float, z_height: float, cell_id: int) -> List[Dict]:
        """Simulate torque measurement at specific RPM"""
        web_interface.set_current_rpm(rpm)
        web_interface.update_status(f"Measuring at {rpm} RPM")
        
        measurements = []
        measurement_duration = 4.0 / self.simulation_speed  # Shortened for demo
        sample_interval = 0.5 / self.simulation_speed
        
        start_time = time.time()
        sample_count = 0
        
        while time.time() - start_time < measurement_duration:
            # Simulate realistic torque data with some noise
            base_torque = 20 + (rpm * 2) + random.gauss(0, 2)  # Base torque increases with RPM
            height_effect = max(0, (z_height + 66) * 10)  # Effect of height on torque
            torque_percent = base_torque + height_effect + random.gauss(0, 1)
            
            measurement = {
                "timestamp": time.time(),
                "elapsed_time": time.time() - start_time,
                "torque_percent": abs(torque_percent),
                "rpm": rpm
            }
            measurements.append(measurement)
            
            # Calculate rotational drag and add to web interface
            rotational_drag = abs(torque_percent) / rpm if rpm > 0 else 0
            web_interface.add_measurement_point(z_height, rotational_drag, rpm, cell_id)
            
            sample_count += 1
            time.sleep(sample_interval)
        
        web_interface.set_current_rpm(0)
        return measurements
    
    def simulate_cell_testing(self, global_cell: int):
        """Simulate testing a complete cell"""
        row, local_cell, x_pos, y_pos = self.get_cell_position(global_cell)
        row_config = None
        for r in self.ROWS:
            if r['row_number'] == row:
                row_config = r
                break
        
        print(f"\nSimulating Cell {global_cell} (Row {row}, Local Cell {local_cell})")
        
        # Set current cell
        web_interface.set_current_cell(global_cell)
        web_interface.update_status(f"Testing Cell {global_cell}")
        
        # Simulate Z-series testing
        current_z = row_config['safe_z']
        z_step = 0
        
        while current_z >= row_config['max_z_travel'] and z_step < 8:  # Limit steps for demo
            z_step += 1
            z_rounded = round(current_z, 3)
            
            print(f"  Z-step {z_step}: Z={z_rounded:.3f}")
            web_interface.update_status(f"Cell {global_cell} - Z-step {z_step}")
            
            # Move to position
            if z_step == 1:
                self.simulate_safe_movement(x_pos, y_pos, current_z)
            else:
                self.simulate_movement(x_pos, y_pos, current_z)
            
            # Test at different RPMs
            for rpm in self.TEST_RPMS:
                measurements = self.simulate_measurement_at_rpm(rpm, z_rounded, global_cell)
                print(f"    RPM {rpm}: {len(measurements)} samples collected")
                
                time.sleep(0.5 / self.simulation_speed)  # Brief pause between RPMs
            
            current_z += self.Z_STEP_SIZE
            time.sleep(0.2 / self.simulation_speed)
    
    def simulate_washing_sequence(self, global_cell: int):
        """Simulate washing sequence after cell testing"""
        print(f"\nSimulating wash sequence for Cell {global_cell}")
        web_interface.update_status(f"Washing after Cell {global_cell}")
        
        # Move to wash station 1
        web_interface.update_status(f"Moving to Wash Station 1")
        self.simulate_safe_movement(self.WASH_STATION1_X, self.WASH_STATION1_Y, -10)
        
        # Simulate washing steps
        wash_steps = [
            "Starting pump 1 (solvent)",
            "Pump 1 running - rinsing",
            "Stopping pump 1",
            "Starting pump 2 (air)",
            "Pump 2 running - drying", 
            "Stopping pump 2"
        ]
        
        for step in wash_steps:
            web_interface.update_status(step)
            print(f"  {step}")
            time.sleep(1.0 / self.simulation_speed)
        
        # Move to wash station 2
        web_interface.update_status(f"Moving to Wash Station 2")
        self.simulate_movement(self.WASH_STATION2_X, self.WASH_STATION2_Y, -10)
        
        # Second wash cycle
        for step in wash_steps:
            step2 = step.replace("Wash Station 1", "Wash Station 2")
            web_interface.update_status(step2)
            print(f"  {step2}")
            time.sleep(1.0 / self.simulation_speed)
        
        web_interface.update_status(f"Wash sequence completed")
    
    def simulate_experiment(self, cells_to_test: List[int]):
        """Simulate complete experiment"""
        print("="*60)
        print("VISCOMETRY PLATFORM SIMULATION")
        print(f"Testing {len(cells_to_test)} cells: {cells_to_test}")
        print("="*60)
        
        self.is_running = True
        web_interface.set_running_state(True)
        
        try:
            # Home position
            web_interface.update_status("Homing viscometer")
            self.simulate_safe_movement(0, 0, 0)
            time.sleep(1.0 / self.simulation_speed)
            
            # Test each cell
            for i, global_cell in enumerate(cells_to_test):
                print(f"\n[{i+1}/{len(cells_to_test)}] Testing Cell {global_cell}")
                
                # Simulate auto-zeroing
                web_interface.update_status(f"Auto-zeroing for Cell {global_cell}")
                time.sleep(2.0 / self.simulation_speed)
                
                # Test the cell
                self.simulate_cell_testing(global_cell)
                
                # Washing sequence
                self.simulate_washing_sequence(global_cell)
                
                # Brief pause between cells
                time.sleep(1.0 / self.simulation_speed)
            
            # Return home
            web_interface.update_status("Returning to home position")
            self.simulate_safe_movement(0, 0, 0)
            
            # Complete
            web_interface.update_status("Experiment completed successfully")
            print("\nSimulation completed successfully!")
            
        except KeyboardInterrupt:
            print("\nSimulation interrupted by user")
            web_interface.update_status("Simulation stopped by user")
        except Exception as e:
            print(f"\nSimulation error: {e}")
            web_interface.update_status(f"Simulation error: {e}")
        finally:
            self.is_running = False
            web_interface.set_running_state(False)
            web_interface.set_current_rpm(0)

def main():
    print("Starting Viscometry Platform Simulation...")
    
    # Start web interface
    try:
        print("Starting web interface on http://localhost:5001")
        web_thread = web_interface.start_in_thread(debug=False)
        print("Web interface started successfully!")
        print("\nOpen your browser to: http://localhost:5001")
        time.sleep(3)  # Give web server time to start
    except Exception as e:
        print(f"Failed to start web interface: {e}")
        return
    
    # Create simulator
    simulator = ViscometrySimulator()
    
    # Configure simulation
    print("\nSimulation Configuration:")
    print("1. Speed: 2x faster than real experiment")
    print("2. Testing cells: [1, 7, 13] (one from each row)")
    print("3. 5 RPM values per Z-level")
    print("4. 8 Z-levels per cell")
    print("\nSimulation will start in 5 seconds...")
    print("Press Ctrl+C to stop the simulation")
    
    simulator.simulation_speed = 2.0  # 2x speed for demo
    
    # Wait a bit then start simulation
    try:
        time.sleep(5)
        
        # Demo cells - one from each row
        demo_cells = [1, 7, 13]
        
        # Start simulation in background thread
        simulation_thread = threading.Thread(
            target=simulator.simulate_experiment,
            args=(demo_cells,),
            daemon=True
        )
        simulation_thread.start()
        
        print("\n" + "="*60)
        print("SIMULATION RUNNING")
        print("Open http://localhost:5001 to view the web interface")
        print("Press Ctrl+C to stop")
        print("="*60)
        
        # Keep main thread alive
        while simulation_thread.is_alive():
            time.sleep(1)
        
        print("\nSimulation finished. Web interface will continue running.")
        print("Press Ctrl+C to exit completely.")
        
        # Keep web interface running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down simulation...")
        web_interface.update_status("Simulation stopped")
        web_interface.set_running_state(False)

if __name__ == "__main__":
    main()

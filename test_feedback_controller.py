#!/usr/bin/env python3
"""
Test script for the Rotational Drag Feedback Controller

This script tests the feedback controller with simulated data to verify
the hit-point detection algorithm works correctly.
"""

import sys
import os
import numpy as np

# Add the src/python_64 directory to path to import the feedback controller
# Get the directory containing this script
script_dir = os.path.dirname(os.path.abspath(__file__))
# Add src/python_64 to the Python path
python_64_dir = os.path.join(script_dir, 'src', 'python_64')
if python_64_dir not in sys.path:
    sys.path.insert(0, python_64_dir)

try:
    from feedback_helper_function import RotationalDragFeedbackController, verify_import
    verify_import()  # Confirm successful import
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Searching in path: {python_64_dir}")
    print(f"Directory exists: {os.path.exists(python_64_dir)}")
    if os.path.exists(python_64_dir):
        print(f"Files in directory: {os.listdir(python_64_dir)}")
    sys.exit(1)

# Import TEST_RPMS or define it locally for testing
TEST_RPMS = [1.0]  # Simple test with one RPM

def generate_test_data():
    """Generate synthetic test data that mimics real viscometer behavior"""
    
    # Simulate Z-heights from -65.5 to -66.5 (1mm range) in 0.1mm steps
    z_heights = np.arange(-65.5, -66.6, -0.1)
    hit_point_z = -66.2  # Simulated hit point
    
    test_data = {}
    
    for z in z_heights:
        rpm_data = {}
        
        for rpm in TEST_RPMS:
            # Simulate normal behavior before hit point
            if z > hit_point_z:
                # Normal trend: rotational drag increases as Z decreases
                base_drag = abs(z + 65.5) * 2.0 * rpm  # Increases as Z gets more negative
                noise = np.random.normal(0, base_drag * 0.05)  # 5% noise
                torque_percent = (base_drag + noise) * rpm
                
                # Create multiple measurements per Z/RPM combination
                measurements = []
                for i in range(5):  # 5 measurements per RPM
                    measurement_noise = np.random.normal(0, torque_percent * 0.02)  # 2% measurement noise
                    measurements.append({
                        'timestamp': 0,
                        'elapsed_time': i * 2.0,
                        'torque_percent': torque_percent + measurement_noise,
                        'rpm': rpm
                    })
                
                rpm_data[rpm] = measurements
                
            else:
                # Hit point behavior: high variability, plateau-like behavior
                base_drag = abs(hit_point_z + 65.5) * 2.0 * rpm  # Plateau level
                
                measurements = []
                for i in range(5):
                    # Much higher noise to simulate oscillations at hit point
                    oscillation = np.random.normal(0, base_drag * 0.3)  # 30% oscillation
                    spike = np.random.choice([0, base_drag * 0.5], p=[0.8, 0.2])  # Random spikes
                    torque_percent = (base_drag + oscillation + spike) * rpm
                    
                    measurements.append({
                        'timestamp': 0,
                        'elapsed_time': i * 2.0,
                        'torque_percent': torque_percent,
                        'rpm': rpm
                    })
                
                rpm_data[rpm] = measurements
        
        test_data[z] = rpm_data
    
    return test_data, hit_point_z

def test_feedback_controller():
    """Test the feedback controller with synthetic data"""
    
    print("Testing Rotational Drag Feedback Controller")
    print("=" * 50)
    
    # Generate test data
    test_data, expected_hit_z = generate_test_data()
    print(f"Generated test data with hit point at Z = {expected_hit_z:.3f}")
    print(f"Testing {len(test_data)} Z-levels with {len(TEST_RPMS)} RPMs each")
    
    # Initialize feedback controller with default configuration
    controller = RotationalDragFeedbackController(
        feedback_enabled=True,
        min_data_points=3,
        second_derivative_threshold=-0.5,
        cv_jump_threshold=0.2,
        trend_r_squared_min=0.8,
        hit_point_confidence_threshold=0.6
    )
    
    # Process data step by step as the real system would
    hit_detected = False
    detection_z = None
    
    for z_height in sorted(test_data.keys(), reverse=True):  # Highest to lowest Z
        print(f"\nProcessing Z = {z_height:.3f}")
        
        # Add measurements to controller
        rpm_data = test_data[z_height]
        controller.add_measurements_at_z(z_height, rpm_data)
        
        # Check for hit point detection
        hit_detected = controller.evaluate_hit_point_detection(TEST_RPMS)
        
        if hit_detected:
            detection_z = z_height
            print(f"*** HIT POINT DETECTED at Z = {z_height:.3f} ***")
            break
    
    # Print results
    print("\n" + "=" * 50)
    print("TEST RESULTS")
    print("=" * 50)
    print(f"Expected hit point Z: {expected_hit_z:.3f}")
    print(f"Hit detected: {hit_detected}")
    if hit_detected:
        print(f"Detected at Z: {detection_z:.3f}")
        
        summary = controller.get_summary()
        print(f"Detection confidence: {summary['hit_point_confidence']:.3f}")
        
        error = abs(detection_z - expected_hit_z)
        print(f"Detection error: {error:.3f} mm")
        
        if error <= 0.2:  # Within 0.2mm is good
            print("✓ DETECTION ACCURACY: GOOD")
        else:
            print("⚠ DETECTION ACCURACY: NEEDS IMPROVEMENT")
    else:
        print("✗ FAILED TO DETECT HIT POINT")
    
    print(f"Total Z-levels processed: {len(controller.z_rpm_drag_data)}")

def test_edge_cases():
    """Test edge cases for the feedback controller"""
    
    print("\n" + "=" * 50)
    print("TESTING EDGE CASES")
    print("=" * 50)
    
    controller = RotationalDragFeedbackController(
        feedback_enabled=True,
        min_data_points=3
    )
    
    # Test 1: Insufficient data
    print("\nTest 1: Insufficient data points")
    single_z_data = {
        1.0: [{'timestamp': 0, 'elapsed_time': 0, 'torque_percent': 5.0, 'rpm': 1.0}]
    }
    controller.add_measurements_at_z(-65.0, {1.0: single_z_data[1.0]})
    hit_detected = controller.evaluate_hit_point_detection(TEST_RPMS)
    print(f"Hit detected with insufficient data: {hit_detected} (should be False)")
    
    # Test 2: Division by zero protection
    print("\nTest 2: Zero RPM handling")
    zero_rpm_data = {
        0.0: [{'timestamp': 0, 'elapsed_time': 0, 'torque_percent': 5.0, 'rpm': 0.0}]
    }
    controller.add_measurements_at_z(-65.1, zero_rpm_data)
    # Should not crash
    print("Zero RPM handled without crashing: ✓")

if __name__ == "__main__":
    # Test the feedback controller
    test_feedback_controller()
    
    # Test edge cases
    test_edge_cases()
    
    print("\n" + "=" * 50)
    print("ALL TESTS COMPLETED")
    print("=" * 50)
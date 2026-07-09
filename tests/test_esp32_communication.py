#!/usr/bin/env python3
"""
ESP32 Washing Station Communication Test Script

This script tests the reliability of ESP32 communication and helps debug 
command execution issues. Use this to verify your ESP32 is responding
properly before running the main viscometer analysis.

Usage:
    python tests/test_esp32_communication.py
"""

import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from viscometry.hardware.pump import PumpESP32

# Configuration
ESP32_PORT = "COM11" 
ESP32_BAUD = 115200
TEST_VIRTUAL = False

def test_basic_communication():
    """Test basic command sending without acknowledgment"""
    print("="*60)
    print("BASIC COMMUNICATION TEST (Legacy Mode)")
    print("="*60)
    
    pump = PumpESP32(port=ESP32_PORT, baud=ESP32_BAUD, virtual=TEST_VIRTUAL)
    
    try:
        pump.open()
        print("ESP32 connection opened successfully")
        
        # Test basic commands
        commands = [
            (b"ST", "Status Request"),
            (b"P1", "Start Pump 1"),
            (b"SP1", "Stop Pump 1"),
            (b"M1", "Start Motor 1"), 
            (b"SM1", "Stop Motor 1"),
            (b"0", "Emergency Stop All")
        ]
        
        for cmd, desc in commands:
            print(f"\nSending: {desc} ({cmd})")
            pump.send_tag(cmd)
            time.sleep(1.5)  # Allow time for response
            
    except Exception as e:
        print(f"Error during basic communication test: {e}")
    finally:
        pump.close()

def test_acknowledgment_communication():
    """Test new acknowledgment-based communication"""
    print("\n" + "="*60)
    print("ACKNOWLEDGMENT COMMUNICATION TEST")
    print("="*60)
    
    pump = PumpESP32(port=ESP32_PORT, baud=ESP32_BAUD, virtual=TEST_VIRTUAL)
    
    try:
        pump.open()
        
        if not hasattr(pump, 'send_command_with_ack'):
            print("WARNING: send_command_with_ack method not available")
            print("Make sure you're using the updated move_to_locations.py")
            return
        
        # Test commands with acknowledgment
        commands = [
            (b"P1", "Start Pump 1"),
            (b"SP1", "Stop Pump 1"),
            (b"M1", "Start Motor 1"),
            (b"SM1", "Stop Motor 1"),
            (b"P3", "Start Pump 3"),
            (b"SP3", "Stop Pump 3"),
            (b"M2", "Start Motor 2"),
            (b"SM2", "Stop Motor 2"),
        ]
        
        success_count = 0
        for cmd, desc in commands:
            print(f"\nTesting: {desc}")
            success = pump.send_command_with_ack(cmd, timeout=3.0, max_retries=2)
            if success:
                success_count += 1
                print(f"✓ SUCCESS: {desc}")
            else:
                print(f"✗ FAILED: {desc}")
            time.sleep(0.5)
        
        print(f"\nRESULTS: {success_count}/{len(commands)} commands successful")
        
        # Emergency stop
        print("\nExecuting emergency stop...")
        pump.send_tag(b"0")
        time.sleep(1)
        
    except Exception as e:
        print(f"Error during acknowledgment test: {e}")
    finally:
        pump.close()

def test_status_monitoring():
    """Test status monitoring functionality"""
    print("\n" + "="*60)
    print("STATUS MONITORING TEST")
    print("="*60)
    
    pump = PumpESP32(port=ESP32_PORT, baud=ESP32_BAUD, virtual=TEST_VIRTUAL)
    
    try:
        pump.open()
        
        if not hasattr(pump, 'get_status'):
            print("WARNING: get_status method not available")
            print("Make sure you're using the updated move_to_locations.py")
            return
        
        # Get initial status
        print("\nInitial Status:")
        status = pump.get_status()
        if status:
            for component, running in status.items():
                print(f"  {component}: {'RUNNING' if running else 'STOPPED'}")
        else:
            print("  Unable to retrieve status")
        
        # Test sequence with status monitoring
        if hasattr(pump, 'send_command_with_ack'):
            print("\nTesting sequence with status monitoring:")
            
            # Start Pump 1
            print("\n1. Starting Pump 1...")
            if pump.send_command_with_ack(b"P1"):
                status = pump.get_status()
                if status and status.get("pump1"):
                    print("✓ Pump 1 confirmed running")
                else:
                    print("⚠ Pump 1 status unclear")
            
            time.sleep(2)
            
            # Stop Pump 1
            print("\n2. Stopping Pump 1...")
            if pump.send_command_with_ack(b"SP1"):
                status = pump.get_status()
                if status and not status.get("pump1"):
                    print("✓ Pump 1 confirmed stopped")
                else:
                    print("⚠ Pump 1 status unclear")
        
        # Final status check
        print("\nFinal Status:")
        final_status = pump.get_status()
        if final_status:
            running_components = [comp for comp, running in final_status.items() if running]
            if running_components:
                print(f"⚠ WARNING: Components still running: {running_components}")
                print("Executing emergency stop...")
                pump.send_tag(b"0")
                time.sleep(1)
            else:
                print("✓ All components stopped")
        
    except Exception as e:
        print(f"Error during status monitoring test: {e}")
    finally:
        pump.close()

def test_wash_sequence_simulation():
    """Simulate a simplified washing sequence"""
    print("\n" + "="*60)
    print("WASH SEQUENCE SIMULATION")
    print("="*60)
    
    pump = PumpESP32(port=ESP32_PORT, baud=ESP32_BAUD, virtual=TEST_VIRTUAL)
    
    try:
        pump.open()
        
        use_ack = hasattr(pump, 'send_command_with_ack')
        print(f"Using {'acknowledgment' if use_ack else 'legacy'} mode")
        
        def send_reliable_command(cmd, desc, wait_time=0):
            print(f"\n  {desc}...")
            if use_ack:
                success = pump.send_command_with_ack(cmd, timeout=3.0)
                if not success:
                    print(f"  ✗ FAILED: {desc}")
                    return False
                print(f"  ✓ SUCCESS: {desc}")
            else:
                pump.send_tag(cmd)
                print(f"  → Sent: {desc}")
                time.sleep(0.5)  # Minimum processing time
            
            if wait_time > 0:
                print(f"  Waiting {wait_time}s...")
                time.sleep(wait_time)
            return True
        
        print("\nSimulating Wash Station 1 sequence:")
        
        # Station 1 sequence
        if not send_reliable_command(b"P1", "Start Pump 1", 2):  # Shortened from 10s
            return
        if not send_reliable_command(b"SP1", "Stop Pump 1"):
            return
        if not send_reliable_command(b"M1", "Start Motor 1", 3):  # Shortened from 60s
            return
        if not send_reliable_command(b"R1", "Start Reverse Rinse 1", 2):  # Shortened from 15s
            return
        if not send_reliable_command(b"SR1", "Stop Reverse Rinse 1"):
            return
        if not send_reliable_command(b"SM1", "Stop Motor 1"):
            return
            
        print("\nSimulating Wash Station 2 sequence:")
        
        # Station 2 sequence
        if not send_reliable_command(b"P3", "Start Pump 3", 2):
            return
        if not send_reliable_command(b"SP3", "Stop Pump 3"):
            return
        if not send_reliable_command(b"M2", "Start Motor 2", 3):
            return
        if not send_reliable_command(b"R2", "Start Reverse Rinse 2", 2):
            return
        if not send_reliable_command(b"SR2", "Stop Reverse Rinse 2"):
            return
        if not send_reliable_command(b"SM2", "Stop Motor 2"):
            return
        
        print("\n✓ Wash sequence simulation completed successfully!")
        
        # Final status check
        if hasattr(pump, 'get_status'):
            final_status = pump.get_status()
            if final_status:
                running = [comp for comp, state in final_status.items() if state]
                if running:
                    print(f"⚠ WARNING: Components still running: {running}")
                    pump.send_tag(b"0")
                    time.sleep(1)
                else:
                    print("✓ All components confirmed stopped")
        
    except Exception as e:
        print(f"Error during wash sequence simulation: {e}")
        # Emergency stop
        pump.send_tag(b"0")
    finally:
        pump.close()

def main():
    print("ESP32 Washing Station Communication Test")
    print(f"Port: {ESP32_PORT}")
    print(f"Baud: {ESP32_BAUD}")
    print(f"Virtual: {TEST_VIRTUAL}")
    
    if not TEST_VIRTUAL:
        print(f"\nEnsure ESP32 is connected to {ESP32_PORT} and upload the latest Arduino code")
        print("Press Enter to continue or Ctrl+C to abort...")
        try:
            input()
        except KeyboardInterrupt:
            print("\nTest aborted by user")
            return
    
    # Run all tests
    test_basic_communication()
    test_acknowledgment_communication()
    test_status_monitoring()
    test_wash_sequence_simulation()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)
    print("\nIf any tests failed:")
    print("1. Check ESP32 is connected and powered")
    print("2. Verify COM port in configuration") 
    print("3. Upload latest Arduino code with acknowledgment support")
    print("4. Check serial monitor for ESP32 debug output")

if __name__ == "__main__":
    main()
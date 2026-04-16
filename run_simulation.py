#!/usr/bin/env python3
"""
Quick start script for Viscometry Platform Web Interface Simulation
"""

import subprocess
import sys
import os
import pathlib

def check_dependencies():
    """Check if web interface dependencies are installed"""
    try:
        import flask
        import flask_socketio
        print("✓ Web interface dependencies are installed")
        return True
    except ImportError:
        print("⚠ Web interface dependencies not installed")
        return False

def install_dependencies():
    """Install dependencies if needed"""
    if not check_dependencies():
        print("Installing web interface dependencies...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "flask==2.3.3", "flask-socketio==5.3.6", "eventlet==0.33.3"
            ])
            print("✓ Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install dependencies: {e}")
            return False
    return True

def main():
    print("="*60)
    print("VISCOMETRY PLATFORM SIMULATION - QUICK START")
    print("="*60)
    
    # Install dependencies if needed
    if not install_dependencies():
        print("\nFailed to install dependencies. Please install manually:")
        print("pip install flask==2.3.3 flask-socketio==5.3.6 eventlet==0.33.3")
        return
    
    print("\nStarting simulation...")
    print("This will:")
    print("1. Start the web interface on http://localhost:5000")
    print("2. Simulate testing 3 cells (one from each row)")
    print("3. Show real-time viscometer movement and data collection")
    print("4. Demonstrate washing sequences")
    
    print("\n" + "="*60)
    print("OPEN YOUR BROWSER TO: http://localhost:5000")
    print("Press Ctrl+C to stop the simulation")
    print("="*60)
    
    # Run the simulation
    try:
        import simulate_viscometry
        simulate_viscometry.main()
    except KeyboardInterrupt:
        print("\nSimulation stopped by user")
    except Exception as e:
        print(f"\nError running simulation: {e}")
        print("\nTry running directly:")
        print("python simulate_viscometry.py")

if __name__ == "__main__":
    main()
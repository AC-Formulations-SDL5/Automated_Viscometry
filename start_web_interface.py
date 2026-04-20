#!/usr/bin/env python3
"""
Standalone Web Interface Starter for Viscometry Platform
Starts the web interface without running the main analysis
"""

import eventlet
eventlet.monkey_patch()

import sys
import os
import pathlib

# Add the src/python_64 directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'python_64'))

from web_interface import web_interface

def main():
    print("="*60)
    print("VISCOMETRY PLATFORM - STANDALONE WEB INTERFACE")
    print("="*60)
    print("Starting web interface on http://localhost:5001")
    print("Note: Instruments will show as disconnected since hardware is not initialized")
    print("Use the main script for full functionality with hardware control")
    print("="*60)
    
    try:
        web_interface.start_server(debug=True)
    except KeyboardInterrupt:
        print("\nWeb interface stopped by user")
    except Exception as e:
        print(f"\nError starting web interface: {e}")

if __name__ == "__main__":
    main()
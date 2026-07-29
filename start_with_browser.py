#!/usr/bin/env python3
"""
Web browser opener for the simulation
Automatically opens http://localhost:5001 in your default browser
"""

import webbrowser
import time
import threading
import subprocess
import sys
import os

def open_browser_after_delay(url="http://localhost:5001", delay=8):
    """Open browser after a delay to allow server to start"""
    time.sleep(delay)
    print(f"\n🌐 Opening browser to {url}")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Could not auto-open browser: {e}")
        print(f"Please manually open: {url}")

def main():
    print("🚀 Starting Viscometry Platform with Auto Browser Opening...")
    
    # Start browser opener in background
    browser_thread = threading.Thread(
        target=open_browser_after_delay,
        daemon=True
    )
    browser_thread.start()
    
    # Start the simulation
    try:
        import run_simulation
        run_simulation.main()
    except KeyboardInterrupt:
        print("\n👋 Simulation stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
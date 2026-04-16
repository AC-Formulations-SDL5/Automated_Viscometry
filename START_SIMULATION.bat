@echo off
echo ===============================================
echo VISCOMETRY PLATFORM WEB INTERFACE SIMULATION
echo ===============================================
echo.
echo This script will:
echo 1. Install required Python packages (if needed)
echo 2. Start the web simulation
echo 3. Open your browser to the interface
echo.
echo Press any key to continue or Ctrl+C to cancel...
pause >nul

echo.
echo Starting simulation...
python run_simulation.py

echo.
echo Simulation finished. Press any key to exit.
pause >nul
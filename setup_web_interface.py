#!/usr/bin/env python3
"""
Setup script for Viscometry Platform Web Interface
Installs dependencies and verifies setup
"""

import subprocess
import sys
import os
import pathlib

def install_requirements():
    """Install web interface requirements"""
    print("Installing web interface dependencies...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "-r", "requirements_web.txt"
        ])
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        return False

def check_directory_structure():
    """Check and create necessary directories"""
    print("Checking directory structure...")
    
    directories = [
        "templates",
        "static",
        "static/css", 
        "static/js",
        "static/images"
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"✓ Created directory: {directory}")
        else:
            print(f"✓ Directory exists: {directory}")
    
    return True

def check_files():
    """Check if all required files exist"""
    print("Checking required files...")
    
    required_files = [
        "src/python_64/web_interface.py",
        "templates/index.html",
        "static/css/style.css",
        "static/js/app.js",
        "static/images/logo.svg"
    ]
    
    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ Missing: {file_path}")
            missing_files.append(file_path)
    
    return len(missing_files) == 0

def test_import():
    """Test if web interface can be imported"""
    print("Testing web interface import...")
    try:
        # Add src/python_64 to path temporarily
        sys.path.insert(0, "src/python_64")
        import web_interface
        print("✓ Web interface module imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import web interface: {e}")
        return False
    finally:
        # Remove from path
        if "src/python_64" in sys.path:
            sys.path.remove("src/python_64")

def main():
    """Main setup function"""
    print("="*60)
    print("VISCOMETRY PLATFORM WEB INTERFACE SETUP")
    print("="*60)
    
    # Change to project root directory
    script_dir = pathlib.Path(__file__).parent
    os.chdir(script_dir)
    
    success = True
    
    # Check directory structure
    if not check_directory_structure():
        success = False
    
    print()
    
    # Check files
    if not check_files():
        success = False
        print("\nSome files are missing. Please ensure all files are created properly.")
    
    print()
    
    # Install requirements
    if not install_requirements():
        success = False
    
    print()
    
    # Test import
    if not test_import():
        success = False
    
    print("\n" + "="*60)
    if success:
        print("✓ SETUP COMPLETED SUCCESSFULLY!")
        print("\nTo start the viscometry platform with web interface:")
        print("1. Navigate to: src/python_64/")
        print("2. Run: python all_cells_with_rotational_drag_feedback.py")
        print("3. Open browser to: http://localhost:5001")
        print("\nThe web interface will start automatically when you run the main script.")
    else:
        print("✗ SETUP FAILED!")
        print("Please check the error messages above and fix any issues.")
    print("="*60)

if __name__ == "__main__":
    main()
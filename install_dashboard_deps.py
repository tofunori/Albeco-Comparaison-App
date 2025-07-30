#!/usr/bin/env python3
"""
Dashboard Dependencies Installer

Script to install required dashboard dependencies.
"""

import subprocess
import sys

def run_command(command, description):
    """Run a command and report results."""
    print(f"\n{description}...")
    print(f"Running: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"[OK] {description} completed successfully")
        if result.stdout:
            print("Output:", result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {description} failed")
        print("Error:", e.stderr.strip() if e.stderr else str(e))
        return False

def main():
    print("Interactive Albedo Dashboard - Dependency Installer")
    print("=" * 60)
    
    # Check if we're in a conda environment
    conda_env = subprocess.run("conda info --envs", shell=True, 
                              capture_output=True, text=True)
    if conda_env.returncode == 0:
        print("Conda is available")
    else:
        print("Conda not found, using pip only")
    
    # Install core packages
    packages_to_install = [
        ("conda install -y plotly", "Installing Plotly via conda"),
        ("conda install -y -c conda-forge pandas numpy", "Installing data packages via conda"),
        ("pip install dash==2.14.2", "Installing Dash"),
        ("pip install dash-bootstrap-components==1.5.0", "Installing Dash Bootstrap Components"),
        ("pip install dash-leaflet==0.1.23", "Installing Dash Leaflet"),
    ]
    
    success_count = 0
    total_count = len(packages_to_install)
    
    for command, description in packages_to_install:
        if run_command(command, description):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"Installation Summary: {success_count}/{total_count} successful")
    
    if success_count == total_count:
        print("[OK] All dependencies installed successfully!")
        print("\nYou can now run the dashboard:")
        print("python app.py")
        print("\nOr use the test runner:")
        print("python run_dashboard.py")
    else:
        print("[WARNING] Some installations failed.")
        print("You may need to install missing packages manually:")
        print("conda install plotly pandas numpy")
        print("pip install dash dash-bootstrap-components dash-leaflet")
    
    print(f"\n{'='*60}")

if __name__ == "__main__":
    main()
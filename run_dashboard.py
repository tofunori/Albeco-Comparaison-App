#!/usr/bin/env python3
"""
Dashboard Runner Script

Simple script to launch the Interactive Albedo Analysis Dashboard
with proper error handling and configuration validation.
"""

import sys
import os
import logging
from pathlib import Path

def check_requirements():
    """Check if required packages are installed."""
    required_packages = [
        'dash', 'dash_bootstrap_components', 'dash_leaflet',
        'plotly', 'pandas', 'numpy', 'geopandas', 'yaml'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("Missing required packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nInstall missing packages with:")
        print("pip install " + " ".join(missing_packages))
        return False
    
    return True

def check_data_files():
    """Check if essential data files exist."""
    data_path = Path("data")
    config_path = Path("config")
    
    essential_paths = [
        data_path / "modis",
        data_path / "aws", 
        data_path / "glacier_masks",
        config_path / "glacier_sites.yaml",
        config_path / "dashboard_config.yaml"
    ]
    
    missing_paths = []
    for path in essential_paths:
        if not path.exists():
            missing_paths.append(str(path))
    
    if missing_paths:
        print("Missing essential data files/directories:")
        for path in missing_paths:
            print(f"  - {path}")
        print("\nPlease ensure all data files are copied from the Albedo_analysis_New project.")
        return False
    
    return True

def main():
    """Main function to run the dashboard with checks."""
    print("🚀 Starting Interactive Albedo Analysis Dashboard...")
    print("=" * 60)
    
    # Check requirements
    print("Checking requirements...")
    if not check_requirements():
        sys.exit(1)
    print("✅ All required packages are installed")
    
    # Check data files
    print("Checking data files...")
    if not check_data_files():
        sys.exit(1)
    print("✅ Essential data files found")
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Import and run the app
        print("Initializing dashboard...")
        from app import app, data_manager
        
        # Get configuration
        config = data_manager.config
        app_config = config.get('app', {})
        
        host = app_config.get('host', '127.0.0.1')
        port = app_config.get('port', 8050)
        debug = app_config.get('debug', True)
        
        print(f"✅ Dashboard initialized successfully")
        print(f"🌐 Starting server at http://{host}:{port}")
        print("📊 Dashboard features:")
        print("   - Interactive glacier map")
        print("   - Real-time statistical analysis")
        print("   - Multiple visualization types")
        print("   - Data export capabilities")
        print()
        print("Press Ctrl+C to stop the server")
        print("=" * 60)
        
        # Run the server
        app.run_server(
            debug=debug,
            host=host,
            port=port,
            dev_tools_hot_reload=debug
        )
        
    except ImportError as e:
        print(f"❌ Error importing dashboard components: {e}")
        print("Please check that all files are present and requirements are installed.")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        print("Check the configuration files and data paths.")
        sys.exit(1)

if __name__ == "__main__":
    main()
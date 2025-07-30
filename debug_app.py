#!/usr/bin/env python3
"""
Debug Dashboard App

Version with detailed error reporting to help diagnose issues.
"""

import sys
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=== Dashboard Debug Information ===")
print(f"Python version: {sys.version}")
print(f"Project root: {project_root}")

# Test imports one by one
try:
    import dash
    print(f"✓ Dash imported - version: {dash.__version__}")
except Exception as e:
    print(f"✗ Dash import failed: {e}")
    sys.exit(1)

try:
    import dash_bootstrap_components as dbc
    print(f"✓ Dash Bootstrap Components imported")
except Exception as e:
    print(f"✗ Dash Bootstrap Components failed: {e}")

try:
    import dash_leaflet as dl
    print(f"✓ Dash Leaflet imported")
except Exception as e:
    print(f"✗ Dash Leaflet failed: {e}")

try:
    import plotly
    print(f"✓ Plotly imported - version: {plotly.__version__}")
except Exception as e:
    print(f"✗ Plotly failed: {e}")

# Test our components
try:
    from dashboard.core.data_manager import DashboardDataManager
    dm = DashboardDataManager()
    print(f"✓ Data Manager initialized")
    
    glaciers = dm.get_available_glaciers()
    print(f"✓ Found {len(glaciers)} glaciers")
    
except Exception as e:
    print(f"✗ Data Manager failed: {e}")
    traceback.print_exc()

# If we get here, try to create a simple dash app
try:
    from dash import html, dcc
    
    app = dash.Dash(__name__)
    
    app.layout = html.Div([
        html.H1("Debug Dashboard"),
        html.P("If you see this, basic Dash is working!"),
        html.Div(id="debug-content")
    ])
    
    print("\n=== Starting Debug Dashboard ===")
    print("Open http://127.0.0.1:8053 in your browser")
    print("Press Ctrl+C to stop")
    
    app.run_server(debug=True, host='127.0.0.1', port=8053)
    
except Exception as e:
    print(f"✗ Failed to create Dash app: {e}")
    traceback.print_exc()
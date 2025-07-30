#!/usr/bin/env python3
"""
Simple Interactive Albedo Analysis Dashboard

Simplified version to avoid initial loading errors.
"""

import dash
from dash import html, dcc, Input, Output, State, callback, ctx
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, date
import logging
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import dashboard components
from dashboard.core.data_manager import DashboardDataManager
from dashboard.components.plots import PlotComponents

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="Interactive Albedo Analysis Dashboard"
)

# Initialize core components
try:
    data_manager = DashboardDataManager()
    plot_components = PlotComponents(data_manager.config)
    logger.info("Dashboard components initialized successfully")
except Exception as e:
    logger.error(f"Error initializing dashboard components: {e}")

# Create simple layout
def create_simple_layout():
    """Create a simple layout that works reliably."""
    
    # Get available glaciers
    try:
        available_glaciers = data_manager.get_available_glaciers()
        glacier_options = [
            {'label': f"{g['name']}", 'value': g['id']} 
            for g in available_glaciers
        ]
    except Exception as e:
        logger.error(f"Error getting glaciers: {e}")
        glacier_options = []
    
    layout = dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H2("Interactive Albedo Analysis Dashboard", className="text-primary mb-4"),
                html.P("Select a glacier and click 'Load Data' to begin analysis.", className="text-muted")
            ])
        ]),
        
        # Controls
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Controls"),
                    dbc.CardBody([
                        html.Label("Select Glacier:"),
                        dcc.Dropdown(
                            id='glacier-dropdown',
                            options=glacier_options,
                            value=glacier_options[0]['value'] if glacier_options else None,
                            placeholder="Choose a glacier"
                        ),
                        html.Br(),
                        dbc.Button("Load Data", id="load-data-btn", color="primary", className="mb-2"),
                        html.Div(id="status-message", className="mt-2")
                    ])
                ])
            ], width=4),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Data Summary"),
                    dbc.CardBody([
                        html.Div(id="data-info", children="No data loaded")
                    ])
                ])
            ], width=8)
        ], className="mb-4"),
        
        # Plots
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Scatter Plot - MODIS vs AWS"),
                    dbc.CardBody([
                        dcc.Graph(id="scatter-plot", figure={})
                    ])
                ])
            ], width=6),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Time Series"),
                    dbc.CardBody([
                        dcc.Graph(id="timeseries-plot", figure={})
                    ])
                ])
            ], width=6)
        ], className="mb-4"),
        
        # Store for data
        dcc.Store(id='glacier-data-store')
        
    ], fluid=True)
    
    return layout

# Set app layout
app.layout = create_simple_layout()

# Callback for loading data
@app.callback(
    [Output('glacier-data-store', 'data'),
     Output('data-info', 'children'),
     Output('status-message', 'children')],
    Input('load-data-btn', 'n_clicks'),
    State('glacier-dropdown', 'value'),
    prevent_initial_call=True
)
def load_glacier_data(n_clicks, glacier_id):
    """Load data when button is clicked."""
    if not n_clicks or not glacier_id:
        return None, "No data loaded", ""
    
    try:
        logger.info(f"Loading data for {glacier_id}")
        
        # Load glacier data
        data = data_manager.load_glacier_data(glacier_id)
        
        if data is not None:
            # Get basic info
            total_records = len(data)
            methods = list(data['method'].unique()) if 'method' in data.columns else []
            date_range = f"{data['date'].min()} to {data['date'].max()}" if 'date' in data.columns else "No dates"
            
            # Create info display
            info_display = [
                html.P(f"Total Records: {total_records:,}"),
                html.P(f"Methods: {', '.join(methods)}"),
                html.P(f"Date Range: {date_range}")
            ]
            
            # Convert to JSON for storage
            data_json = data.to_json(date_format='iso')
            
            return data_json, info_display, dbc.Alert("Data loaded successfully!", color="success")
        else:
            return None, [html.P("No data available", className="text-danger")], dbc.Alert("Error loading data", color="danger")
            
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return None, [html.P(f"Error: {str(e)}", className="text-danger")], dbc.Alert(f"Error: {str(e)}", color="danger")

# Callback for updating plots
@app.callback(
    [Output('scatter-plot', 'figure'),
     Output('timeseries-plot', 'figure')],
    Input('glacier-data-store', 'data'),
    prevent_initial_call=True
)
def update_plots(data_json):
    """Update plots when data is loaded."""
    if not data_json:
        empty_fig = go.Figure()
        empty_fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return empty_fig, empty_fig
    
    try:
        # Load data
        data = pd.read_json(data_json)
        
        # Create scatter plot
        scatter_fig = plot_components.create_scatter_plot(data)
        
        # Create time series plot
        timeseries_fig = plot_components.create_time_series_plot(data)
        
        return scatter_fig, timeseries_fig
        
    except Exception as e:
        logger.error(f"Error creating plots: {e}")
        error_fig = go.Figure()
        error_fig.add_annotation(
            text=f"Error creating plot: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return error_fig, error_fig

if __name__ == '__main__':
    # Get configuration
    config = data_manager.config
    app_config = config.get('app', {})
    
    # Run the app
    app.run_server(
        debug=app_config.get('debug', True),
        host=app_config.get('host', '127.0.0.1'),
        port=app_config.get('port', 8051)  # Different port to avoid conflicts
    )
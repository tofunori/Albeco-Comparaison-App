#!/usr/bin/env python3
"""
Fixed Interactive Albedo Analysis Dashboard

Version with improved error handling and simplified initial load.
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
import traceback
from typing import List

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


def calculate_scatter_plot_statistics(data, selected_methods=None):
    """Calculate correlation, bias, MAE, and RMSE for scatter plot data."""
    try:
        if data is None or data.empty:
            return {}
        
        # Filter methods if specified
        if selected_methods:
            plot_data = data[data['method'].isin(selected_methods)] if 'method' in data.columns else data
        else:
            plot_data = data
        
        # Check for required columns
        if 'albedo' not in plot_data.columns or 'aws_albedo' not in plot_data.columns:
            return {}
        
        statistics = {}
        
        # Calculate statistics for each method
        methods_in_data = plot_data['method'].unique() if 'method' in plot_data.columns else ['Overall']
        
        for method in methods_in_data:
            if 'method' in plot_data.columns:
                method_data = plot_data[plot_data['method'] == method]
            else:
                method_data = plot_data
            
            # Remove NaN values
            clean_data = method_data.dropna(subset=['albedo', 'aws_albedo'])
            
            if len(clean_data) < 2:
                continue
            
            x_vals = clean_data['aws_albedo'].values  # AWS (reference)
            y_vals = clean_data['albedo'].values     # MODIS (predicted)
            
            # Calculate statistics
            correlation = np.corrcoef(x_vals, y_vals)[0, 1]
            bias = np.mean(y_vals - x_vals)  # Mean difference (MODIS - AWS)
            mae = np.mean(np.abs(y_vals - x_vals))  # Mean Absolute Error
            rmse = np.sqrt(np.mean((y_vals - x_vals) ** 2))  # Root Mean Square Error
            
            statistics[method] = {
                'correlation': correlation,
                'bias': bias,
                'mae': mae,
                'rmse': rmse,
                'n_points': len(clean_data)
            }
        
        return statistics
        
    except Exception as e:
        logger.error(f"Error calculating scatter plot statistics: {e}")
        return {}


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
    data_manager = None
    plot_components = None

def create_layout():
    """Create the dashboard layout."""
    
    if data_manager is None:
        return html.Div([
            html.H1("Dashboard Error", className="text-center text-danger"),
            html.P("Error initializing dashboard components", className="text-center"),
        ])
    
    try:
        # Get available glaciers
        available_glaciers = data_manager.get_available_glaciers()
        glacier_options = [
            {'label': f"{g['name']} ({g['region']})", 'value': g['id']} 
            for g in available_glaciers
        ]
        
        layout = dbc.Container([
            # Store components
            dcc.Store(id='glacier-data-store'),
            dcc.Store(id='pixel-data-store'),
            dcc.Store(id='selected-pixels-store', data=[]),
            dcc.Store(id='current-glacier-store', data=None),
            
            # Download components
            dcc.Download(id="download-data"),
            dcc.Download(id="download-plot"),
            
            # Header
            dbc.Row([
                dbc.Col([
                    html.H2("Interactive Albedo Analysis Dashboard", className="text-primary mb-3"),
                    html.P("Select a glacier and load data to begin analysis.", className="text-muted")
                ])
            ], className="mb-4"),
            
            # Controls Row
            dbc.Row([
                # Sidebar Controls
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Glacier Selection"),
                        dbc.CardBody([
                            html.Label("Choose Glacier:"),
                            dcc.Dropdown(
                                id='glacier-dropdown',
                                options=glacier_options,
                                value="athabasca",  # Default to Athabasca Glacier
                                placeholder="Select a glacier",
                                clearable=False
                            ),
                            html.Br(),
                            dbc.Button("Load Data", id="load-data-btn", color="primary", size="sm"),
                            dbc.Spinner(html.Div(id='load-status', className='mt-2'), size="sm")
                        ])
                    ], className="mb-3"),
                    
                    dbc.Card([
                        dbc.CardHeader("MODIS Methods"),
                        dbc.CardBody([
                            dcc.Checklist(
                                id='method-checklist',
                                options=[
                                    {'label': 'MOD09GA', 'value': 'MOD09GA'},
                                    {'label': 'MYD09GA', 'value': 'MYD09GA'},
                                    {'label': 'MOD10A1', 'value': 'mod10a1'}, 
                                    {'label': 'MYD10A1', 'value': 'myd10a1'},
                                    {'label': 'MCD43A3', 'value': 'mcd43a3'}
                                ],
                                value=['MOD09GA', 'MYD09GA', 'mod10a1', 'myd10a1', 'mcd43a3'],
                                inline=True
                            )
                        ])
                    ], className="mb-3"),
                    
                    dbc.Card([
                        dbc.CardHeader("Analysis Controls"),
                        dbc.CardBody([
                            dbc.Button("Update Plots", id="update-plots-btn", color="success", size="sm", className="mb-2"),
                            dbc.Switch(id='aws-toggle', label='Include AWS data', value=True),
                            html.Hr(),
                            html.Label("Data Selection Mode:", className="form-label"),
                            dbc.Tooltip(
                                "Base dataset mode: All (use full dataset, filter by selection if any), Selected (require pixel selection), Best (highest quality data, filter by selection if any)",
                                target="data-mode-radio",
                                placement="top"
                            ),
                            dcc.RadioItems(
                                id='data-mode-radio',
                                options=[
                                    {'label': 'All pixels', 'value': 'all'},
                                    {'label': 'Selected pixels only', 'value': 'selected'},
                                    {'label': 'Best quality pixels', 'value': 'best'}
                                ],
                                value='all',
                                inline=True,
                                className='mb-2'
                            ),
                            html.Hr(),
                            html.Label("Export Options:", className="form-label"),
                            dbc.ButtonGroup([
                                dbc.Button("Export Data", id="export-data-btn", color="info", size="sm"),
                                dbc.Button("Export Plot", id="export-plot-btn", color="secondary", size="sm")
                            ], className="mb-2 d-block"),
                            dbc.Tooltip("Download current filtered data as CSV", target="export-data-btn", placement="top"),
                            dbc.Tooltip("Export current visualization (basic implementation)", target="export-plot-btn", placement="top"),
                            html.Hr(),
                            html.Div(id='pixel-selection-summary', className='mt-2')
                        ])
                    ])
                ], width=3),
                
                # Main Content
                dbc.Col([
                    # Data Summary
                    dbc.Card([
                        dbc.CardHeader("Data Summary"),
                        dbc.CardBody([
                            html.Div(id='data-summary', children="No data loaded")
                        ])
                    ], className="mb-3"),
                    
                    # Tabs for different views
                    dbc.Tabs([
                        dbc.Tab(label="Map & Selection", tab_id="map-tab"),
                        dbc.Tab(label="Scatter Analysis", tab_id="scatter-tab"),
                        dbc.Tab(label="Time Series", tab_id="timeseries-tab"),
                        dbc.Tab(label="Box Plots", tab_id="boxplot-tab"),
                        dbc.Tab(label="Histograms", tab_id="histogram-tab"),
                        dbc.Tab(label="Correlation", tab_id="correlation-tab"),
                        dbc.Tab(label="Statistics", tab_id="stats-tab")
                    ], id="tabs", active_tab="map-tab"),
                    
                    # Content based on active tab
                    dbc.Spinner(html.Div(id="tab-content", className="mt-3"), size="lg")
                    
                ], width=9)
            ]),
            
            # Footer with instructions
            html.Hr(),
            dbc.Row([
                dbc.Col([
                    html.Small([
                        "Instructions: ",
                        html.Strong("1) "), "Select a glacier and load data. ",
                        html.Strong("2) "), "Click pixel markers on the Map tab to select them (plots update automatically). ",
                        html.Strong("3) "), "Use other tabs to analyze selected pixel data. ",
                        html.Strong("4) "), "Export results as needed."
                    ], className="text-muted text-center")
                ])
            ], className="mb-3")
        ], fluid=True)
        
        return layout
        
    except Exception as e:
        logger.error(f"Error creating layout: {e}")
        return html.Div([
            html.H1("Layout Error", className="text-center text-danger"),
            html.P(f"Error: {str(e)}", className="text-center"),
        ])

# Set app layout
app.layout = create_layout()

# Auto-load Athabasca data on startup
@app.callback(
    [Output('glacier-data-store', 'data'),
     Output('pixel-data-store', 'data'),
     Output('current-glacier-store', 'data'),
     Output('data-summary', 'children'),
     Output('load-status', 'children'),
     Output('tabs', 'active_tab')],  # Also set active tab to map
    Input('glacier-dropdown', 'value'),
    prevent_initial_call=False  # Allow initial call to auto-load
)
def auto_load_default_data(glacier_id):
    """Auto-load data when glacier dropdown has a default value."""
    if not glacier_id:
        return None, None, None, "No data loaded", "", "map-tab"
    
    try:
        logger.info(f"Auto-loading data for {glacier_id}")
        
        # Load data with our data manager
        data = data_manager.load_glacier_data(glacier_id)
        pixel_data = data_manager.get_pixel_locations(glacier_id)
        
        if data is not None and not data.empty:
            # Create summary
            total_records = len(data)
            methods = list(data['method'].unique()) if 'method' in data.columns else []
            date_range = ""
            if 'date' in data.columns:
                date_range = f"{data['date'].min()} to {data['date'].max()}"
            
            pixel_count = data['pixel_id'].nunique() if 'pixel_id' in data.columns else 'N/A'
            
            summary = [
                html.P(f"📊 Total Records: {total_records:,}", className="mb-1"),
                html.P(f"🛰️ Methods: {', '.join(methods)}", className="mb-1"),
                html.P(f"📅 Date Range: {date_range}", className="mb-1"),
                html.P(f"🗺️ Pixels: {pixel_count}", className="mb-1")
            ]
            
            # Store data as JSON
            data_json = data.to_json(date_format='iso')
            pixel_json = pixel_data.to_json(date_format='iso') if pixel_data is not None else None
            
            status = dbc.Alert("✅ Data loaded automatically!", color="success", className="mt-2")
            
            return data_json, pixel_json, glacier_id, summary, status, "map-tab"
            
        else:
            return None, None, None, [html.P("❌ No data available", className="text-danger")], dbc.Alert("❌ No data found", color="warning"), "map-tab"
            
    except Exception as e:
        logger.error(f"Error auto-loading data for {glacier_id}: {e}")
        error_msg = [html.P(f"❌ Error: {str(e)}", className="text-danger")]
        status = dbc.Alert(f"❌ Error: {str(e)}", color="danger")
        return None, None, None, error_msg, status, "map-tab"

# Callback for loading data
@app.callback(
    [Output('glacier-data-store', 'data', allow_duplicate=True),
     Output('pixel-data-store', 'data', allow_duplicate=True),
     Output('current-glacier-store', 'data', allow_duplicate=True),
     Output('data-summary', 'children', allow_duplicate=True),
     Output('load-status', 'children', allow_duplicate=True)],
    Input('load-data-btn', 'n_clicks'),
    State('glacier-dropdown', 'value'),
    prevent_initial_call=True
)
def load_data(n_clicks, glacier_id):
    """Load glacier data when button is clicked."""
    if not n_clicks or not glacier_id:
        return None, None, None, "No data loaded", ""
    
    try:
        logger.info(f"Loading data for {glacier_id}")
        
        # Load data with our data manager
        data = data_manager.load_glacier_data(glacier_id)
        pixel_data = data_manager.get_pixel_locations(glacier_id)
        
        if data is not None and not data.empty:
            # Create summary
            total_records = len(data)
            methods = list(data['method'].unique()) if 'method' in data.columns else []
            date_range = ""
            if 'date' in data.columns:
                date_range = f"{data['date'].min()} to {data['date'].max()}"
            
            pixel_count = data['pixel_id'].nunique() if 'pixel_id' in data.columns else 'N/A'
            
            summary = [
                html.P(f"📊 Total Records: {total_records:,}", className="mb-1"),
                html.P(f"🛰️ Methods: {', '.join(methods)}", className="mb-1"),
                html.P(f"📅 Date Range: {date_range}", className="mb-1"),
                html.P(f"🗺️ Pixels: {pixel_count}", className="mb-1")
            ]
            
            # Store data as JSON
            data_json = data.to_json(date_format='iso')
            pixel_json = pixel_data.to_json(date_format='iso') if pixel_data is not None else None
            
            status = dbc.Alert("✅ Data loaded successfully!", color="success", className="mt-2")
            
            return data_json, pixel_json, glacier_id, summary, status
            
        else:
            return None, None, None, [html.P("❌ No data available", className="text-danger")], dbc.Alert("❌ No data found", color="warning")
            
    except Exception as e:
        logger.error(f"Error loading data for {glacier_id}: {e}")
        error_msg = [html.P(f"❌ Error: {str(e)}", className="text-danger")]
        status = dbc.Alert(f"❌ Error: {str(e)}", color="danger")
        return None, None, None, error_msg, status

# Callback for tab content
@app.callback(
    Output('tab-content', 'children'),
    [Input('tabs', 'active_tab'),
     Input('update-plots-btn', 'n_clicks'),
     Input('method-checklist', 'value'),
     Input('aws-toggle', 'value'),
     Input('data-mode-radio', 'value')],
    [State('glacier-data-store', 'data'),
     State('pixel-data-store', 'data'),
     State('current-glacier-store', 'data'),
     State('selected-pixels-store', 'data')],
    prevent_initial_call=True
)
def update_tab_content(active_tab, n_clicks, selected_methods, include_aws, data_mode, data_json, pixel_json, glacier_id, selected_pixels):
    """Update content based on active tab."""
    
    # Handle map tab separately (doesn't need plots button click)
    if active_tab == "map-tab":
        if not data_json or not pixel_json or not glacier_id:
            return dbc.Alert("🔄 Load data first to see the map", color="info")
        
        return create_map_content(pixel_json, glacier_id, selected_pixels or [])
    
    # Other tabs need data
    if not data_json:
        return dbc.Alert("🔄 Load data first to see visualizations", color="info")
    
    try:
        # Load data from JSON string using StringIO to avoid deprecation warning
        from io import StringIO
        data = pd.read_json(StringIO(data_json))
        
        # Apply data filtering based on mode
        data = _filter_data_by_mode(data, data_mode, selected_pixels)
        
        # Filter by methods
        if selected_methods and 'method' in data.columns:
            data = data[data['method'].isin(selected_methods)]
        
        # Handle AWS data
        if not include_aws:
            # Remove AWS columns
            aws_cols = [col for col in data.columns if 'aws' in col.lower()]
            for col in aws_cols:
                data[col] = None
        
        # Create status message for data filtering
        status_elements = []
        if selected_pixels:
            status_elements.append(
                dbc.Alert([
                    html.Strong("📊 Filtered View: "),
                    f"Showing {len(data):,} records from {len(selected_pixels)} selected pixel(s): {', '.join(selected_pixels)}"
                ], color="info", className="mb-2")
            )
        elif data_mode == 'best':
            status_elements.append(
                dbc.Alert([
                    html.Strong("🌟 Quality Filtered: "),
                    f"Showing {len(data):,} best quality records"
                ], color="success", className="mb-2")
            )
        else:
            status_elements.append(
                dbc.Alert([
                    html.Strong("📈 Full Dataset: "),
                    f"Showing all {len(data):,} records"
                ], color="light", className="mb-2")
            )
        
        if active_tab == "scatter-tab":
            fig = plot_components.create_scatter_plot(data, selected_methods)
            
            # Calculate statistics for scatter plot
            stats = calculate_scatter_plot_statistics(data, selected_methods)
            
            # Create statistics cards
            stats_cards = []
            if stats:
                for method, method_stats in stats.items():
                    stats_cards.append(
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader(html.H6(f"{method} Statistics", className="mb-0")),
                                dbc.CardBody([
                                    html.P([
                                        html.Strong("Correlation: "), f"{method_stats['correlation']:.3f}",
                                        html.Br(),
                                        html.Strong("Bias: "), f"{method_stats['bias']:.3f}",
                                        html.Br(),
                                        html.Strong("MAE: "), f"{method_stats['mae']:.3f}",
                                        html.Br(),
                                        html.Strong("RMSE: "), f"{method_stats['rmse']:.3f}",
                                        html.Br(),
                                        html.Small(f"n = {method_stats['n_points']} points", className="text-muted")
                                    ], className="mb-0")
                                ])
                            ])
                        ], width=12//min(len(stats), 4))  # Responsive columns
                    )
            
            # Combine plot and statistics
            content = status_elements + [
                dcc.Graph(figure=fig, style={'height': '500px'}),
                html.Hr(),
                html.H5("Statistical Metrics", className="mt-3 mb-3"),
                dbc.Row(stats_cards, className="mb-3") if stats_cards else html.P("No statistics available", className="text-muted")
            ]
            
            return html.Div(content)
            
        elif active_tab == "timeseries-tab":
            fig = plot_components.create_time_series_plot(data, selected_methods)
            return html.Div(status_elements + [dcc.Graph(figure=fig, style={'height': '500px'})])
            
        elif active_tab == "boxplot-tab":
            fig = plot_components.create_box_plot(data, selected_methods)
            return html.Div(status_elements + [dcc.Graph(figure=fig, style={'height': '500px'})])
            
        elif active_tab == "histogram-tab":
            fig = plot_components.create_histogram(data, selected_methods)
            return html.Div(status_elements + [dcc.Graph(figure=fig, style={'height': '500px'})])
            
        elif active_tab == "correlation-tab":
            fig = plot_components.create_correlation_matrix(data)
            return html.Div(status_elements + [dcc.Graph(figure=fig, style={'height': '500px'})])
            
        elif active_tab == "stats-tab":
            # Calculate basic statistics
            stats = data_manager.calculate_statistics(data, selected_methods)
            
            if stats:
                stats_cards = []
                for key, value in stats.items():
                    if isinstance(value, (int, float)):
                        if key == 'sample_size':
                            formatted_value = f"{value:,.0f}"
                        else:
                            formatted_value = f"{value:.4f}"
                    else:
                        formatted_value = str(value)
                    
                    stats_cards.append(
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(formatted_value, className="text-primary"),
                                html.P(key.replace('_', ' ').title())
                            ])
                        ], className="text-center")
                    )
                
                stats_content = [
                    dbc.Row([
                        dbc.Col(card, width=6 if len(stats_cards) <= 2 else 4)
                        for card in stats_cards[:6]  # Show max 6 stats
                    ])
                ]
                return html.Div(status_elements + stats_content)
            else:
                return html.Div(status_elements + [dbc.Alert("No statistics available", color="warning")])
        
        return html.P("Select a tab to view content")
        
    except Exception as e:
        logger.error(f"Error updating tab content: {e}")
        return dbc.Alert(f"Error creating visualization: {str(e)}", color="danger")

def create_map_content(pixel_json, glacier_id, selected_pixels):
    """Create the map content for the map tab."""
    try:
        from io import StringIO
        import pandas as pd
        
        # Load pixel data
        pixel_data = pd.read_json(StringIO(pixel_json))
        
        # Get glacier info for coordinates
        glacier_info = data_manager.glacier_config.get('glaciers', {}).get(glacier_id, {})
        coords = glacier_info.get('coordinates', {})
        center_lat = coords.get('lat', 52.0)
        center_lon = coords.get('lon', -117.0)
        
        # Create map elements
        map_children = [dl.TileLayer()]
        
        # Add pixel markers
        if not pixel_data.empty and 'latitude' in pixel_data.columns and 'longitude' in pixel_data.columns:
            for _, pixel in pixel_data.iterrows():
                pixel_id = str(pixel['pixel_id'])
                is_selected = pixel_id in selected_pixels
                
                marker_color = 'red' if is_selected else 'blue'
                marker_size = 25 if is_selected else 20  # Increased from 12/8 to 25/20
                
                # Create tooltip
                tooltip_text = f"Pixel ID: {pixel_id}\nLat: {pixel['latitude']:.4f}\nLon: {pixel['longitude']:.4f}"
                if 'glacier_fraction' in pixel:
                    tooltip_text += f"\nGlacier Fraction: {pixel['glacier_fraction']:.3f}"
                
                marker = dl.Marker(
                    position=[pixel['latitude'], pixel['longitude']],
                    id={'type': 'pixel-marker', 'pixel_id': pixel_id},
                    children=[
                        dl.Tooltip(tooltip_text),
                        dl.Popup([
                            html.Div([
                                html.P(f"Pixel ID: {pixel_id}"),
                                dbc.Button(
                                    "Toggle Selection" if pixel_id not in selected_pixels else "Remove Selection",
                                    id={'type': 'pixel-toggle-btn', 'pixel_id': pixel_id},
                                    color="primary" if pixel_id not in selected_pixels else "danger",
                                    size="sm"
                                )
                            ])
                        ])
                    ],
                    icon={
                        'iconUrl': f'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-{marker_color}.png',
                        'shadowUrl': 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                        'iconSize': [marker_size, marker_size],
                        'iconAnchor': [marker_size//2, marker_size],
                        'popupAnchor': [1, -marker_size],
                        'shadowSize': [marker_size, marker_size]
                    }
                )
                map_children.append(marker)
        
        # Add AWS station marker
        try:
            aws_info = data_manager.get_aws_station_info(glacier_id)
            if aws_info:
                aws_marker = dl.Marker(
                    position=[aws_info['lat'], aws_info['lon']],
                    id="aws-station-marker",
                    children=[dl.Tooltip(f"AWS Station: {aws_info.get('name', 'Station')}")],
                    icon={
                        'iconUrl': 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
                        'shadowUrl': 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                        'iconSize': [15, 15],
                        'iconAnchor': [7, 15],
                        'popupAnchor': [1, -15],
                        'shadowSize': [15, 15]
                    }
                )
                map_children.append(aws_marker)
        except Exception as e:
            logger.warning(f"Could not add AWS marker: {e}")
        
        # Create the map
        map_component = dl.Map(
            id="glacier-map",
            style={'width': '100%', 'height': '500px'},
            center=[center_lat, center_lon],
            zoom=12,
            children=map_children
        )
        
        # Create selection info
        selection_info = []
        if selected_pixels:
            selection_info = [
                html.H6(f"Selected Pixels ({len(selected_pixels)}):"),
                html.Ul([html.Li(f"Pixel {pid}") for pid in selected_pixels])
            ]
        else:
            selection_info = [html.P("Click on pixel markers and use popup buttons to select them for analysis", className="text-muted")]
        
        # Return map layout
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Interactive Glacier Map"),
                    dbc.CardBody([
                        map_component
                    ])
                ])
            ], width=8),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Pixel Selection"),
                    dbc.CardBody([
                        html.Div(selection_info, id="selection-info"),
                        html.Hr(),
                        dbc.Button("Clear Selection", id="clear-selection-btn", color="warning", size="sm"),
                        html.Div([
                            html.Small("Blue markers: Unselected pixels", className="text-muted d-block"),
                            html.Small("Red markers: Selected pixels", className="text-muted d-block"),
                            html.Small("Green markers: AWS station", className="text-muted d-block"),
                            html.Small("Click markers → Use popup buttons to select", className="text-info d-block mt-1")
                        ], className="mt-2")
                    ])
                ])
            ], width=4)
        ])
        
    except Exception as e:
        logger.error(f"Error creating map content: {e}")
        return dbc.Alert(f"Error creating map: {str(e)}", color="danger")

def _filter_data_by_mode(data: pd.DataFrame, data_mode: str, selected_pixels: List[str]) -> pd.DataFrame:
    """Filter data based on the selected data mode and pixel selection."""
    try:
        filtered_data = data.copy()
        
        # Step 1: Apply data mode filtering
        if data_mode == 'best' and 'qa_mode' in filtered_data.columns:
            # Filter to best quality data first
            best_data = filtered_data[filtered_data['qa_mode'] == 'clear_land']
            if best_data.empty:
                # Fallback to any available QA mode if 'clear_land' is not available
                qa_modes = filtered_data['qa_mode'].unique()
                logger.info(f"Available QA modes: {qa_modes}")
                # Take the mode that appears most frequently (likely the best available)
                best_mode = filtered_data['qa_mode'].mode().iloc[0] if not filtered_data['qa_mode'].mode().empty else qa_modes[0]
                best_data = filtered_data[filtered_data['qa_mode'] == best_mode]
            filtered_data = best_data
            logger.info(f"Applied 'best' quality filter: {len(filtered_data)} records")
        
        # Step 2: Apply pixel selection filter (ALWAYS when pixels are selected)
        if selected_pixels and 'pixel_id' in filtered_data.columns and len(selected_pixels) > 0:
            # Normalize pixel IDs for consistent matching
            normalized_selected_pixels = []
            for pid in selected_pixels:
                normalized_pid = str(pid)
                if normalized_pid.endswith('.0'):
                    normalized_pid = normalized_pid[:-2]
                normalized_selected_pixels.append(normalized_pid)
            
            # Always filter by selected pixels when pixels are selected, regardless of data mode
            data_pixel_ids = filtered_data['pixel_id'].astype(str)
            # Also normalize data pixel IDs to handle any float conversion
            normalized_data_pixel_ids = [pid[:-2] if pid.endswith('.0') else pid for pid in data_pixel_ids]
            filtered_data['normalized_pixel_id'] = normalized_data_pixel_ids
            
            pixel_filtered_data = filtered_data[filtered_data['normalized_pixel_id'].isin(normalized_selected_pixels)]
            
            # Remove the temporary column
            if not pixel_filtered_data.empty:
                pixel_filtered_data = pixel_filtered_data.drop('normalized_pixel_id', axis=1)
            
            if not pixel_filtered_data.empty:
                filtered_data = pixel_filtered_data
                logger.info(f"Applied pixel selection filter: {len(filtered_data)} records for pixels {selected_pixels}")
            else:
                logger.warning(f"No data found for selected pixels {selected_pixels}, keeping current dataset")
        
        # Log final result
        if data_mode == 'selected' and (not selected_pixels or len(selected_pixels) == 0):
            # Special case: 'selected' mode but no pixels selected
            logger.info("Data mode is 'selected' but no pixels are selected - returning empty dataset")
            return pd.DataFrame()  # Return empty dataframe
        
        logger.info(f"Final filtered dataset: {len(filtered_data)} records (mode: {data_mode}, selected pixels: {len(selected_pixels) if selected_pixels else 0})")
        return filtered_data
            
    except Exception as e:
        logger.error(f"Error filtering data by mode: {e}")
        return data

# Callback for pixel selection from popup buttons
@app.callback(
    [Output('selected-pixels-store', 'data'),
     Output('selection-info', 'children')],
    [Input({'type': 'pixel-toggle-btn', 'pixel_id': dash.dependencies.ALL}, 'n_clicks')],
    [State('selected-pixels-store', 'data'),
     State('pixel-data-store', 'data')],
    prevent_initial_call=True
)
def handle_pixel_selection(n_clicks_list, current_selected, pixel_json):
    """Handle pixel selection from popup buttons."""
    if not pixel_json:
        return current_selected or [], [html.P("No pixel data available", className="text-muted")]
    
    try:
        current_selected = current_selected or []
        
        # Check if any button was clicked
        if n_clicks_list and any(n_clicks_list):
            # Get the triggered component
            if ctx.triggered:
                triggered_id = ctx.triggered[0]['prop_id']
                logger.info(f"Button triggered: {triggered_id}")
                
                # Extract pixel_id from triggered component
                if 'pixel_id' in triggered_id:
                    try:
                        # The triggered_id looks like: {"pixel_id":"9073025950.0","type":"pixel-toggle-btn"}.n_clicks
                        # Let's use a more direct regex approach since JSON parsing is problematic
                        import re
                        pixel_id_match = re.search(r'"pixel_id":"([^"]+)"', triggered_id)
                        
                        if pixel_id_match:
                            pixel_id = pixel_id_match.group(1)
                            # Normalize pixel ID format: remove .0 if present
                            if pixel_id.endswith('.0'):
                                pixel_id = pixel_id[:-2]
                            logger.info(f"Extracted and normalized pixel_id: {pixel_id}")
                            
                            # Toggle pixel selection
                            if pixel_id in current_selected:
                                current_selected.remove(pixel_id)
                                logger.info(f"Removed pixel {pixel_id}")
                            else:
                                current_selected.append(pixel_id)
                                logger.info(f"Added pixel {pixel_id}")
                        else:
                            logger.error(f"Could not extract pixel_id from: {triggered_id}")
                            
                    except Exception as parse_error:
                        logger.error(f"Error parsing button ID: {parse_error}")
                        # Final fallback - try to extract any numeric value that looks like a pixel ID
                        import re
                        numbers = re.findall(r'\d+\.?\d*', triggered_id)
                        if numbers:
                            pixel_id = numbers[0]  # Take the first number found
                            # Normalize pixel ID format: remove .0 if present
                            if pixel_id.endswith('.0'):
                                pixel_id = pixel_id[:-2]
                            logger.info(f"Fallback extracted and normalized pixel_id: {pixel_id}")
                            if pixel_id in current_selected:
                                current_selected.remove(pixel_id)
                            else:
                                current_selected.append(pixel_id)
        
        # Update selection info
        if current_selected:
            selection_info = [
                html.H6(f"Selected Pixels ({len(current_selected)}):"),
                html.Ul([html.Li(f"Pixel {pid}") for pid in current_selected])
            ]
        else:
            selection_info = [html.P("Click on pixel markers and use popup buttons to select", className="text-muted")]
        
        return current_selected, selection_info
        
    except Exception as e:
        logger.error(f"Error handling pixel selection: {e}")
        import traceback
        traceback.print_exc()
        return current_selected or [], [html.P("Error handling selection", className="text-danger")]

# Callback for clearing selection
@app.callback(
    Output('selected-pixels-store', 'data', allow_duplicate=True),
    Input('clear-selection-btn', 'n_clicks'),
    prevent_initial_call=True
)
def clear_selection(n_clicks):
    """Clear pixel selection."""
    if n_clicks:
        return []
    return dash.no_update

# Callback to update map when selection changes
@app.callback(
    Output('tab-content', 'children', allow_duplicate=True),
    [Input('selected-pixels-store', 'data'),
     Input('method-checklist', 'value'),
     Input('aws-toggle', 'value'),
     Input('data-mode-radio', 'value')],
    [State('tabs', 'active_tab'),
     State('pixel-data-store', 'data'),
     State('current-glacier-store', 'data'),
     State('glacier-data-store', 'data')],
    prevent_initial_call=True
)
def update_content_on_selection(selected_pixels, selected_methods, include_aws, data_mode, active_tab, pixel_json, glacier_id, data_json):
    """Update content when pixel selection changes."""
    if not data_json or not glacier_id:
        return dash.no_update
        
    if active_tab == "map-tab" and pixel_json:
        return create_map_content(pixel_json, glacier_id, selected_pixels or [])
    
    # For other tabs, update the visualizations with selected pixels
    elif active_tab in ["scatter-tab", "timeseries-tab", "boxplot-tab", "histogram-tab", "correlation-tab", "stats-tab"]:
        try:
            from io import StringIO
            data = pd.read_json(StringIO(data_json))
            
            # Apply data filtering based on mode
            data = _filter_data_by_mode(data, data_mode, selected_pixels)
            
            # Show message if no data after filtering
            if data.empty:
                return dbc.Alert(f"No data available for current selection mode", color="warning")
            
            # Filter by methods
            if selected_methods and 'method' in data.columns:
                data = data[data['method'].isin(selected_methods)]
            
            # Handle AWS data
            if not include_aws:
                aws_cols = [col for col in data.columns if 'aws' in col.lower()]
                for col in aws_cols:
                    data[col] = None
            
            # Create status message for data filtering
            status_elements = []
            if selected_pixels:
                status_elements.append(
                    dbc.Alert([
                        html.Strong("📊 Filtered View: "),
                        f"Showing {len(data):,} records from {len(selected_pixels)} selected pixel(s): {', '.join(selected_pixels)}"
                    ], color="info", className="mb-2")
                )
            elif data_mode == 'best':
                status_elements.append(
                    dbc.Alert([
                        html.Strong("🌟 Quality Filtered: "),
                        f"Showing {len(data):,} best quality records"
                    ], color="success", className="mb-2")
                )
            else:
                status_elements.append(
                    dbc.Alert([
                        html.Strong("📈 Full Dataset: "),
                        f"Showing all {len(data):,} records"
                    ], color="light", className="mb-2")
                )
            
            if active_tab == "scatter-tab":
                fig = plot_components.create_scatter_plot(data, selected_methods)
                
                # Calculate statistics for scatter plot
                stats = calculate_scatter_plot_statistics(data, selected_methods)
                
                # Create statistics cards
                stats_cards = []
                if stats:
                    for method, method_stats in stats.items():
                        stats_cards.append(
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader(html.H6(f"{method} Statistics", className="mb-0")),
                                    dbc.CardBody([
                                        html.P([
                                            html.Strong("Correlation: "), f"{method_stats['correlation']:.3f}",
                                            html.Br(),
                                            html.Strong("Bias: "), f"{method_stats['bias']:.3f}",
                                            html.Br(),
                                            html.Strong("MAE: "), f"{method_stats['mae']:.3f}",
                                            html.Br(),
                                            html.Strong("RMSE: "), f"{method_stats['rmse']:.3f}",
                                            html.Br(),
                                            html.Small(f"n = {method_stats['n_points']} points", className="text-muted")
                                        ], className="mb-0")
                                    ])
                                ])
                            ], width=12//min(len(stats), 4))  # Responsive columns
                        )
                
                # Combine plot and statistics
                content = status_elements + [
                    dcc.Graph(figure=fig, style={'height': '500px'}),
                    html.Hr(),
                    html.H5("Statistical Metrics", className="mt-3 mb-3"),
                    dbc.Row(stats_cards, className="mb-3") if stats_cards else html.P("No statistics available", className="text-muted")
                ]
                
                return html.Div(content)
                
            elif active_tab == "timeseries-tab":
                fig = plot_components.create_time_series_plot(data, selected_methods)
                return html.Div(status_elements + [dcc.Graph(figure=fig, style={'height': '500px'})])
                
            elif active_tab == "boxplot-tab":
                fig = plot_components.create_box_plot(data, selected_methods)
                return html.Div(status_elements + [dcc.Graph(figure=fig, style={'height': '500px'})])
                
            elif active_tab == "histogram-tab":
                fig = plot_components.create_histogram(data, selected_methods)
                return html.Div(status_elements + [dcc.Graph(figure=fig, style={'height': '500px'})])
                
            elif active_tab == "correlation-tab":
                fig = plot_components.create_correlation_matrix(data)
                return html.Div(status_elements + [dcc.Graph(figure=fig, style={'height': '500px'})])
                
            elif active_tab == "stats-tab":
                stats = data_manager.calculate_statistics(data, selected_methods)
                
                if stats:
                    stats_cards = []
                    for key, value in stats.items():
                        if isinstance(value, (int, float)):
                            if key == 'sample_size':
                                formatted_value = f"{value:,.0f}"
                            else:
                                formatted_value = f"{value:.4f}"
                        else:
                            formatted_value = str(value)
                        
                        stats_cards.append(
                            dbc.Card([
                                dbc.CardBody([
                                    html.H4(formatted_value, className="text-primary"),
                                    html.P(key.replace('_', ' ').title())
                                ])
                            ], className="text-center")
                        )
                    
                    stats_content = [
                        dbc.Row([
                            dbc.Col(card, width=6 if len(stats_cards) <= 2 else 4)
                            for card in stats_cards[:6]
                        ])
                    ]
                    return html.Div(status_elements + stats_content)
                else:
                    return html.Div(status_elements + [dbc.Alert("No statistics available for selected data", color="warning")])
                    
        except Exception as e:
            logger.error(f"Error updating content on selection: {e}")
            return dbc.Alert(f"Error updating visualization: {str(e)}", color="danger")
    
    return dash.no_update

# Callback to update pixel selection summary in sidebar
@app.callback(
    Output('pixel-selection-summary', 'children'),
    [Input('selected-pixels-store', 'data'),
     Input('glacier-data-store', 'data')],
    prevent_initial_call=True
)
def update_pixel_selection_summary(selected_pixels, data_json):
    """Update the pixel selection summary in the sidebar."""
    if not selected_pixels:
        return html.Small("No pixels selected", className="text-muted")
    
    try:
        summary_content = [
            html.Small(f"Selected: {len(selected_pixels)} pixel(s)", className="text-primary d-block"),
            html.Small(f"Pixels: {', '.join(selected_pixels)}", className="text-muted d-block")
        ]
        
        # If we have data, calculate how many records are for selected pixels
        if data_json:
            from io import StringIO
            data = pd.read_json(StringIO(data_json))
            
            if 'pixel_id' in data.columns:
                # Normalize pixel IDs for consistent matching
                normalized_selected_pixels = []
                for pid in selected_pixels:
                    normalized_pid = str(pid)
                    if normalized_pid.endswith('.0'):
                        normalized_pid = normalized_pid[:-2]
                    normalized_selected_pixels.append(normalized_pid)
                
                # Normalize data pixel IDs and filter
                data_pixel_ids = data['pixel_id'].astype(str)
                normalized_data_pixel_ids = [pid[:-2] if pid.endswith('.0') else pid for pid in data_pixel_ids]
                data['normalized_pixel_id'] = normalized_data_pixel_ids
                
                selected_data = data[data['normalized_pixel_id'].isin(normalized_selected_pixels)]
                record_count = len(selected_data)
                
                summary_content.append(
                    html.Small(f"Records: {record_count:,}", className="text-success d-block")
                )
        
        return summary_content
        
    except Exception as e:
        logger.error(f"Error updating pixel selection summary: {e}")
        return html.Small("Error updating summary", className="text-danger")

# Callback for exporting data
@app.callback(
    Output("download-data", "data"),
    Input("export-data-btn", "n_clicks"),
    [State('glacier-data-store', 'data'),
     State('selected-pixels-store', 'data'),
     State('method-checklist', 'value'),
     State('data-mode-radio', 'value'),
     State('current-glacier-store', 'data')],
    prevent_initial_call=True
)
def export_data(n_clicks, data_json, selected_pixels, selected_methods, data_mode, glacier_id):
    """Export the current filtered data as CSV."""
    if not n_clicks or not data_json:
        return dash.no_update
        
    try:
        from io import StringIO
        data = pd.read_json(StringIO(data_json))
        
        # Apply the same filtering as the visualizations
        data = _filter_data_by_mode(data, data_mode, selected_pixels)
        
        if selected_methods and 'method' in data.columns:
            data = data[data['method'].isin(selected_methods)]
        
        if data.empty:
            return dash.no_update
            
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"albedo_data_{glacier_id}_{data_mode}_{timestamp}.csv"
        
        return dcc.send_data_frame(data.to_csv, filename, index=False)
        
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        return dash.no_update

# Callback for exporting plots (basic implementation)
@app.callback(
    Output("download-plot", "data"),
    Input("export-plot-btn", "n_clicks"),
    [State('tabs', 'active_tab'),
     State('current-glacier-store', 'data')],
    prevent_initial_call=True
)
def export_plot(n_clicks, active_tab, glacier_id):
    """Export the current plot (placeholder - would need plot state to implement fully)."""
    if not n_clicks or not glacier_id:
        return dash.no_update
        
    try:
        # This is a placeholder - in a full implementation you'd capture the current plot
        # For now, just return a message file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"plot_export_{glacier_id}_{active_tab}_{timestamp}.txt"
        
        message = f"Plot export requested for {glacier_id} - {active_tab} at {timestamp}\n"
        message += "Note: Full plot export functionality would require additional implementation."
        
        return dict(content=message, filename=filename)
        
    except Exception as e:
        logger.error(f"Error exporting plot: {e}")
        return dash.no_update

if __name__ == '__main__':
    print("🚀 Starting Fixed Albedo Dashboard...")
    print("📊 Dashboard will be available at: http://127.0.0.1:8054")
    print("🛑 Press Ctrl+C to stop")
    
    app.run_server(
        debug=True,
        host='127.0.0.1',
        port=8054  # Different port
    )
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
                                    {'label': 'Best quality pixels', 'value': 'best'},
                                    {'label': 'Closest to AWS', 'value': 'closest_aws'},
                                    {'label': 'High glacier fraction', 'value': 'high_glacier_fraction'},
                                    {'label': 'Custom filters', 'value': 'custom'}
                                ],
                                value='all',
                                inline=False,
                                className='mb-2'
                            ),
                            
                            # Advanced filtering controls (shown when custom mode is selected)
                            html.Div([
                                html.Hr(),
                                html.Label("Advanced Filters:", className="form-label"),
                                
                                # Distance filtering controls
                                html.Div([
                                    dbc.Switch(
                                        id='distance-filter-toggle',
                                        label='Distance Filter',
                                        value=False,
                                        className='mb-2'
                                    ),
                                    html.Div([
                                        html.Label("Number of closest pixels:", className="form-label small"),
                                        dcc.Slider(
                                            id='closest-pixels-slider',
                                            min=1, max=20, step=1, value=5,
                                            marks={i: str(i) for i in [1, 5, 10, 15, 20]},
                                            tooltip={"placement": "bottom", "always_visible": True}
                                        ),
                                        html.Label("Max distance (km):", className="form-label small mt-2"),
                                        dcc.Input(
                                            id='max-distance-input',
                                            type='number',
                                            placeholder='e.g., 10.0',
                                            value=10.0,
                                            min=0.1, max=50.0, step=0.1,
                                            size='10',
                                            className='form-control form-control-sm mb-2'
                                        )
                                    ], id='distance-filter-controls', style={'display': 'none'})
                                ]),
                                
                                # Glacier fraction filtering controls
                                html.Div([
                                    dbc.Switch(
                                        id='fraction-filter-toggle',
                                        label='Glacier Fraction Filter',
                                        value=False,
                                        className='mb-2'
                                    ),
                                    html.Div([
                                        html.Label("Minimum glacier fraction:", className="form-label small"),
                                        dcc.Slider(
                                            id='glacier-fraction-slider',
                                            min=0.0, max=1.0, step=0.1, value=0.7,
                                            marks={i/10: f'{i/10:.1f}' for i in range(0, 11, 2)},
                                            tooltip={"placement": "bottom", "always_visible": True}
                                        )
                                    ], id='fraction-filter-controls', style={'display': 'none'})
                                ])
                            ], id='advanced-filters-section', style={'display': 'none'}),
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
     Input('data-mode-radio', 'value'),
     Input('distance-filter-toggle', 'value'),
     Input('closest-pixels-slider', 'value'),
     Input('max-distance-input', 'value'),
     Input('fraction-filter-toggle', 'value'),
     Input('glacier-fraction-slider', 'value')],
    [State('glacier-data-store', 'data'),
     State('pixel-data-store', 'data'),
     State('current-glacier-store', 'data'),
     State('selected-pixels-store', 'data')],
    prevent_initial_call=True
)
def update_tab_content(active_tab, n_clicks, selected_methods, include_aws, data_mode, 
                      use_distance_filter, top_n_closest, max_distance_km,
                      use_fraction_filter, min_glacier_fraction,
                      data_json, pixel_json, glacier_id, selected_pixels):
    """Update content based on active tab."""
    
    # Handle map tab separately (doesn't need plots button click)
    if active_tab == "map-tab":
        if not data_json or not pixel_json or not glacier_id:
            return dbc.Alert("🔄 Load data first to see the map", color="info")
        
        # Build filter parameters for map
        filter_params = {
            'data_mode': data_mode,
            'use_distance_filter': use_distance_filter,
            'top_n_closest': top_n_closest,
            'max_distance_km': max_distance_km,
            'use_glacier_fraction': use_fraction_filter,
            'min_glacier_fraction': min_glacier_fraction
        }
        return create_map_content(pixel_json, glacier_id, selected_pixels or [], data_json, filter_params)
    
    # Other tabs need data
    if not data_json:
        return dbc.Alert("🔄 Load data first to see visualizations", color="info")
    
    try:
        # Load data from JSON string using StringIO to avoid deprecation warning
        from io import StringIO
        data = pd.read_json(StringIO(data_json))
        
        # Get glacier info for enhanced filtering
        glacier_info = data_manager.glacier_config.get('glaciers', {}).get(glacier_id, {})
        
        # Build filter parameters
        filter_params = {
            'use_distance_filter': use_distance_filter,
            'top_n_closest': top_n_closest,
            'max_distance_km': max_distance_km,
            'use_glacier_fraction': use_fraction_filter,
            'min_glacier_fraction': min_glacier_fraction
        }
        
        # Apply enhanced data filtering
        data = _filter_data_by_mode_enhanced(data, data_mode, selected_pixels, glacier_info, filter_params)
        
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

def get_pixel_marker_style(pixel_id, is_selected, passes_filter, filter_params=None):
    """Determine marker style based on pixel state."""
    # DEBUG: Log parameters for troubleshooting
    logger.info(f"Styling pixel {pixel_id}: is_selected={is_selected}, passes_filter={passes_filter}, filter_params={filter_params}")
    
    # Define marker styles for different states
    styles = {
        'excluded': {
            'color': 'grey',
            'size': 15,
            'opacity': 0.5,
            'icon_url': 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-grey.png'
        },
        'default': {
            'color': 'blue',
            'size': 20,
            'opacity': 0.8,
            'icon_url': 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png'
        },
        'filtered': {
            'color': 'green',
            'size': 25,
            'opacity': 1.0,
            'icon_url': 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png'
        },
        'selected': {
            'color': 'red',
            'size': 30,
            'opacity': 1.0,
            'icon_url': 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png'
        },
        'filtered_selected': {
            'color': 'orange',
            'size': 32,
            'opacity': 1.0,
            'icon_url': 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-orange.png'
        }
    }
    
    # Determine pixel state
    if is_selected and passes_filter:
        return styles['filtered_selected']
    elif is_selected:
        return styles['selected']
    elif passes_filter:
        return styles['filtered']
    elif filter_params and (filter_params.get('use_distance_filter') or filter_params.get('use_glacier_fraction')):
        # If any filter is active but pixel doesn't pass, mark as excluded
        return styles['excluded']
    else:
        return styles['default']

def determine_filtered_pixels(pixel_data, data_json, glacier_id, filter_params):
    """Determine which pixels pass the current filters."""
    try:
        if not filter_params or not data_json:
            return set()
            
        from io import StringIO
        import pandas as pd
        
        # Load full data for filtering calculations
        data = pd.read_json(StringIO(data_json))
        
        # For custom filters mode, apply filtering directly here based on pixel-level data
        data_mode = filter_params.get('data_mode', 'all')
        
        if data_mode == 'custom':
            # Apply glacier fraction filtering if enabled
            if filter_params.get('use_glacier_fraction', False):
                min_fraction = filter_params.get('min_glacier_fraction', 0.7)
                
                # Get unique pixels with their glacier fractions
                if 'glacier_fraction' not in pixel_data.columns:
                    logger.error(f"glacier_fraction column not found in pixel_data. Available columns: {list(pixel_data.columns)}")
                    return set()
                    
                unique_pixels = pixel_data[['pixel_id', 'glacier_fraction']].drop_duplicates()
                logger.info(f"Unique pixels shape: {unique_pixels.shape}")
                logger.info(f"Glacier fraction values: {unique_pixels['glacier_fraction'].unique()[:5]}...")
                
                # Filter pixels that pass the glacier fraction threshold
                passing_pixels = unique_pixels[unique_pixels['glacier_fraction'] >= min_fraction]
                
                logger.info(f"Glacier fraction filter: {len(passing_pixels)} out of {len(unique_pixels)} pixels pass (>= {min_fraction})")
                result_set = set(str(pid) for pid in passing_pixels['pixel_id'].unique())
                logger.info(f"Returning pixel IDs: {result_set}")
                return result_set
            
            # If no specific filters are enabled, return all pixels
            return set(str(pid) for pid in pixel_data['pixel_id'].unique())
        
        elif data_mode in ['high_glacier_fraction', 'closest_aws']:
            # For other special modes, use the enhanced filtering
            glacier_info = data_manager.glacier_config.get('glaciers', {}).get(glacier_id, {})
            filtered_data = _filter_data_by_mode_enhanced(data, data_mode, [], glacier_info, filter_params)
            
            # Return set of pixel IDs that pass filters
            if 'pixel_id' in filtered_data.columns:
                return set(str(pid) for pid in filtered_data['pixel_id'].unique())
            else:
                return set()
        
        else:
            # For 'all', 'selected', 'best' modes, no filtering applied
            return set(str(pid) for pid in pixel_data['pixel_id'].unique())
            
    except Exception as e:
        logger.error(f"Error determining filtered pixels: {e}")
        import traceback
        traceback.print_exc()
        return set()

def create_map_content(pixel_json, glacier_id, selected_pixels, data_json=None, filter_params=None):
    """Create the map content for the map tab with enhanced filtering visualization."""
    try:
        from io import StringIO
        import pandas as pd
        
        # Load pixel data
        pixel_data = pd.read_json(StringIO(pixel_json))
        logger.info(f"Pixel data columns: {list(pixel_data.columns)}")
        logger.info(f"Pixel data shape: {pixel_data.shape}")
        
        # Determine which pixels pass current filters
        filtered_pixel_ids = determine_filtered_pixels(pixel_data, data_json, glacier_id, filter_params)
        logger.info(f"Filtered pixel IDs: {filtered_pixel_ids} (count: {len(filtered_pixel_ids)})")
        logger.info(f"All pixel IDs in data: {set(str(p) for p in pixel_data['pixel_id'].unique())}")
        
        # Calculate map center from actual pixel data (more accurate than config)
        if not pixel_data.empty and 'latitude' in pixel_data.columns and 'longitude' in pixel_data.columns:
            center_lat = pixel_data['latitude'].mean()
            center_lon = pixel_data['longitude'].mean()
            logger.info(f"Map center calculated from pixel data: lat={center_lat:.6f}, lon={center_lon:.6f}")
        else:
            # Fallback to configuration coordinates
            glacier_info = data_manager.glacier_config.get('glaciers', {}).get(glacier_id, {})
            coords = glacier_info.get('coordinates', {})
            center_lat = coords.get('lat', 52.0)
            center_lon = coords.get('lon', -117.0)
            logger.info(f"Using config coordinates as fallback: lat={center_lat}, lon={center_lon}")
        
        # Create map elements
        map_children = [dl.TileLayer()]
        
        # Add enhanced pixel markers with filtering visualization
        if not pixel_data.empty and 'latitude' in pixel_data.columns and 'longitude' in pixel_data.columns:
            for _, pixel in pixel_data.iterrows():
                pixel_id = str(pixel['pixel_id'])
                is_selected = pixel_id in selected_pixels
                passes_filter = pixel_id in filtered_pixel_ids
                
                # DEBUG: Log filter determination
                logger.info(f"Pixel {pixel_id}: in selected_pixels={is_selected}, in filtered_pixel_ids={passes_filter}")
                
                # Get enhanced marker style
                style = get_pixel_marker_style(pixel_id, is_selected, passes_filter, filter_params)
                # Log for debugging first few pixels to avoid spam
                if _ < 3:  # Only log first 3 pixels to avoid spam
                    logger.info(f"Pixel {pixel_id}: is_selected={is_selected}, passes_filter={passes_filter}, style_color={style['color']}")
                
                # Create enhanced tooltip with filter information
                tooltip_text = f"Pixel ID: {pixel_id}\nLat: {pixel['latitude']:.4f}\nLon: {pixel['longitude']:.4f}"
                if 'glacier_fraction' in pixel:
                    tooltip_text += f"\nGlacier Fraction: {pixel['glacier_fraction']:.3f}"
                
                # Add filter-specific information to tooltip
                if filter_params:
                    if filter_params.get('use_distance_filter') and data_json:
                        tooltip_text += f"\n{'✓' if passes_filter else '✗'} Distance Filter"
                    if filter_params.get('use_glacier_fraction'):
                        min_fraction = filter_params.get('min_glacier_fraction', 0.7)
                        tooltip_text += f"\n{'✓' if passes_filter else '✗'} Glacier Fraction ≥ {min_fraction}"
                
                # Enhanced popup with filter status
                popup_content = [
                    html.P(f"Pixel ID: {pixel_id}"),
                    html.P(f"Status: {'✓ Passes filters' if passes_filter else '✗ Excluded by filters'}", 
                          className="text-success" if passes_filter else "text-muted"),
                    dbc.Button(
                        "Toggle Selection" if pixel_id not in selected_pixels else "Remove Selection",
                        id={'type': 'pixel-toggle-btn', 'pixel_id': pixel_id},
                        color="primary" if pixel_id not in selected_pixels else "danger",
                        size="sm"
                    )
                ]
                
                # Use CircleMarker with dynamic ID for color changes (dash-leaflet requirement)
                # Include filter state and timestamp in ID to force re-render when colors change
                filter_state = f"{passes_filter}_{style['color']}"
                import time
                timestamp = int(time.time() * 1000) % 10000  # Short timestamp to avoid long IDs
                
                marker = dl.CircleMarker(
                    center=[pixel['latitude'], pixel['longitude']],
                    id={'type': 'pixel-marker', 'pixel_id': pixel_id, 'filter_state': filter_state, 'ts': timestamp},
                    children=[
                        dl.Tooltip(tooltip_text),
                        dl.Popup(html.Div(popup_content))
                    ],
                    radius=style['size'] // 2,
                    fillColor=style['color'],
                    color=style['color'],
                    weight=2,
                    opacity=style['opacity'],
                    fillOpacity=style['opacity'] * 0.8
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
        
        # Create enhanced selection info and filtering stats
        selection_info = []
        if selected_pixels:
            selection_info = [
                html.H6(f"Selected Pixels ({len(selected_pixels)}):"),
                html.Ul([html.Li(f"Pixel {pid}") for pid in selected_pixels])
            ]
        else:
            selection_info = [html.P("Click on pixel markers and use popup buttons to select them for analysis", className="text-muted")]
        
        # Create filtering statistics
        total_pixels = len(pixel_data)
        filtered_pixels_count = len(filtered_pixel_ids)
        selected_pixels_count = len(selected_pixels)
        filtered_and_selected = len(set(selected_pixels) & filtered_pixel_ids)
        
        filter_stats = []
        if filter_params and (filter_params.get('use_distance_filter') or filter_params.get('use_glacier_fraction')):
            filter_stats = [
                html.H6("Filter Statistics:", className="mt-3"),
                html.P(f"📊 Total pixels: {total_pixels}", className="mb-1 small"),
                html.P(f"✅ Pass filters: {filtered_pixels_count}", className="mb-1 small text-success"),
                html.P(f"🔴 Selected: {selected_pixels_count}", className="mb-1 small text-danger"),
                html.P(f"🟠 Both filtered & selected: {filtered_and_selected}", className="mb-1 small text-warning"),
            ]
        
        # Create enhanced legend
        legend_items = []
        if filter_params and (filter_params.get('use_distance_filter') or filter_params.get('use_glacier_fraction')):
            legend_items = [
                html.Small("● Available pixels", className="text-primary d-block", style={'color': 'blue'}),
                html.Small("● Pass current filters", className="text-success d-block", style={'color': 'green'}),
                html.Small("● Manually selected", className="text-danger d-block", style={'color': 'red'}),
                html.Small("● Filtered + Selected", className="text-warning d-block", style={'color': 'orange'}),
                html.Small("● Excluded by filters", className="text-muted d-block", style={'color': 'grey'}),
                html.Small("▲ AWS station", className="text-success d-block", style={'color': 'green'}),
            ]
        else:
            legend_items = [
                html.Small("● Available pixels", className="text-primary d-block", style={'color': 'blue'}),
                html.Small("● Selected pixels", className="text-danger d-block", style={'color': 'red'}),
                html.Small("▲ AWS station", className="text-success d-block", style={'color': 'green'}),
            ]
        
        # Return enhanced map layout
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Interactive Glacier Map with Live Filtering"),
                    dbc.CardBody([
                        map_component
                    ])
                ])
            ], width=8),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Pixel Selection & Filtering"),
                    dbc.CardBody([
                        html.Div(selection_info, id="selection-info"),
                        html.Hr(),
                        dbc.Button("Clear Selection", id="clear-selection-btn", color="warning", size="sm"),
                        html.Div(filter_stats),
                        html.Hr() if filter_stats else None,
                        html.H6("Map Legend:", className="mt-2"),
                        html.Div(legend_items, className="mt-2"),
                        html.Hr(),
                        html.Small("💡 Tip: Change filter settings to see live pixel highlighting!", 
                                 className="text-info d-block mt-2")
                    ])
                ])
            ], width=4)
        ])
        
    except Exception as e:
        logger.error(f"Error creating map content: {e}")
        return dbc.Alert(f"Error creating map: {str(e)}", color="danger")

def calculate_pixel_distance_to_aws(pixels_df: pd.DataFrame, aws_station_coords: dict) -> pd.DataFrame:
    """Calculate distance from each pixel to AWS station."""
    try:
        if pixels_df.empty or not aws_station_coords:
            return pixels_df
            
        from utils.config.helpers import calculate_distance_km
        
        aws_lat = aws_station_coords.get('lat')
        aws_lon = aws_station_coords.get('lon')
        
        if aws_lat is None or aws_lon is None:
            logger.warning("AWS coordinates not available for distance calculation")
            return pixels_df
            
        # Calculate distance for each pixel
        distances = []
        for _, pixel in pixels_df.iterrows():
            try:
                pixel_lat = float(pixel['latitude'])
                pixel_lon = float(pixel['longitude'])
                distance = calculate_distance_km(aws_lat, aws_lon, pixel_lat, pixel_lon)
                distances.append(distance)
            except (ValueError, TypeError):
                distances.append(float('inf'))  # Invalid coordinates
                
        pixels_with_distance = pixels_df.copy()
        pixels_with_distance['distance_to_aws'] = distances
        
        logger.info(f"Calculated distances for {len(pixels_with_distance)} pixels")
        return pixels_with_distance.sort_values('distance_to_aws')
        
    except Exception as e:
        logger.error(f"Error calculating pixel distances to AWS: {e}")
        return pixels_df


def filter_pixels_by_distance(pixels_df: pd.DataFrame, max_distance_km: float = None, 
                            top_n_closest: int = None) -> pd.DataFrame:
    """Filter pixels by distance to AWS station."""
    try:
        if pixels_df.empty or 'distance_to_aws' not in pixels_df.columns:
            return pixels_df
            
        filtered_pixels = pixels_df.copy()
        
        # Apply distance threshold filter
        if max_distance_km is not None:
            filtered_pixels = filtered_pixels[
                filtered_pixels['distance_to_aws'] <= max_distance_km
            ]
            logger.info(f"Applied distance filter: {len(filtered_pixels)} pixels within {max_distance_km}km")
            
        # Apply top N closest filter
        if top_n_closest is not None and len(filtered_pixels) > top_n_closest:
            filtered_pixels = filtered_pixels.head(top_n_closest)
            logger.info(f"Applied closest N filter: top {top_n_closest} pixels selected")
            
        return filtered_pixels
        
    except Exception as e:
        logger.error(f"Error filtering pixels by distance: {e}")
        return pixels_df


def filter_pixels_by_glacier_fraction(data_df: pd.DataFrame, min_fraction: float = 0.5) -> pd.DataFrame:
    """Filter data by minimum glacier fraction threshold."""
    try:
        if data_df.empty or 'glacier_fraction' not in data_df.columns:
            return data_df
            
        filtered_data = data_df[data_df['glacier_fraction'] >= min_fraction]
        logger.info(f"Applied glacier fraction filter (>= {min_fraction}): {len(filtered_data)} records")
        return filtered_data
        
    except Exception as e:
        logger.error(f"Error filtering by glacier fraction: {e}")
        return data_df


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


def _filter_data_by_mode_enhanced(data: pd.DataFrame, data_mode: str, selected_pixels: List[str],
                                glacier_info: dict = None, filter_params: dict = None) -> pd.DataFrame:
    """Enhanced data filtering with distance and glacier fraction support."""
    try:
        filtered_data = data.copy()
        filter_params = filter_params or {}
        
        # Step 1: Apply data mode filtering
        if data_mode == 'best' and 'qa_mode' in filtered_data.columns:
            # Filter to best quality data first
            best_data = filtered_data[filtered_data['qa_mode'] == 'clear_land']
            if best_data.empty:
                # Fallback to any available QA mode if 'clear_land' is not available
                qa_modes = filtered_data['qa_mode'].unique()
                logger.info(f"Available QA modes: {qa_modes}")
                best_mode = filtered_data['qa_mode'].mode().iloc[0] if not filtered_data['qa_mode'].mode().empty else qa_modes[0]
                best_data = filtered_data[filtered_data['qa_mode'] == best_mode]
            filtered_data = best_data
            logger.info(f"Applied 'best' quality filter: {len(filtered_data)} records")
            
        elif data_mode == 'closest_aws':
            # Filter by distance to AWS station
            if glacier_info and 'aws_stations' in glacier_info:
                aws_stations = glacier_info['aws_stations']
                if aws_stations:
                    # Use first AWS station (could be enhanced to support multiple)
                    aws_station = list(aws_stations.values())[0]
                    
                    # Get unique pixels and calculate distances
                    pixels_df = filtered_data[['pixel_id', 'latitude', 'longitude']].drop_duplicates()
                    pixels_with_distance = calculate_pixel_distance_to_aws(pixels_df, aws_station)
                    
                    # Apply distance filters
                    max_distance = filter_params.get('max_distance_km', 10.0)  # Default 10km
                    top_n = filter_params.get('top_n_closest', 10)  # Default top 10
                    
                    filtered_pixels = filter_pixels_by_distance(pixels_with_distance, max_distance, top_n)
                    closest_pixel_ids = filtered_pixels['pixel_id'].astype(str).tolist()
                    
                    # Filter data to only include closest pixels
                    filtered_data = filtered_data[filtered_data['pixel_id'].astype(str).isin(closest_pixel_ids)]
                    logger.info(f"Applied closest AWS filter: {len(filtered_data)} records from {len(closest_pixel_ids)} pixels")
                    
        elif data_mode == 'high_glacier_fraction':
            # Filter by glacier fraction
            min_fraction = filter_params.get('min_glacier_fraction', 0.7)  # Default 70%
            filtered_data = filter_pixels_by_glacier_fraction(filtered_data, min_fraction)
            
        elif data_mode == 'custom':
            # Apply custom combination of filters
            if filter_params.get('use_glacier_fraction', False):
                min_fraction = filter_params.get('min_glacier_fraction', 0.5)
                filtered_data = filter_pixels_by_glacier_fraction(filtered_data, min_fraction)
                
            if filter_params.get('use_distance_filter', False) and glacier_info:
                aws_stations = glacier_info.get('aws_stations', {})
                if aws_stations:
                    aws_station = list(aws_stations.values())[0]
                    pixels_df = filtered_data[['pixel_id', 'latitude', 'longitude']].drop_duplicates()
                    pixels_with_distance = calculate_pixel_distance_to_aws(pixels_df, aws_station)
                    
                    max_distance = filter_params.get('max_distance_km')
                    top_n = filter_params.get('top_n_closest')
                    
                    filtered_pixels = filter_pixels_by_distance(pixels_with_distance, max_distance, top_n)
                    closest_pixel_ids = filtered_pixels['pixel_id'].astype(str).tolist()
                    filtered_data = filtered_data[filtered_data['pixel_id'].astype(str).isin(closest_pixel_ids)]
        
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
        
        logger.info(f"Final enhanced filtered dataset: {len(filtered_data)} records (mode: {data_mode}, selected pixels: {len(selected_pixels) if selected_pixels else 0})")
        return filtered_data
            
    except Exception as e:
        logger.error(f"Error in enhanced filtering: {e}")
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
     Input('data-mode-radio', 'value'),
     Input('distance-filter-toggle', 'value'),
     Input('closest-pixels-slider', 'value'),
     Input('max-distance-input', 'value'),
     Input('fraction-filter-toggle', 'value'),
     Input('glacier-fraction-slider', 'value')],
    [State('tabs', 'active_tab'),
     State('pixel-data-store', 'data'),
     State('current-glacier-store', 'data'),
     State('glacier-data-store', 'data')],
    prevent_initial_call=True
)
def update_content_on_selection(selected_pixels, selected_methods, include_aws, data_mode,
                              use_distance_filter, top_n_closest, max_distance_km,
                              use_fraction_filter, min_glacier_fraction,
                              active_tab, pixel_json, glacier_id, data_json):
    """Update content when pixel selection changes."""
    if not data_json or not glacier_id:
        return dash.no_update
        
    # Skip map tab - it's handled by the main callback to avoid conflicts
    if active_tab == "map-tab":
        return dash.no_update
    
    # For other tabs, update the visualizations with selected pixels
    elif active_tab in ["scatter-tab", "timeseries-tab", "boxplot-tab", "histogram-tab", "correlation-tab", "stats-tab"]:
        try:
            from io import StringIO
            data = pd.read_json(StringIO(data_json))
            
            # Apply enhanced data filtering based on mode with custom filter support
            glacier_info = data_manager.glacier_config.get('glaciers', {}).get(glacier_id, {})
            filter_params = {
                'data_mode': data_mode,
                'use_distance_filter': use_distance_filter,
                'top_n_closest': top_n_closest,
                'max_distance_km': max_distance_km,
                'use_glacier_fraction': use_fraction_filter,
                'min_glacier_fraction': min_glacier_fraction
            }
            data = _filter_data_by_mode_enhanced(data, data_mode, selected_pixels, glacier_info, filter_params)
            
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
     State('current-glacier-store', 'data'),
     State('distance-filter-toggle', 'value'),
     State('closest-pixels-slider', 'value'),
     State('max-distance-input', 'value'),
     State('fraction-filter-toggle', 'value'),
     State('glacier-fraction-slider', 'value')],
    prevent_initial_call=True
)
def export_data(n_clicks, data_json, selected_pixels, selected_methods, data_mode, glacier_id,
                use_distance_filter, top_n_closest, max_distance_km, use_fraction_filter, min_glacier_fraction):
    """Export the current filtered data as CSV."""
    if not n_clicks or not data_json:
        return dash.no_update
        
    try:
        from io import StringIO
        data = pd.read_json(StringIO(data_json))
        
        # Apply the same filtering as the visualizations
        # Apply enhanced data filtering with custom filter support
        glacier_info = data_manager.glacier_config.get('glaciers', {}).get(glacier_id, {})
        filter_params = {
            'data_mode': data_mode,
            'use_distance_filter': use_distance_filter,
            'top_n_closest': top_n_closest,
            'max_distance_km': max_distance_km,
            'use_glacier_fraction': use_fraction_filter,
            'min_glacier_fraction': min_glacier_fraction
        }
        data = _filter_data_by_mode_enhanced(data, data_mode, selected_pixels, glacier_info, filter_params)
        
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


# Callback to show/hide advanced filtering controls
@app.callback(
    Output('advanced-filters-section', 'style'),
    Input('data-mode-radio', 'value')
)
def toggle_advanced_filters(data_mode):
    """Show advanced filters only when custom mode is selected."""
    if data_mode == 'custom':
        return {'display': 'block'}
    else:
        return {'display': 'none'}


# Callback to show/hide distance filter controls
@app.callback(
    Output('distance-filter-controls', 'style'),
    Input('distance-filter-toggle', 'value')
)
def toggle_distance_controls(is_enabled):
    """Show distance filter controls when toggle is enabled."""
    if is_enabled:
        return {'display': 'block'}
    else:
        return {'display': 'none'}


# Callback to show/hide glacier fraction filter controls
@app.callback(
    Output('fraction-filter-controls', 'style'),
    Input('fraction-filter-toggle', 'value')
)
def toggle_fraction_controls(is_enabled):
    """Show glacier fraction filter controls when toggle is enabled."""
    if is_enabled:
        return {'display': 'block'}
    else:
        return {'display': 'none'}


if __name__ == '__main__':
    print("🚀 Starting Fixed Albedo Dashboard...")
    print("📊 Dashboard will be available at: http://127.0.0.1:8054")
    print("🛑 Press Ctrl+C to stop")
    
    app.run_server(
        debug=True,
        host='127.0.0.1',
        port=8054  # Different port
    )
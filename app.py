#!/usr/bin/env python3
"""
Interactive Albedo Analysis Dashboard

Main application file for the interactive web-based dashboard that integrates
with the existing albedo analysis framework to provide real-time visualization
and comparison of MODIS satellite data against AWS ground station measurements.
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

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import dashboard components
from dashboard.core.data_manager import DashboardDataManager
from dashboard.components.layout import DashboardLayout
from dashboard.components.map_component import MapComponent
from dashboard.components.plots import PlotComponents
from dashboard.components.controls import ControlComponents

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
    external_scripts=[
        "https://unpkg.com/three@0.159.0/build/three.min.js",
    ],
    suppress_callback_exceptions=True,
    title="Interactive Albedo Analysis Dashboard",
    assets_folder="dashboard/assets",
)

# Initialize core components
try:
    data_manager = DashboardDataManager()
    layout_manager = DashboardLayout(data_manager.config)
    map_component = MapComponent(data_manager.config)
    plot_components = PlotComponents(data_manager.config)
    control_components = ControlComponents(data_manager.config)
    
    logger.info("Dashboard components initialized successfully")
except Exception as e:
    logger.error(f"Error initializing dashboard components: {e}")
    traceback.print_exc()

# Inject simple Tailwind init and Three.js background after page load
app.index_string = (
    """
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            {%favicon%}
            {%css%}
            <script>
              window.tailwind = {
                config: {
                  prefix: 'tw-',
                  corePlugins: { preflight: false }
                }
              }
            </script>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="tw-bg-slate-50">
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                <script defer src="/assets/three-bg.js"></script>
                {%renderer%}
            </footer>
        </body>
    </html>
    """
)

# Set app layout
try:
    available_glaciers = data_manager.get_available_glaciers()
    app.layout = layout_manager.create_main_layout(available_glaciers)
    logger.info(f"App layout created with {len(available_glaciers)} available glaciers")
except Exception as e:
    logger.error(f"Error creating app layout: {e}")
    app.layout = html.Div([
        html.H1("Dashboard Error", className="text-center text-danger"),
        html.P(f"Error initializing dashboard: {str(e)}", className="text-center"),
        html.P("Please check the configuration and data files.", className="text-center text-muted")
    ])

# Callback for glacier selection and data loading
@app.callback(
    [Output('glacier-data-store', 'data'),
     Output('pixel-data-store', 'data'),
     Output('glacier-info', 'children'),
     Output('data-summary-content', 'children'),
     Output('date-range-picker', 'start_date'),
     Output('date-range-picker', 'end_date'),
     Output('date-range-info', 'children')],
    Input('glacier-dropdown', 'value'),
    prevent_initial_call=False
)
def update_glacier_selection(glacier_id):
    """Update data stores and info when glacier is selected."""
    try:
        if not glacier_id:
            empty_info = [html.P("Select a glacier to view information", className='text-muted')]
            return None, None, empty_info, empty_info, None, None, "No glacier selected"
        
        logger.info(f"Loading data for glacier: {glacier_id}")
        
        # Load glacier data with error handling
        try:
            glacier_data = data_manager.load_glacier_data(glacier_id)
        except Exception as e:
            logger.error(f"Error loading glacier data: {e}")
            glacier_data = None
        
        try:
            pixel_data = data_manager.get_pixel_locations(glacier_id)
        except Exception as e:
            logger.error(f"Error loading pixel data: {e}")
            pixel_data = None
        
        try:
            data_summary = data_manager.get_data_summary(glacier_id)
        except Exception as e:
            logger.error(f"Error loading data summary: {e}")
            data_summary = {}
        
        # Get glacier info
        glacier_info = data_manager.glacier_config.get('glaciers', {}).get(glacier_id, {})
        
        # Update glacier info display
        try:
            glacier_info_display = control_components.update_glacier_info(
                glacier_id, glacier_info, data_summary
            )
        except Exception as e:
            logger.error(f"Error updating glacier info display: {e}")
            glacier_info_display = [html.P("Error loading glacier information", className='text-danger')]
        
        # Update data summary display
        summary_display = []
        try:
            if data_summary and 'total_records' in data_summary:
                summary_display = [
                    html.P(f"Total Records: {data_summary['total_records']:,}", className='mb-1'),
                    html.P(f"Pixels: {data_summary.get('pixel_count', 0)}", className='mb-1'),
                    html.P(f"Methods: {', '.join(data_summary.get('available_methods', []))}", className='mb-1')
                ]
            else:
                summary_display = [html.P("No data summary available", className='text-muted')]
        except Exception as e:
            logger.error(f"Error creating summary display: {e}")
            summary_display = [html.P("Error loading summary", className='text-danger')]
        
        # Update date range
        try:
            start_date, end_date, date_info = control_components.update_date_range_info(data_summary)
        except Exception as e:
            logger.error(f"Error updating date range: {e}")
            start_date, end_date, date_info = None, None, "Error loading dates"
        
        # Convert data to JSON serializable format for storage
        try:
            glacier_data_json = glacier_data.to_json(date_format='iso') if glacier_data is not None else None
            pixel_data_json = pixel_data.to_json(date_format='iso') if pixel_data is not None else None
        except Exception as e:
            logger.error(f"Error converting data to JSON: {e}")
            glacier_data_json = None
            pixel_data_json = None
        
        return (glacier_data_json, pixel_data_json, glacier_info_display, 
                summary_display, start_date, end_date, date_info)
        
    except Exception as e:
        logger.error(f"Critical error in glacier selection callback: {e}")
        import traceback
        traceback.print_exc()
        error_msg = [html.P(f"Critical error: {str(e)}", className='text-danger')]
        return None, None, error_msg, error_msg, None, None, "Critical error"

# Callback for map updates
@app.callback(
    Output('map-container', 'children'),
    [Input('glacier-dropdown', 'value'),
     Input('pixel-data-store', 'data'),
     Input('selected-pixels-store', 'data')],
    prevent_initial_call=False
)
def update_map(glacier_id, pixel_data_json, selected_pixels):
    """Update the map display based on glacier selection and pixel data."""
    try:
        if not glacier_id:
            return html.P("Select a glacier to view map", className="text-center text-muted mt-5")
        
        if not pixel_data_json:
            return html.P("Loading map data...", className="text-center text-muted mt-5")
        
        # Load pixel data from JSON with error handling
        try:
            pixel_data = pd.read_json(pixel_data_json)
        except Exception as e:
            logger.error(f"Error parsing pixel data JSON: {e}")
            return html.P("Error loading pixel data for map", className="text-center text-danger")
        
        # Get glacier info for coordinates
        glacier_info = data_manager.glacier_config.get('glaciers', {}).get(glacier_id, {})
        coords = glacier_info.get('coordinates', {})
        center_lat = coords.get('lat', 52.0)
        center_lon = coords.get('lon', -117.0)
        
        # Create simple map as fallback
        try:
            # Combine all map elements
            map_children = [dl.TileLayer()]
            
            # Add pixel markers if available
            if pixel_data is not None and not pixel_data.empty:
                try:
                    pixel_markers = map_component.create_pixel_markers(pixel_data, selected_pixels or [])
                    if pixel_markers:
                        map_children.extend(pixel_markers)
                except Exception as e:
                    logger.error(f"Error creating pixel markers: {e}")
            
            # Add AWS marker if available
            try:
                aws_info = data_manager.get_aws_station_info(glacier_id)
                if aws_info:
                    aws_marker = map_component.create_aws_marker(aws_info)
                    if aws_marker:
                        map_children.append(aws_marker)
            except Exception as e:
                logger.error(f"Error creating AWS marker: {e}")
            
            # Add glacier boundary if available
            try:
                glacier_boundary = map_component.create_glacier_boundary(glacier_id, glacier_info)
                if glacier_boundary:
                    map_children.append(glacier_boundary)
            except Exception as e:
                logger.error(f"Error creating glacier boundary: {e}")
            
            # Create map with all elements
            complete_map = dl.Map(
                id="glacier-map",
                style={'width': '100%', 'height': '500px'},
                center=[center_lat, center_lon],
                zoom=map_component.default_zoom,
                children=map_children
            )
            
            return complete_map
            
        except Exception as e:
            logger.error(f"Error creating map: {e}")
            return html.P(f"Error creating map: {str(e)}", className="text-center text-danger")
        
    except Exception as e:
        logger.error(f"Critical error in map callback: {e}")
        import traceback
        traceback.print_exc()
        return html.P(f"Critical map error: {str(e)}", className="text-center text-danger")

# Callback for plot updates
@app.callback(
    [Output('scatter-plot', 'figure'),
     Output('timeseries-plot', 'figure'),
     Output('box-plot', 'figure'),
     Output('histogram-plot', 'figure'),
     Output('stats-table', 'figure'),
     Output('correlation-matrix', 'figure')],
    [Input('update-analysis-btn', 'n_clicks')],
    [State('glacier-data-store', 'data'),
     State('method-checklist', 'value'),
     State('selected-pixels-store', 'data'),
     State('pixel-mode-radio', 'value'),
     State('aws-toggle', 'value'),
     State('date-range-picker', 'start_date'),
     State('date-range-picker', 'end_date')]
)
def update_plots(n_clicks, glacier_data_json, selected_methods, selected_pixels, 
                pixel_mode, include_aws, start_date, end_date):
    """Update all plots based on current selections."""
    try:
        if not glacier_data_json:
            empty_fig = plot_components._create_empty_plot("No data available - select a glacier")
            return empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig
        
        if not n_clicks:
            empty_fig = plot_components._create_empty_plot("Click 'Update Analysis' to generate plots")
            return empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig
        
        # Load data from JSON
        data = pd.read_json(glacier_data_json)
        
        # Apply filters
        filtered_data = data.copy()
        
        # Filter by selected methods
        if selected_methods and 'method' in filtered_data.columns:
            filtered_data = filtered_data[filtered_data['method'].isin(selected_methods)]
        
        # Filter by pixel selection mode
        if pixel_mode == 'selected' and selected_pixels:
            # Convert selected pixels to integers for consistent matching
            try:
                selected_pixel_ints = [int(pid) for pid in selected_pixels]
                filtered_data = filtered_data[filtered_data['pixel_id'].isin(selected_pixel_ints)]
            except (ValueError, TypeError):
                # Fallback to string comparison if int conversion fails
                filtered_data = filtered_data[filtered_data['pixel_id'].astype(str).isin(selected_pixels)]
        elif pixel_mode == 'best':
            # Select best pixels automatically (placeholder logic)
            if 'glacier_fraction' in filtered_data.columns:
                best_pixels = (filtered_data.groupby('pixel_id')['glacier_fraction']
                             .first().nlargest(2).index.tolist())
                filtered_data = filtered_data[filtered_data['pixel_id'].isin(best_pixels)]
        
        # Filter by date range
        if start_date and end_date and 'date' in filtered_data.columns:
            filtered_data['date'] = pd.to_datetime(filtered_data['date'])
            filtered_data = filtered_data[
                (filtered_data['date'] >= start_date) & 
                (filtered_data['date'] <= end_date)
            ]
        
        # Remove AWS data if not included
        if not include_aws:
            aws_cols = [col for col in filtered_data.columns if 'aws' in col.lower()]
            for col in aws_cols:
                filtered_data[col] = np.nan
        
        # Create plots
        scatter_fig = plot_components.create_scatter_plot(filtered_data, selected_methods)
        timeseries_fig = plot_components.create_time_series_plot(filtered_data, selected_methods)
        box_fig = plot_components.create_box_plot(filtered_data, selected_methods)
        histogram_fig = plot_components.create_histogram(filtered_data, selected_methods)
        
        # Calculate statistics and create summary
        stats = data_manager.calculate_statistics(filtered_data, selected_methods)
        stats_fig = plot_components.create_statistical_summary_table(stats)
        correlation_fig = plot_components.create_correlation_matrix(filtered_data)
        
        return scatter_fig, timeseries_fig, box_fig, histogram_fig, stats_fig, correlation_fig
        
    except Exception as e:
        logger.error(f"Error updating plots: {e}")
        error_fig = plot_components._create_empty_plot(f"Error creating plots: {str(e)}")
        return error_fig, error_fig, error_fig, error_fig, error_fig, error_fig

# Callback for pixel selection from map clicks
@app.callback(
    [Output('selected-pixels-store', 'data'),
     Output('selected-pixels-count', 'children'),
     Output('selection-info-content', 'children')],
    [Input('glacier-map', 'click_lat_lng')],
    [State('selected-pixels-store', 'data'),
     State('pixel-data-store', 'data')],
    prevent_initial_call=True
)
def handle_map_click(click_lat_lng, current_selected, pixel_data_json):
    """Do not toggle selection on map click to avoid double-toggles. Only refresh details table."""
    try:
        selected_pixels = current_selected or []
        if not pixel_data_json or not selected_pixels:
            return selected_pixels, len(selected_pixels), [html.P("No pixels selected", className='text-muted')]

        # Build details table from current selection
        from io import StringIO
        df = pd.read_json(StringIO(pixel_data_json))
        header = html.Tr([html.Th("Pixel ID"), html.Th("Glacier Fraction"), html.Th("Elevation (m)")])
        rows = []
        for pid in selected_pixels:
            try:
                pid_int = int(pid)
                info = df[df['pixel_id'] == pid_int]
            except (ValueError, TypeError):
                info = df[df['pixel_id'].astype(str) == str(pid)]
            if not info.empty:
                r = info.iloc[0]
                gf = (f"{float(r['glacier_fraction']):.3f}" if 'glacier_fraction' in r and pd.notna(r['glacier_fraction']) else "—")
                elev = (f"{int(r['elevation'])}" if 'elevation' in r and pd.notna(r['elevation']) else "—")
                rows.append(html.Tr([html.Td(str(int(r['pixel_id']))), html.Td(gf), html.Td(elev)]))
        selection_content = [html.Table([header] + rows, className='table table-sm')] if rows else [html.P("No pixels selected", className='text-muted')]
        return selected_pixels, len(selected_pixels), selection_content

    except Exception as e:
        logger.error(f"Error handling map click: {e}")
        return current_selected or [], len(current_selected or []), [html.P(f"Error: {str(e)}", className='text-danger')]

# Callback for reset selection
@app.callback(
    Output('selected-pixels-store', 'data', allow_duplicate=True),
    Input('reset-selection-btn', 'n_clicks'),
    prevent_initial_call=True
)
def reset_selection(n_clicks):
    """Reset pixel selection."""
    if n_clicks:
        return []
    return dash.no_update

# Callback for pixel selection from popup buttons (supports map popups)
@app.callback(
    [Output('selected-pixels-store', 'data', allow_duplicate=True),
     Output('selected-pixels-count', 'children', allow_duplicate=True),
     Output('selection-info-content', 'children', allow_duplicate=True)],
    [Input({'type': 'pixel-toggle-btn', 'pixel_id': dash.dependencies.ALL}, 'n_clicks')],
    [State('selected-pixels-store', 'data'),
     State('pixel-data-store', 'data')],
    prevent_initial_call=True
)
def handle_pixel_selection_from_popup(n_clicks_list, current_selected, pixel_json):
    """Handle pixel selection toggling via popup button clicks."""
    current_selected = current_selected or []
    if not pixel_json:
        return current_selected, len(current_selected), [html.P("No pixel data available", className='text-muted')]

    try:
        # Check if any button was clicked
        if n_clicks_list and any(n_clicks_list):
            if ctx.triggered:
                triggered_id = ctx.triggered[0]['prop_id']
                # Extract pixel_id from the triggered component id string
                import re
                pixel_id_match = re.search(r'"pixel_id":"([^\"]+)"', triggered_id)
                if pixel_id_match:
                    pixel_id = pixel_id_match.group(1)
                    if pixel_id.endswith('.0'):
                        pixel_id = pixel_id[:-2]
                    # Toggle selection
                    if pixel_id in current_selected:
                        current_selected.remove(pixel_id)
                    else:
                        current_selected.append(pixel_id)

        # Build selection info table from pixel_json
        if current_selected and pixel_json:
            try:
                from io import StringIO
                df = pd.read_json(StringIO(pixel_json))
                header = html.Tr([html.Th("Pixel ID"), html.Th("Glacier Fraction"), html.Th("Elevation (m)")])
                rows = []
                for pid in current_selected:
                    try:
                        pid_int = int(pid)
                        info = df[df['pixel_id'] == pid_int]
                    except (ValueError, TypeError):
                        info = df[df['pixel_id'].astype(str) == str(pid)]
                    if not info.empty:
                        r = info.iloc[0]
                        gf = (f"{float(r['glacier_fraction']):.3f}" if 'glacier_fraction' in r and pd.notna(r['glacier_fraction']) else "—")
                        elev = (f"{int(r['elevation'])}" if 'elevation' in r and pd.notna(r['elevation']) else "—")
                        rows.append(html.Tr([html.Td(str(int(r['pixel_id']))), html.Td(gf), html.Td(elev)]))
                selection_info = [html.Table([header] + rows, className='table table-sm')]
            except Exception:
                selection_info = [html.P(f"Selected Pixels: {', '.join(current_selected)}", className='mb-1')]
        else:
            selection_info = [html.P("No pixels selected", className='text-muted')]

        return current_selected, len(current_selected), selection_info

    except Exception as e:
        return current_selected, len(current_selected), [html.P(f"Error handling selection: {str(e)}", className='text-danger')]

# Callback for clear cache
@app.callback(
    Output('status-badge', 'children'),
    Input('clear-cache-btn', 'n_clicks'),
    prevent_initial_call=True
)
def clear_cache(n_clicks):
    """Clear data cache."""
    if n_clicks:
        data_manager.clear_cache()
        return "Cache Cleared"
    return "Ready"

# Callback for status updates
@app.callback(
    Output('last-update', 'children'),
    [Input('update-analysis-btn', 'n_clicks')],
    prevent_initial_call=True
)
def update_status(n_clicks):
    """Update last update timestamp."""
    return f"Last updated: {datetime.now().strftime('%H:%M:%S')}"

if __name__ == '__main__':
    # Get configuration
    config = data_manager.config
    app_config = config.get('app', {})
    
    # Run the app
    app.run_server(
        debug=app_config.get('debug', True),
        host=app_config.get('host', '127.0.0.1'),
        port=app_config.get('port', 8050)
    )
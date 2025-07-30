#!/usr/bin/env python3
"""
Control Components for Albedo Dashboard

This module provides the user interface controls for data selection,
including glacier selection, method toggles, date ranges, and pixel selection modes.
"""

import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


class ControlComponents:
    """
    Handles the creation of user interface control components for the dashboard.
    
    Features:
    - Glacier selection dropdown
    - MODIS method checkboxes
    - Date range picker
    - Pixel selection mode toggle
    - AWS data inclusion toggle
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize control components with configuration."""
        self.config = config
        self.analysis_config = config.get('analysis', {})
        
        # Available MODIS products
        self.modis_products = self.analysis_config.get('albedo', {}).get('modis_products', [
            'MOD09GA', 'MOD10A1', 'MCD43A3'
        ])
        
        logger.info("Control components initialized")
    
    def create_glacier_selector(self, available_glaciers: List[Dict[str, Any]]) -> dbc.Card:
        """
        Create glacier selection dropdown with availability indicators.
        
        Args:
            available_glaciers: List of glacier information dictionaries
            
        Returns:
            Bootstrap Card component with glacier selector
        """
        # Create dropdown options
        options = []
        for glacier in available_glaciers:
            # Create availability indicator
            availability = glacier.get('data_available', {})
            available_count = sum(availability.values())
            total_count = len(availability)
            
            availability_text = f" ({available_count}/{total_count} datasets)"
            
            option_label = f"{glacier['name']}{availability_text}"
            if available_count == 0:
                option_label += " ⚠️"
            elif available_count == total_count:
                option_label += " ✅"
            
            options.append({
                'label': option_label,
                'value': glacier['id']
            })
        
        glacier_selector = dbc.Card([
            dbc.CardHeader("Glacier Selection"),
            dbc.CardBody([
                dcc.Dropdown(
                    id='glacier-dropdown',
                    options=options,
                    value=options[0]['value'] if options else None,
                    placeholder="Select a glacier",
                    clearable=False
                ),
                html.Div(id='glacier-info', className='mt-2')
            ])
        ], className='mb-3')
        
        return glacier_selector
    
    def create_method_selector(self) -> dbc.Card:
        """
        Create MODIS method selection checkboxes.
        
        Returns:
            Bootstrap Card component with method selector
        """
        method_options = [
            {'label': method, 'value': method} 
            for method in self.modis_products
        ]
        
        method_selector = dbc.Card([
            dbc.CardHeader("MODIS Methods"),
            dbc.CardBody([
                dcc.Checklist(
                    id='method-checklist',
                    options=method_options,
                    value=self.modis_products,  # All selected by default
                    inline=True,
                    inputStyle={"margin-right": "5px", "margin-left": "10px"}
                )
            ])
        ], className='mb-3')
        
        return method_selector
    
    def create_date_range_selector(self) -> dbc.Card:
        """
        Create date range picker with data availability indicators.
        
        Returns:
            Bootstrap Card component with date range selector
        """
        date_selector = dbc.Card([
            dbc.CardHeader("Date Range"),
            dbc.CardBody([
                dcc.DatePickerRange(
                    id='date-range-picker',
                    start_date=None,  # Will be set based on data
                    end_date=None,    # Will be set based on data
                    display_format='YYYY-MM-DD',
                    style={'width': '100%'}
                ),
                html.Div(id='date-range-info', className='mt-2')
            ])
        ], className='mb-3')
        
        return date_selector
    
    def create_pixel_mode_selector(self) -> dbc.Card:
        """
        Create pixel selection mode toggle.
        
        Returns:
            Bootstrap Card component with pixel mode selector
        """
        pixel_mode_selector = dbc.Card([
            dbc.CardHeader("Pixel Selection Mode"),
            dbc.CardBody([
                dbc.RadioItems(
                    id='pixel-mode-radio',
                    options=[
                        {'label': 'All Available Pixels', 'value': 'all'},
                        {'label': 'Selected Pixels Only', 'value': 'selected'},
                        {'label': 'Best Pixels (Auto-select)', 'value': 'best'}
                    ],
                    value='all',
                    inline=False
                ),
                html.Div([
                    html.Small("Selected pixels: ", className='text-muted'),
                    html.Span(id='selected-pixels-count', children='0', className='badge badge-secondary')
                ], className='mt-2')
            ])
        ], className='mb-3')
        
        return pixel_mode_selector
    
    def create_aws_toggle(self) -> dbc.Card:
        """
        Create AWS data inclusion toggle.
        
        Returns:
            Bootstrap Card component with AWS toggle
        """
        aws_toggle = dbc.Card([
            dbc.CardHeader("AWS Ground Data"),
            dbc.CardBody([
                dbc.Switch(
                    id='aws-toggle',
                    label='Include AWS ground station data',
                    value=True
                ),
                html.Div(id='aws-info', className='mt-2')
            ])
        ], className='mb-3')
        
        return aws_toggle
    
    def create_analysis_controls(self) -> dbc.Card:
        """
        Create analysis control buttons and options.
        
        Returns:
            Bootstrap Card component with analysis controls
        """
        analysis_controls = dbc.Card([
            dbc.CardHeader("Analysis Controls"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            "Update Analysis",
                            id='update-analysis-btn',
                            color='primary',
                            className='mb-2',
                            style={'width': '100%'}
                        )
                    ], width=6),
                    dbc.Col([
                        dbc.Button(
                            "Export Data",
                            id='export-data-btn',
                            color='secondary',
                            className='mb-2',
                            style={'width': '100%'}
                        )
                    ], width=6)
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            "Reset Selection",
                            id='reset-selection-btn',
                            color='warning',
                            size='sm',
                            style={'width': '100%'}
                        )
                    ], width=6),
                    dbc.Col([
                        dbc.Button(
                            "Clear Cache",
                            id='clear-cache-btn',
                            color='info',
                            size='sm',
                            style={'width': '100%'}
                        )
                    ], width=6)
                ])
            ])
        ], className='mb-3')
        
        return analysis_controls
    
    def create_data_summary_card(self) -> dbc.Card:
        """
        Create data summary information card.
        
        Returns:
            Bootstrap Card component with data summary
        """
        summary_card = dbc.Card([
            dbc.CardHeader("Data Summary"),
            dbc.CardBody([
                html.Div(id='data-summary-content', children=[
                    html.P("Select a glacier to view data summary", className='text-muted')
                ])
            ])
        ], className='mb-3')
        
        return summary_card
    
    def create_sidebar(self, available_glaciers: List[Dict[str, Any]]) -> html.Div:
        """
        Create the complete sidebar with all control components.
        
        Args:
            available_glaciers: List of available glacier information
            
        Returns:
            HTML Div containing all sidebar components
        """
        sidebar = html.Div([
            html.H4("Interactive Albedo Analysis", className='text-center mb-4'),
            
            # Glacier selection
            self.create_glacier_selector(available_glaciers),
            
            # Method selection
            self.create_method_selector(),
            
            # Date range selection
            self.create_date_range_selector(),
            
            # Pixel selection mode
            self.create_pixel_mode_selector(),
            
            # AWS data toggle
            self.create_aws_toggle(),
            
            # Analysis controls
            self.create_analysis_controls(),
            
            # Data summary
            self.create_data_summary_card()
            
        ], style={
            'height': '100vh',
            'overflow-y': 'auto',
            'padding': '20px',
            'background-color': '#f8f9fa'
        })
        
        return sidebar
    
    def create_loading_overlay(self) -> html.Div:
        """
        Create loading overlay for data processing.
        
        Returns:
            HTML Div with loading spinner
        """
        loading_overlay = html.Div([
            dbc.Spinner(
                html.Div(id="loading-output"),
                size="lg",
                color="primary",
                type="border",
                fullscreen=True,
                spinner_style={"width": "3rem", "height": "3rem"}
            )
        ], id='loading-overlay', style={'display': 'none'})
        
        return loading_overlay
    
    def update_glacier_info(self, glacier_id: str, glacier_info: Dict[str, Any], 
                           data_summary: Dict[str, Any]) -> List[html.Div]:
        """
        Update glacier information display.
        
        Args:
            glacier_id: Selected glacier identifier
            glacier_info: Glacier configuration information
            data_summary: Summary of available data
            
        Returns:
            List of HTML components for glacier info
        """
        try:
            if not glacier_info:
                return [html.P("Glacier information not available", className='text-muted')]
            
            info_components = []
            
            # Basic glacier info
            name = glacier_info.get('name', glacier_id.title())
            region = glacier_info.get('region', 'Unknown')
            coordinates = glacier_info.get('coordinates', {})
            
            info_components.extend([
                html.H6(name, className='text-primary'),
                html.P(f"Region: {region}", className='mb-1'),
            ])
            
            if coordinates:
                lat = coordinates.get('lat', 'N/A')
                lon = coordinates.get('lon', 'N/A')
                info_components.append(
                    html.P(f"Coordinates: {lat}°, {lon}°", className='mb-1')
                )
            
            # Data availability
            if 'data_available' in glacier_info:
                availability = glacier_info['data_available']
                info_components.append(html.Hr())
                info_components.append(html.P("Data availability:", className='font-weight-bold mb-1'))
                
                for data_type, available in availability.items():
                    icon = "✅" if available else "❌"
                    info_components.append(
                        html.P(f"{icon} {data_type.upper()}", className='mb-1')
                    )
            
            # Data summary
            if data_summary and 'total_records' in data_summary:
                info_components.append(html.Hr())
                info_components.append(html.P("Data Summary:", className='font-weight-bold mb-1'))
                info_components.append(
                    html.P(f"Total records: {data_summary['total_records']:,}", className='mb-1')
                )
                
                if 'pixel_count' in data_summary:
                    info_components.append(
                        html.P(f"Available pixels: {data_summary['pixel_count']}", className='mb-1')
                    )
                
                if 'available_methods' in data_summary:
                    methods = ', '.join(data_summary['available_methods'])
                    info_components.append(
                        html.P(f"Methods: {methods}", className='mb-1')
                    )
            
            return info_components
            
        except Exception as e:
            logger.error(f"Error updating glacier info: {e}")
            return [html.P("Error loading glacier information", className='text-danger')]
    
    def update_date_range_info(self, data_summary: Dict[str, Any]) -> Tuple[Optional[date], Optional[date], str]:
        """
        Update date range picker based on available data.
        
        Args:
            data_summary: Summary of available data
            
        Returns:
            Tuple of (start_date, end_date, info_text)
        """
        try:
            if not data_summary or 'date_range' not in data_summary:
                return None, None, "No date information available"
            
            date_range = data_summary['date_range']
            start_date_str = date_range.get('start')
            end_date_str = date_range.get('end')
            
            if not start_date_str or not end_date_str:
                return None, None, "Date range not available"
            
            # Convert to datetime objects
            start_date = pd.to_datetime(start_date_str).date()
            end_date = pd.to_datetime(end_date_str).date()
            
            info_text = f"Available data: {start_date} to {end_date}"
            
            return start_date, end_date, info_text
            
        except Exception as e:
            logger.error(f"Error updating date range info: {e}")
            return None, None, f"Error: {str(e)}"
#!/usr/bin/env python3
"""
Main Layout Component for Albedo Dashboard

This module defines the overall layout structure of the interactive dashboard,
organizing the sidebar controls, map, and visualization panels.
"""

import dash_bootstrap_components as dbc
from dash import html, dcc
import dash_leaflet as dl
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class DashboardLayout:
    """
    Handles the creation of the main dashboard layout.
    
    Features:
    - Responsive design with sidebar and main content area
    - Tabbed interface for different visualization types
    - Integrated map and plot panels
    - Loading states and error handling
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize layout with configuration."""
        self.config = config
        self.app_config = config.get('app', {})
        
        # Layout settings
        self.sidebar_width = 3
        self.main_content_width = 9
        
        logger.info("Dashboard layout initialized")
    
    def create_main_layout(self, available_glaciers: List[Dict[str, Any]]) -> html.Div:
        """
        Create the main dashboard layout.
        
        Args:
            available_glaciers: List of available glacier information
            
        Returns:
            HTML Div containing the complete layout
        """
        from .controls import ControlComponents
        
        # Initialize control components
        control_components = ControlComponents(self.config)
        
        layout = dbc.Container([
            # Store components for data management
            dcc.Store(id='glacier-data-store'),
            dcc.Store(id='pixel-data-store'),
            dcc.Store(id='selected-pixels-store', data=[]),
            dcc.Store(id='filtered-data-store'),
            
            # Loading overlay
            control_components.create_loading_overlay(),
            
            # Main row with sidebar and content
            dbc.Row([
                # Sidebar
                dbc.Col([
                    control_components.create_sidebar(available_glaciers)
                ], width=self.sidebar_width, className='bg-light'),
                
                # Main content area
                dbc.Col([
                    self.create_main_content_area()
                ], width=self.main_content_width)
            ], className='h-100'),
            
            # Interval component for periodic updates (if needed)
            dcc.Interval(
                id='interval-component',
                interval=30*1000,  # Update every 30 seconds
                n_intervals=0,
                disabled=True  # Disabled by default
            )
            
        ], fluid=True, className='h-100')
        
        return layout
    
    def create_main_content_area(self) -> html.Div:
        """
        Create the main content area with tabs for different views.
        
        Returns:
            HTML Div containing the main content
        """
        content_area = html.Div([
            # Header with title and status
            self.create_header(),
            
            # Tabbed interface
            dbc.Tabs([
                # Map and Selection Tab
                dbc.Tab(
                    label="Map & Selection",
                    tab_id="map-tab",
                    children=[
                        html.Div([
                            self.create_map_panel(),
                            self.create_selection_info_panel()
                        ], className='p-3')
                    ]
                ),
                
                # Scatter Plot Tab
                dbc.Tab(
                    label="Scatter Analysis",
                    tab_id="scatter-tab",
                    children=[
                        html.Div([
                            self.create_plot_panel("scatter-plot", "MODIS vs AWS Scatter Plot")
                        ], className='p-3')
                    ]
                ),
                
                # Time Series Tab
                dbc.Tab(
                    label="Time Series",
                    tab_id="timeseries-tab",
                    children=[
                        html.Div([
                            self.create_plot_panel("timeseries-plot", "Albedo Time Series")
                        ], className='p-3')
                    ]
                ),
                
                # Distribution Analysis Tab
                dbc.Tab(
                    label="Distributions",
                    tab_id="distribution-tab",
                    children=[
                        html.Div([
                            dbc.Row([
                                dbc.Col([
                                    self.create_plot_panel("box-plot", "Box Plot Analysis")
                                ], width=6),
                                dbc.Col([
                                    self.create_plot_panel("histogram-plot", "Histogram Analysis")
                                ], width=6)
                            ])
                        ], className='p-3')
                    ]
                ),
                
                # Statistical Summary Tab
                dbc.Tab(
                    label="Statistics",
                    tab_id="stats-tab",
                    children=[
                        html.Div([
                            dbc.Row([
                                dbc.Col([
                                    self.create_plot_panel("stats-table", "Statistical Summary")
                                ], width=6),
                                dbc.Col([
                                    self.create_plot_panel("correlation-matrix", "Correlation Matrix")
                                ], width=6)
                            ])
                        ], className='p-3')
                    ]
                )
            ], id="main-tabs", active_tab="map-tab")
        ])
        
        return content_area
    
    def create_header(self) -> html.Div:
        """
        Create the header with title and status indicators.
        
        Returns:
            HTML Div containing header elements
        """
        header = html.Div([
            dbc.Row([
                dbc.Col([
                    html.H3(
                        self.app_config.get('title', 'Interactive Albedo Analysis Dashboard'),
                        className='text-primary mb-0'
                    )
                ], width=8),
                dbc.Col([
                    html.Div([
                        dbc.Badge("Ready", color="success", id="status-badge", className="mr-2"),
                        html.Span(id="last-update", className="text-muted small")
                    ], className='text-right')
                ], width=4)
            ])
        ], className='border-bottom pb-2 mb-3')
        
        return header
    
    def create_map_panel(self) -> dbc.Card:
        """
        Create the map panel with interactive glacier map.
        
        Returns:
            Bootstrap Card containing the map
        """
        map_panel = dbc.Card([
            dbc.CardHeader([
                html.H5("Interactive Glacier Map", className="mb-0"),
                html.Small("Click on pixels to select them for analysis", className="text-muted")
            ]),
            dbc.CardBody([
                # Placeholder for map - will be populated by callbacks
                html.Div(id="map-container", children=[
                    html.Div([
                        html.P("Map will be loaded after glacier selection", 
                              className="text-center text-muted mt-5 pt-5")
                    ], style={'height': '400px'})
                ])
            ])
        ], className='mb-3')
        
        return map_panel
    
    def create_selection_info_panel(self) -> dbc.Card:
        """
        Create panel showing current selection information.
        
        Returns:
            Bootstrap Card with selection info
        """
        info_panel = dbc.Card([
            dbc.CardHeader("Selection Information"),
            dbc.CardBody([
                html.Div(id="selection-info-content", children=[
                    html.P("No pixels selected", className="text-muted")
                ])
            ])
        ], className='mb-3')
        
        return info_panel
    
    def create_plot_panel(self, plot_id: str, title: str) -> dbc.Card:
        """
        Create a panel for displaying plots.
        
        Args:
            plot_id: Unique identifier for the plot
            title: Display title for the panel
            
        Returns:
            Bootstrap Card containing plot area
        """
        plot_panel = dbc.Card([
            dbc.CardHeader([
                html.H5(title, className="mb-0"),
                dbc.Button(
                    "📥",
                    id=f"export-{plot_id}",
                    color="outline-secondary",
                    size="sm",
                    className="float-right",
                    title="Export plot"
                )
            ]),
            dbc.CardBody([
                dcc.Loading(
                    id=f"loading-{plot_id}",
                    children=[
                        dcc.Graph(
                            id=plot_id,
                            figure={},
                            style={'height': '400px'},
                            config={
                                'displayModeBar': True,
                                'displaylogo': False,
                                'modeBarButtonsToRemove': ['pan2d', 'lasso2d']
                            }
                        )
                    ],
                    type="default"
                )
            ])
        ])
        
        return plot_panel
    
    def create_error_modal(self) -> dbc.Modal:
        """
        Create modal dialog for error messages.
        
        Returns:
            Bootstrap Modal component
        """
        error_modal = dbc.Modal([
            dbc.ModalHeader("Error"),
            dbc.ModalBody(id="error-modal-body"),
            dbc.ModalFooter([
                dbc.Button("Close", id="close-error-modal", className="ml-auto")
            ])
        ], id="error-modal", is_open=False)
        
        return error_modal
    
    def create_export_modal(self) -> dbc.Modal:
        """
        Create modal dialog for data export options.
        
        Returns:
            Bootstrap Modal component
        """
        export_modal = dbc.Modal([
            dbc.ModalHeader("Export Data"),
            dbc.ModalBody([
                html.H6("Export Format:"),
                dbc.RadioItems(
                    id="export-format-radio",
                    options=[
                        {"label": "CSV (Comma-separated values)", "value": "csv"},
                        {"label": "PNG (Plot image)", "value": "png"},
                        {"label": "HTML (Interactive plot)", "value": "html"}
                    ],
                    value="csv"
                ),
                html.Hr(),
                html.H6("Data Selection:"),
                dbc.Checklist(
                    id="export-data-checklist",
                    options=[
                        {"label": "Raw data", "value": "raw"},
                        {"label": "Filtered data", "value": "filtered"},
                        {"label": "Statistical summary", "value": "stats"}
                    ],
                    value=["filtered"]
                )
            ]),
            dbc.ModalFooter([
                dbc.Button("Export", id="confirm-export", color="primary"),
                dbc.Button("Cancel", id="cancel-export", className="ml-2")
            ])
        ], id="export-modal", is_open=False)
        
        return export_modal
    
    def create_about_modal(self) -> dbc.Modal:
        """
        Create modal dialog with application information.
        
        Returns:
            Bootstrap Modal component
        """
        about_modal = dbc.Modal([
            dbc.ModalHeader("About This Dashboard"),
            dbc.ModalBody([
                html.H5("Interactive Albedo Analysis Dashboard"),
                html.P([
                    "This dashboard provides interactive analysis of glacier albedo measurements ",
                    "from MODIS satellite sensors compared against ground-based AWS (Automatic Weather Station) data."
                ]),
                html.H6("Features:"),
                html.Ul([
                    html.Li("Interactive map with pixel selection"),
                    html.Li("Real-time statistical analysis"),
                    html.Li("Multiple visualization types"),
                    html.Li("Data export capabilities"),
                    html.Li("Comparison of MOD09GA, MOD10A1, and MCD43A3 products")
                ]),
                html.H6("Data Sources:"),
                html.Ul([
                    html.Li("MODIS satellite albedo products"),
                    html.Li("AWS ground station measurements"), 
                    html.Li("Glacier boundary shapefiles")
                ]),
                html.Hr(),
                html.P("Built with Plotly Dash and integrated with existing albedo analysis framework.",
                      className="text-muted small")
            ]),
            dbc.ModalFooter([
                dbc.Button("Close", id="close-about-modal")
            ])
        ], id="about-modal", is_open=False, size="lg")
        
        return about_modal
    
    def create_navbar(self) -> dbc.Navbar:
        """
        Create navigation bar (optional).
        
        Returns:
            Bootstrap Navbar component
        """
        navbar = dbc.Navbar([
            dbc.NavbarBrand(
                self.app_config.get('title', 'Albedo Dashboard'),
                className="ml-2"
            ),
            dbc.Nav([
                dbc.NavItem([
                    dbc.Button("About", id="about-btn", color="link", size="sm")
                ])
            ], className="ml-auto", navbar=True)
        ], color="dark", dark=True, sticky="top")
        
        return navbar
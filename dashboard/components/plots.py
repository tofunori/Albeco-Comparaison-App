#!/usr/bin/env python3
"""
Interactive Plot Components for Albedo Dashboard

This module provides interactive visualization components using Plotly,
including scatter plots, time series, box plots, and statistical summaries.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PlotComponents:
    """
    Handles the creation of interactive plot components for the albedo dashboard.
    
    Features:
    - Scatter plots (MODIS vs AWS)
    - Time series analysis
    - Box plots for method comparison
    - Histograms for distribution analysis
    - Statistical summary tables
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize plot components with configuration."""
        self.config = config
        self.plot_config = config.get('visualization', {}).get('plots', {})
        
        # Color scheme - distinct, vibrant colors for each method
        self.colors = self.plot_config.get('color_scheme', {
            'MOD09GA': '#0066CC',    # Bright Blue
            'MYD09GA': '#FF6600',    # Bright Orange  
            'mod10a1': '#00AA00',    # Bright Green
            'myd10a1': '#CC0000',    # Bright Red
            'mcd43a3': '#9900CC',    # Bright Purple
            'MOD10A1': '#00AA00',    # Bright Green (fallback for uppercase)
            'MYD10A1': '#CC0000',    # Bright Red (fallback for uppercase)  
            'MCD43A3': '#9900CC',    # Bright Purple (fallback for uppercase)
            'AWS': '#8c564b'         # Brown
        })
        
        # Figure settings
        self.figure_size = self.plot_config.get('figure_size', [12, 8])
        self.dpi = self.plot_config.get('dpi', 100)
        
        logger.info("Plot components initialized")
    
    def create_scatter_plot(self, data: pd.DataFrame, 
                          methods: Optional[List[str]] = None,
                          title: str = "MODIS vs AWS Albedo Comparison") -> go.Figure:
        """
        Create scatter plot comparing MODIS methods against AWS measurements.
        
        Args:
            data: DataFrame with MODIS and AWS albedo data
            methods: List of MODIS methods to include
            title: Plot title
            
        Returns:
            Plotly Figure object
        """
        try:
            if data is None or data.empty:
                return self._create_empty_plot("No data available for scatter plot")
            
            # Filter methods if specified
            if methods:
                plot_data = data[data['method'].isin(methods)] if 'method' in data.columns else data
            else:
                plot_data = data
            
            # Check for required columns
            if 'albedo' not in plot_data.columns or 'aws_albedo' not in plot_data.columns:
                return self._create_empty_plot("Required albedo columns not found")
            
            # Ensure method column is string type for proper categorical handling
            if 'method' in plot_data.columns:
                plot_data = plot_data.copy()
                plot_data['method'] = plot_data['method'].astype(str)
            
            logger.info(f"Creating scatter plot for methods: {plot_data['method'].unique() if 'method' in plot_data.columns else 'No method column'}")
            logger.info(f"Available colors: {self.colors}")
            logger.info(f"Data shape: {plot_data.shape}, columns: {list(plot_data.columns)}")
            
            # Use Plotly Express for better color handling
            if 'method' in plot_data.columns:
                # Include date in hover data if available
                hover_data_fields = ['method']
                if 'date' in plot_data.columns:
                    hover_data_fields.append('date')
                
                fig = px.scatter(
                    plot_data, 
                    x='aws_albedo', 
                    y='albedo',
                    color='method',
                    color_discrete_map=self.colors,  # Explicit color mapping
                    title=title,
                    labels={
                        'aws_albedo': 'AWS Albedo',
                        'albedo': 'MODIS Albedo',
                        'method': 'Method',
                        'date': 'Date'
                    },
                    hover_data=hover_data_fields
                )
                
                # Update marker size and opacity
                fig.update_traces(
                    marker=dict(size=8, opacity=0.8, line=dict(width=0))
                )
                
            else:
                # Fallback for data without method column
                fig = px.scatter(
                    plot_data, 
                    x='aws_albedo', 
                    y='albedo',
                    title=title,
                    labels={
                        'aws_albedo': 'AWS Albedo',
                        'albedo': 'MODIS Albedo'
                    }
                )
                fig.update_traces(
                    marker=dict(size=8, opacity=0.8, line=dict(width=0), color='#1f77b4')
                )
            
            # Add trend lines for each method
            if 'method' in plot_data.columns:
                methods_in_data = plot_data['method'].unique()
                for method in methods_in_data:
                    method_data = plot_data[plot_data['method'] == method]
                    clean_data = method_data.dropna(subset=['albedo', 'aws_albedo'])
                    
                    if len(clean_data) > 2:
                        try:
                            x_vals = clean_data['aws_albedo']
                            y_vals = clean_data['albedo']
                            
                            z = np.polyfit(x_vals, y_vals, 1)
                            p = np.poly1d(z)
                            
                            x_trend = np.linspace(x_vals.min(), x_vals.max(), 100)
                            y_trend = p(x_trend)
                            
                            method_color = self.colors.get(method, '#1f77b4')
                            
                            fig.add_trace(go.Scatter(
                                x=x_trend,
                                y=y_trend,
                                mode='lines',
                                name=f'{method} Trend',
                                line=dict(
                                    color=method_color,
                                    dash='dash',
                                    width=2
                                ),
                                showlegend=False
                            ))
                        except Exception as e:
                            logger.warning(f"Could not create trend line for {method}: {e}")
            
            # Add 1:1 reference line
            if not plot_data.empty:
                all_values = pd.concat([
                    plot_data['albedo'].dropna(),
                    plot_data['aws_albedo'].dropna()
                ])
                min_val = all_values.min()
                max_val = all_values.max()
                
                fig.add_trace(go.Scatter(
                    x=[min_val, max_val],
                    y=[min_val, max_val],
                    mode='lines',
                    name='1:1 Line',
                    line=dict(color='black', dash='dot', width=1),
                    showlegend=True
                ))
            
            # Update layout
            fig.update_layout(
                width=self.figure_size[0] * 80,
                height=self.figure_size[1] * 60,
                showlegend=True,
                hovermode='closest'
            )
            
            # Debug info
            logger.info(f"Final figure has {len(fig.data)} traces")
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating scatter plot: {e}")
            return self._create_empty_plot(f"Error creating scatter plot: {str(e)}")
    
    def create_time_series_plot(self, data: pd.DataFrame,
                               methods: Optional[List[str]] = None,
                               title: str = "Albedo Time Series") -> go.Figure:
        """
        Create time series plot showing albedo values over time.
        
        Args:
            data: DataFrame with time series data
            methods: List of MODIS methods to include
            title: Plot title
            
        Returns:
            Plotly Figure object
        """
        try:
            if data is None or data.empty:
                return self._create_empty_plot("No data available for time series plot")
            
            if 'date' not in data.columns:
                return self._create_empty_plot("Date column not found for time series")
            
            # Convert date column and ensure method is string
            plot_data = data.copy()
            plot_data['date'] = pd.to_datetime(plot_data['date'])
            
            if 'method' in plot_data.columns:
                plot_data['method'] = plot_data['method'].astype(str)
            
            # Filter methods if specified
            if methods and 'method' in plot_data.columns:
                plot_data = plot_data[plot_data['method'].isin(methods)]
            
            # Create base figure using Plotly Express for MODIS data
            if 'method' in plot_data.columns and 'albedo' in plot_data.columns:
                # Remove NaN values for cleaner plot
                modis_data = plot_data.dropna(subset=['albedo'])
                
                if not modis_data.empty:
                    fig = px.line(
                        modis_data,
                        x='date',
                        y='albedo',
                        color='method',
                        color_discrete_map=self.colors,
                        title=title,
                        labels={
                            'date': 'Date',
                            'albedo': 'Albedo',
                            'method': 'Method'
                        },
                        markers=True
                    )
                    
                    # Update marker and line properties
                    fig.update_traces(
                        marker=dict(size=4),
                        line=dict(width=1)
                    )
                else:
                    fig = go.Figure()
            else:
                fig = go.Figure()
            
            # Add AWS data if available
            if 'aws_albedo' in plot_data.columns:
                aws_data = plot_data.dropna(subset=['aws_albedo'])
                if not aws_data.empty:
                    fig.add_trace(go.Scatter(
                        x=aws_data['date'],
                        y=aws_data['aws_albedo'],
                        mode='markers+lines',
                        name='AWS',
                        marker=dict(
                            color=self.colors.get('AWS', '#8c564b'),
                            size=4
                        ),
                        line=dict(
                            color=self.colors.get('AWS', '#8c564b'),
                            width=2
                        )
                    ))
            
            # Update layout
            fig.update_layout(
                width=self.figure_size[0] * 80,
                height=self.figure_size[1] * 60,
                showlegend=True,
                hovermode='x unified'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating time series plot: {e}")
            return self._create_empty_plot(f"Error creating time series plot: {str(e)}")
    
    def create_box_plot(self, data: pd.DataFrame,
                       methods: Optional[List[str]] = None,
                       title: str = "Albedo Distribution by Method") -> go.Figure:
        """
        Create box plot showing albedo distribution for different methods.
        
        Args:
            data: DataFrame with albedo data
            methods: List of MODIS methods to include
            title: Plot title
            
        Returns:
            Plotly Figure object
        """
        try:
            if data is None or data.empty:
                return self._create_empty_plot("No data available for box plot")
            
            if 'method' not in data.columns or 'albedo' not in data.columns:
                return self._create_empty_plot("Required columns not found for box plot")
            
            # Prepare data with method as string for categorical handling
            plot_data = data.copy()
            plot_data['method'] = plot_data['method'].astype(str)
            
            # Filter methods if specified
            if methods:
                plot_data = plot_data[plot_data['method'].isin(methods)]
            
            # Remove NaN values for cleaner plot
            modis_data = plot_data.dropna(subset=['albedo'])
            
            if not modis_data.empty:
                # Create box plot using Plotly Express
                fig = px.box(
                    modis_data,
                    x='method',
                    y='albedo',
                    color='method',
                    color_discrete_map=self.colors,
                    title=title,
                    labels={
                        'method': 'Method',
                        'albedo': 'Albedo'
                    },
                    points='outliers'  # Show outlier points
                )
                
                # Remove the separate color legend since x-axis already shows methods
                fig.update_layout(showlegend=False)
            else:
                fig = go.Figure()
            
            # Add AWS data if available
            if 'aws_albedo' in plot_data.columns:
                aws_data = plot_data['aws_albedo'].dropna()
                if not aws_data.empty:
                    fig.add_trace(go.Box(
                        y=aws_data,
                        name='AWS',
                        marker_color=self.colors.get('AWS', '#8c564b'),
                        boxpoints='outliers',
                        x=['AWS'] * len(aws_data)  # Position AWS box
                    ))
                    fig.update_layout(showlegend=True)  # Show legend when AWS is present
            
            # Update layout
            fig.update_layout(
                width=self.figure_size[0] * 80,          
                height=self.figure_size[1] * 60,
                xaxis_title='Method',
                yaxis_title='Albedo'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating box plot: {e}")
            return self._create_empty_plot(f"Error creating box plot: {str(e)}")
    
    def create_histogram(self, data: pd.DataFrame,
                        methods: Optional[List[str]] = None,
                        title: str = "Albedo Value Distribution") -> go.Figure:
        """
        Create histogram showing albedo value distributions.
        
        Args:
            data: DataFrame with albedo data
            methods: List of MODIS methods to include
            title: Plot title
            
        Returns:
            Plotly Figure object
        """
        try:
            if data is None or data.empty:
                return self._create_empty_plot("No data available for histogram")
            
            # Prepare data with method as string for categorical handling
            plot_data = data.copy()
            if 'method' in plot_data.columns:
                plot_data['method'] = plot_data['method'].astype(str)
            
            # Filter methods if specified
            if methods and 'method' in plot_data.columns:
                plot_data = plot_data[plot_data['method'].isin(methods)]
            
            # Create histogram using Plotly Express for MODIS data
            if 'method' in plot_data.columns and 'albedo' in plot_data.columns:
                # Remove NaN values for cleaner plot
                modis_data = plot_data.dropna(subset=['albedo'])
                
                if not modis_data.empty:
                    fig = px.histogram(
                        modis_data,
                        x='albedo',
                        color='method',
                        color_discrete_map=self.colors,
                        title=title,
                        labels={
                            'albedo': 'Albedo',
                            'method': 'Method',
                            'count': 'Frequency'
                        },
                        nbins=30,
                        opacity=0.7,
                        barmode='overlay'  # Overlay histograms for comparison
                    )
                else:
                    fig = go.Figure()
            else:
                fig = go.Figure()
            
            # Add AWS data if available
            if 'aws_albedo' in plot_data.columns:
                aws_data = plot_data['aws_albedo'].dropna()
                if not aws_data.empty:
                    fig.add_trace(go.Histogram(
                        x=aws_data,
                        name='AWS',
                        opacity=0.7,
                        marker_color=self.colors.get('AWS', '#8c564b'),
                        nbinsx=30
                    ))
            
            # Update layout
            fig.update_layout(
                width=self.figure_size[0] * 80,
                height=self.figure_size[1] * 60,
                barmode='overlay',
                showlegend=True,
                xaxis_title='Albedo',
                yaxis_title='Frequency'
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating histogram: {e}")
            return self._create_empty_plot(f"Error creating histogram: {str(e)}")
    
    def create_statistical_summary_table(self, stats: Dict[str, Any]) -> go.Figure:
        """
        Create a table displaying statistical summary.
        
        Args:
            stats: Dictionary with statistical results
            
        Returns:
            Plotly Figure with table
        """
        try:
            if not stats:
                return self._create_empty_plot("No statistical data available")
            
            # Prepare table data
            headers = ['Metric', 'Value']
            values = []
            
            # Extract key statistics
            key_metrics = [
                ('Correlation (r)', 'correlation'),
                ('RMSE', 'rmse'),
                ('Bias', 'bias'),
                ('MAE', 'mae'),
                ('Sample Size', 'sample_size')
            ]
            
            for display_name, key in key_metrics:
                if key in stats:
                    value = stats[key]
                    if isinstance(value, (int, float)):
                        if key == 'sample_size':
                            formatted_value = f"{value:,.0f}"
                        else:
                            formatted_value = f"{value:.4f}"
                    else:
                        formatted_value = str(value)
                    values.append([display_name, formatted_value])
            
            if not values:
                return self._create_empty_plot("No statistics to display")
            
            # Create table
            fig = go.Figure(data=[go.Table(
                header=dict(
                    values=headers,
                    fill_color='lightblue',
                    align='left',
                    font=dict(size=12, color='black')
                ),
                cells=dict(
                    values=list(zip(*values)),
                    fill_color='white',
                    align='left',
                    font=dict(size=11, color='black')
                )
            )])
            
            fig.update_layout(
                title="Statistical Summary",
                width=400,
                height=300,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating statistical summary table: {e}")
            return self._create_empty_plot(f"Error creating summary table: {str(e)}")
    
    def create_correlation_matrix(self, data: pd.DataFrame) -> go.Figure:
        """
        Create correlation matrix heatmap.
        
        Args:
            data: DataFrame with multiple albedo methods
            
        Returns:
            Plotly Figure with heatmap
        """
        try:
            if data is None or data.empty:
                return self._create_empty_plot("No data available for correlation matrix")
            
            # Pivot data to get methods as columns
            if 'method' in data.columns and 'albedo' in data.columns:
                pivot_data = data.pivot_table(
                    index='date' if 'date' in data.columns else data.index,
                    columns='method',
                    values='albedo',
                    aggfunc='mean'
                )
                
                # Add AWS data if available
                if 'aws_albedo' in data.columns:
                    aws_series = data.groupby('date' if 'date' in data.columns else data.index)['aws_albedo'].mean()
                    pivot_data['AWS'] = aws_series
                
                # Calculate correlation matrix
                corr_matrix = pivot_data.corr()
                
                # Create heatmap
                fig = go.Figure(data=go.Heatmap(
                    z=corr_matrix.values,
                    x=corr_matrix.columns,
                    y=corr_matrix.index,
                    colorscale='RdBu',
                    zmid=0,
                    text=corr_matrix.values.round(3),
                    texttemplate='%{text}',
                    textfont={"size": 10},
                    hoverongaps=False
                ))
                
                fig.update_layout(
                    title="Method Correlation Matrix",
                    width=500,
                    height=400
                )
                
                return fig
            
            else:
                return self._create_empty_plot("Insufficient data for correlation matrix")
                
        except Exception as e:
            logger.error(f"Error creating correlation matrix: {e}")
            return self._create_empty_plot(f"Error creating correlation matrix: {str(e)}")
    
    def _create_empty_plot(self, message: str) -> go.Figure:
        """Create an empty plot with a message."""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            width=self.figure_size[0] * 80,
            height=self.figure_size[1] * 60
        )
        return fig
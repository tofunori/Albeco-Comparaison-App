#!/usr/bin/env python3
"""
Interactive Map Component for Albedo Dashboard

This module provides the interactive map functionality using dash-leaflet,
displaying glaciers, MODIS pixels, and AWS stations with selection capabilities.
"""

import dash_leaflet as dl
import plotly.express as px
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class MapComponent:
    """
    Handles the interactive map display for the albedo analysis dashboard.
    
    Features:
    - Display glacier boundaries
    - Show MODIS pixel locations
    - AWS station markers
    - Pixel selection via clicking
    - Multi-pixel selection support
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the map component with configuration."""
        self.config = config
        self.map_config = config.get('visualization', {}).get('map', {})
        
        # Default map settings
        self.default_zoom = self.map_config.get('default_zoom', 10)
        self.marker_size = self.map_config.get('marker_size', 8)
        self.selected_marker_size = self.map_config.get('selected_marker_size', 12)
        
        # Color scheme
        self.colors = config.get('visualization', {}).get('plots', {}).get('color_scheme', {
            'MOD09GA': '#1f77b4',
            'MOD10A1': '#ff7f0e',
            'MCD43A3': '#2ca02c',
            'AWS': '#d62728'
        })
        
        logger.info("Map component initialized")
    
    def create_base_map(self, center_lat: float = 52.0, center_lon: float = -117.0) -> dl.Map:
        """
        Create the base map with default settings.
        
        Args:
            center_lat: Initial map center latitude
            center_lon: Initial map center longitude
            
        Returns:
            dash_leaflet Map component
        """
        return dl.Map(
            id="glacier-map",
            style={'width': '100%', 'height': '600px'},
            center=[center_lat, center_lon],
            zoom=self.default_zoom,
            children=[
                dl.TileLayer(),
                dl.LayerGroup(id="pixel-layer"),
                dl.LayerGroup(id="aws-layer"),
                dl.LayerGroup(id="glacier-boundary-layer")
            ]
        )
    
    def create_pixel_markers(self, pixels_df: pd.DataFrame, 
                           selected_pixels: Optional[List[str]] = None) -> List[dl.Marker]:
        """
        Create markers for MODIS pixels.
        
        Args:
            pixels_df: DataFrame with pixel information
            selected_pixels: List of selected pixel IDs
            
        Returns:
            List of dash_leaflet Marker components
        """
        if pixels_df is None or pixels_df.empty:
            return []
        
        markers = []
        selected_pixels = selected_pixels or []
        
        # Normalize selected pixels to handle type consistency
        # Convert all selected pixels to strings and handle float conversion
        normalized_selected = []
        for pixel_id in selected_pixels:
            # Convert to string and handle potential .0 suffix from float conversion
            str_id = str(pixel_id)
            if str_id.endswith('.0'):
                str_id = str_id[:-2]  # Remove .0 suffix
            normalized_selected.append(str_id)
        
        for _, pixel in pixels_df.iterrows():
            try:
                # Normalize pixel ID consistently
                raw_pixel_id = pixel['pixel_id']
                pixel_id = str(int(raw_pixel_id))  # Convert to int first, then string to avoid .0
                
                lat = float(pixel['latitude'])
                lon = float(pixel['longitude'])
                
                # Determine marker properties based on selection
                is_selected = pixel_id in normalized_selected
                marker_size = self.selected_marker_size if is_selected else self.marker_size
                marker_color = 'red' if is_selected else 'blue'
                
                # Create tooltip with pixel information
                tooltip_content = self._create_pixel_tooltip(pixel)
                
                marker = dl.Marker(
                    position=[lat, lon],
                    id={'type': 'pixel-marker', 'pixel_id': pixel_id},
                    children=[
                        dl.Tooltip(tooltip_content)
                    ],
                    icon={
                        'iconUrl': 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-' + marker_color + '.png',
                        'shadowUrl': 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                        'iconSize': [marker_size, marker_size],
                        'iconAnchor': [marker_size//2, marker_size],
                        'popupAnchor': [1, -marker_size],
                        'shadowSize': [marker_size, marker_size]
                    }
                )
                
                markers.append(marker)
                
            except Exception as e:
                logger.warning(f"Error creating marker for pixel {pixel.get('pixel_id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Created {len(markers)} pixel markers")
        return markers
    
    def _create_pixel_tooltip(self, pixel: pd.Series) -> str:
        """Create tooltip content for a pixel marker."""
        tooltip_lines = [
            f"Pixel ID: {pixel['pixel_id']}",
            f"Coordinates: {pixel['latitude']:.4f}, {pixel['longitude']:.4f}"
        ]
        
        # Add additional information if available
        if 'glacier_fraction' in pixel and pd.notna(pixel['glacier_fraction']):
            tooltip_lines.append(f"Glacier Fraction: {pixel['glacier_fraction']:.3f}")
        
        if 'elevation' in pixel and pd.notna(pixel['elevation']):
            tooltip_lines.append(f"Elevation: {pixel['elevation']:.0f} m")
        
        return " | ".join(tooltip_lines)
    
    def create_aws_marker(self, aws_info: Dict[str, Any]) -> Optional[dl.Marker]:
        """
        Create marker for AWS station.
        
        Args:
            aws_info: Dictionary with AWS station information
            
        Returns:
            dash_leaflet Marker component or None
        """
        try:
            if not aws_info:
                return None
            
            lat = float(aws_info['lat'])
            lon = float(aws_info['lon'])
            name = aws_info.get('name', 'AWS Station')
            elevation = aws_info.get('elevation', 'Unknown')
            
            # Create tooltip
            tooltip_content = f"{name} | Elevation: {elevation} m | Coordinates: {lat:.4f}, {lon:.4f}"
            
            marker = dl.Marker(
                position=[lat, lon],
                id="aws-station-marker",
                children=[
                    dl.Tooltip(tooltip_content)
                ],
                icon={
                    'iconUrl': 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
                    'shadowUrl': 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                    'iconSize': [15, 15],
                    'iconAnchor': [7, 15],
                    'popupAnchor': [1, -15],
                    'shadowSize': [15, 15]
                }
            )
            
            logger.info(f"Created AWS marker for {name}")
            return marker
            
        except Exception as e:
            logger.error(f"Error creating AWS marker: {e}")
            return None
    
    def create_glacier_boundary(self, glacier_id: str, 
                              glacier_info: Dict[str, Any]) -> Optional[dl.GeoJSON]:
        """
        Create glacier boundary overlay (placeholder - would need shapefile processing).
        
        Args:
            glacier_id: Glacier identifier
            glacier_info: Glacier configuration information
            
        Returns:
            dash_leaflet GeoJSON component or None
        """
        try:
            # This is a placeholder - in full implementation would load actual shapefiles
            # For now, create a simple circle around the glacier center
            coords = glacier_info.get('coordinates', {})
            if not coords:
                return None
            
            lat = coords.get('lat')
            lon = coords.get('lon')
            
            if lat is None or lon is None:
                return None
            
            # Create a simple circle boundary (placeholder)
            circle = dl.Circle(
                center=[lat, lon],
                radius=5000,  # 5km radius
                id=f"glacier-boundary-{glacier_id}",
                color='purple',
                fill=True,
                fillOpacity=0.2,
                children=[
                    dl.Tooltip(f"{glacier_info.get('name', glacier_id)} Boundary (Approximate)")
                ]
            )
            
            logger.info(f"Created boundary for {glacier_id}")
            return circle
            
        except Exception as e:
            logger.error(f"Error creating glacier boundary for {glacier_id}: {e}")
            return None
    
    def update_map_view(self, glacier_id: str, glacier_info: Dict[str, Any], 
                       pixels_df: Optional[pd.DataFrame] = None,
                       selected_pixels: Optional[List[str]] = None) -> Tuple[List[Any], List[float], int]:
        """
        Update map view for a specific glacier.
        
        Args:
            glacier_id: Glacier identifier
            glacier_info: Glacier configuration
            pixels_df: DataFrame with pixel locations
            selected_pixels: List of selected pixel IDs
            
        Returns:
            Tuple of (map_children, center_coordinates, zoom_level)
        """
        try:
            # Get glacier center coordinates
            coords = glacier_info.get('coordinates', {})
            center_lat = coords.get('lat', 52.0)
            center_lon = coords.get('lon', -117.0)
            
            map_children = [dl.TileLayer()]
            
            # Add glacier boundary
            boundary = self.create_glacier_boundary(glacier_id, glacier_info)
            if boundary:
                map_children.append(boundary)
            
            # Add pixel markers
            if pixels_df is not None and not pixels_df.empty:
                pixel_markers = self.create_pixel_markers(pixels_df, selected_pixels)
                if pixel_markers:
                    map_children.extend(pixel_markers)
            
            # Add AWS station marker (from data manager)
            # This would be populated by the data manager in the callback
            
            logger.info(f"Updated map view for {glacier_id}")
            return map_children, [center_lat, center_lon], self.default_zoom
            
        except Exception as e:
            logger.error(f"Error updating map view for {glacier_id}: {e}")
            return [dl.TileLayer()], [52.0, -117.0], self.default_zoom
    
    def get_selected_pixels_from_clicks(self, click_data: List[Dict[str, Any]]) -> List[str]:
        """
        Extract selected pixel IDs from map click events.
        
        Args:
            click_data: List of click event data
            
        Returns:
            List of selected pixel IDs
        """
        selected_pixels = []
        
        if not click_data:
            return selected_pixels
        
        try:
            for click_event in click_data:
                if isinstance(click_event, dict) and 'id' in click_event:
                    marker_id = click_event['id']
                    if isinstance(marker_id, dict) and marker_id.get('type') == 'pixel-marker':
                        pixel_id = marker_id.get('pixel_id')
                        if pixel_id and pixel_id not in selected_pixels:
                            selected_pixels.append(pixel_id)
            
            logger.info(f"Extracted {len(selected_pixels)} selected pixels from clicks")
            return selected_pixels
            
        except Exception as e:
            logger.error(f"Error extracting selected pixels from clicks: {e}")
            return []
    
    def create_legend(self) -> dl.Marker:
        """Create a legend for the map markers."""
        legend_html = """
        <div style="position: fixed; 
                    top: 10px; right: 10px; width: 200px; height: 120px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <h4>Map Legend</h4>
        <div><span style="color:blue;">●</span> MODIS Pixels</div>
        <div><span style="color:red;">●</span> Selected Pixels</div>
        <div><span style="color:green;">●</span> AWS Station</div>
        <div><span style="color:purple;">—</span> Glacier Boundary</div>
        </div>
        """
        
        return dl.Marker(
            position=[0, 0],
            icon={
                'iconUrl': 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMSIgaGVpZ2h0PSIxIj48L3N2Zz4=',
                'iconSize': [1, 1]
            },
            children=[dl.DivIcon(html=legend_html)]
        )
#!/usr/bin/env python3
"""
Data Manager for Interactive Dashboard

This module provides the interface between the dashboard and the existing
albedo analysis framework, handling data loading, caching, and processing.
"""

import pandas as pd
import numpy as np
import yaml
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import sys
import os

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Try to import optional dependencies
try:
    import geopandas as gpd
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False

# Try to import analysis modules with fallbacks
try:
    from data_processing.loaders.pivot_loaders import create_pivot_based_loader
    HAS_PIVOT_LOADER = True
except ImportError:
    HAS_PIVOT_LOADER = False
    create_pivot_based_loader = None

try:
    from analysis.core.statistical_analyzer import StatisticalAnalyzer
    HAS_STATISTICAL_ANALYZER = True
except ImportError:
    HAS_STATISTICAL_ANALYZER = False
    StatisticalAnalyzer = None

logger = logging.getLogger(__name__)


class DashboardDataManager:
    """
    Manages data loading, processing, and caching for the interactive dashboard.
    
    Integrates with the existing albedo analysis framework to provide
    real-time data access and statistical calculations.
    """
    
    def __init__(self, config_path: str = "config/dashboard_config.yaml"):
        """Initialize the data manager with configuration."""
        self.config = self._load_config(config_path)
        self.glacier_config = self._load_glacier_config()
        self.data_cache = {}
        self.pixel_cache = {}
        
        # Initialize statistical analyzer if available
        if HAS_STATISTICAL_ANALYZER and StatisticalAnalyzer is not None:
            self.stats_analyzer = StatisticalAnalyzer(self.config.get('analysis', {}))
        else:
            self.stats_analyzer = None
            logger.warning("Statistical analyzer not available, using simplified calculations")
        
        # Initialize data paths
        data_config = self.config.get('data', {})
        self.data_base_path = Path(data_config.get('base_path', 'data'))
        self.modis_path = Path(data_config.get('modis_path', 'data/modis'))
        self.aws_path = Path(data_config.get('aws_path', 'data/aws'))
        self.masks_path = Path(data_config.get('glacier_masks_path', 'data/glacier_masks'))
        
        logger.info("Dashboard Data Manager initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load dashboard configuration."""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            return {}
    
    def _load_glacier_config(self) -> Dict[str, Any]:
        """Load glacier sites configuration."""
        try:
            with open("config/glacier_sites.yaml", 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            logger.error(f"Error loading glacier config: {e}")
            return {}
    
    def get_available_glaciers(self) -> List[Dict[str, Any]]:
        """Get list of available glaciers with metadata."""
        glaciers = []
        
        for glacier_id, glacier_info in self.glacier_config.get('glaciers', {}).items():
            glacier_data = {
                'id': glacier_id,
                'name': glacier_info.get('name', glacier_id.title()),
                'region': glacier_info.get('region', 'Unknown'),
                'coordinates': glacier_info.get('coordinates', {}),
                'data_available': self._check_data_availability(glacier_id, glacier_info)
            }
            glaciers.append(glacier_data)
        
        return glaciers
    
    def _check_data_availability(self, glacier_id: str, glacier_info: Dict[str, Any]) -> Dict[str, bool]:
        """Check if required data files exist for a glacier."""
        availability = {
            'modis': False,
            'aws': False,
            'mask': False
        }
        
        try:
            # Check MODIS data
            modis_files = glacier_info.get('data_files', {}).get('modis', {})
            if modis_files:
                modis_file = list(modis_files.values())[0]  # Get first file
                modis_path = self.modis_path / glacier_id / modis_file
                availability['modis'] = modis_path.exists()
            
            # Check AWS data
            aws_file = glacier_info.get('data_files', {}).get('aws')
            if aws_file:
                aws_file_path = self.aws_path / aws_file
                availability['aws'] = aws_file_path.exists()
            
            # Check mask data
            mask_file = glacier_info.get('data_files', {}).get('mask')
            if mask_file:
                mask_path = Path(mask_file)
                if not mask_path.is_absolute():
                    mask_path = project_root / mask_file
                availability['mask'] = mask_path.exists()
                
        except Exception as e:
            logger.error(f"Error checking data availability for {glacier_id}: {e}")
        
        return availability
    
    def load_glacier_data(self, glacier_id: str, force_reload: bool = False) -> Optional[pd.DataFrame]:
        """
        Load MODIS and AWS data for a specific glacier.
        
        Args:
            glacier_id: Identifier for the glacier
            force_reload: Force reload data even if cached
            
        Returns:
            DataFrame with merged MODIS and AWS data
        """
        cache_key = f"{glacier_id}_data"
        
        if not force_reload and cache_key in self.data_cache:
            logger.info(f"Using cached data for {glacier_id}")
            return self.data_cache[cache_key]
        
        try:
            glacier_info = self.glacier_config['glaciers'][glacier_id]
            
            # Use simple CSV loading for now (complex loader has compatibility issues)
            logger.info(f"Using simple CSV loading for {glacier_id}")
            merged_data = self._load_simple_csv_data(glacier_id, glacier_info)
            
            if merged_data is not None and not merged_data.empty:
                self.data_cache[cache_key] = merged_data
                logger.info(f"Successfully loaded data for {glacier_id}: {len(merged_data)} records")
                return merged_data
            else:
                logger.warning(f"No data loaded for {glacier_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading data for {glacier_id}: {e}")
            return None
    
    def get_pixel_locations(self, glacier_id: str) -> Optional[pd.DataFrame]:
        """
        Get pixel locations and metadata for a glacier.
        
        Args:
            glacier_id: Identifier for the glacier
            
        Returns:
            DataFrame with pixel coordinates and metadata
        """
        cache_key = f"{glacier_id}_pixels"
        
        if cache_key in self.pixel_cache:
            return self.pixel_cache[cache_key]
        
        try:
            data = self.load_glacier_data(glacier_id)
            if data is None:
                return None
            
            # Extract unique pixel information
            pixel_cols = ['pixel_id', 'latitude', 'longitude', 'glacier_fraction', 'elevation']
            available_cols = [col for col in pixel_cols if col in data.columns]
            
            if not available_cols:
                logger.warning(f"No pixel location columns found for {glacier_id}")
                return None
            
            pixels = data[available_cols].drop_duplicates(subset=['pixel_id'])
            pixels = pixels.reset_index(drop=True)
            
            # Cache the pixel data
            self.pixel_cache[cache_key] = pixels
            logger.info(f"Extracted {len(pixels)} unique pixels for {glacier_id}")
            
            return pixels
            
        except Exception as e:
            logger.error(f"Error getting pixel locations for {glacier_id}: {e}")
            return None
    
    def get_aws_station_info(self, glacier_id: str) -> Optional[Dict[str, Any]]:
        """Get AWS station information for a glacier."""
        try:
            glacier_info = self.glacier_config['glaciers'][glacier_id]
            aws_stations = glacier_info.get('aws_stations', {})
            
            if aws_stations:
                # Return the first station (most glaciers have one)
                station_id = list(aws_stations.keys())[0]
                station_info = aws_stations[station_id].copy()
                station_info['id'] = station_id
                return station_info
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting AWS station info for {glacier_id}: {e}")
            return None
    
    def filter_data(self, glacier_id: str, pixel_ids: Optional[List[str]] = None, 
                   methods: Optional[List[str]] = None, 
                   date_range: Optional[Tuple[str, str]] = None) -> Optional[pd.DataFrame]:
        """
        Filter glacier data based on selection criteria.
        
        Args:
            glacier_id: Identifier for the glacier
            pixel_ids: List of pixel IDs to include
            methods: List of MODIS methods to include
            date_range: Tuple of (start_date, end_date)
            
        Returns:
            Filtered DataFrame
        """
        try:
            data = self.load_glacier_data(glacier_id)
            if data is None:
                return None
            
            filtered_data = data.copy()
            
            # Filter by pixel IDs
            if pixel_ids:
                filtered_data = filtered_data[filtered_data['pixel_id'].isin(pixel_ids)]
            
            # Filter by methods
            if methods and 'method' in filtered_data.columns:
                filtered_data = filtered_data[filtered_data['method'].isin(methods)]
            
            # Filter by date range
            if date_range and 'date' in filtered_data.columns:
                start_date, end_date = date_range
                filtered_data['date'] = pd.to_datetime(filtered_data['date'])
                filtered_data = filtered_data[
                    (filtered_data['date'] >= start_date) & 
                    (filtered_data['date'] <= end_date)
                ]
            
            logger.info(f"Filtered data for {glacier_id}: {len(filtered_data)} records")
            return filtered_data
            
        except Exception as e:
            logger.error(f"Error filtering data for {glacier_id}: {e}")
            return None
    
    def _load_simple_csv_data(self, glacier_id: str, glacier_info: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """
        Simple CSV data loading fallback method.
        
        Args:
            glacier_id: Glacier identifier
            glacier_info: Glacier configuration
            
        Returns:
            DataFrame with basic data loading
        """
        try:
            # Load MODIS data
            modis_files = glacier_info.get('data_files', {}).get('modis', {})
            if not modis_files:
                logger.error(f"No MODIS files configured for {glacier_id}")
                return None
            
            # Get the first MODIS file
            modis_file = list(modis_files.values())[0]
            modis_path = self.modis_path / glacier_id / modis_file
            
            if not modis_path.exists():
                logger.error(f"MODIS file not found: {modis_path}")
                return None
            
            # Load MODIS data
            modis_data = pd.read_csv(modis_path)
            logger.info(f"Loaded MODIS data: {len(modis_data)} records, columns: {list(modis_data.columns)}")
            
            # Ensure date column is properly formatted
            if 'date' in modis_data.columns:
                modis_data['date'] = pd.to_datetime(modis_data['date'])
            
            # Load AWS data if available
            aws_file = glacier_info.get('data_files', {}).get('aws')
            if aws_file:
                aws_path = self.aws_path / aws_file
                if aws_path.exists():
                    aws_data = pd.read_csv(aws_path)
                    logger.info(f"Loaded AWS data: {len(aws_data)} records")
                    
                    # Simple merge by date (basic implementation)
                    if 'Time' in aws_data.columns and 'date' in modis_data.columns:
                        # Convert AWS time to date
                        aws_data['date'] = pd.to_datetime(aws_data['Time']).dt.date
                        modis_data['modis_date'] = modis_data['date'].dt.date
                        
                        # Merge on date
                        merged_data = pd.merge(modis_data, aws_data[['date', 'Albedo']], 
                                             left_on='modis_date', right_on='date', 
                                             how='left', suffixes=('', '_aws'))
                        merged_data.rename(columns={'Albedo': 'aws_albedo'}, inplace=True)
                        
                        # Clean up temporary columns
                        merged_data.drop(['modis_date', 'date_aws'], axis=1, inplace=True, errors='ignore')
                        
                        logger.info(f"Merged with AWS data: {len(merged_data)} records")
                        return merged_data
                    else:
                        logger.warning("Could not merge AWS data - missing required columns")
                        # Add empty AWS column for compatibility
                        modis_data['aws_albedo'] = None
                else:
                    logger.warning(f"AWS file not found: {aws_path}")
                    modis_data['aws_albedo'] = None
            else:
                logger.info("No AWS file configured")
                modis_data['aws_albedo'] = None
            
            return modis_data
            
        except Exception as e:
            logger.error(f"Error in simple CSV loading for {glacier_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def calculate_statistics(self, data: pd.DataFrame, 
                           methods: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Calculate statistics for the provided data.
        
        Args:
            data: DataFrame with MODIS and AWS data
            methods: List of methods to analyze
            
        Returns:
            Dictionary with statistical results
        """
        try:
            if data is None or data.empty:
                return {}
            
            # Use the existing statistical analyzer if available
            if self.stats_analyzer is not None:
                # Use basic metrics method (the correct method name)
                if 'albedo' in data.columns and 'aws_albedo' in data.columns:
                    clean_data = data.dropna(subset=['albedo', 'aws_albedo'])
                    if len(clean_data) > 0:
                        stats = self.stats_analyzer.calculate_basic_metrics(
                            clean_data['aws_albedo'], clean_data['albedo']
                        )
                        return stats
                return {}
            
            # Fallback to simple statistics calculation
            return self._calculate_simple_statistics(data, methods)
            
        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            return {}
    
    def _calculate_simple_statistics(self, data: pd.DataFrame, methods: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Simple statistics calculation fallback.
        
        Args:
            data: DataFrame with data
            methods: List of methods to analyze
            
        Returns:
            Dictionary with basic statistics
        """
        try:
            stats = {}
            
            if 'albedo' in data.columns and 'aws_albedo' in data.columns:
                # Remove NaN values
                clean_data = data.dropna(subset=['albedo', 'aws_albedo'])
                
                if len(clean_data) > 0:
                    modis_vals = clean_data['albedo']
                    aws_vals = clean_data['aws_albedo']
                    
                    # Basic statistics
                    correlation = np.corrcoef(modis_vals, aws_vals)[0, 1] if len(clean_data) > 1 else 0
                    rmse = np.sqrt(np.mean((modis_vals - aws_vals) ** 2))
                    bias = np.mean(modis_vals - aws_vals)
                    mae = np.mean(np.abs(modis_vals - aws_vals))
                    
                    stats = {
                        'correlation': correlation,
                        'rmse': rmse,
                        'bias': bias,
                        'mae': mae,
                        'sample_size': len(clean_data)
                    }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in simple statistics calculation: {e}")
            return {}
    
    def get_data_summary(self, glacier_id: str) -> Dict[str, Any]:
        """Get summary information about glacier data."""
        try:
            data = self.load_glacier_data(glacier_id)
            pixels = self.get_pixel_locations(glacier_id)
            aws_info = self.get_aws_station_info(glacier_id)
            
            if data is None:
                return {'error': 'No data available'}
            
            summary = {
                'glacier_id': glacier_id,
                'total_records': len(data),
                'date_range': {
                    'start': data['date'].min() if 'date' in data.columns else None,
                    'end': data['date'].max() if 'date' in data.columns else None
                },
                'pixel_count': len(pixels) if pixels is not None else 0,
                'available_methods': data['method'].unique().tolist() if 'method' in data.columns else [],
                'aws_station': aws_info
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting data summary for {glacier_id}: {e}")
            return {'error': str(e)}
    
    def clear_cache(self):
        """Clear all cached data."""
        self.data_cache.clear()
        self.pixel_cache.clear()
        logger.info("Data cache cleared")
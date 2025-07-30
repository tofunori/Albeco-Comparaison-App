#!/usr/bin/env python3
"""
Pivot-based Data Loaders for MODIS Albedo Analysis Framework

This module implements the exact methodology that successfully produces 515 merged observations
for Athabasca glacier with proper statistical validation.

Key methodology:
1. Load data and convert to long format if needed
2. Apply Terra/Aqua merging using mean aggregation
3. Use pivot_table for data reshaping
4. Simple pd.merge for temporal alignment
5. Residual-based outlier detection

Structure:
- Base Classes: Abstract interfaces for data loaders
- MODIS Loaders: Multi-product MODIS data handling
- AWS Loaders: Automatic Weather Station data handling
- Factory Functions: Loader creation utilities
"""

# ============================================================================
# IMPORTS
# ============================================================================
import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# ============================================================================
# BASE CLASSES
# ============================================================================


class PivotBasedDataLoader(ABC):
    """Base class for pivot-based data loading that matches user methodology."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    @abstractmethod
    def load_data(self, file_path: str) -> pd.DataFrame:
        """Load data from file."""
        pass
    
    @abstractmethod
    def get_method_name(self) -> str:
        """Get the method name for this loader."""
        pass


# ============================================================================
# MODIS DATA LOADERS
# ============================================================================


class AthabascaMultiProductLoader(PivotBasedDataLoader):
    """
    Loader for Athabasca multi-product CSV files that matches the user's methodology.
    
    Handles the format: Athabasca_MultiProduct_with_AWS.csv
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.method_mapping = {
            'MOD09GA': 'MOD09GA',
            'MYD09GA': 'MYD09GA', 
            'mcd43a3': 'MCD43A3',  # Normalize case
            'mod10a1': 'MOD10A1',  # Normalize case
            'myd10a1': 'MYD10A1'   # Normalize case
        }
        
    def load_data(self, file_path: str) -> pd.DataFrame:
        """Load and process multi-product data exactly like the user's notebook."""
        logger.info(f"Loading Athabasca multi-product data from: {file_path}")
        
        # Step 1: Load and validate CSV file
        data = self._load_csv_file(file_path)
        if data.empty:
            return pd.DataFrame()
        
        # Step 2: Check data format and process accordingly
        if self._is_long_format(data):
            return self._process_long_format(data)
        else:
            return self._convert_wide_to_long(data)
    
    def _load_csv_file(self, file_path: str) -> pd.DataFrame:
        """Load and validate CSV file."""
        try:
            data = pd.read_csv(file_path)
            logger.info(f"Loaded data shape: {data.shape}")
            logger.info(f"Available columns: {list(data.columns)}")
            
            # Convert date to datetime
            data['date'] = pd.to_datetime(data['date'])
            return data
        except Exception as e:
            logger.error(f"Failed to load CSV file: {e}")
            return pd.DataFrame()
    
    def _is_long_format(self, data: pd.DataFrame) -> bool:
        """Check if data is already in long format."""
        return 'method' in data.columns and 'albedo' in data.columns
    
    def _process_long_format(self, data: pd.DataFrame) -> pd.DataFrame:
        """Process data that's already in long format."""
        logger.info("Data is already in long format")
        
        # Standardize method names
        data['method'] = data['method'].str.upper()
        method_mapping = {
            'MOD09GA': 'MOD09GA',
            'MYD09GA': 'MYD09GA',
            'MCD43A3': 'MCD43A3',
            'MOD10A1': 'MOD10A1',
            'MYD10A1': 'MYD10A1'
        }
        
        # Filter for valid methods and apply mapping
        valid_data = data[data['method'].isin(method_mapping.keys())].copy()
        valid_data['method'] = valid_data['method'].map(method_mapping)
        
        if len(valid_data) > 0:
            logger.info(f"Found {len(valid_data)} records in long format")
            logger.info(f"Available methods: {sorted(valid_data['method'].unique())}")
            return valid_data
        else:
            logger.error("No valid method data found in long format")
            return pd.DataFrame()
    
    def _convert_wide_to_long(self, data: pd.DataFrame) -> pd.DataFrame:
        """Convert wide format to long format."""
        logger.info("Converting wide format to long format")
        long_format_rows = []
        
        for orig_method, standard_method in self.method_mapping.items():
            method_rows = self._extract_method_data(data, orig_method, standard_method)
            if not method_rows.empty:
                long_format_rows.append(method_rows)
        
        # Combine all method data
        if long_format_rows:
            modis_long = pd.concat(long_format_rows, ignore_index=True)
            logger.info(f"Converted to long format: {len(modis_long)} records")
            logger.info(f"Available methods: {sorted(modis_long['method'].unique())}")
            return modis_long
        else:
            logger.error("No valid method data found")
            return pd.DataFrame()
    
    def _extract_method_data(self, data: pd.DataFrame, orig_method: str, standard_method: str) -> pd.DataFrame:
        """Extract data for a specific method from wide format."""
        albedo_col = f'albedo_{orig_method}'
        
        if albedo_col not in data.columns:
            return pd.DataFrame()
        
        # Get rows where this method has data
        method_data = data[data[albedo_col].notna()].copy()
        
        if len(method_data) == 0:
            return pd.DataFrame()
        
        # Create long format records with core columns
        method_rows = method_data[['pixel_id', 'date', 'qa_mode', albedo_col]].copy()
        method_rows['method'] = standard_method
        method_rows['albedo'] = method_rows[albedo_col]
        method_rows = method_rows.drop(columns=[albedo_col])
        
        # Add spatial coordinates
        self._add_spatial_coordinates(method_rows, method_data)
        
        # Add additional analysis columns
        self._add_analysis_columns(method_rows, method_data, orig_method)
        
        return method_rows
    
    def _add_spatial_coordinates(self, method_rows: pd.DataFrame, method_data: pd.DataFrame) -> None:
        """Add spatial coordinates to method data."""
        if 'longitude' in method_data.columns and 'latitude' in method_data.columns:
            method_rows['longitude'] = method_data['longitude']
            method_rows['latitude'] = method_data['latitude']
    
    def _add_analysis_columns(self, method_rows: pd.DataFrame, method_data: pd.DataFrame, orig_method: str) -> None:
        """Add additional columns needed for analysis."""
        additional_cols = ['glacier_fraction', 'solar_zenith', 'ndsi', 'elevation', 'slope', 'aspect']
        
        for col in additional_cols:
            method_col = f'{col}_{orig_method}'
            if method_col in method_data.columns:
                method_rows[col] = method_data[method_col]
            elif col in method_data.columns:  # Fallback to general column
                method_rows[col] = method_data[col]
    
    def get_method_name(self) -> str:
        return "AthabascaMultiProduct"



# ============================================================================
# AWS DATA LOADERS
# ============================================================================

class AthabascaAWSLoader(PivotBasedDataLoader):
    """
    AWS data loader for Athabasca that handles both integrated and separate AWS files.
    
    Supports multiple AWS data formats:
    - Integrated AWS data in multi-product files
    - Separate AWS files with various formats (Haig, Coropuna, standard)
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
    def load_data(self, file_path: str) -> pd.DataFrame:
        """Load AWS data with proper date handling."""
        logger.info(f"Loading AWS data from: {file_path}")
        
        # Determine file type and load accordingly
        if 'MultiProduct_with_AWS.csv' in file_path:
            return self._load_integrated_aws(file_path)
        else:
            return self._load_separate_aws(file_path)
    
    def _load_integrated_aws(self, file_path: str) -> pd.DataFrame:
        """Load AWS data that's integrated in the multi-product file."""
        data = pd.read_csv(file_path)
        
        # Extract AWS data
        aws_data = data[data['albedo_AWS'].notna()][['date', 'albedo_AWS']].copy()
        aws_data['date'] = pd.to_datetime(aws_data['date'])
        aws_data = aws_data.rename(columns={'albedo_AWS': 'Albedo'})
        
        # Remove duplicates and sort
        aws_data = aws_data.drop_duplicates().sort_values('date').reset_index(drop=True)
        
        logger.info(f"Loaded integrated AWS data: {len(aws_data)} records")
        return aws_data
    
    def _load_separate_aws(self, file_path: str) -> pd.DataFrame:
        """Load AWS data from separate file with format auto-detection."""
        try:
            # Auto-detect file format
            file_format = self._detect_aws_format(file_path)
            
            if file_format == 'haig':
                return self._load_haig_format(file_path)
            else:
                return self._load_standard_format(file_path)
                
        except Exception as e:
            logger.error(f"Failed to load separate AWS data: {e}")
            return pd.DataFrame()
    
    def _detect_aws_format(self, file_path: str) -> str:
        """Detect AWS file format by examining file structure."""
        with open(file_path, 'r') as f:
            first_lines = [f.readline() for _ in range(10)]
        
        is_haig_format = any(';' in line and ('Year' in line or '2002' in line) for line in first_lines)
        return 'haig' if is_haig_format else 'standard'
    
    def _load_haig_format(self, file_path: str) -> pd.DataFrame:
        """Load Haig AWS format (semicolon separated, Year/Day columns)."""
        logger.info("Detected Haig AWS format (semicolon separated)")
        
        # Find header line and read data
        data_start = self._find_haig_header(file_path)
        aws_data = pd.read_csv(file_path, sep=';', skiprows=data_start, decimal=',')
        
        # Clean and process data
        aws_data.columns = aws_data.columns.str.strip()
        logger.info(f"AWS columns: {list(aws_data.columns)}")
        
        # Create date from Year and Day columns
        aws_data = self._process_haig_dates(aws_data)
        
        # Extract albedo column
        aws_data = self._extract_haig_albedo(aws_data)
        
        return aws_data
    
    def _find_haig_header(self, file_path: str) -> int:
        """Find the header line in Haig format files."""
        with open(file_path, 'r') as f:
            for i, line in enumerate(f):
                if 'Year;Day' in line:
                    return i
        return 0
    
    def _process_haig_dates(self, aws_data: pd.DataFrame) -> pd.DataFrame:
        """Process Year and Day columns into datetime."""
        aws_data = aws_data.dropna(subset=['Year', 'Day'])
        aws_data['Year'] = aws_data['Year'].astype(int)
        aws_data['Day'] = aws_data['Day'].astype(int)
        aws_data['date'] = pd.to_datetime(
            aws_data['Year'].astype(str) + '-' + aws_data['Day'].astype(str).str.zfill(3), 
            format='%Y-%j'
        )
        return aws_data
    
    def _extract_haig_albedo(self, aws_data: pd.DataFrame) -> pd.DataFrame:
        """Extract albedo column from Haig format data."""
        albedo_cols = [col for col in aws_data.columns if 'albedo' in col.lower()]
        if not albedo_cols:
            raise ValueError(f"No albedo column found. Available columns: {list(aws_data.columns)}")
        
        albedo_col = albedo_cols[0]
        logger.info(f"Using albedo column: '{albedo_col}'")
        aws_data['Albedo'] = pd.to_numeric(aws_data[albedo_col], errors='coerce')
        aws_data = aws_data[['date', 'Albedo']].copy()
        
        # Clean and validate data
        return self._clean_aws_data(aws_data)
    
    def _load_standard_format(self, file_path: str) -> pd.DataFrame:
        """Load standard AWS formats (Time/Timestamp columns)."""
        aws_data = pd.read_csv(file_path)
        logger.info(f"AWS columns: {list(aws_data.columns)}")
        
        # Process based on available time columns
        if 'Time' in aws_data.columns:
            aws_data['date'] = pd.to_datetime(aws_data['Time'])
        elif 'Timestamp' in aws_data.columns:
            aws_data['date'] = pd.to_datetime(aws_data['Timestamp'])
        else:
            raise ValueError(f"Unknown AWS format. Available columns: {list(aws_data.columns)}")
        
        aws_data = aws_data[['date', 'Albedo']].copy()
        
        # Clean and validate data
        return self._clean_aws_data(aws_data)
    
    def _clean_aws_data(self, aws_data: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate AWS data."""
        # Remove duplicates, invalid values, and sort
        aws_data = aws_data.dropna(subset=['Albedo'])
        aws_data = aws_data[aws_data['Albedo'] > 0]  # Remove invalid albedo values
        aws_data = aws_data.drop_duplicates().sort_values('date').reset_index(drop=True)
        
        logger.info(f"Cleaned AWS data: {len(aws_data)} records")
        return aws_data
    
    def get_method_name(self) -> str:
        return "AWS"



# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

def create_pivot_based_loader(data_type: str, config: Dict[str, Any], glacier_config: Dict[str, Any] = None) -> PivotBasedDataLoader:
    """Factory function to create appropriate pivot-based data loader.
    
    Args:
        data_type: Type of data to load ('athabasca_multiproduct', 'AWS')
        config: Framework configuration dictionary
        glacier_config: Optional glacier-specific configuration
        
    Returns:
        Appropriate data loader instance
        
    Raises:
        ValueError: If data_type is not supported
    """
    if data_type == "athabasca_multiproduct" or (glacier_config and glacier_config.get('data_type') == "athabasca_multiproduct"):
        return AthabascaMultiProductLoader(config)
    elif data_type == "AWS":
        return AthabascaAWSLoader(config)
    else:
        raise ValueError(f"Unknown data type: {data_type}. Supported types: 'athabasca_multiproduct', 'AWS'")


# ============================================================================
# NOTES
# ============================================================================
# PivotBasedProcessor has been moved to data_processing.processors.pivot_processor
# for better separation of concerns between data loading and data processing.
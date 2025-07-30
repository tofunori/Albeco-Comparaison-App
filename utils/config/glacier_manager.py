#!/usr/bin/env python3
"""
Glacier Configuration Manager for Dynamic Glacier Management

This module provides functionality to dynamically add, validate, and manage
glacier configurations through the interactive interface.

Key Features:
- Dynamic glacier configuration creation
- File format detection and validation
- Configuration backup and rollback
- Data compatibility checking
- YAML configuration file management
"""

import os
import shutil
import logging
import pandas as pd
import yaml
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class GlacierConfigManager:
    """Manager for dynamic glacier configuration operations."""
    
    def __init__(self, config_path: str = 'config/glacier_sites.yaml'):
        """Initialize the glacier configuration manager.
        
        Args:
            config_path: Path to the glacier sites configuration file
        """
        self.config_path = Path(config_path)
        self.backup_dir = Path('config/backups')
        self.backup_dir.mkdir(exist_ok=True)
        
    def load_current_config(self) -> Dict[str, Any]:
        """Load the current glacier configuration."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {'glaciers': {}}
        except FileNotFoundError:
            logger.warning(f"Configuration file not found: {self.config_path}")
            return {'glaciers': {}}
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {'glaciers': {}}
    
    def backup_config(self) -> str:
        """Create a backup of the current configuration.
        
        Returns:
            Path to the backup file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f"glacier_sites_backup_{timestamp}.yaml"
        
        try:
            shutil.copy2(self.config_path, backup_path)
            logger.info(f"Configuration backed up to: {backup_path}")
            return str(backup_path)
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise
    
    def restore_config(self, backup_path: str) -> bool:
        """Restore configuration from backup.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            True if restoration was successful
        """
        try:
            shutil.copy2(backup_path, self.config_path)
            logger.info(f"Configuration restored from: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore configuration: {e}")
            return False
    
    def validate_glacier_id(self, glacier_id: str, current_config: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate glacier ID for uniqueness and format.
        
        Args:
            glacier_id: Proposed glacier identifier
            current_config: Current configuration dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if ID is empty or None
        if not glacier_id or not glacier_id.strip():
            return False, "Glacier ID cannot be empty"
        
        # Clean and validate ID format
        glacier_id = glacier_id.strip().lower()
        
        # Check for valid characters (alphanumeric and underscores only)
        if not glacier_id.replace('_', '').replace('-', '').isalnum():
            return False, "Glacier ID can only contain letters, numbers, underscores, and hyphens"
        
        # Check if ID already exists
        if glacier_id in current_config.get('glaciers', {}):
            return False, f"Glacier ID '{glacier_id}' already exists"
        
        return True, ""
    
    def validate_coordinates(self, lat: float, lon: float) -> Tuple[bool, str]:
        """Validate geographic coordinates.
        
        Args:
            lat: Latitude value
            lon: Longitude value
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            lat = float(lat)
            lon = float(lon)
            
            if not (-90 <= lat <= 90):
                return False, f"Latitude must be between -90 and 90, got {lat}"
            
            if not (-180 <= lon <= 180):
                return False, f"Longitude must be between -180 and 180, got {lon}"
            
            return True, ""
        except (ValueError, TypeError):
            return False, "Coordinates must be valid numbers"
    
    def detect_data_format(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Detect the format of a data file.
        
        Args:
            file_path: Path to the data file
            
        Returns:
            Tuple of (data_type, format_info)
        """
        if not os.path.exists(file_path):
            return "unknown", {"error": "File does not exist"}
        
        try:
            # Read a sample of the file to detect format
            df = pd.read_csv(file_path, nrows=10)
            columns = list(df.columns)
            
            format_info = {
                "columns": columns,
                "row_count": len(df),
                "file_size": os.path.getsize(file_path)
            }
            
            # Check for multi-product format (has 'method' column)
            if 'method' in columns and 'albedo' in columns:
                # Check available methods
                full_df = pd.read_csv(file_path)
                methods = full_df['method'].unique().tolist() if 'method' in full_df.columns else []
                format_info["methods"] = methods
                format_info["total_rows"] = len(full_df)
                return "athabasca_multiproduct", format_info
            
            # Check for standard MODIS format
            modis_cols = ['date', 'latitude', 'longitude', 'albedo']
            if all(col in columns for col in modis_cols):
                return "standard_modis", format_info
            
            # Check for AWS format
            if 'Time' in columns and 'Albedo' in columns:
                return "standard_aws", format_info
            elif 'Timestamp' in columns and 'Albedo' in columns:
                return "coropuna_aws", format_info
            elif 'Year' in columns and 'Day' in columns and any('albedo' in col.lower() for col in columns):
                return "haig_aws", format_info
            
            return "unknown", format_info
            
        except Exception as e:
            return "error", {"error": str(e)}
    
    def validate_modis_file(self, file_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate a MODIS data file.
        
        Args:
            file_path: Path to the MODIS file
            
        Returns:
            Tuple of (is_valid, error_message, file_info)
        """
        data_type, format_info = self.detect_data_format(file_path)
        
        if data_type == "error":
            return False, f"Error reading file: {format_info.get('error', 'Unknown error')}", {}
        
        if data_type == "unknown":
            return False, "Unrecognized MODIS data format. Expected columns like date, latitude, longitude, albedo", format_info
        
        if data_type in ["athabasca_multiproduct", "standard_modis"]:
            return True, "", format_info
        
        return False, f"File appears to be {data_type} format, not MODIS data", format_info
    
    def validate_aws_file(self, file_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate an AWS data file.
        
        Args:
            file_path: Path to the AWS file
            
        Returns:
            Tuple of (is_valid, error_message, file_info)
        """
        data_type, format_info = self.detect_data_format(file_path)
        
        if data_type == "error":
            return False, f"Error reading file: {format_info.get('error', 'Unknown error')}", {}
        
        if data_type in ["standard_aws", "coropuna_aws", "haig_aws"]:
            return True, "", format_info
        
        return False, f"File does not appear to be AWS data format. Expected columns like Time/Timestamp and Albedo", format_info
    
    def validate_mask_file(self, file_path: str) -> Tuple[bool, str]:
        """Validate a glacier mask file.
        
        Args:
            file_path: Path to the mask file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not os.path.exists(file_path):
            return False, "Mask file does not exist"
        
        file_ext = Path(file_path).suffix.lower()
        
        # Check for supported formats
        if file_ext == '.shp':
            # Check for associated shapefile components
            base_path = Path(file_path).with_suffix('')
            required_files = ['.shx', '.dbf']
            missing_files = []
            
            for ext in required_files:
                if not (base_path.with_suffix(ext)).exists():
                    missing_files.append(f"{base_path.name}{ext}")
            
            if missing_files:
                return False, f"Missing shapefile components: {', '.join(missing_files)}"
            
            return True, ""
        
        elif file_ext in ['.tif', '.tiff']:
            # Basic check for TIFF files
            return True, ""
        
        else:
            return False, f"Unsupported mask format: {file_ext}. Supported formats: .shp, .tif, .tiff"
    
    def create_glacier_config(self, glacier_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a glacier configuration dictionary.
        
        Args:
            glacier_data: Dictionary containing glacier information
            
        Returns:
            Formatted glacier configuration
        """
        config = {
            "name": glacier_data["name"],
            "region": glacier_data["region"],
            "coordinates": {
                "lat": float(glacier_data["coordinates"]["lat"]),
                "lon": float(glacier_data["coordinates"]["lon"])
            },
            "data_files": {
                "modis": {},
                "aws": glacier_data["data_files"]["aws"],
                "mask": glacier_data["data_files"]["mask"]
            },
            "aws_stations": {},
            "data_type": glacier_data.get("data_type", "athabasca_multiproduct"),
            "outlier_threshold": float(glacier_data.get("outlier_threshold", 2.5))
        }
        
        # Set up MODIS file references based on data type
        modis_file = glacier_data["data_files"]["modis"]
        if glacier_data.get("data_type") == "athabasca_multiproduct":
            # Use same file for all MODIS products
            config["data_files"]["modis"] = {
                "MOD09GA": modis_file,
                "MOD10A1": modis_file,
                "MCD43A3": modis_file
            }
        else:
            # For other formats, might need separate files
            config["data_files"]["modis"]["MOD09GA"] = modis_file
        
        # Add AWS station information
        if "aws_stations" in glacier_data:
            config["aws_stations"] = glacier_data["aws_stations"]
        
        return config
    
    def add_glacier(self, glacier_id: str, glacier_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Add a new glacier to the configuration.
        
        Args:
            glacier_id: Unique identifier for the glacier
            glacier_data: Dictionary containing glacier configuration data
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Load current configuration
            current_config = self.load_current_config()
            
            # Validate glacier ID
            valid_id, id_error = self.validate_glacier_id(glacier_id, current_config)
            if not valid_id:
                return False, id_error
            
            # Create backup
            backup_path = self.backup_config()
            
            # Create glacier configuration
            glacier_config = self.create_glacier_config(glacier_data)
            
            # Add to configuration
            current_config["glaciers"][glacier_id] = glacier_config
            
            # Save updated configuration
            with open(self.config_path, 'w') as f:
                yaml.dump(current_config, f, default_flow_style=False, indent=2)
            
            logger.info(f"Successfully added glacier '{glacier_id}' to configuration")
            return True, f"Glacier '{glacier_id}' added successfully. Backup created at: {backup_path}"
            
        except Exception as e:
            logger.error(f"Failed to add glacier: {e}")
            return False, f"Failed to add glacier: {str(e)}"
    
    def get_existing_glacier_ids(self) -> List[str]:
        """Get list of existing glacier IDs.
        
        Returns:
            List of glacier identifiers
        """
        config = self.load_current_config()
        return list(config.get("glaciers", {}).keys())
    
    def get_glacier_info(self, glacier_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific glacier.
        
        Args:
            glacier_id: Glacier identifier
            
        Returns:
            Glacier configuration or None if not found
        """
        config = self.load_current_config()
        return config.get("glaciers", {}).get(glacier_id)
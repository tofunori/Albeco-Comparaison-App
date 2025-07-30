#!/usr/bin/env python3
"""
Input Validation Utilities for MODIS Albedo Analysis Framework

This module provides non-breaking validation functions that can be used
to verify inputs and data integrity without modifying existing functionality.
All functions are designed to be backward-compatible and optional.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
import logging

logger = logging.getLogger(__name__)


def validate_file_exists(file_path: Union[str, Path], description: str = "File") -> bool:
    """
    Validate that a file exists and is accessible.
    
    Args:
        file_path: Path to the file to check
        description: Human-readable description for logging
        
    Returns:
        bool: True if file exists and is readable, False otherwise
        
    Example:
        >>> validate_file_exists("data/modis/glacier.csv", "MODIS data")
        True
    """
    try:
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"{description} does not exist: {file_path}")
            return False
        if not path.is_file():
            logger.warning(f"{description} is not a file: {file_path}")
            return False
        if not os.access(path, os.R_OK):
            logger.warning(f"{description} is not readable: {file_path}")
            return False
        return True
    except Exception as e:
        logger.error(f"Error validating {description}: {e}")
        return False


def validate_dataframe_structure(df: pd.DataFrame, required_columns: List[str], 
                                name: str = "DataFrame") -> Tuple[bool, List[str]]:
    """
    Validate that a DataFrame has the required column structure.
    
    Args:
        df: DataFrame to validate
        required_columns: List of column names that must be present
        name: Name of the DataFrame for logging
        
    Returns:
        Tuple[bool, List[str]]: (is_valid, missing_columns)
        
    Example:
        >>> df = pd.DataFrame({'date': [], 'albedo': []})
        >>> is_valid, missing = validate_dataframe_structure(df, ['date', 'albedo', 'method'])
        >>> print(f"Valid: {is_valid}, Missing: {missing}")
        Valid: False, Missing: ['method']
    """
    try:
        if df.empty:
            logger.warning(f"{name} is empty")
            return False, required_columns
            
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.warning(f"{name} missing required columns: {missing_columns}")
            logger.debug(f"{name} has columns: {list(df.columns)}")
            return False, missing_columns
        
        logger.debug(f"{name} structure validation passed")
        return True, []
        
    except Exception as e:
        logger.error(f"Error validating {name} structure: {e}")
        return False, required_columns


def validate_albedo_values(values: np.ndarray, name: str = "Albedo values") -> Dict[str, Any]:
    """
    Validate albedo values are within physically reasonable ranges.
    
    Args:
        values: Array of albedo values to validate
        name: Description for logging
        
    Returns:
        Dict with validation results:
        - valid: bool, True if all values are reasonable
        - n_total: Total number of values
        - n_valid: Number of valid values (0.0 <= albedo <= 1.0)
        - n_invalid: Number of invalid values
        - invalid_range: Range of invalid values if any
        
    Example:
        >>> values = np.array([0.2, 0.8, 1.5, -0.1])
        >>> result = validate_albedo_values(values)
        >>> print(f"Valid: {result['valid']}, Invalid count: {result['n_invalid']}")
        Valid: False, Invalid count: 2
    """
    try:
        # Remove NaN values for validation
        clean_values = values[~np.isnan(values)]
        
        # Physical range for albedo: 0.0 to 1.0
        valid_mask = (clean_values >= 0.0) & (clean_values <= 1.0)
        n_valid = np.sum(valid_mask)
        n_invalid = len(clean_values) - n_valid
        
        result = {
            'valid': n_invalid == 0,
            'n_total': len(values),
            'n_clean': len(clean_values),
            'n_valid': n_valid,
            'n_invalid': n_invalid,
            'n_nan': len(values) - len(clean_values)
        }
        
        if n_invalid > 0:
            invalid_values = clean_values[~valid_mask]
            result['invalid_range'] = (float(np.min(invalid_values)), float(np.max(invalid_values)))
            logger.warning(f"{name}: {n_invalid}/{len(clean_values)} values outside valid range [0,1]")
            logger.debug(f"{name}: Invalid range: {result['invalid_range']}")
        else:
            result['invalid_range'] = None
            logger.debug(f"{name}: All {n_valid} values are valid")
            
        return result
        
    except Exception as e:
        logger.error(f"Error validating {name}: {e}")
        return {
            'valid': False,
            'n_total': len(values) if hasattr(values, '__len__') else 0,
            'error': str(e)
        }


def validate_correlation_data(aws_values: np.ndarray, modis_values: np.ndarray,
                             min_samples: int = 10) -> Dict[str, Any]:
    """
    Validate data pairs for correlation analysis.
    
    Args:
        aws_values: Array of AWS albedo measurements
        modis_values: Array of MODIS albedo values
        min_samples: Minimum number of valid pairs required
        
    Returns:
        Dict with validation results:
        - valid: bool, True if data is suitable for correlation
        - n_pairs: Number of data pairs
        - n_valid_pairs: Number of valid pairs (no NaN)
        - aws_valid: Validation results for AWS values
        - modis_valid: Validation results for MODIS values
        - sufficient_data: bool, True if enough samples for correlation
        
    Example:
        >>> aws = np.array([0.8, 0.7, np.nan])
        >>> modis = np.array([0.75, 0.72, 0.6])
        >>> result = validate_correlation_data(aws, modis)
        >>> print(f"Suitable for correlation: {result['valid']}")
    """
    try:
        # Basic length validation
        if len(aws_values) != len(modis_values):
            logger.error("AWS and MODIS arrays have different lengths")
            return {'valid': False, 'error': 'Length mismatch'}
        
        # Find valid pairs (no NaN in either array)
        valid_mask = ~(np.isnan(aws_values) | np.isnan(modis_values))
        n_valid_pairs = np.sum(valid_mask)
        
        # Validate individual arrays
        aws_valid = validate_albedo_values(aws_values[valid_mask], "AWS values")
        modis_valid = validate_albedo_values(modis_values[valid_mask], "MODIS values")
        
        # Check minimum sample size
        sufficient_data = n_valid_pairs >= min_samples
        
        result = {
            'valid': aws_valid['valid'] and modis_valid['valid'] and sufficient_data,
            'n_pairs': len(aws_values),
            'n_valid_pairs': n_valid_pairs,
            'aws_valid': aws_valid,
            'modis_valid': modis_valid,
            'sufficient_data': sufficient_data,
            'min_samples_required': min_samples
        }
        
        if not sufficient_data:
            logger.warning(f"Insufficient data for correlation: {n_valid_pairs} < {min_samples}")
        
        if result['valid']:
            logger.debug(f"Correlation data validation passed: {n_valid_pairs} valid pairs")
        
        return result
        
    except Exception as e:
        logger.error(f"Error validating correlation data: {e}")
        return {'valid': False, 'error': str(e)}


def validate_glacier_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate glacier configuration dictionary structure.
    
    Args:
        config: Glacier configuration dictionary
        
    Returns:
        Tuple[bool, List[str]]: (is_valid, error_messages)
        
    Example:
        >>> config = {'name': 'Test Glacier', 'coordinates': {'lat': 50.0, 'lon': -115.0}}
        >>> valid, errors = validate_glacier_config(config)
    """
    errors = []
    
    try:
        # Required fields
        required_fields = ['name']
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Validate coordinates if present
        if 'coordinates' in config:
            coords = config['coordinates']
            if not isinstance(coords, dict):
                errors.append("Coordinates must be a dictionary")
            else:
                if 'lat' in coords:
                    lat = coords['lat']
                    if not isinstance(lat, (int, float)) or not (-90 <= lat <= 90):
                        errors.append(f"Invalid latitude: {lat} (must be -90 to 90)")
                
                if 'lon' in coords:
                    lon = coords['lon']
                    if not isinstance(lon, (int, float)) or not (-180 <= lon <= 180):
                        errors.append(f"Invalid longitude: {lon} (must be -180 to 180)")
        
        # Validate elevation if present
        if 'elevation' in config:
            elev = config.get('elevation')
            if elev is not None and (not isinstance(elev, (int, float)) or elev < -500 or elev > 9000):
                errors.append(f"Invalid elevation: {elev}m (must be -500 to 9000)")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.debug(f"Glacier config validation passed for: {config.get('name', 'Unknown')}")
        else:
            logger.warning(f"Glacier config validation failed: {len(errors)} errors")
            for error in errors:
                logger.debug(f"Config error: {error}")
        
        return is_valid, errors
        
    except Exception as e:
        error_msg = f"Error validating glacier config: {e}"
        logger.error(error_msg)
        return False, [error_msg]


def validate_analysis_results(results_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate analysis results DataFrame for reasonableness.
    
    Args:
        results_df: DataFrame with analysis results
        
    Returns:
        Dict with validation summary:
        - valid: bool, overall validation status
        - checks: Dict of individual validation results
        
    Example:
        >>> df = pd.DataFrame({'r': [0.8, 0.9], 'rmse': [0.1, 0.2]})
        >>> result = validate_analysis_results(df)
    """
    checks = {}
    
    try:
        # Check correlation values
        if 'r' in results_df.columns:
            r_values = results_df['r'].dropna()
            checks['correlation_range'] = {
                'valid': ((r_values >= -1.0) & (r_values <= 1.0)).all(),
                'values_outside_range': len(r_values[(r_values < -1.0) | (r_values > 1.0)])
            }
        
        # Check RMSE values (should be positive)
        if 'rmse' in results_df.columns:
            rmse_values = results_df['rmse'].dropna()
            checks['rmse_positive'] = {
                'valid': (rmse_values >= 0).all(),
                'negative_values': len(rmse_values[rmse_values < 0])
            }
        
        # Check sample sizes
        sample_cols = ['n_samples', 'n']
        for col in sample_cols:
            if col in results_df.columns:
                n_values = results_df[col].dropna()
                checks[f'{col}_reasonable'] = {
                    'valid': ((n_values > 0) & (n_values < 100000)).all(),
                    'min_samples': int(n_values.min()) if len(n_values) > 0 else 0,
                    'max_samples': int(n_values.max()) if len(n_values) > 0 else 0
                }
                break
        
        # Overall validation
        all_valid = all(check.get('valid', True) for check in checks.values())
        
        result = {
            'valid': all_valid,
            'checks': checks,
            'n_rows': len(results_df)
        }
        
        if all_valid:
            logger.debug(f"Analysis results validation passed ({len(results_df)} rows)")
        else:
            failed_checks = [k for k, v in checks.items() if not v.get('valid', True)]
            logger.warning(f"Analysis results validation failed: {failed_checks}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error validating analysis results: {e}")
        return {'valid': False, 'error': str(e)}
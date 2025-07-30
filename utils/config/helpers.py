import yaml
import logging
import os
from typing import Dict, Any, Optional
import pandas as pd
from datetime import datetime


def load_config(config_path: str) -> Dict[str, Any]:
    """Load YAML configuration file."""
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML file: {e}")


def setup_logging(config: Dict[str, Any]) -> None:
    """Set up logging configuration."""
    log_config = config.get('logging', {})
    level = getattr(logging, log_config.get('level', 'INFO'))
    format_str = log_config.get('format', '%(asctime)s - %(levelname)s - %(message)s')
    
    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_config.get('file', 'albedo_analysis.log'))
        ]
    )


def ensure_directory_exists(path: str) -> None:
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


def validate_file_exists(file_path: str) -> bool:
    """Check if file exists."""
    return os.path.isfile(file_path)


def get_full_path(base_path: str, relative_path: str) -> str:
    """Get full path from base and relative paths."""
    return os.path.join(base_path, relative_path)


def standardize_date_column(data: pd.DataFrame, date_column: str = 'date') -> pd.DataFrame:
    """Standardize date column to datetime format."""
    if date_column in data.columns:
        data[date_column] = pd.to_datetime(data[date_column])
    return data


def filter_by_date_range(data: pd.DataFrame, 
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        date_column: str = 'date') -> pd.DataFrame:
    """Filter DataFrame by date range."""
    if date_column not in data.columns:
        return data
        
    filtered_data = data.copy()
    
    if start_date:
        start_dt = pd.to_datetime(start_date)
        filtered_data = filtered_data[filtered_data[date_column] >= start_dt]
        
    if end_date:
        end_dt = pd.to_datetime(end_date)
        filtered_data = filtered_data[filtered_data[date_column] <= end_dt]
        
    return filtered_data


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometers using Haversine formula."""
    import numpy as np
    
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    
    a = (np.sin(dlat/2)**2 + 
         np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2)
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    
    return R * c


def remove_outliers(data: pd.DataFrame, column: str, 
                   method: str = 'iqr', factor: float = 1.5) -> pd.DataFrame:
    """Remove outliers from specified column."""
    if column not in data.columns:
        return data
        
    if method == 'iqr':
        Q1 = data[column].quantile(0.25)
        Q3 = data[column].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - factor * IQR
        upper_bound = Q3 + factor * IQR
        
        mask = (data[column] >= lower_bound) & (data[column] <= upper_bound)
        return data[mask]
    
    elif method == 'zscore':
        import numpy as np
        from scipy import stats
        
        z_scores = np.abs(stats.zscore(data[column]))
        return data[z_scores < factor]
    
    else:
        raise ValueError(f"Unknown outlier removal method: {method}")


def create_summary_stats(data: pd.DataFrame, group_by: Optional[str] = None) -> pd.DataFrame:
    """Create summary statistics for numerical columns."""
    numeric_cols = data.select_dtypes(include=['number']).columns
    
    if group_by and group_by in data.columns:
        summary = data.groupby(group_by)[numeric_cols].agg([
            'count', 'mean', 'std', 'min', 'max'
        ]).round(4)
    else:
        summary = data[numeric_cols].agg([
            'count', 'mean', 'std', 'min', 'max'
        ]).round(4)
    
    return summary


def save_results(data: pd.DataFrame, file_path: str, format: str = 'csv') -> None:
    """Save results to file in specified format."""
    ensure_directory_exists(os.path.dirname(file_path))
    
    if format.lower() == 'csv':
        data.to_csv(file_path, index=False)
    elif format.lower() == 'excel':
        data.to_excel(file_path, index=False)
    elif format.lower() == 'pickle':
        data.to_pickle(file_path)
    else:
        raise ValueError(f"Unsupported format: {format}")


def get_timestamp() -> str:
    """Get current timestamp as string."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")
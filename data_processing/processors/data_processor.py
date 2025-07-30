import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from scipy import stats

logger = logging.getLogger(__name__)


class DataValidator:
    """Data validation and quality control utilities."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    def validate_temporal_consistency(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Check for temporal gaps and inconsistencies."""
        if 'date' not in data.columns or data.empty:
            return {'valid': False, 'errors': ['No date column or empty data']}
        
        results = {'valid': True, 'errors': [], 'warnings': [], 'stats': {}}
        
        # Check for duplicate dates
        duplicates = data['date'].duplicated().sum()
        if duplicates > 0:
            results['warnings'].append(f"Found {duplicates} duplicate dates")
        
        # Check temporal coverage
        date_range = data['date'].max() - data['date'].min()
        results['stats']['temporal_span_days'] = date_range.days
        
        # Check for large gaps
        data_sorted = data.sort_values('date')
        time_diffs = data_sorted['date'].diff()
        large_gaps = time_diffs[time_diffs > timedelta(days=30)]
        
        if len(large_gaps) > 0:
            results['warnings'].append(f"Found {len(large_gaps)} gaps > 30 days")
            results['stats']['max_gap_days'] = time_diffs.max().days
        
        return results
    
    def validate_spatial_consistency(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Check spatial data consistency."""
        results = {'valid': True, 'errors': [], 'warnings': [], 'stats': {}}
        
        if 'lat' not in data.columns or 'lon' not in data.columns:
            results['errors'].append("Missing latitude or longitude columns")
            results['valid'] = False
            return results
        
        # Check coordinate ranges
        lat_range = (data['lat'].min(), data['lat'].max())
        lon_range = (data['lon'].min(), data['lon'].max())
        
        if not (-90 <= lat_range[0] <= lat_range[1] <= 90):
            results['errors'].append(f"Invalid latitude range: {lat_range}")
            results['valid'] = False
        
        if not (-180 <= lon_range[0] <= lon_range[1] <= 180):
            results['errors'].append(f"Invalid longitude range: {lon_range}")
            results['valid'] = False
        
        # Check for reasonable spatial extent (should be within a glacier region)
        lat_span = lat_range[1] - lat_range[0]
        lon_span = lon_range[1] - lon_range[0]
        
        if lat_span > 5 or lon_span > 5:  # More than ~500km span seems unreasonable for a single glacier
            results['warnings'].append(f"Large spatial extent: {lat_span:.2f}° lat, {lon_span:.2f}° lon")
        
        results['stats'] = {
            'lat_range': lat_range,
            'lon_range': lon_range,
            'spatial_extent': {'lat_span': lat_span, 'lon_span': lon_span}
        }
        
        return results
    
    def detect_outliers(self, data: pd.DataFrame, column: str, 
                       method: str = 'iqr', threshold: float = 2.0) -> Dict[str, Any]:
        """Detect outliers in specified column."""
        if column not in data.columns or data[column].isna().all():
            return {'outliers': [], 'method': method, 'threshold': threshold}
        
        outlier_indices = []
        
        if method == 'iqr':
            Q1 = data[column].quantile(0.25)
            Q3 = data[column].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            
            outliers = data[(data[column] < lower_bound) | (data[column] > upper_bound)]
            outlier_indices = outliers.index.tolist()
            
        elif method == 'zscore':
            z_scores = np.abs(stats.zscore(data[column].dropna()))
            outlier_mask = z_scores > threshold
            outlier_indices = data.index[data[column].notna()][outlier_mask].tolist()
            
        elif method == 'modified_zscore':
            median = data[column].median()
            mad = np.median(np.abs(data[column] - median))
            modified_z_scores = 0.6745 * (data[column] - median) / mad
            outlier_indices = data[np.abs(modified_z_scores) > threshold].index.tolist()
        
        return {
            'outliers': outlier_indices,
            'method': method,
            'threshold': threshold,
            'count': len(outlier_indices),
            'percentage': len(outlier_indices) / len(data) * 100
        }
    
    def validate_albedo_values(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Validate albedo values for physical consistency."""
        results = {'valid': True, 'errors': [], 'warnings': [], 'stats': {}}
        
        if 'albedo' not in data.columns:
            results['errors'].append("No albedo column found")
            results['valid'] = False
            return results
        
        albedo = data['albedo'].dropna()
        
        if len(albedo) == 0:
            results['errors'].append("All albedo values are NaN")
            results['valid'] = False
            return results
        
        # Check basic range
        out_of_range = albedo[(albedo < 0) | (albedo > 1)]
        if len(out_of_range) > 0:
            results['errors'].append(f"{len(out_of_range)} albedo values outside [0,1] range")
            results['valid'] = False
        
        # Check for unrealistic values for snow/ice
        very_low = albedo[albedo < 0.1]
        very_high = albedo[albedo > 0.95]
        
        if len(very_low) > len(albedo) * 0.1:  # More than 10% very low values
            results['warnings'].append(f"{len(very_low)} very low albedo values (<0.1)")
        
        if len(very_high) > len(albedo) * 0.05:  # More than 5% very high values
            results['warnings'].append(f"{len(very_high)} very high albedo values (>0.95)")
        
        # Statistical summary
        results['stats'] = {
            'count': len(albedo),
            'mean': albedo.mean(),
            'std': albedo.std(),
            'min': albedo.min(),
            'max': albedo.max(),
            'percentiles': {
                '5': albedo.quantile(0.05),
                '25': albedo.quantile(0.25),
                '50': albedo.quantile(0.50),
                '75': albedo.quantile(0.75),
                '95': albedo.quantile(0.95)
            }
        }
        
        return results


class DataProcessor:
    """Main data processing and integration utilities."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.validator = DataValidator(config)
        
    def align_temporal_data(self, modis_data: pd.DataFrame, 
                           aws_data: pd.DataFrame,
                           tolerance_hours: int = 12) -> pd.DataFrame:
        """Align MODIS and AWS data temporally."""
        if modis_data.empty or aws_data.empty:
            return pd.DataFrame()
        
        # Ensure both datasets have date columns
        for df, name in [(modis_data, 'MODIS'), (aws_data, 'AWS')]:
            if 'date' not in df.columns:
                logger.error(f"No date column in {name} data")
                return pd.DataFrame()
        
        aligned_data = []
        tolerance = pd.Timedelta(hours=tolerance_hours)
        
        for _, modis_row in modis_data.iterrows():
            modis_date = modis_row['date']
            
            # Find AWS measurements within tolerance
            time_diff = np.abs(aws_data['date'] - modis_date)
            within_tolerance = time_diff <= tolerance
            
            if within_tolerance.any():
                # Get closest AWS measurement
                closest_idx = time_diff[within_tolerance].idxmin()
                aws_row = aws_data.loc[closest_idx]
                
                # Combine data
                combined_row = {
                    'date': modis_date,
                    'modis_lat': modis_row.get('lat'),
                    'modis_lon': modis_row.get('lon'),
                    'modis_albedo': modis_row.get('albedo'),
                    'aws_albedo': aws_row.get('albedo'),
                    'aws_station': aws_row.get('station_id'),
                    'time_diff_hours': time_diff.loc[closest_idx].total_seconds() / 3600
                }
                
                aligned_data.append(combined_row)
        
        return pd.DataFrame(aligned_data)
    
    def spatial_matching(self, modis_data: pd.DataFrame, 
                        aws_coordinates: Dict[str, Dict[str, float]],
                        max_distance_km: float = 5.0) -> pd.DataFrame:
        """Match MODIS pixels with nearby AWS stations."""
        if modis_data.empty or not aws_coordinates:
            return pd.DataFrame()
        
        from ..utils.helpers import calculate_distance_km
        
        matched_data = []
        
        for _, modis_row in modis_data.iterrows():
            modis_lat = modis_row.get('lat')
            modis_lon = modis_row.get('lon')
            
            if pd.isna(modis_lat) or pd.isna(modis_lon):
                continue
            
            # Find nearest AWS station
            closest_station = None
            min_distance = float('inf')
            
            for station_id, coords in aws_coordinates.items():
                if coords['lat'] is None or coords['lon'] is None:
                    continue
                    
                distance = calculate_distance_km(
                    modis_lat, modis_lon, coords['lat'], coords['lon']
                )
                
                if distance < min_distance and distance <= max_distance_km:
                    min_distance = distance
                    closest_station = station_id
            
            if closest_station:
                matched_row = modis_row.copy()
                matched_row['nearest_aws_station'] = closest_station
                matched_row['distance_to_aws_km'] = min_distance
                matched_data.append(matched_row)
        
        return pd.DataFrame(matched_data)
    
    def merge_datasets(self, datasets: Dict[str, pd.DataFrame], 
                      merge_keys: List[str] = None) -> pd.DataFrame:
        """Merge multiple datasets with consistent structure."""
        if not datasets:
            return pd.DataFrame()
        
        if merge_keys is None:
            merge_keys = ['date']
        
        # Start with first dataset
        dataset_names = list(datasets.keys())
        merged = datasets[dataset_names[0]].copy()
        
        # Add source column
        merged['source'] = dataset_names[0]
        
        # Merge additional datasets
        for name in dataset_names[1:]:
            dataset = datasets[name].copy()
            dataset['source'] = name
            
            # Align columns
            common_cols = set(merged.columns) & set(dataset.columns)
            merged = merged[list(common_cols)]
            dataset = dataset[list(common_cols)]
            
            # Concatenate
            merged = pd.concat([merged, dataset], ignore_index=True)
        
        return merged
    
    def generate_data_report(self, data: pd.DataFrame, data_type: str) -> Dict[str, Any]:
        """Generate comprehensive data quality report."""
        report = {
            'data_type': data_type,
            'timestamp': datetime.now().isoformat(),
            'basic_stats': {},
            'validation_results': {},
            'recommendations': []
        }
        
        if data.empty:
            report['basic_stats'] = {'record_count': 0}
            report['recommendations'] = ['Data is empty - check data loading process']
            return report
        
        # Basic statistics
        report['basic_stats'] = {
            'record_count': len(data),
            'column_count': len(data.columns),
            'missing_values': data.isnull().sum().to_dict(),
            'data_types': data.dtypes.astype(str).to_dict()
        }
        
        # Validation results
        if 'date' in data.columns:
            report['validation_results']['temporal'] = self.validator.validate_temporal_consistency(data)
        
        if 'lat' in data.columns and 'lon' in data.columns:
            report['validation_results']['spatial'] = self.validator.validate_spatial_consistency(data)
        
        if 'albedo' in data.columns:
            report['validation_results']['albedo'] = self.validator.validate_albedo_values(data)
            report['validation_results']['outliers'] = self.validator.detect_outliers(data, 'albedo')
        
        # Generate recommendations
        report['recommendations'] = self._generate_recommendations(report['validation_results'])
        
        return report
    
    def _generate_recommendations(self, validation_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        for category, results in validation_results.items():
            if not results.get('valid', True):
                recommendations.append(f"Address {category} validation errors before proceeding")
            
            if results.get('warnings'):
                recommendations.append(f"Review {category} warnings: {len(results['warnings'])} issues found")
        
        if 'outliers' in validation_results:
            outlier_count = validation_results['outliers'].get('count', 0)
            if outlier_count > 0:
                recommendations.append(f"Consider removing or investigating {outlier_count} outliers")
        
        return recommendations
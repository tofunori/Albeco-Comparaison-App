import numpy as np
import pandas as pd
import logging
from typing import Dict, Any, List, Optional, Tuple
from scipy import optimize

logger = logging.getLogger(__name__)


class AlbedoCalculator:
    """Advanced albedo calculation methods for different MODIS products."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    def calculate_mod09ga_albedo(self, data: pd.DataFrame, 
                                method: str = 'broadband') -> pd.Series:
        """Calculate albedo from MOD09GA surface reflectance data."""
        if method == 'broadband':
            return self._broadband_albedo_mod09ga(data)
        elif method == 'narrowband':
            return self._narrowband_albedo_mod09ga(data)
        elif method == 'liang':
            return self._liang_albedo_mod09ga(data)
        else:
            raise ValueError(f"Unknown albedo calculation method: {method}")
    
    def _broadband_albedo_mod09ga(self, data: pd.DataFrame) -> pd.Series:
        """Calculate broadband albedo using simple band combination."""
        # Ensure required bands are present
        required_bands = ['red_reflectance', 'nir_reflectance']
        if not all(band in data.columns for band in required_bands):
            logger.error(f"Missing required bands: {required_bands}")
            return pd.Series(np.nan, index=data.index)
        
        # Simple broadband albedo approximation
        red = data['red_reflectance']
        nir = data['nir_reflectance']
        
        # Coefficients based on literature (simplified)
        albedo = 0.356 * red + 0.130 * nir
        
        return np.clip(albedo, 0, 1)
    
    def _narrowband_albedo_mod09ga(self, data: pd.DataFrame) -> pd.Series:
        """Calculate narrowband albedo with more spectral bands."""
        # Check for additional bands
        band_weights = {
            'blue_reflectance': 0.115,
            'green_reflectance': 0.148,
            'red_reflectance': 0.356,
            'nir_reflectance': 0.130,
            'swir1_reflectance': 0.188,
            'swir2_reflectance': 0.063
        }
        
        albedo = pd.Series(0.0, index=data.index)
        total_weight = 0
        
        for band, weight in band_weights.items():
            if band in data.columns:
                albedo += weight * data[band]
                total_weight += weight
        
        if total_weight > 0:
            albedo = albedo / total_weight
        else:
            logger.warning("No valid bands found for narrowband albedo calculation")
            return pd.Series(np.nan, index=data.index)
        
        return np.clip(albedo, 0, 1)
    
    def _liang_albedo_mod09ga(self, data: pd.DataFrame) -> pd.Series:
        """Calculate albedo using Liang (2001) algorithm."""
        # Liang coefficients for MODIS bands
        coefficients = {
            'red_reflectance': 0.3973,
            'nir_reflectance': 0.2382,
            'blue_reflectance': 0.2618,
            'green_reflectance': 0.1304
        }
        
        albedo = pd.Series(0.0048, index=data.index)  # Constant term
        
        for band, coeff in coefficients.items():
            if band in data.columns:
                albedo += coeff * data[band]
        
        return np.clip(albedo, 0, 1)
    
    def calculate_mod10a1_albedo(self, data: pd.DataFrame) -> pd.Series:
        """Process MOD10A1 snow albedo data."""
        if 'snow_albedo' not in data.columns:
            logger.error("Missing snow_albedo column in MOD10A1 data")
            return pd.Series(np.nan, index=data.index)
        
        albedo = data['snow_albedo'].copy()
        
        # Handle different value ranges
        if albedo.max() > 1:
            # Assume percentage values (0-100)
            albedo = albedo / 100.0
        
        # Apply snow cover filter if available
        if 'snow_cover' in data.columns:
            # Only use pixels with significant snow cover
            snow_threshold = self.config.get('analysis', {}).get('quality_filters', {}).get('snow_threshold', 10)
            mask = data['snow_cover'] >= snow_threshold
            albedo[~mask] = np.nan
        
        return np.clip(albedo, 0, 1)
    
    def calculate_mcd43a3_albedo(self, data: pd.DataFrame, 
                                solar_zenith: Optional[pd.Series] = None) -> pd.Series:
        """Calculate blue-sky albedo from MCD43A3 BRDF data."""
        required_cols = ['white_sky_albedo', 'black_sky_albedo']
        if not all(col in data.columns for col in required_cols):
            logger.error(f"Missing required columns: {required_cols}")
            return pd.Series(np.nan, index=data.index)
        
        white_sky = data['white_sky_albedo']
        black_sky = data['black_sky_albedo']
        
        if solar_zenith is not None:
            # Calculate blue-sky albedo using solar zenith angle
            # Formula: α_blue = α_black * (1 - S) + α_white * S
            # where S is the sky light fraction
            S = self._calculate_sky_light_fraction(solar_zenith)
            albedo = black_sky * (1 - S) + white_sky * S
        else:
            # Simple average if no solar zenith angle available
            albedo = 0.5 * (white_sky + black_sky)
        
        return np.clip(albedo, 0, 1)
    
    def _calculate_sky_light_fraction(self, solar_zenith: pd.Series) -> pd.Series:
        """Calculate sky light fraction from solar zenith angle."""
        # Simplified parameterization
        # In practice, this would depend on atmospheric conditions
        sza_rad = np.radians(solar_zenith)
        
        # Approximate formula (Wang et al., 2015)
        S = 0.28 * np.exp(-3.0 * np.cos(sza_rad))
        
        return np.clip(S, 0, 1)
    
    def apply_topographic_correction(self, albedo: pd.Series, 
                                   illumination: pd.Series) -> pd.Series:
        """Apply topographic correction to albedo values."""
        if illumination is None or illumination.isna().all():
            return albedo
        
        # Simple cosine correction
        corrected_albedo = albedo / np.maximum(illumination, 0.1)  # Avoid division by zero
        
        return np.clip(corrected_albedo, 0, 1)
    
    def calculate_spectral_albedo(self, reflectance_data: pd.DataFrame, 
                                band_weights: Dict[str, float]) -> pd.Series:
        """Calculate spectral albedo from multiple bands."""
        albedo = pd.Series(0.0, index=reflectance_data.index)
        total_weight = 0
        
        for band, weight in band_weights.items():
            if band in reflectance_data.columns:
                band_data = reflectance_data[band]
                # Apply quality filtering
                valid_mask = (band_data >= 0) & (band_data <= 1)
                albedo += weight * band_data * valid_mask
                total_weight += weight
        
        if total_weight > 0:
            albedo = albedo / total_weight
        else:
            albedo = pd.Series(np.nan, index=reflectance_data.index)
        
        return np.clip(albedo, 0, 1)
    
    def temporal_smoothing(self, albedo_series: pd.Series, 
                          window_days: int = 7,
                          method: str = 'rolling_mean') -> pd.Series:
        """Apply temporal smoothing to albedo time series."""
        if method == 'rolling_mean':
            return albedo_series.rolling(window=window_days, center=True).mean()
        elif method == 'rolling_median':
            return albedo_series.rolling(window=window_days, center=True).median()
        elif method == 'gaussian':
            from scipy.ndimage import gaussian_filter1d
            sigma = window_days / 3.0  # Standard deviation
            smoothed = gaussian_filter1d(albedo_series.values, sigma=sigma)
            return pd.Series(smoothed, index=albedo_series.index)
        else:
            raise ValueError(f"Unknown smoothing method: {method}")
    
    def gap_filling(self, albedo_series: pd.Series, 
                   method: str = 'interpolation',
                   max_gap_days: int = 10) -> pd.Series:
        """Fill gaps in albedo time series."""
        if method == 'interpolation':
            # Linear interpolation for small gaps
            filled = albedo_series.interpolate(method='linear', limit=max_gap_days)
        elif method == 'seasonal':
            # Use seasonal patterns for gap filling
            filled = self._seasonal_gap_filling(albedo_series, max_gap_days)
        elif method == 'climatology':
            # Use climatological averages
            filled = self._climatological_gap_filling(albedo_series, max_gap_days)
        else:
            raise ValueError(f"Unknown gap filling method: {method}")
        
        return filled
    
    def _seasonal_gap_filling(self, series: pd.Series, max_gap: int) -> pd.Series:
        """Fill gaps using seasonal patterns."""
        # Simple implementation - use day-of-year averages
        filled = series.copy()
        
        if series.index.dtype.name.startswith('datetime'):
            doy_means = series.groupby(series.index.dayofyear).mean()
            
            for idx in series[series.isna()].index:
                doy = idx.dayofyear
                if doy in doy_means.index and not np.isnan(doy_means[doy]):
                    filled[idx] = doy_means[doy]
        
        return filled
    
    def _climatological_gap_filling(self, series: pd.Series, max_gap: int) -> pd.Series:
        """Fill gaps using climatological averages."""
        filled = series.copy()
        overall_mean = series.mean()
        
        if not np.isnan(overall_mean):
            filled = filled.fillna(overall_mean)
        
        return filled
    
    def quality_assessment(self, albedo: pd.Series, 
                          quality_flags: Optional[pd.Series] = None) -> Dict[str, Any]:
        """Assess quality of calculated albedo values."""
        assessment = {
            'total_values': len(albedo),
            'valid_values': albedo.notna().sum(),
            'data_completeness': albedo.notna().sum() / len(albedo),
            'mean_albedo': albedo.mean(),
            'std_albedo': albedo.std(),
            'min_albedo': albedo.min(),
            'max_albedo': albedo.max()
        }
        
        # Check for unrealistic values
        very_low = (albedo < 0.05).sum()
        very_high = (albedo > 0.95).sum()
        
        assessment['quality_flags'] = {
            'very_low_values': very_low,
            'very_high_values': very_high,
            'suspicious_values': very_low + very_high
        }
        
        if quality_flags is not None:
            good_quality = (quality_flags == 0).sum()  # Assuming 0 means good quality
            assessment['quality_flags']['good_quality_pixels'] = good_quality
            assessment['quality_flags']['good_quality_fraction'] = good_quality / len(quality_flags)
        
        return assessment
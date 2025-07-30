#!/usr/bin/env python3
"""
Outlier Detection Module

This module contains outlier detection algorithms, including the residual-based
method that replaces Z-score detection with superior performance.
"""

import pandas as pd
import numpy as np
import logging
from scipy import stats as scipy_stats
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class OutlierDetector:
    """
    Implements various outlier detection algorithms for albedo analysis.
    
    The primary method is residual-based detection which uses a 2.5σ threshold
    on residuals from linear regression, providing superior performance to Z-score methods.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.default_threshold = config.get('analysis', {}).get('albedo', {}).get('outlier_threshold', 2.5)
    
    def perform_outlier_analysis(self, merged_data: pd.DataFrame) -> Dict[str, Any]:
        """Perform comprehensive outlier analysis on merged dataset."""
        outlier_results = {}
        
        modis_methods = [col for col in merged_data.columns if col in ['MCD43A3', 'MOD09GA', 'MOD10A1']]
        
        if not modis_methods or 'AWS' not in merged_data.columns:
            return outlier_results
        
        logger.info(f"Performing residual-based outlier detection ({self.default_threshold}σ threshold)")
        
        stats_with_outliers = {}
        stats_without_outliers = {}
        outlier_info = {}
        
        for method in modis_methods:
            mask = merged_data[[method, 'AWS']].notna().all(axis=1)
            if mask.sum() == 0:
                continue
                
            x_all = merged_data.loc[mask, 'AWS']
            y_all = merged_data.loc[mask, method]
            
            # Stats with outliers
            r_all, _ = scipy_stats.pearsonr(x_all, y_all)
            rmse_all = np.sqrt(np.mean((y_all - x_all)**2))
            mae_all = np.mean(np.abs(y_all - x_all))
            bias_all = np.mean(y_all - x_all)
            stats_with_outliers[method] = {
                'n': len(x_all), 'r': r_all, 'rmse': rmse_all, 
                'mae': mae_all, 'bias': bias_all
            }
            
            # Remove residual outliers
            slope, intercept = np.polyfit(x_all, y_all, 1)
            predicted = slope * x_all + intercept
            residuals = y_all - predicted
            residual_threshold = self.default_threshold * residuals.std()
            residual_outliers = np.abs(residuals) > residual_threshold
            
            outlier_series = pd.Series(residual_outliers, index=mask[mask].index).reindex(merged_data.index, fill_value=False)
            clean_mask = mask & ~outlier_series
            
            n_outliers = residual_outliers.sum()
            outlier_info[method] = {
                'n_total': len(x_all),
                'n_outliers': n_outliers,
                'outlier_percentage': (n_outliers / len(x_all)) * 100,
                'residual_threshold': residual_threshold,
                'outlier_indices': mask[mask].index[residual_outliers].tolist()
            }
            
            if clean_mask.sum() > 0:
                x_clean = merged_data.loc[clean_mask, 'AWS']
                y_clean = merged_data.loc[clean_mask, method]
                
                r_clean, _ = scipy_stats.pearsonr(x_clean, y_clean)
                rmse_clean = np.sqrt(np.mean((y_clean - x_clean)**2))
                mae_clean = np.mean(np.abs(y_clean - x_clean))
                bias_clean = np.mean(y_clean - x_clean)
                stats_without_outliers[method] = {
                    'n': len(x_clean), 'r': r_clean, 'rmse': rmse_clean,
                    'mae': mae_clean, 'bias': bias_clean
                }
                
                r_improvement = ((r_clean - r_all) / abs(r_all)) * 100 if r_all != 0 else 0
                rmse_improvement = ((rmse_all - rmse_clean) / rmse_all) * 100 if rmse_all != 0 else 0
                
                outlier_info[method].update({
                    'r_improvement_pct': r_improvement,
                    'rmse_improvement_pct': rmse_improvement
                })
                
                logger.info(f"{method}: Removed {n_outliers} outliers ({n_outliers/len(x_all)*100:.1f}%), "
                           f"r improved by {r_improvement:.1f}%")
        
        return {
            'stats_with_outliers': stats_with_outliers,
            'stats_without_outliers': stats_without_outliers,
            'outlier_info': outlier_info
        }
    
    def detect_residual_outliers(self, merged_data: pd.DataFrame, method: str, 
                                threshold: float = None) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Detect outliers using residual-based approach.
        
        This replaces Z-score outlier detection with the user's superior approach.
        """
        if threshold is None:
            threshold = self.default_threshold
            
        if method not in merged_data.columns or 'AWS' not in merged_data.columns:
            return merged_data, pd.Series([], dtype=bool)
        
        # Get valid data
        mask = merged_data[[method, 'AWS']].notna().all(axis=1)
        if mask.sum() == 0:
            return merged_data, pd.Series([], dtype=bool)
        
        x_all = merged_data.loc[mask, 'AWS']
        y_all = merged_data.loc[mask, method]
        
        # Calculate residuals from linear regression
        slope, intercept = np.polyfit(x_all, y_all, 1)
        predicted = slope * x_all + intercept
        residuals = y_all - predicted
        
        # Detect outliers based on residual threshold
        residual_threshold = threshold * residuals.std()
        outlier_mask_subset = np.abs(residuals) > residual_threshold
        
        # Create full outlier mask for the entire dataset
        outlier_mask_full = pd.Series(False, index=merged_data.index)
        outlier_mask_full.loc[mask] = outlier_mask_subset
        
        # Remove outliers
        clean_data = merged_data[~outlier_mask_full].copy()
        
        n_outliers = outlier_mask_subset.sum()
        logger.info(f"Residual-based outlier detection for {method}: removed {n_outliers} outliers ({n_outliers/len(y_all)*100:.1f}%)")
        
        return clean_data, outlier_mask_full
    
    def detect_zscore_outliers(self, data: pd.Series, threshold: float = 3.0) -> pd.Series:
        """
        Detect outliers using Z-score method (legacy).
        
        Note: This method is kept for compatibility but residual-based is preferred.
        """
        z_scores = np.abs(scipy_stats.zscore(data.dropna()))
        outlier_mask = pd.Series(False, index=data.index)
        outlier_mask.loc[data.dropna().index] = z_scores > threshold
        
        return outlier_mask
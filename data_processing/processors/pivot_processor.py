#!/usr/bin/env python3
"""
Pivot-based data processor that implements the user's proven methodology.

This module contains the PivotBasedProcessor class that handles Terra/Aqua merging,
pivot table creation, and residual-based outlier detection.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PivotBasedProcessor:
    """
    Main processor that implements the user's proven methodology using pivot tables.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    def apply_terra_aqua_merge(self, modis_data: pd.DataFrame) -> pd.DataFrame:
        """
        Apply Terra/Aqua merging exactly as done in the user's notebook.
        
        This matches the merge_terra_aqua function from compare_albedo.ipynb.
        """
        logger.info("Applying Terra/Aqua merge...")
        
        modis_data = modis_data.copy()
        modis_data['method'] = modis_data['method'].str.upper()
        
        albedo_col = 'albedo'
        product_pairs = {'MOD09GA': 'MYD09GA', 'MOD10A1': 'MYD10A1'}
        combined_rows = []
        
        # Process Terra/Aqua pairs
        for terra, aqua in product_pairs.items():
            terra_df = modis_data[modis_data['method'] == terra].copy()
            aqua_df = modis_data[modis_data['method'] == aqua].copy()
            
            if len(terra_df) == 0 and len(aqua_df) == 0:
                continue
            
            # Terra-only data (no Aqua counterpart)
            if len(terra_df) > 0 and len(aqua_df) == 0:
                terra_df['source'] = 'terra_only'
                combined_rows.append(terra_df)
                continue
            
            # Aqua-only data (no Terra counterpart)
            if len(aqua_df) > 0 and len(terra_df) == 0:
                aqua_df['source'] = 'aqua_only'
                aqua_df['method'] = terra  # Rename to Terra for consistency
                combined_rows.append(aqua_df)
                continue
                
            # Normal case: merge Terra and Aqua data
            merged = pd.merge(terra_df, aqua_df, on=['date', 'pixel_id'], suffixes=('_terra', '_aqua'), how='outer')
            
            # Combine albedo values (mean of both or single available)
            terra_albedo, aqua_albedo = f'{albedo_col}_terra', f'{albedo_col}_aqua'
            merged[albedo_col] = merged[[terra_albedo, aqua_albedo]].mean(axis=1)
            merged['method'] = terra  # Use Terra name for combined
            merged['source'] = np.where(
                merged[terra_albedo].notna() & merged[aqua_albedo].notna(), 'combined',
                np.where(merged[terra_albedo].notna(), 'terra_only', 'aqua_only')
            )
            
            # Preserve spatial coordinates
            merged['latitude'] = merged['latitude_terra'].combine_first(merged['latitude_aqua'])
            merged['longitude'] = merged['longitude_terra'].combine_first(merged['longitude_aqua'])
            
            # Preserve additional important columns
            additional_cols = ['glacier_fraction', 'solar_zenith', 'ndsi', 'elevation', 'slope', 'aspect', 'qa_mode']
            for col in additional_cols:
                terra_col = f'{col}_terra'
                aqua_col = f'{col}_aqua'
                if terra_col in merged.columns or aqua_col in merged.columns:
                    if terra_col in merged.columns and aqua_col in merged.columns:
                        # For numerical columns, take mean; for categorical, prefer terra
                        if col in ['glacier_fraction', 'elevation', 'slope', 'aspect']:
                            merged[col] = merged[[terra_col, aqua_col]].mean(axis=1)
                        elif col == 'solar_zenith':
                            # For solar zenith, prefer valid values over -999
                            terra_valid = (merged[terra_col] != -999) & merged[terra_col].notna()
                            aqua_valid = (merged[aqua_col] != -999) & merged[aqua_col].notna()
                            
                            merged[col] = merged[terra_col].copy()
                            merged.loc[~terra_valid & aqua_valid, col] = merged.loc[~terra_valid & aqua_valid, aqua_col]
                            merged.loc[~terra_valid & ~aqua_valid, col] = -999
                        else:
                            # For categorical columns like qa_mode, prefer terra
                            merged[col] = merged[terra_col].combine_first(merged[aqua_col])
                    elif terra_col in merged.columns:
                        merged[col] = merged[terra_col]
                    elif aqua_col in merged.columns:
                        merged[col] = merged[aqua_col]
            
            # Keep essential columns plus preserved additional columns
            base_cols = ['date', 'pixel_id', 'method', albedo_col, 'latitude', 'longitude', 'source']
            preserved_cols = [col for col in additional_cols if col in merged.columns]
            keep_cols = base_cols + preserved_cols
            
            result = merged[keep_cols]
            combined_rows.append(result)
        
        # Keep non-paired methods unchanged (like MCD43A3)
        other_methods = modis_data[~modis_data['method'].isin(list(product_pairs.keys()) + list(product_pairs.values()))]
        
        final_result = pd.concat(combined_rows + [other_methods], ignore_index=True) if combined_rows else other_methods
        
        logger.info(f"Terra/Aqua merge complete - Final MODIS rows: {len(final_result)}")
        if 'source' in final_result.columns:
            source_counts = final_result['source'].value_counts().to_dict()
            logger.info(f"Source breakdown: {source_counts}")
        
        return final_result
    
    def create_pivot_and_merge(self, modis_data: pd.DataFrame, aws_data: pd.DataFrame) -> pd.DataFrame:
        """
        Create pivot table and merge with AWS data exactly as in user's notebook.
        
        This is the core methodology that produces 515 merged observations.
        """
        logger.info("Creating pivot table and merging with AWS data...")
        
        # Create pivot table (matching user's approach)
        modis_pivot = modis_data.pivot_table(index='date', columns='method', values='albedo', aggfunc='mean')
        logger.info(f"Created MODIS pivot table: {modis_pivot.shape}")
        logger.info(f"Available methods: {list(modis_pivot.columns)}")
        
        # Create additional pivots for analysis columns
        additional_columns = ['glacier_fraction', 'solar_zenith', 'ndsi', 'pixel_id']
        additional_data = {}
        
        for col in additional_columns:
            if col in modis_data.columns:
                if col == 'pixel_id':
                    additional_data[col] = modis_data.pivot_table(index='date', columns='method', values=col, aggfunc='first')
                else:
                    additional_data[col] = modis_data.pivot_table(index='date', columns='method', values=col, aggfunc='mean')
                logger.info(f"Added {col} data to analysis")
        
        # Merge with AWS data (simple inner join as in user's notebook)
        merged = pd.merge(modis_pivot, aws_data[['date', 'Albedo']], on='date', how='inner')
        merged.rename(columns={'Albedo': 'AWS'}, inplace=True)
        merged.set_index('date', inplace=True)
        
        # Add the additional columns to the merged dataframe
        for col in additional_columns:
            if col in additional_data:
                # For each method, add the corresponding column data
                for method in modis_pivot.columns:
                    if method in additional_data[col].columns:
                        merged[f'{col}_{method}'] = additional_data[col][method]
                
                # Create general column that prioritizes valid data over -999 values
                available_cols = [f'{col}_{method}' for method in modis_pivot.columns 
                                if f'{col}_{method}' in merged.columns]
                if available_cols:
                    # Replace -999 with NaN to treat as missing data
                    temp_cols = merged[available_cols].copy()
                    temp_cols = temp_cols.replace(-999, np.nan)
                    
                    # Use the first available valid value across methods
                    merged[col] = temp_cols.bfill(axis=1).iloc[:, 0]
                    
                    # Special handling for solar_zenith
                    if col == 'solar_zenith':
                        all_missing = merged[available_cols].eq(-999).all(axis=1)
                        merged.loc[all_missing, col] = np.nan
        
        logger.info(f"Final merged dataset: {merged.shape}")
        logger.info(f"Date range: {merged.index.min()} to {merged.index.max()}")
        logger.info(f"Total overlapping observations: {len(merged)}")
        
        return merged
    
    def detect_residual_outliers(self, merged_data: pd.DataFrame, method: str, threshold: float = 2.5) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Detect outliers using residual-based approach as in user's notebook.
        
        This replaces Z-score outlier detection with the user's superior approach.
        """
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
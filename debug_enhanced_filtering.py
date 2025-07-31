#!/usr/bin/env python3
"""
Debug script for enhanced filtering functions
"""

import sys
sys.path.append('.')

import pandas as pd
import logging
from dashboard.core.data_manager import DashboardDataManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_glacier_fraction_filtering():
    """Test glacier fraction filtering on Haig data."""
    print("=== Testing Enhanced Filtering for Haig Glacier ===")
    
    # Initialize data manager
    data_manager = DashboardDataManager()
    
    # Load Haig data
    print("\n--- Loading Haig Data ---")
    haig_data = data_manager.load_glacier_data('haig')
    
    if haig_data is None or haig_data.empty:
        print("ERROR: Failed to load Haig data")
        return
    
    print(f"[OK] Loaded Haig data: {len(haig_data)} records")
    print(f"   Columns: {list(haig_data.columns)}")
    
    # Check glacier_fraction column
    if 'glacier_fraction' in haig_data.columns:
        print(f"   Glacier fraction range: {haig_data['glacier_fraction'].min():.3f} - {haig_data['glacier_fraction'].max():.3f}")
        print(f"   Mean glacier fraction: {haig_data['glacier_fraction'].mean():.3f}")
        
        # Count records with high glacier fraction (≥ 0.7)
        high_fraction_data = haig_data[haig_data['glacier_fraction'] >= 0.7]
        print(f"   Records with glacier_fraction >= 0.7: {len(high_fraction_data)}")
        
        if len(high_fraction_data) == 0:
            print("   ERROR: NO RECORDS with glacier_fraction >= 0.7!")
            print("   Let's check the distribution:")
            print(f"   Records with glacier_fraction >= 0.5: {len(haig_data[haig_data['glacier_fraction'] >= 0.5])}")
            print(f"   Records with glacier_fraction >= 0.3: {len(haig_data[haig_data['glacier_fraction'] >= 0.3])}")
            print(f"   Records with glacier_fraction >= 0.1: {len(haig_data[haig_data['glacier_fraction'] >= 0.1])}")
        else:
            print(f"   [OK] Found {len(high_fraction_data)} records with high glacier fraction")
    else:
        print("   ERROR: No 'glacier_fraction' column found!")
        return
    
    # Test the enhanced filtering function
    print("\n--- Testing Enhanced Filtering Function ---")
    try:
        # Import the enhanced filtering function
        from app_fixed import filter_pixels_by_glacier_fraction
        
        # Test with different thresholds
        for threshold in [0.1, 0.3, 0.5, 0.7, 0.9]:
            filtered_data = filter_pixels_by_glacier_fraction(haig_data, threshold)
            print(f"   Threshold {threshold}: {len(filtered_data)} records (from {len(haig_data)})")
        
        print("[OK] Enhanced filtering function works")
        
    except Exception as e:
        print(f"ERROR: Error testing enhanced filtering function: {e}")
    
    # Test AWS station info
    print("\n--- Testing AWS Station Info ---")
    glacier_info = data_manager.glacier_config.get('glaciers', {}).get('haig', {})
    aws_stations = glacier_info.get('aws_stations', {})
    
    if aws_stations:
        for station_id, station_info in aws_stations.items():
            print(f"   Station {station_id}: {station_info}")
        print("[OK] AWS station info found")
    else:
        print("ERROR: No AWS station info found!")

if __name__ == "__main__":
    test_glacier_fraction_filtering()
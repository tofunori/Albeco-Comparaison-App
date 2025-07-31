#!/usr/bin/env python3
"""
Test script to verify Haig and Coropuna glacier data loading
"""

import sys
sys.path.append('.')

from dashboard.core.data_manager import DashboardDataManager
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_glacier_loading():
    """Test loading Haig and Coropuna glacier data."""
    print("=== Testing Glacier Data Loading ===")
    
    # Initialize data manager
    data_manager = DashboardDataManager()
    
    # Test Haig glacier
    print("\n--- Testing Haig Glacier ---")
    try:
        haig_data = data_manager.load_glacier_data('haig')
        if haig_data is not None:
            print(f"[SUCCESS] Haig data loaded successfully: {len(haig_data)} records")
            print(f"   Columns: {list(haig_data.columns)}")
            print(f"   Methods: {haig_data['method'].unique() if 'method' in haig_data.columns else 'No method column'}")
            print(f"   Date range: {haig_data['date'].min()} to {haig_data['date'].max()}" if 'date' in haig_data.columns else "   No date column")
        else:
            print("[FAILED] Haig data loading failed - returned None")
    except Exception as e:
        print(f"[FAILED] Haig data loading failed with error: {e}")
    
    # Test Coropuna glacier
    print("\n--- Testing Coropuna Glacier ---")
    try:
        coropuna_data = data_manager.load_glacier_data('coropuna')
        if coropuna_data is not None:
            print(f"[SUCCESS] Coropuna data loaded successfully: {len(coropuna_data)} records")
            print(f"   Columns: {list(coropuna_data.columns)}")
            print(f"   Methods: {coropuna_data['method'].unique() if 'method' in coropuna_data.columns else 'No method column'}")
            print(f"   Date range: {coropuna_data['date'].min()} to {coropuna_data['date'].max()}" if 'date' in coropuna_data.columns else "   No date column")
        else:
            print("[FAILED] Coropuna data loading failed - returned None")
    except Exception as e:
        print(f"[FAILED] Coropuna data loading failed with error: {e}")
    
    # Test available glaciers
    print("\n--- Available Glaciers ---")
    try:
        glaciers = data_manager.get_available_glaciers()
        for glacier in glaciers:
            print(f"Glacier: {glacier['name']} ({glacier['id']})")
            print(f"   MODIS available: {glacier['data_available']['modis']}")
            print(f"   AWS available: {glacier['data_available']['aws']}")
    except Exception as e:
        print(f"[FAILED] Error getting available glaciers: {e}")

if __name__ == "__main__":
    test_glacier_loading()
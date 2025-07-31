#!/usr/bin/env python3
"""
Test Haig glacier coordinates in the dashboard
"""

import sys
sys.path.append('.')

from dashboard.core.data_manager import DashboardDataManager

def test_haig_coordinates():
    """Test if Haig glacier coordinates are correctly loaded."""
    print("=== Testing Haig Glacier Coordinates ===")
    
    # Initialize data manager
    data_manager = DashboardDataManager()
    
    # Get Haig glacier info
    haig_info = data_manager.glacier_config.get('glaciers', {}).get('haig', {})
    
    if haig_info:
        coords = haig_info.get('coordinates', {})
        print(f"Haig glacier info found:")
        print(f"  Name: {haig_info.get('name', 'Unknown')}")
        print(f"  Coordinates: {coords}")
        print(f"  Latitude: {coords.get('lat', 'Not found')}")
        print(f"  Longitude: {coords.get('lon', 'Not found')}")
        
        # Check if coordinates are the expected ones
        expected_lat = 50.714
        expected_lon = -115.309
        
        actual_lat = coords.get('lat')
        actual_lon = coords.get('lon')
        
        if actual_lat == expected_lat and actual_lon == expected_lon:
            print("[SUCCESS] Coordinates match expected values!")
        else:
            print(f"[ERROR] Coordinates don't match!")
            print(f"  Expected: lat={expected_lat}, lon={expected_lon}")
            print(f"  Actual: lat={actual_lat}, lon={actual_lon}")
    else:
        print("[ERROR] Haig glacier info not found in configuration")
    
    # Also test available glaciers
    print("\n--- All Available Glaciers ---")
    glaciers = data_manager.get_available_glaciers()
    for glacier in glaciers:
        if glacier['id'] == 'haig':
            print(f"Haig in available glaciers: {glacier}")

if __name__ == "__main__":
    test_haig_coordinates()
#!/usr/bin/env python3
"""
Test Data Loading

Simple test script to verify data loading functionality works
without requiring the full dashboard dependencies.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from dashboard.core.data_manager import DashboardDataManager
    
    print("Testing Data Loading Functionality")
    print("=" * 50)
    
    # Initialize data manager
    print("Initializing data manager...")
    dm = DashboardDataManager()
    print("[OK] Data manager initialized")
    
    # Get available glaciers
    print("\nGetting available glaciers...")
    glaciers = dm.get_available_glaciers()
    print(f"[OK] Found {len(glaciers)} glaciers:")
    
    for glacier in glaciers:
        print(f"  - {glacier['name']} ({glacier['id']})")
        availability = glacier.get('data_available', {})
        for data_type, available in availability.items():
            status = "[OK]" if available else "[MISSING]"
            print(f"    {status} {data_type.upper()}")
    
    # Test loading data for first available glacier
    if glaciers:
        glacier_id = glaciers[0]['id']
        print(f"\nTesting data loading for {glacier_id}...")
        
        try:
            data = dm.load_glacier_data(glacier_id)
            if data is not None:
                print(f"[OK] Data loaded: {len(data)} records")
                print(f"   Columns: {list(data.columns)}")
                
                # Test pixel locations
                pixels = dm.get_pixel_locations(glacier_id)
                if pixels is not None:
                    print(f"[OK] Pixel locations: {len(pixels)} pixels")
                
                # Test data summary
                summary = dm.get_data_summary(glacier_id)
                print(f"[OK] Data summary: {summary.get('total_records', 'N/A')} total records")
                
                # Test simple statistics
                if len(data) > 0:
                    stats = dm.calculate_statistics(data)
                    print(f"[OK] Statistics calculated: {len(stats)} metrics")
                    for key, value in stats.items():
                        if isinstance(value, float):
                            print(f"   {key}: {value:.4f}")
                        else:
                            print(f"   {key}: {value}")
                
            else:
                print("[ERROR] No data loaded")
                
        except Exception as e:
            print(f"[ERROR] Error loading data: {e}")
    
    print("\nData loading test completed!")
    print("\nTo run the full dashboard, install the required packages:")
    print("pip install plotly dash dash-bootstrap-components dash-leaflet")
    print("\nThen run: python app.py")
    
except Exception as e:
    print(f"[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()
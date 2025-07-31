#!/usr/bin/env python3
"""
Debug script to test map marker filtering logic
"""

import sys
sys.path.append('.')

import pandas as pd
import logging
from io import StringIO

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_determine_filtered_pixels():
    """Test the determine_filtered_pixels function with mock data"""
    print("=== Testing determine_filtered_pixels function ===")
    
    # Create mock pixel data (like what would be passed to the map callback)
    pixel_data = pd.DataFrame({
        'pixel_id': ['1', '2'],
        'latitude': [52.1, 52.2],
        'longitude': [-117.1, -117.2], 
        'glacier_fraction': [0.8, 0.5]  # pixel 1 should pass (>= 0.7), pixel 2 should fail
    })
    
    # Create mock data_json (full dataset as JSON string)
    full_data = pd.DataFrame({
        'pixel_id': ['1', '1', '2', '2'] * 100,  # Multiple records per pixel
        'date': ['2020-01-01'] * 400,
        'albedo': [0.7] * 400,
        'glacier_fraction': [0.8, 0.8, 0.5, 0.5] * 100  # pixel 1: 0.8, pixel 2: 0.5
    })
    data_json = full_data.to_json()
    
    # Mock filter parameters
    filter_params = {
        'data_mode': 'custom',
        'use_glacier_fraction': True,
        'min_glacier_fraction': 0.7
    }
    
    print(f"Mock pixel data shape: {pixel_data.shape}")
    print(f"Pixel fractions: {dict(zip(pixel_data['pixel_id'], pixel_data['glacier_fraction']))}")
    print(f"Filter threshold: {filter_params['min_glacier_fraction']}")
    print(f"Expected: pixel '1' passes (0.8 >= 0.7), pixel '2' fails (0.5 < 0.7)")
    
    # Test the function (need to import it)
    try:
        from app_fixed import determine_filtered_pixels
        
        result = determine_filtered_pixels(pixel_data, data_json, 'test_glacier', filter_params)
        
        print(f"\\nResult: {result}")
        print(f"Result type: {type(result)}")
        print(f"Length: {len(result)}")
        
        # Check if the result is correct
        expected = {'1'}  # Only pixel 1 should pass
        if result == expected:
            print("✅ CORRECT: Function returned expected result")
        else:
            print(f"❌ ERROR: Expected {expected}, got {result}")
            
    except Exception as e:
        print(f"ERROR: Could not test function: {e}")
        import traceback
        traceback.print_exc()

def test_marker_styling():
    """Test the get_pixel_marker_style function"""
    print("\\n=== Testing get_pixel_marker_style function ===")
    
    try:
        from app_fixed import get_pixel_marker_style
        
        # Test different scenarios
        test_cases = [
            # (pixel_id, is_selected, passes_filter, expected_color)
            ('1', False, True, 'green'),    # Passes filter only
            ('2', False, False, 'grey'),    # Excluded by filter 
            ('3', True, False, 'red'),      # Selected but excluded
            ('4', True, True, 'orange'),    # Both selected and passes filter
            ('5', False, False, 'blue'),    # Default (no filters active)
        ]
        
        # Mock filter params with active filter
        filter_params = {
            'use_glacier_fraction': True,
            'min_glacier_fraction': 0.7
        }
        
        for pixel_id, is_selected, passes_filter, expected_color in test_cases:
            style = get_pixel_marker_style(pixel_id, is_selected, passes_filter, filter_params)
            actual_color = style['color']
            
            if actual_color == expected_color:
                print(f"✅ Pixel {pixel_id}: {actual_color} (correct)")
            else:
                print(f"❌ Pixel {pixel_id}: expected {expected_color}, got {actual_color}")
                
    except Exception as e:
        print(f"ERROR: Could not test styling function: {e}")

if __name__ == "__main__":
    test_determine_filtered_pixels()
    test_marker_styling()
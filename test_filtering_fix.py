#!/usr/bin/env python3
"""
Test the filtering fix for pixel color changes
"""

import sys
sys.path.append('.')

import pandas as pd
from io import StringIO

def test_pixel_filtering_modes():
    """Test pixel filtering for different data modes."""
    print("=== Testing Pixel Filtering Modes ===")
    
    # Mock pixel data
    pixel_data = pd.DataFrame({
        'pixel_id': [9073025950, 9073025951],
        'latitude': [52.1948, 52.1950],
        'longitude': [-117.2511, -117.2512],
        'glacier_fraction': [0.969, 0.850]
    })
    
    # Mock full data for filtering
    full_data = pd.DataFrame({
        'pixel_id': [9073025950, 9073025950, 9073025951, 9073025951],
        'date': ['2020-01-01', '2020-01-02', '2020-01-01', '2020-01-02'],
        'albedo': [0.8, 0.75, 0.7, 0.72],
        'qa_mode': [1, 1, 2, 1]  # 1 = best quality, 2 = lower quality
    })
    
    data_json = full_data.to_json()
    
    # Import the function we want to test
    from app_fixed import determine_filtered_pixels
    
    print(f"Test data: {len(pixel_data)} pixels, {len(full_data)} records")
    print(f"Pixel IDs: {list(pixel_data['pixel_id'])}")
    
    # Test different modes
    test_cases = [
        {'data_mode': 'all', 'expected_count': 2, 'description': 'All pixels mode'},
        {'data_mode': 'selected', 'expected_count': 0, 'description': 'Selected pixels mode (empty)'},
        {'data_mode': 'best', 'expected_count': 1, 'description': 'Best quality pixels mode'},
        {'data_mode': 'closest_aws', 'expected_count': 1, 'description': 'Closest to AWS mode'},
        {'data_mode': 'custom', 'use_glacier_fraction': True, 'min_glacier_fraction': 0.9, 'expected_count': 1, 'description': 'Custom glacier fraction filter'},
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['description']} ---")
        
        filter_params = {
            'data_mode': test_case['data_mode']
        }
        
        # Add custom parameters if needed
        if 'use_glacier_fraction' in test_case:
            filter_params['use_glacier_fraction'] = test_case['use_glacier_fraction']
            filter_params['min_glacier_fraction'] = test_case['min_glacier_fraction']
        
        try:
            result = determine_filtered_pixels(pixel_data, data_json, 'test_glacier', filter_params)
            result_count = len(result)
            expected_count = test_case['expected_count']
            
            print(f"  Filter params: {filter_params}")
            print(f"  Result: {result}")
            print(f"  Count: {result_count} (expected: {expected_count})")
            
            if result_count == expected_count:
                print(f"  ✅ PASS: Correct number of pixels filtered")
            else:
                print(f"  ❌ FAIL: Expected {expected_count}, got {result_count}")
                
            # Test pixel ID format consistency
            if result:
                sample_id = list(result)[0]
                if sample_id.isdigit():
                    print(f"  ✅ PASS: Pixel ID format is consistent (integer string): '{sample_id}'")
                else:
                    print(f"  ❌ FAIL: Pixel ID format issue: '{sample_id}'")
                    
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n=== Test Complete ===")

def test_pixel_id_consistency():
    """Test pixel ID type consistency."""
    print("\n=== Testing Pixel ID Consistency ===")
    
    # Test different input formats
    test_inputs = [
        [9073025950, 9073025951],           # Pure integers
        [9073025950.0, 9073025951.0],       # Floats from JSON
        ['9073025950', '9073025951'],       # String integers
        ['9073025950.0', '9073025951.0'],   # String floats
    ]
    
    expected_output = {'9073025950', '9073025951'}
    
    for i, input_data in enumerate(test_inputs, 1):
        print(f"\nTest {i}: Input format {type(input_data[0]).__name__}: {input_data}")
        
        # Simulate the normalization logic
        try:
            result = set(str(int(float(pid))) for pid in input_data)
            print(f"  Result: {result}")
            
            if result == expected_output:
                print(f"  ✅ PASS: Consistent output format")
            else:
                print(f"  ❌ FAIL: Expected {expected_output}, got {result}")
                
        except Exception as e:
            print(f"  ❌ ERROR: {e}")

if __name__ == "__main__":
    test_pixel_filtering_modes()
    test_pixel_id_consistency()

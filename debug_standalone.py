#!/usr/bin/env python3
"""
Standalone debug script to test filtering logic without dash dependencies
"""

import pandas as pd
import logging
from io import StringIO

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_pixel_marker_style(pixel_id, is_selected, passes_filter, filter_params=None):
    """Determine marker style based on pixel state."""
    # Define marker styles for different states
    styles = {
        'excluded': {
            'color': 'grey',
            'size': 15,
            'opacity': 0.5,
        },
        'default': {
            'color': 'blue',
            'size': 20,
            'opacity': 0.8,
        },
        'filtered': {
            'color': 'green',
            'size': 25,
            'opacity': 1.0,
        },
        'selected': {
            'color': 'red',
            'size': 30,
            'opacity': 1.0,
        },
        'filtered_selected': {
            'color': 'orange',
            'size': 32,
            'opacity': 1.0,
        }
    }
    
    # Determine pixel state
    if is_selected and passes_filter:
        return styles['filtered_selected']
    elif is_selected:
        return styles['selected']
    elif passes_filter:
        return styles['filtered']
    elif filter_params and (filter_params.get('use_distance_filter') or filter_params.get('use_glacier_fraction')):
        # If any filter is active but pixel doesn't pass, mark as excluded
        return styles['excluded']
    else:
        return styles['default']

def determine_filtered_pixels(pixel_data, data_json, glacier_id, filter_params):
    """Determine which pixels pass the current filters."""
    try:
        if not filter_params or not data_json:
            return set()
            
        # Load full data for filtering calculations
        data = pd.read_json(StringIO(data_json))
        
        # For custom filters mode, apply filtering directly here based on pixel-level data
        data_mode = filter_params.get('data_mode', 'all')
        
        if data_mode == 'custom':
            # Apply glacier fraction filtering if enabled
            if filter_params.get('use_glacier_fraction', False):
                min_fraction = filter_params.get('min_glacier_fraction', 0.7)
                
                # Get unique pixels with their glacier fractions
                if 'glacier_fraction' not in pixel_data.columns:
                    logger.error(f"glacier_fraction column not found in pixel_data. Available columns: {list(pixel_data.columns)}")
                    return set()
                    
                unique_pixels = pixel_data[['pixel_id', 'glacier_fraction']].drop_duplicates()
                logger.info(f"Unique pixels shape: {unique_pixels.shape}")
                logger.info(f"Glacier fraction values: {unique_pixels['glacier_fraction'].unique()}")
                
                # Filter pixels that pass the glacier fraction threshold
                passing_pixels = unique_pixels[unique_pixels['glacier_fraction'] >= min_fraction]
                
                logger.info(f"Glacier fraction filter: {len(passing_pixels)} out of {len(unique_pixels)} pixels pass (>= {min_fraction})")
                result_set = set(str(pid) for pid in passing_pixels['pixel_id'].unique())
                logger.info(f"Returning pixel IDs: {result_set}")
                return result_set
            
            # If no specific filters are enabled, return all pixels
            return set(str(pid) for pid in pixel_data['pixel_id'].unique())
        
        else:
            # For 'all', 'selected', 'best' modes, no filtering applied
            return set(str(pid) for pid in pixel_data['pixel_id'].unique())
            
    except Exception as e:
        logger.error(f"Error determining filtered pixels: {e}")
        import traceback
        traceback.print_exc()
        return set()

def test_functions():
    """Test the filtering and styling functions"""
    print("=== Testing Standalone Functions ===")
    
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
    
    print(f"\\nMock pixel data:")
    for _, row in pixel_data.iterrows():
        print(f"  Pixel {row['pixel_id']}: glacier_fraction={row['glacier_fraction']}")
    
    print(f"\\nFilter threshold: {filter_params['min_glacier_fraction']}")
    print(f"Expected: pixel '1' passes (0.8 >= 0.7), pixel '2' fails (0.5 < 0.7)")
    
    # Test determine_filtered_pixels
    print("\\n--- Testing determine_filtered_pixels ---")
    filtered_pixel_ids = determine_filtered_pixels(pixel_data, data_json, 'test_glacier', filter_params)
    
    print(f"Filtered pixel IDs: {filtered_pixel_ids}")
    print(f"Count: {len(filtered_pixel_ids)}")
    
    # Test marker styling for each pixel
    print("\\n--- Testing get_pixel_marker_style ---")
    selected_pixels = set()  # No pixels selected
    
    for _, pixel in pixel_data.iterrows():
        pixel_id = str(pixel['pixel_id'])
        is_selected = pixel_id in selected_pixels
        passes_filter = pixel_id in filtered_pixel_ids
        
        style = get_pixel_marker_style(pixel_id, is_selected, passes_filter, filter_params)
        
        print(f"Pixel {pixel_id}:")
        print(f"  glacier_fraction: {pixel['glacier_fraction']}")
        print(f"  is_selected: {is_selected}")
        print(f"  passes_filter: {passes_filter}")
        print(f"  style_color: {style['color']}")
        
        # Validate result
        expected_color = 'green' if passes_filter else 'grey'
        if style['color'] == expected_color:
            print(f"  ✅ Correct color: {style['color']}")
        else:
            print(f"  ❌ Wrong color: expected {expected_color}, got {style['color']}")
        print()

if __name__ == "__main__":
    test_functions()
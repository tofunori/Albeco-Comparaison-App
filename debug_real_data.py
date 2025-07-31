#!/usr/bin/env python3
"""
Debug script to test filtering logic with real Athabasca data
"""

import pandas as pd
import logging
from io import StringIO
from dashboard.core.data_manager import DashboardDataManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_pixel_marker_style(pixel_id, is_selected, passes_filter, filter_params=None):
    """Determine marker style based on pixel state."""
    # DEBUG: Log parameters for troubleshooting
    logger.info(f"Styling pixel {pixel_id}: is_selected={is_selected}, passes_filter={passes_filter}, filter_params={filter_params}")
    
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
                logger.info(f"Glacier fraction values: {unique_pixels['glacier_fraction'].unique()[:5]}...")
                
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

def test_real_data():
    """Test with actual Athabasca data"""
    print("=== Testing with Real Athabasca Data ===")
    
    # Load real data
    dm = DashboardDataManager()
    pixel_data = dm.get_pixel_locations('athabasca')
    full_data = dm.load_glacier_data('athabasca')
    
    print(f"\nPixel data shape: {pixel_data.shape}")
    print(f"Pixel data columns: {list(pixel_data.columns)}")
    print(f"Pixel IDs: {pixel_data['pixel_id'].unique()}")
    print(f"Glacier fractions: {pixel_data['glacier_fraction'].values}")
    
    # Convert to JSON like the real app does
    data_json = full_data.to_json(date_format='iso')
    
    # Test with threshold of 0.4 (both pixels should pass according to issue description)
    filter_params = {
        'data_mode': 'custom',
        'use_glacier_fraction': True,
        'min_glacier_fraction': 0.4
    }
    
    print(f"\nFilter threshold: {filter_params['min_glacier_fraction']}")
    print(f"Expected: both pixels should pass (0.969 >= 0.4 and 0.659 >= 0.4)")
    
    # Test determine_filtered_pixels
    print("\n--- Testing determine_filtered_pixels ---")
    filtered_pixel_ids = determine_filtered_pixels(pixel_data, data_json, 'athabasca', filter_params)
    
    print(f"Filtered pixel IDs: {filtered_pixel_ids}")
    print(f"Count: {len(filtered_pixel_ids)}")
    
    # Test marker styling for each pixel
    print("\n--- Testing get_pixel_marker_style ---")
    selected_pixels = []  # No pixels selected
    
    for _, pixel in pixel_data.iterrows():
        pixel_id = str(pixel['pixel_id'])
        is_selected = pixel_id in selected_pixels
        passes_filter = pixel_id in filtered_pixel_ids
        
        print(f"\nPixel {pixel_id}:")
        print(f"  glacier_fraction: {pixel['glacier_fraction']}")
        print(f"  is_selected: {is_selected}")
        print(f"  passes_filter: {passes_filter}")
        print(f"  pixel_id in filtered_pixel_ids: {pixel_id in filtered_pixel_ids}")
        print(f"  filtered_pixel_ids contains: {filtered_pixel_ids}")
        
        style = get_pixel_marker_style(pixel_id, is_selected, passes_filter, filter_params)
        
        print(f"  style_color: {style['color']}")
        
        # Validate result
        expected_color = 'green' if passes_filter else 'grey'
        if style['color'] == expected_color:
            print(f"  ✓ Correct color: {style['color']}")
        else:
            print(f"  ✗ Wrong color: expected {expected_color}, got {style['color']}")

if __name__ == "__main__":
    test_real_data()
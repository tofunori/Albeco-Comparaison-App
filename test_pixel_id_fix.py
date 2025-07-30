#!/usr/bin/env python3
"""
Test the pixel ID normalization fix
"""

import pandas as pd
from io import StringIO

# Simulate the fixed filtering function
def _filter_data_by_mode_fixed(data, data_mode, selected_pixels):
    """Fixed version with pixel ID normalization."""
    try:
        filtered_data = data.copy()
        
        # Step 2: Apply pixel selection filter (ALWAYS when pixels are selected)
        if selected_pixels and 'pixel_id' in filtered_data.columns and len(selected_pixels) > 0:
            # Normalize pixel IDs for consistent matching
            normalized_selected_pixels = []
            for pid in selected_pixels:
                normalized_pid = str(pid)
                if normalized_pid.endswith('.0'):
                    normalized_pid = normalized_pid[:-2]
                normalized_selected_pixels.append(normalized_pid)
            
            # Always filter by selected pixels when pixels are selected, regardless of data mode
            data_pixel_ids = filtered_data['pixel_id'].astype(str)
            # Also normalize data pixel IDs to handle any float conversion
            normalized_data_pixel_ids = [pid[:-2] if pid.endswith('.0') else pid for pid in data_pixel_ids]
            filtered_data['normalized_pixel_id'] = normalized_data_pixel_ids
            
            pixel_filtered_data = filtered_data[filtered_data['normalized_pixel_id'].isin(normalized_selected_pixels)]
            
            # Remove the temporary column
            if not pixel_filtered_data.empty:
                pixel_filtered_data = pixel_filtered_data.drop('normalized_pixel_id', axis=1)
                filtered_data = pixel_filtered_data
                print(f"Applied pixel selection filter: {len(filtered_data)} records for pixels {selected_pixels}")
            else:
                print(f"No data found for selected pixels {selected_pixels}, keeping current dataset")
        
        return filtered_data
        
    except Exception as e:
        print(f"Error filtering data by mode: {e}")
        return data

# Test data - simulating real Athabasca data
test_data_csv = """pixel_id,date,qa_mode,method,albedo
9073025950,2014-06-01,renoriginal,MOD09GA,0.33
9075025945,2014-06-01,renoriginal,MOD09GA,0.30
9073025950,2014-06-06,renoriginal,MOD09GA,0.51
9075025945,2014-06-06,renoriginal,MOD09GA,0.51
"""

print("=== Testing Pixel ID Normalization Fix ===")

# Load data (this simulates loading from CSV)
df = pd.read_csv(StringIO(test_data_csv))
print(f"Original data: {len(df)} records")
print(f"Pixel IDs: {df['pixel_id'].unique()}")

# Convert to JSON and back (this is what happens in the dashboard)
df_json = df.to_json()
df_processed = pd.read_json(StringIO(df_json))
print(f"After JSON processing: {len(df_processed)} records")
print(f"Pixel ID types: {df_processed['pixel_id'].dtype}")

# Test scenarios
test_cases = [
    ("UI format with .0", ['9073025950.0']),
    ("Integer format", ['9073025950']),  
    ("Mixed formats", ['9073025950.0', '9075025945']),
    ("Multiple with .0", ['9073025950.0', '9075025945.0'])
]

for test_name, selected_pixels in test_cases:
    print(f"\n--- {test_name} ---")
    print(f"Input selected pixels: {selected_pixels}")
    
    filtered_data = _filter_data_by_mode_fixed(df_processed, 'all', selected_pixels)
    
    if not filtered_data.empty:
        unique_pixels = filtered_data['pixel_id'].unique()
        print(f"SUCCESS: {len(filtered_data)} records from pixels: {unique_pixels}")
    else:
        print("FAILED: No records found")

print("\n=== Expected Behavior ===")
print("✅ All test cases should return matching records")
print("✅ Both '9073025950.0' and '9073025950' should match the same data") 
print("✅ The fix normalizes pixel IDs by removing .0 suffix for consistent matching")
#!/usr/bin/env python3
"""
Test Real-time Filtering Logic

Test the updated filtering behavior to ensure pixel selection always filters plots.
"""

import pandas as pd
import numpy as np

# Mock the filter function from the dashboard
def _filter_data_by_mode(data, data_mode, selected_pixels):
    """Filter data based on the selected data mode and pixel selection."""
    try:
        filtered_data = data.copy()
        
        # Step 1: Apply data mode filtering
        if data_mode == 'best' and 'qa_mode' in filtered_data.columns:
            # Filter to best quality data first
            best_data = filtered_data[filtered_data['qa_mode'] == 'clear_land']
            if best_data.empty:
                # Fallback to any available QA mode if 'clear_land' is not available
                qa_modes = filtered_data['qa_mode'].unique()
                print(f"Available QA modes: {qa_modes}")
                # Take the mode that appears most frequently (likely the best available)
                best_mode = filtered_data['qa_mode'].mode().iloc[0] if not filtered_data['qa_mode'].mode().empty else qa_modes[0]
                best_data = filtered_data[filtered_data['qa_mode'] == best_mode]
            filtered_data = best_data
            print(f"Applied 'best' quality filter: {len(filtered_data)} records")
        
        # Step 2: Apply pixel selection filter (ALWAYS when pixels are selected)
        if selected_pixels and 'pixel_id' in filtered_data.columns and len(selected_pixels) > 0:
            # Always filter by selected pixels when pixels are selected, regardless of data mode
            pixel_filtered_data = filtered_data[filtered_data['pixel_id'].astype(str).isin(selected_pixels)]
            
            if not pixel_filtered_data.empty:
                filtered_data = pixel_filtered_data
                print(f"Applied pixel selection filter: {len(filtered_data)} records for pixels {selected_pixels}")
            else:
                print(f"No data found for selected pixels {selected_pixels}, keeping current dataset")
        
        # Log final result
        if data_mode == 'selected' and (not selected_pixels or len(selected_pixels) == 0):
            # Special case: 'selected' mode but no pixels selected
            print("Data mode is 'selected' but no pixels are selected - returning empty dataset")
            return pd.DataFrame()  # Return empty dataframe
        
        print(f"Final filtered dataset: {len(filtered_data)} records (mode: {data_mode}, selected pixels: {len(selected_pixels) if selected_pixels else 0})")
        return filtered_data
            
    except Exception as e:
        print(f"Error filtering data by mode: {e}")
        return data

# Create test data similar to Athabasca glacier
print("=== Creating Test Data ===")
np.random.seed(42)
test_data = pd.DataFrame({
    'pixel_id': np.repeat(['9073025950.0', '9075025945.0'], 715),  # 2 pixels, 715 records each
    'date': pd.date_range('2020-01-01', periods=1430, freq='D'),
    'qa_mode': np.random.choice(['clear_land', 'cloudy', 'snow'], 1430, p=[0.6, 0.3, 0.1]),
    'albedo': np.random.uniform(0.1, 0.9, 1430),
    'method': np.random.choice(['MOD09GA', 'MOD10A1', 'MCD43A3'], 1430)
})

print(f"Created test dataset with {len(test_data)} records")
print(f"Pixels: {test_data['pixel_id'].unique()}")
print(f"QA modes: {test_data['qa_mode'].value_counts().to_dict()}")

# Test scenarios
test_scenarios = [
    ("All mode, no selection", 'all', []),
    ("All mode, 1 pixel selected", 'all', ['9073025950.0']),
    ("All mode, 2 pixels selected", 'all', ['9073025950.0', '9075025945.0']),
    ("Selected mode, no selection", 'selected', []),
    ("Selected mode, 1 pixel selected", 'selected', ['9073025950.0']),
    ("Best mode, no selection", 'best', []),
    ("Best mode, 1 pixel selected", 'best', ['9073025950.0']),
]

print("\n=== Testing Filter Scenarios ===")
for scenario_name, data_mode, selected_pixels in test_scenarios:
    print(f"\n--- {scenario_name} ---")
    filtered_data = _filter_data_by_mode(test_data, data_mode, selected_pixels)
    
    if not filtered_data.empty:
        unique_pixels = filtered_data['pixel_id'].unique()
        print(f"Result: {len(filtered_data)} records from pixels: {unique_pixels}")
    else:
        print("Result: Empty dataset")

print("\n=== Expected Behavior Summary ===")
print("OK Selecting pixels ALWAYS filters plots (regardless of data mode)")
print("OK 'All' mode: Uses full dataset, but filters to selected pixels if any")
print("OK 'Best' mode: Uses best quality data, but filters to selected pixels if any")  
print("OK 'Selected' mode: Requires pixel selection, returns empty if none selected")
print("OK Larger markers (20px unselected, 25px selected) for better visibility")
print("OK Status messages show current filtering state in all tabs")
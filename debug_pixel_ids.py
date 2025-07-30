#!/usr/bin/env python3
"""
Debug pixel ID format mismatch issue
"""

import pandas as pd
import json
from io import StringIO

# Test data similar to what we have
test_data = """pixel_id,date,qa_mode,method,albedo
9073025950,2014-06-01,renoriginal,MOD09GA,0.33
9075025945,2014-06-01,renoriginal,MOD09GA,0.30
9073025950,2014-06-06,renoriginal,MOD09GA,0.51
9075025945,2014-06-06,renoriginal,MOD09GA,0.51
"""

print("=== Testing Pixel ID Format Issue ===")

# Load data as CSV
df = pd.read_csv(StringIO(test_data))
print(f"Original data types: {df.dtypes}")
print(f"Original pixel_id values: {df['pixel_id'].unique()}")
print(f"Original pixel_id type: {type(df['pixel_id'].iloc[0])}")

# Convert to JSON (what happens in the dashboard)
df_json = df.to_json()
print(f"\nJSON representation: {df_json[:200]}...")

# Load back from JSON (what happens when dashboard reads stored data)
df_from_json = pd.read_json(StringIO(df_json))
print(f"\nAfter JSON roundtrip:")
print(f"Data types: {df_from_json.dtypes}")
print(f"Pixel_id values: {df_from_json['pixel_id'].unique()}")
print(f"Pixel_id type: {type(df_from_json['pixel_id'].iloc[0])}")

# Test string conversion (what happens in filtering)
print(f"\nString conversions:")
print(f"Original as string: {df['pixel_id'].astype(str).unique()}")
print(f"After JSON as string: {df_from_json['pixel_id'].astype(str).unique()}")

# Test filtering scenario
selected_pixels = ['9073025950.0']  # What comes from UI
print(f"\nFiltering test:")
print(f"Selected pixels: {selected_pixels}")
print(f"Matches in original data: {df[df['pixel_id'].astype(str).isin(selected_pixels)]}")
print(f"Matches in JSON data: {df_from_json[df_from_json['pixel_id'].astype(str).isin(selected_pixels)]}")

# Test with integer matching
selected_pixels_int = ['9073025950']  # Without decimal
print(f"\nMatches with integer format: {df_from_json[df_from_json['pixel_id'].astype(str).isin(selected_pixels_int)]}")

print("\n=== ROOT CAUSE IDENTIFIED ===")
print("The issue is that:")
print("1. CSV has integer pixel IDs: 9073025950")
print("2. JSON conversion turns them into floats: 9073025950.0") 
print("3. UI selection extracts: '9073025950.0'")
print("4. But filtering might be inconsistent with string conversions")
#!/usr/bin/env python3
"""
Simple test for direct CSV loading
"""

import pandas as pd
from pathlib import Path

# Test direct CSV loading
modis_file = "data/modis/athabasca/Athabasca_Terra_Aqua_MultiProduct_2014-01-01_to_2021-01-01.csv"
aws_file = "data/aws/iceAWS_Atha_albedo_daily_20152020_filled_clean.csv"

print("Testing direct CSV loading...")

# Load MODIS data
if Path(modis_file).exists():
    modis_data = pd.read_csv(modis_file)
    print(f"MODIS data loaded: {len(modis_data)} records")
    print(f"Columns: {list(modis_data.columns)}")
    print(f"Methods: {modis_data['method'].unique() if 'method' in modis_data.columns else 'No method column'}")
    print(f"Date range: {modis_data['date'].min()} to {modis_data['date'].max() if 'date' in modis_data.columns else 'No date column'}")
else:
    print(f"MODIS file not found: {modis_file}")

print()

# Load AWS data
if Path(aws_file).exists():
    aws_data = pd.read_csv(aws_file)
    print(f"AWS data loaded: {len(aws_data)} records")
    print(f"Columns: {list(aws_data.columns)}")
    print(f"First few rows:")
    print(aws_data.head())
else:
    print(f"AWS file not found: {aws_file}")

print("\nDirect CSV loading test completed!")
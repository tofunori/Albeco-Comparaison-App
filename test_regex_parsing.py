#!/usr/bin/env python3
"""
Test the regex-based pixel ID parsing
"""

import re

# Test the actual format from the logs
test_ids = [
    '{"pixel_id":"9073025950.0","type":"pixel-toggle-btn"}.n_clicks',
    '{"pixel_id":"9075025945.0","type":"pixel-toggle-btn"}.n_clicks',
    '{"pixel_id":"1","type":"pixel-toggle-btn"}.n_clicks'
]

print("=== Testing Regex Pixel ID Extraction ===")

for test_id in test_ids:
    print(f"\nTesting: {test_id}")
    
    # Use the regex pattern from the fix
    pixel_id_match = re.search(r'"pixel_id":"([^"]+)"', test_id)
    
    if pixel_id_match:
        pixel_id = pixel_id_match.group(1)
        print(f"SUCCESS: Extracted pixel_id = {pixel_id}")
    else:
        print("FAILED: Could not extract pixel_id")
        
        # Test fallback
        numbers = re.findall(r'\d+\.?\d*', test_id)
        if numbers:
            pixel_id = numbers[0]
            print(f"FALLBACK: Extracted pixel_id = {pixel_id}")

print("\n=== Summary ===")
print("The regex approach should now work correctly!")
print("Pattern: '\"pixel_id\":\"([^\"]+)\"' extracts the value between quotes")
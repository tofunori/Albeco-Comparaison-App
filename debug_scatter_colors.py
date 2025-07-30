#!/usr/bin/env python3
"""
Debug scatter plot color assignment issue
"""

import plotly.graph_objects as go
import pandas as pd
import numpy as np
from io import StringIO

# Test data with different methods
test_data = """method,albedo,aws_albedo
MOD09GA,0.25,0.30
MOD09GA,0.35,0.40
MYD09GA,0.45,0.50
MYD09GA,0.55,0.60
mod10a1,0.65,0.70
mod10a1,0.75,0.80
myd10a1,0.30,0.35
mcd43a3,0.40,0.45
"""

print("=== Debugging Scatter Plot Colors ===")

# Load test data
df = pd.read_csv(StringIO(test_data))
print(f"Test data: {len(df)} records")
print(f"Methods: {df['method'].unique()}")

# Color scheme matching the dashboard
colors = {
    'MOD09GA': '#0066CC',    # Bright Blue
    'MYD09GA': '#FF6600',    # Bright Orange  
    'mod10a1': '#00AA00',    # Bright Green
    'myd10a1': '#CC0000',    # Bright Red
    'mcd43a3': '#9900CC',    # Bright Purple
}

# Create scatter plot with the same logic as the dashboard
fig = go.Figure()

methods_in_data = df['method'].unique()
print(f"\nCreating traces for methods: {methods_in_data}")

for method in methods_in_data:
    method_data = df[df['method'] == method]
    
    if method_data.empty:
        continue
    
    x_vals = method_data['aws_albedo']
    y_vals = method_data['albedo']
    
    # Get color for this method
    method_color = colors.get(method, '#1f77b4')
    print(f"Method: {method}, Color: {method_color}, Points: {len(method_data)}")
    
    # Create scatter trace - EXACTLY as in the dashboard
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=y_vals,
        mode='markers',
        name=method,
        marker=dict(
            color=method_color,
            size=8,
            opacity=0.8
        ),
        hovertemplate=f'<b>{method}</b><br>' +
                    'AWS Albedo: %{x:.3f}<br>' +
                    'MODIS Albedo: %{y:.3f}<br>' +
                    '<extra></extra>'
    ))

# Update layout
fig.update_layout(
    title="Debug: MODIS vs AWS Albedo Comparison",
    xaxis_title='AWS Albedo',
    yaxis_title='MODIS Albedo',
    width=800,
    height=600,
    showlegend=True,
    hovermode='closest'
)

# Save the debug plot
fig.write_html("debug_scatter_colors.html")
print(f"\nDebug plot saved as: debug_scatter_colors.html")

# Check the actual trace data
print(f"\nTrace details:")
for i, trace in enumerate(fig.data):
    print(f"Trace {i}: {trace.name}, Color: {trace.marker.color}, Points: {len(trace.x)}")

print("\n=== Next steps ===")
print("1. Open debug_scatter_colors.html in browser")
print("2. Check if colors are working in this simple test")
print("3. If colors work here, the issue is in the dashboard data processing")
print("4. If colors don't work here, the issue is in the Plotly trace creation")
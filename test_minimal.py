#!/usr/bin/env python3
"""
Minimal Dashboard Test

Test basic Dash functionality without complex components.
"""

import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# Create minimal app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Simple layout
app.layout = html.Div([
    html.H1("Dashboard Test", className="text-center"),
    html.P("If you can see this, Dash is working!", className="text-center"),
    
    dcc.Dropdown(
        id='test-dropdown',
        options=[
            {'label': 'Option 1', 'value': '1'},
            {'label': 'Option 2', 'value': '2'}
        ],
        value='1'
    ),
    
    html.Div(id='test-output'),
    
    dcc.Graph(
        id='test-graph',
        figure={
            'data': [{'x': [1, 2, 3], 'y': [4, 5, 6], 'type': 'scatter'}],
            'layout': {'title': 'Test Plot'}
        }
    )
])

@app.callback(
    Output('test-output', 'children'),
    Input('test-dropdown', 'value')
)
def update_output(value):
    return f"You selected: {value}"

if __name__ == '__main__':
    print("Starting minimal test dashboard...")
    app.run_server(debug=True, host='127.0.0.1', port=8052)
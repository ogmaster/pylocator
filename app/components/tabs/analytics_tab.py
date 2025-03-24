"""
Analytics tab component.
"""
import dash_bootstrap_components as dbc
from dash import dcc, html

def create_analytics_tab():
    """Creates the analytics tab layout."""
    return dbc.Tab(label="Analytics", children=[
        dbc.Row([
            dbc.Col([
                html.H4("Object Activity"),
                dcc.Graph(id='activity-heatmap', style={'height': '70vh'}),
                dbc.Row([
                    dbc.Col([
                        html.Label("Time Range:"),
                        dcc.Dropdown(
                            id='analytics-timeframe',
                            options=[
                                {'label': 'Past Hour', 'value': '1h'},
                                {'label': 'Past 6 Hours', 'value': '6h'},
                                {'label': 'Past Day', 'value': '24h'},
                                {'label': 'Past Week', 'value': '7d'},
                            ],
                            value='1h'
                        ),
                    ], width=3),
                    dbc.Col([
                        html.Label("Resolution:"),
                        dcc.Dropdown(
                            id='heatmap-resolution',
                            options=[
                                {'label': '10x10 Grid', 'value': '10'},
                                {'label': '20x20 Grid', 'value': '20'},
                                {'label': '50x50 Grid', 'value': '50'},
                            ],
                            value='20'
                        ),
                    ], width=3),
                    dbc.Col([
                        html.Button("Generate Heatmap", id="generate-heatmap-button", className="btn btn-primary mt-4"),
                    ], width=2),
                ]),
            ], width=12),
        ]),
    ]) 
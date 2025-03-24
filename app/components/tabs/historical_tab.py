"""
Historical data tab component.
"""
import dash_bootstrap_components as dbc
from dash import dcc, html
from datetime import datetime, timedelta

def create_historical_tab():
    """Creates the historical data tab layout."""
    return dbc.Tab(label="Historical Data", children=[
        dbc.Row([
            dbc.Col([
                html.H4("Object History"),
                dbc.Row([
                    dbc.Col([
                        html.Label("Object ID:"),
                        dcc.Dropdown(id='history-object-selector', placeholder="Select an object"),
                    ], width=3),
                    dbc.Col([
                        html.Label("Time Range:"),
                        dcc.DatePickerRange(
                            id='history-date-range',
                            start_date=(datetime.now() - timedelta(hours=1)).date(),
                            end_date=datetime.now().date(),
                            display_format='YYYY-MM-DD'
                        ),
                    ], width=4),
                    dbc.Col([
                        html.Label("Time Resolution:"),
                        dcc.Dropdown(
                            id='history-resolution',
                            options=[
                                {'label': 'Raw Data', 'value': 'raw'},
                                {'label': '1 second', 'value': '1s'},
                                {'label': '10 seconds', 'value': '10s'},
                                {'label': '1 minute', 'value': '1m'},
                                {'label': '10 minutes', 'value': '10m'},
                            ],
                            value='raw'
                        ),
                    ], width=3),
                    dbc.Col([
                        html.Button("Load Data", id="load-history-button", className="btn btn-primary mt-4"),
                    ], width=2),
                ]),
                dcc.Graph(id='history-plot', style={'height': '60vh'}),
            ], width=12),
        ]),
    ]) 
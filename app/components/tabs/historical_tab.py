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
                html.H4("Object Movement History"),
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
                html.Br(),
                
                # Visualization type selector
                dbc.Row([
                    dbc.Col([
                        html.Label("Visualization Options:"),
                        dbc.RadioItems(
                            id="history-viz-type",
                            options=[
                                {"label": "Movement Trail", "value": "trail"},
                                {"label": "Heatmap", "value": "heatmap"},
                                {"label": "Position vs Time", "value": "position_time"}
                            ],
                            value="trail",
                            inline=True
                        ),
                    ], width=12)
                ]),
                html.Br(),
                
                # Make the graph take up the full width and taller
                dcc.Graph(id='history-plot', style={'height': '70vh'}),
                
                # Add animation playback controls below the graph
                dbc.Row([
                    dbc.Col([
                        html.Div(id='animation-controls', children=[
                            html.Label("Movement Playback:"),
                            html.Div([
                                dbc.Button("Play", id="play-button", color="success", size="sm", className="me-2"),
                                dbc.Button("Pause", id="pause-button", color="primary", size="sm", className="me-2"),
                                dbc.Button("Reset", id="reset-button", color="secondary", size="sm", className="me-2"),
                                html.Span("Speed:"),
                                dbc.Select(
                                    id="playback-speed",
                                    options=[
                                        {"label": "0.5x", "value": "0.5"},
                                        {"label": "1x", "value": "1"},
                                        {"label": "2x", "value": "2"},
                                        {"label": "5x", "value": "5"}
                                    ],
                                    value="1",
                                    style={"width": "80px", "display": "inline-block", "margin": "0 10px"}
                                )
                            ], style={"margin-bottom": "10px"}),
                            dcc.Slider(
                                id='movement-slider',
                                min=0,
                                max=100,
                                step=0.25,
                                value=100,
                                marks=None,
                                tooltip={"placement": "bottom", "always_visible": True}
                            ),
                            dcc.Interval(
                                id='interval-animation',
                                interval=50,  # 50ms = 0.05 seconds (faster for smoother animation)
                                n_intervals=0,
                                disabled=True
                            ),
                        ], style={"padding": "10px", "background": "#f8f9fa", "border-radius": "5px"})
                    ], width=12)
                ], className="mt-3"),
            ], width=12),  # Make the column take up full width
        ]),
    ]) 
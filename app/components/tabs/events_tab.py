"""
Event browser tab component.
"""
import dash_bootstrap_components as dbc
from dash import dcc, html
from datetime import datetime, timedelta

def create_events_tab():
    """Creates the event browser tab layout."""
    return dbc.Tab(label="Event Browser", children=[
        dbc.Row([
            dbc.Col([
                html.H4("System Events"),
                dbc.Row([
                    dbc.Col([
                        html.Label("Event Type:"),
                        dcc.Dropdown(
                            id='event-type-filter',
                            options=[
                                {'label': 'All Events', 'value': 'all'},
                                {'label': 'Appearances', 'value': 'appearance'},
                                {'label': 'Disappearances', 'value': 'disappearance'},
                            ],
                            value='all'
                        ),
                    ], width=3),
                    dbc.Col([
                        html.Label("Time Range:"),
                        dcc.DatePickerRange(
                            id='event-date-range',
                            start_date=(datetime.now() - timedelta(days=1)).date(),
                            end_date=datetime.now().date(),
                            display_format='YYYY-MM-DD'
                        ),
                    ], width=4),
                    dbc.Col([
                        html.Button("Load Events", id="load-events-button", className="btn btn-primary mt-4"),
                    ], width=2),
                ]),
                html.Div(id="events-table-container"),
            ], width=12),
        ]),
    ]) 
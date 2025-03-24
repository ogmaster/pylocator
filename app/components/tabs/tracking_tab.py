"""
Real-time tracking tab layout.
"""
import dash_bootstrap_components as dbc
from dash import dcc, html


def create_config_panel():
    """Creates the configuration panel layout."""
    return html.Div([
        html.Label("Update Frequency (updates/sec):"),
        dcc.Slider(
            id='update-frequency',
            min=1, max=10, step=1, value=3,
            marks={i: f'{i}' for i in range(1, 11)},
        ),
        html.Br(),
        
        html.Label("Object Timeout (seconds):"),
        dcc.Input(
            id='object-timeout',
            type='number',
            value=5,
            min=1,
            max=60,
            step=1
        ),
        html.Br(),
        
        dbc.Checklist(
            id='show-trails',
            options=[{'label': 'Show Trails', 'value': 'show'}],
            value=[],
            switch=True,
        ),
        html.Label("Trail Length:"),
        dcc.Slider(
            id='trail-length',
            min=5,
            max=50,
            step=5,
            value=20,
            marks={i: f'{i}' for i in range(5, 51, 10)},
            disabled=True
        ),
        html.Br(),
        
        dbc.Checklist(
        id='show-zones',
        options=[{'label': 'Show Zones', 'value': 'show'}],
        value=['show'],  # Enabled by default
        switch=True,
        ),
        html.Br(),
        
        html.H5("Plot Boundaries"),
        dbc.Row([
            dbc.Col([
                html.Label("Min X:"),
                dcc.Input(id='min-x', type='number', value=0, style={'width': '100%'})
            ], width=6),
            dbc.Col([
                html.Label("Min Y:"),
                dcc.Input(id='min-y', type='number', value=0, style={'width': '100%'})
            ], width=6),
        ]),
        dbc.Row([
            dbc.Col([
                html.Label("Max X:"),
                dcc.Input(id='max-x', type='number', value=100, style={'width': '100%'})
            ], width=6),
            dbc.Col([
                html.Label("Max Y:"),
                dcc.Input(id='max-y', type='number', value=100, style={'width': '100%'})
            ], width=6),
        ]),
        html.Br(),
        
        html.H5("Background Image"),
        dcc.Upload(
            id='upload-image',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select a Floor Plan')
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px 0'
            },
        ),
        html.Div(id='upload-output'),
        
        # Store components for state
        dcc.Store(id='background-image-store'),
        dcc.Store(id='selected-object', data=None),
    ])


def create_tracking_tab():
    """Creates the real-time tracking tab layout."""
    return dbc.Tab(label="Real-time Tracking", children=[
        dbc.Row([
            dbc.Col([
                # Main plot
                dcc.Graph(
                    id='tracking-plot',
                    style={'height': '70vh'},
                    config={'displayModeBar': True}
                ),
                # Update interval
                dcc.Interval(
                    id='interval-component',
                    interval=1000/3 * 1000,  # default 3 updates per second
                    n_intervals=0
                ),
            ], width=9),
            
            dbc.Col([
                # Configuration panel
                html.H4("Configuration"),
                create_config_panel()
            ], width=3),
        ]),
        
        dbc.Row([
            dbc.Col([
                html.H4("Object Details"),
                html.Div(id='object-details')
            ], width=12)
        ]),
    ]) 
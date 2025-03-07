import os
import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import paho.mqtt.client as mqtt
import json
import time
import threading
import base64
import io
from PIL import Image
import numpy as np

# Object store class to manage tracked objects
class ObjectStore:
    def __init__(self, timeout=5):
        self.objects = {}  # {id: {x, y, last_update, history: [(x,y,t)], ...}}
        self.timeout = timeout  # seconds to keep objects visible after disappearing
        self._lock = threading.Lock()
    
    def update_object(self, obj_id, x, y):
        with self._lock:
            now = time.time()
            if obj_id not in self.objects:
                self.objects[obj_id] = {
                    'x': x, 'y': y, 'last_update': now,
                    'history': [(x, y, now)]
                }
            else:
                self.objects[obj_id]['x'] = x
                self.objects[obj_id]['y'] = y
                self.objects[obj_id]['last_update'] = now
                self.objects[obj_id]['history'].append((x, y, now))
                # Limit history size
                if len(self.objects[obj_id]['history']) > 100:
                    self.objects[obj_id]['history'] = self.objects[obj_id]['history'][-100:]
    
    def get_active_objects(self):
        with self._lock:
            now = time.time()
            active = {}
            for obj_id, data in self.objects.items():
                if now - data['last_update'] <= self.timeout:
                    active[obj_id] = data
            return active
    
    def get_object_trails(self, max_trail_points=20):
        trails = {}
        with self._lock:
            now = time.time()
            for obj_id, data in self.objects.items():
                if now - data['last_update'] <= self.timeout:
                    history = data['history'][-max_trail_points:]
                    trails[obj_id] = {
                        'x': [h[0] for h in history],
                        'y': [h[1] for h in history]
                    }
        return trails

# MQTT Client
class MQTTClient:
    def __init__(self, broker="localhost", port=1883, object_store=None):
        self.client = mqtt.Client()
        self.broker = broker
        self.port = port
        self.object_store = object_store
        
        # Set up callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
    def connect(self):
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()
        
    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected with result code {rc}")
        # Subscribe to topics
        client.subscribe("objects/tracking/position")
        
    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            if msg.topic == "objects/tracking/position":
                obj_id = payload.get('id')
                x = payload.get('x')
                y = payload.get('y')
                if obj_id and x is not None and y is not None:
                    self.object_store.update_object(obj_id, x, y)
        except Exception as e:
            print(f"Error processing message: {e}")
            
    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

# Initialize global objects
object_store = ObjectStore(timeout=5)
mqtt_client = MQTTClient(
    broker=os.environ.get("MQTT_BROKER", "localhost"),
    port=1883,
    object_store=object_store
)

# Start MQTT client
mqtt_client.connect()

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# App layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Real-time Object Tracking"),
            html.Hr(),
        ], width=12)
    ]),
    
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
                interval=1000/3 * 1000,  # default 3 updates per second in milliseconds
                n_intervals=0
            ),
        ], width=9),
        
        dbc.Col([
            # Configuration panel
            html.H4("Configuration"),
            html.Label("Update Frequency (updates/sec):"),
            dcc.Slider(
                id='update-frequency',
                min=1,
                max=10,
                step=1,
                value=3,
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
            
        ], width=3),
    ]),
    
    dbc.Row([
        dbc.Col([
            html.H4("Object Details"),
            html.Div(id='object-details')
        ], width=12)
    ]),
    
], fluid=True)

# Callbacks
@callback(
    Output('interval-component', 'interval'),
    Input('update-frequency', 'value')
)
def update_interval(value):
    # Convert updates per second to milliseconds
    return (1000 / value)

@callback(
    Output('object-timeout', 'value'),
    Input('object-timeout', 'value')
)
def update_timeout(value):
    object_store.timeout = value
    return value

@callback(
    Output('trail-length', 'disabled'),
    Input('show-trails', 'value')
)
def toggle_trail_length(show_trails):
    return 'show' not in show_trails

@callback(
    Output('tracking-plot', 'figure'),
    Input('interval-component', 'n_intervals'),
    Input('show-trails', 'value'),
    Input('trail-length', 'value'),
    Input('min-x', 'value'),
    Input('min-y', 'value'),
    Input('max-x', 'value'),
    Input('max-y', 'value'),
    Input('background-image-store', 'data'),
)
def update_graph(n, show_trails, trail_length, min_x, min_y, max_x, max_y, bg_image):
    # Create base figure
    fig = go.Figure()
    
    # Add background image if available
    if bg_image:
        # Add image as layout
        fig.add_layout_image(
            dict(
                source=bg_image,
                xref="x",
                yref="y",
                x=min_x,
                y=max_y,
                sizex=max_x - min_x,
                sizey=max_y - min_y,
                sizing="stretch",
                opacity=0.5,
                layer="below"
            )
        )
    
    # Get active objects
    active_objects = object_store.get_active_objects()
    
    # Plot points for each object
    x_vals = []
    y_vals = []
    ids = []
    
    for obj_id, data in active_objects.items():
        x_vals.append(data['x'])
        y_vals.append(data['y'])
        ids.append(obj_id)
    
    # Add scatter plot for current positions
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=y_vals,
        mode='markers',
        marker=dict(size=10),
        text=ids,
        name='Objects',
        customdata=ids,
        hoverinfo='text'
    ))
    
    # Add trails if enabled
    if 'show' in show_trails:
        trails = object_store.get_object_trails(max_trail_points=trail_length)
        
        for obj_id, trail in trails.items():
            if len(trail['x']) > 1:  # Only add trails with more than one point
                fig.add_trace(go.Scatter(
                    x=trail['x'],
                    y=trail['y'],
                    mode='lines',
                    line=dict(width=1, dash='dot'),
                    name=f"Trail-{obj_id}",
                    showlegend=False,
                    hoverinfo='none'
                ))
    
    # Update layout with boundary settings
    fig.update_layout(
        xaxis=dict(range=[min_x, max_x]),
        yaxis=dict(range=[min_y, max_y]),
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False,
        uirevision='constant',  # keeps zoom level consistent
    )
    
    return fig

@callback(
    [Output('background-image-store', 'data'),
     Output('upload-output', 'children')],
    Input('upload-image', 'contents'),
    State('upload-image', 'filename')
)
def update_background(contents, filename):
    if contents is not None:
        try:
            # Process the uploaded image
            content_type, content_string = contents.split(',')
            
            # Return the image data and success message
            return contents, html.Div(f"Uploaded: {filename}")
        except Exception as e:
            return None, html.Div(f"Error processing file: {str(e)}")
    return dash.no_update, dash.no_update

@callback(
    Output('selected-object', 'data'),
    Input('tracking-plot', 'clickData')
)
def update_selected_object(clickData):
    if clickData:
        # Get the object ID from the clicked point
        point = clickData['points'][0]
        if 'customdata' in point:
            return point['customdata']
    return None

@callback(
    Output('object-details', 'children'),
    Input('selected-object', 'data'),
    Input('interval-component', 'n_intervals')
)
def display_object_details(obj_id, n):
    if not obj_id:
        return html.Div("Click on an object to see details")
    
    active_objects = object_store.get_active_objects()
    if obj_id in active_objects:
        obj = active_objects[obj_id]
        return html.Div([
            html.H5(f"Object ID: {obj_id}"),
            html.P(f"Current Position: ({obj['x']:.2f}, {obj['y']:.2f})"),
            html.P(f"Last Update: {time.strftime('%H:%M:%S', time.localtime(obj['last_update']))}"),
            html.P(f"History Points: {len(obj['history'])}")
        ])
    else:
        return html.Div(f"Object {obj_id} is no longer active")

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0')
"""
Distributed Object Tracking System - Main Application
"""
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc

# Import configuration
from config import (
    API_SERVICE_URL, MQTT_BROKER, MQTT_PORT, 
    MQTT_TOPIC, DEFAULT_TIMEOUT
)

# Import services
from services import ObjectStore, MQTTClient

# Import tab layouts
from components.tabs.tracking_tab import create_tracking_tab
from components.tabs.historical_tab import create_historical_tab
from components.tabs.events_tab import create_events_tab
from components.tabs.analytics_tab import create_analytics_tab
from components.tabs.zones_tab import create_zone_management_tab

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Initialize global objects
object_store = ObjectStore(timeout=DEFAULT_TIMEOUT)
mqtt_client = MQTTClient(
    broker=MQTT_BROKER, 
    port=MQTT_PORT, 
    object_store=object_store,
    topic=MQTT_TOPIC
)

# Import callbacks and set the shared variables
import callbacks.tracking_callbacks
callbacks.tracking_callbacks.object_store = object_store
callbacks.tracking_callbacks.api_service_url = API_SERVICE_URL

import callbacks.historical_callbacks
callbacks.historical_callbacks.object_store = object_store
callbacks.historical_callbacks.api_service_url = API_SERVICE_URL

import callbacks.events_callbacks
callbacks.events_callbacks.api_service_url = API_SERVICE_URL

import callbacks.analytics_callbacks
callbacks.analytics_callbacks.object_store = object_store
callbacks.analytics_callbacks.api_service_url = API_SERVICE_URL

import callbacks.zones_callbacks
callbacks.zones_callbacks.api_service_url = API_SERVICE_URL

# Start MQTT client
mqtt_client.connect()

# App layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("Distributed Object Tracking System"),
            html.Hr(),
        ], width=12)
    ]),
    
    # Main tabs
    dbc.Tabs([
        create_tracking_tab(),
        create_historical_tab(),
        create_events_tab(),
        create_analytics_tab(),
        create_zone_management_tab()
    ]),
], fluid=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
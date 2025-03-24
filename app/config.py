"""
Configuration settings for the Distributed Object Tracking System.
"""
import os

# API and MQTT settings
API_SERVICE_URL = os.environ.get("API_SERVICE_URL", "http://localhost:5001")
MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = 1883
MQTT_TOPIC = "objects/tracking/position"

# Default configuration
DEFAULT_TIMEOUT = 5  # seconds
DEFAULT_UPDATE_FREQUENCY = 3  # updates per second
MAX_HISTORY_POINTS = 100 
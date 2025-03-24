"""
MQTT client service for receiving real-time object tracking data.
"""
import json
import time
import paho.mqtt.client as mqtt


class MQTTClient:
    """Handles MQTT communication for real-time object tracking updates."""
    
    def __init__(self, broker, port=1883, object_store=None, topic=None):
        """Initialize MQTT client.
        
        Args:
            broker: MQTT broker address
            port: MQTT broker port
            object_store: ObjectStore instance for updating object positions
            topic: MQTT topic to subscribe to
        """
        self.client = mqtt.Client()
        self.broker = broker
        self.port = port
        self.object_store = object_store
        self.topic = topic
        
        # Set up callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
    def connect(self):
        """Connect to MQTT broker with retry logic."""
        retry_count = 0
        max_retries = 10
        
        while retry_count < max_retries:
            try:
                self.client.connect(self.broker, self.port, 60)
                self.client.loop_start()
                print(f"Connected to MQTT broker at {self.broker}")
                return True
            except Exception as e:
                retry_count += 1
                print(f"Connection attempt {retry_count} failed: {e}")
                time.sleep(2)
        
        print("Failed to connect to MQTT broker after multiple attempts")
        return False
        
    def on_connect(self, client, userdata, flags, rc):
        """Callback for when client connects to broker."""
        print(f"Connected with result code {rc}")
        # Subscribe to topics
        client.subscribe(self.topic)
        
    def on_message(self, client, userdata, msg):
        """Callback for when a message is received."""
        try:
            payload = json.loads(msg.payload.decode())
            if msg.topic == self.topic:
                obj_id = payload.get('id')
                x = payload.get('x')
                y = payload.get('y')
                if obj_id and x is not None and y is not None:
                    self.object_store.update_object(obj_id, x, y)
        except Exception as e:
            print(f"Error processing message: {e}")
            
    def disconnect(self):
        """Disconnect from MQTT broker."""
        self.client.loop_stop()
        self.client.disconnect() 
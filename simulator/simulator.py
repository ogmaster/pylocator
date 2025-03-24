import paho.mqtt.client as mqtt
import json
import time
import random
import math
import os

# Configuration
broker_address = os.environ.get("MQTT_BROKER", "localhost")
broker_port = 1883
topic = "objects/tracking/position"
object_count = 10
update_interval = 1/10  # seconds (10 updates per second)

print(f"Connecting to MQTT broker at {broker_address}:{broker_port}")

# Connect to MQTT
client = mqtt.Client()

# Add connection retry logic
connected = False
retry_count = 0
max_retries = 10

while not connected and retry_count < max_retries:
    try:
        client.connect(broker_address, broker_port)
        connected = True
        print(f"Connected to MQTT broker at {broker_address}")
    except Exception as e:
        retry_count += 1
        print(f"Connection attempt {retry_count} failed: {e}")
        time.sleep(3)

if not connected:
    print("Failed to connect to MQTT broker after multiple attempts")
    exit(1)

# Generate some moving objects
objects = {}
for i in range(object_count):
    objects[f"obj_{i}"] = {
        "x": random.uniform(0, 100),
        "y": random.uniform(0, 100),
        "speed": random.uniform(0.5, 2),
        "direction": random.uniform(0, 2 * math.pi)
    }

try:
    while True:
        # Update object positions
        for obj_id, obj in objects.items():
            # Move object
            obj["x"] += math.cos(obj["direction"]) * obj["speed"]
            obj["y"] += math.sin(obj["direction"]) * obj["speed"]
            
            # Bounce off walls
            if obj["x"] < 0 or obj["x"] > 100:
                obj["direction"] = math.pi - obj["direction"]
                obj["x"] = max(0, min(100, obj["x"]))
                
            if obj["y"] < 0 or obj["y"] > 100:
                obj["direction"] = -obj["direction"]
                obj["y"] = max(0, min(100, obj["y"]))
            
            # Occasionally change direction
            if random.random() < 0.05:
                obj["direction"] += random.uniform(-0.5, 0.5)
            
            # Send position update
            message = {
                "id": obj_id,
                "x": obj["x"],
                "y": obj["y"]
            }
            client.publish(topic, json.dumps(message))
            
        time.sleep(update_interval)
except KeyboardInterrupt:
    print("Simulator stopped")
    client.disconnect()
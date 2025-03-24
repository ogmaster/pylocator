import os
import json
import time
from paho.mqtt import client as mqtt_client
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from pymongo import MongoClient

# Environment variables
mqtt_broker = os.environ.get("MQTT_BROKER", "localhost")
mqtt_port = 1883
mqtt_topic = "objects/tracking/position"

influxdb_url = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
influxdb_token = os.environ.get("INFLUXDB_TOKEN", "my-token")
influxdb_org = os.environ.get("INFLUXDB_ORG", "tracking")
influxdb_bucket = os.environ.get("INFLUXDB_BUCKET", "object_positions")

mongodb_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")

# Connect to InfluxDB
influx_client = InfluxDBClient(url=influxdb_url, token=influxdb_token, org=influxdb_org)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

# Connect to MongoDB
mongo_client = MongoClient(mongodb_uri)
db = mongo_client['object_tracking']
objects_collection = db['objects']
events_collection = db['events']


class ZoneProcessor:
    def __init__(self, db_client):
        self.db = db_client['object_tracking']
        self.zones_collection = self.db['zones']
        self.zone_events_collection = self.db['zone_events']
        self.object_zones = {}  # tracks which objects are in which zones
        self.zones = self._load_zones()
        
    def _load_zones(self):
        """Load all active zones from the database"""
        zones = {}
        for zone in self.zones_collection.find({"active": True}):
            zones[zone["_id"]] = zone
        return zones
        
    def reload_zones(self):
        """Reload zones from the database (called periodically)"""
        self.zones = self._load_zones()
        
    def is_point_in_polygon(self, point, polygon):
        """Check if a point is inside a polygon using ray casting algorithm"""
        x, y = point
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]['x'], polygon[0]['y']
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]['x'], polygon[i % n]['y']
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
        
    def process_position(self, obj_id, x, y, timestamp):
        """Process an object position and generate zone events if needed"""
        # Get current zones for this object
        current_zones = self.object_zones.get(obj_id, set())
        new_zones = set()
        
        # Check each zone
        for zone_id, zone in self.zones.items():
            polygon = zone['polygon']
            if self.is_point_in_polygon((x, y), polygon):
                new_zones.add(zone_id)
                
                # Check if this is a zone entry
                if zone_id not in current_zones:
                    # Generate zone entry event
                    self.zone_events_collection.insert_one({
                        "object_id": obj_id,
                        "zone_id": zone_id,
                        "event_type": "enter",
                        "timestamp": timestamp,
                        "metadata": {
                            "entry_point": {"x": x, "y": y}
                        }
                    })
                    print(f"Object {obj_id} entered zone {zone['name']}")
        
        # Check for zone exits
        for zone_id in current_zones:
            if zone_id not in new_zones:
                # Generate zone exit event
                self.zone_events_collection.insert_one({
                    "object_id": obj_id,
                    "zone_id": zone_id,
                    "event_type": "exit",
                    "timestamp": timestamp,
                    "metadata": {
                        "exit_point": {"x": x, "y": y}
                    }
                })
                
                # Update duration in the entry event
                last_entry = self.zone_events_collection.find_one({
                    "object_id": obj_id,
                    "zone_id": zone_id,
                    "event_type": "enter"
                }, sort=[("timestamp", -1)])
                
                if last_entry:
                    entry_time = last_entry["timestamp"]
                    duration = timestamp - entry_time
                    self.zone_events_collection.update_one(
                        {"_id": last_entry["_id"]},
                        {"$set": {"duration": duration}}
                    )
                
                print(f"Object {obj_id} exited zone {self.zones[zone_id]['name']}")
        
        # Update the object's zones
        self.object_zones[obj_id] = new_zones


zone_processor = ZoneProcessor(mongo_client)
# MQTT Connection
def connect_mqtt():

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
            client.subscribe(mqtt_topic)
        else:
            print(f"Failed to connect, return code {rc}")
    
    client = mqtt_client.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Add connection retry logic
    retry_count = 0
    while retry_count < 10:
        try:
            client.connect(mqtt_broker, mqtt_port)
            break
        except Exception as e:
            print(f"Connection attempt {retry_count} failed: {e}")
            retry_count += 1
            time.sleep(2)
    
    return client

def on_message(client, userdata, msg):
    try:
        # Parse message
        payload = json.loads(msg.payload.decode())
        obj_id = payload.get('id')
        x = payload.get('x')
        y = payload.get('y')
        timestamp = payload.get('timestamp', time.time())
        
        if obj_id and x is not None and y is not None:
            # Store in InfluxDB
            point = Point("object_position") \
                .tag("object_id", obj_id) \
                .field("x", float(x)) \
                .field("y", float(y)) \
                .time(int(timestamp * 1e9))  # Convert to nanoseconds
            
            write_api.write(bucket=influxdb_bucket, record=point)
            
            # Update MongoDB (last known position and metadata)
            objects_collection.update_one(
                {"_id": obj_id},
                {
                    "$set": {
                        "last_position": {"x": x, "y": y},
                        "last_updated": timestamp
                    },
                    "$setOnInsert": {
                        "first_seen": timestamp,
                        "type": "default"
                    }
                },
                upsert=True
            )
            zone_processor.process_position(obj_id, x, y, timestamp)
            # Log disappearance/appearance events
            check_appearance_events(obj_id, timestamp)
            
            print(f"Processed position for {obj_id}: ({x}, {y})")
    except Exception as e:
        print(f"Error processing message: {e}")

def check_appearance_events(obj_id, timestamp):
    """Detect and record object appearances and disappearances"""
    # Get object info
    obj = objects_collection.find_one({"_id": obj_id})
    
    # If object exists and was previously marked as gone
    if obj and obj.get("status") == "gone":
        # Record reappearance event
        events_collection.insert_one({
            "object_id": obj_id,
            "event_type": "appearance",
            "timestamp": timestamp,
            "details": {
                "previous_disappearance": obj.get("last_disappearance")
            }
        })
        # Update object status
        objects_collection.update_one(
            {"_id": obj_id},
            {"$set": {"status": "active"}}
        )

def main():
    # Connect to MQTT broker
    client = connect_mqtt()
    client.loop_forever()

if __name__ == "__main__":
    main()
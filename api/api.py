import os
from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from influxdb_client import InfluxDBClient
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import uuid
import uvicorn
import redis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
import socket
import psutil
import time

app = FastAPI(title="Object Tracking API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
influxdb_url = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
influxdb_token = os.environ.get("INFLUXDB_TOKEN", "my-token")
influxdb_org = os.environ.get("INFLUXDB_ORG", "tracking")
influxdb_bucket = os.environ.get("INFLUXDB_BUCKET", "object_positions")
mongodb_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
redis_host = os.environ.get("REDIS_HOST", "redis")
redis_port = int(os.environ.get("REDIS_PORT", "6379"))

# DB Clients
influx_client = InfluxDBClient(url=influxdb_url, token=influxdb_token, org=influxdb_org)
query_api = influx_client.query_api()

mongo_client = MongoClient(mongodb_uri)
db = mongo_client['object_tracking']
objects_collection = db['objects']
events_collection = db['events']

# Create database indexes for performance
def create_indexes():
    # Create indexes for frequently queried collections
    objects_collection.create_index("status")
    db['zones'].create_index("active")
    db['zone_events'].create_index([("object_id", 1), ("timestamp", -1)])
    db['zone_events'].create_index([("zone_id", 1), ("timestamp", -1)])
    db['events'].create_index([("object_id", 1), ("timestamp", -1)])
    db['events'].create_index("event_type")

# Initialize FastAPI Cache on startup
@app.on_event("startup")
async def startup():
    redis_client = redis.Redis(host=redis_host, port=redis_port)
    FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
    create_indexes()  # Create MongoDB indexes

def format_timestamp(timestamp):
    """Format timestamp to ISO format string, handling various input types."""
    if isinstance(timestamp, datetime):
        return timestamp.isoformat()
    elif isinstance(timestamp, (float, int)):
        return datetime.fromtimestamp(timestamp).isoformat()
    else:
        return str(timestamp)

@app.get("/")
def read_root():
    return {"status": "online", "service": "Object Tracking API"}

@app.get("/objects", response_model=List[Dict[str, Any]])
def get_objects(status: Optional[str] = None, limit: int = 100):
    """Get all tracked objects with optional status filter"""
    query = {}
    if status:
        query["status"] = status
    
    objects = list(objects_collection.find(query).limit(limit))
    
    # Convert MongoDB _id to string
    for obj in objects:
        obj["_id"] = str(obj["_id"])
    
    return objects

@app.get("/objects/{object_id}")
def get_object(object_id: str):
    """Get details for a specific object"""
    obj = objects_collection.find_one({"_id": object_id})
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    
    # Convert MongoDB _id to string
    obj["_id"] = str(obj["_id"])
    
    return obj

@app.get("/objects/{object_id}/history")
def get_object_history(
    object_id: str, 
    start: Optional[str] = None,
    end: Optional[str] = None,
    interval: Optional[str] = None
):
    """Get position history for an object with optional time range"""
    try:
        # Set default time range if not provided
        if not end:
            end_time = datetime.now()
        else:
            end_time = datetime.fromisoformat(end)
            
        if not start:
            start_time = end_time - timedelta(hours=1)
        else:
            start_time = datetime.fromisoformat(start)
        
        # Build Flux query
        flux_query = f'''
        from(bucket: "{influxdb_bucket}")
            |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
            |> filter(fn: (r) => r._measurement == "object_position")
            |> filter(fn: (r) => r.object_id == "{object_id}")
        '''
        
        # Add aggregation if interval specified
        if interval:
            flux_query += f'''
            |> aggregateWindow(every: {interval}, fn: mean, createEmpty: false)
            '''
            
        # Execute query
        tables = query_api.query(flux_query)
        
        # Process results
        results = []
        for table in tables:
            for record in table.records:
                field = record.get_field()
                value = record.get_value()
                time = record.get_time().isoformat()
                
                # Find existing time entry or create new one
                existing = next((r for r in results if r["time"] == time), None)
                if existing:
                    existing[field] = value
                else:
                    results.append({"time": time, field: value})
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying data: {str(e)}")

@app.get("/events")
def get_events(
    event_type: Optional[str] = None,
    object_id: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 100
):
    """Get system events with optional filters"""
    query = {}
    
    if event_type:
        query["event_type"] = event_type
    if object_id:
        query["object_id"] = object_id
    
    time_query = {}
    if start:
        time_query["$gte"] = datetime.fromisoformat(start)
    if end:
        time_query["$lte"] = datetime.fromisoformat(end)
    
    if time_query:
        query["timestamp"] = time_query
    
    events = list(events_collection.find(query).sort("timestamp", -1).limit(limit))
    
    # Convert MongoDB _id to string
    for event in events:
        event["_id"] = str(event["_id"])
        # Format timestamp for JSON response
        if "timestamp" in event:
            event["timestamp"] = format_timestamp(event["timestamp"])
    
    return events

@app.get("/zones")
@cache(expire=60)  # Cache for 60 seconds
def get_zones(active_only: bool = True):
    """Get all zones"""
    query = {}
    if active_only:
        query["active"] = True
    
    zones = list(db['zones'].find(query))
    for zone in zones:
        zone["_id"] = str(zone["_id"])
    
    return zones

@app.get("/zones/{zone_id}")
@cache(expire=60)  # Cache for 60 seconds
def get_zone(zone_id: str):
    """Get a specific zone by ID"""
    zone = db['zones'].find_one({"_id": zone_id})
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    zone["_id"] = str(zone["_id"])
    return zone

@app.post("/zones")
def create_zone(zone: dict):
    """Create a new zone"""
    if "_id" not in zone:
        zone["_id"] = f"zone_{str(uuid.uuid4())[:8]}"
    
    zone["created_at"] = datetime.now()
    zone["updated_at"] = datetime.now()
    zone["active"] = True
    
    db['zones'].insert_one(zone)
    # Invalidate the zones cache when a new zone is created
    FastAPICache.clear(namespace="zones")
    return {"id": zone["_id"], "status": "created"}

@app.put("/zones/{zone_id}")
def update_zone(zone_id: str, zone_update: dict):
    """Update an existing zone"""
    zone_update["updated_at"] = datetime.now()
    
    result = db['zones'].update_one(
        {"_id": zone_id},
        {"$set": zone_update}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    # Invalidate both the specific zone cache and the zones list cache
    FastAPICache.clear(namespace=f"zones_{zone_id}")
    FastAPICache.clear(namespace="zones")
    return {"status": "updated"}

@app.delete("/zones/{zone_id}")
def delete_zone(zone_id: str, hard_delete: bool = False):
    """Delete a zone (or mark as inactive)"""
    if hard_delete:
        result = db['zones'].delete_one({"_id": zone_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Zone not found")
    else:
        # Soft delete
        result = db['zones'].update_one(
            {"_id": zone_id},
            {"$set": {"active": False, "updated_at": datetime.now()}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Zone not found")
    
    # Invalidate both the specific zone cache and the zones list cache
    FastAPICache.clear(namespace=f"zones_{zone_id}")
    FastAPICache.clear(namespace="zones")
    return {"status": "deleted"}

@app.get("/zone-events")
@cache(expire=30)  # Cache for 30 seconds
def get_zone_events(
    zone_id: Optional[str] = None,
    object_id: Optional[str] = None,
    event_type: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 100
):
    """Get zone events with various filters"""
    query = {}
    
    if zone_id:
        query["zone_id"] = zone_id
    if object_id:
        query["object_id"] = object_id
    if event_type and event_type != "all":
        query["event_type"] = event_type
    
    time_query = {}
    if start:
        time_query["$gte"] = datetime.fromisoformat(start)
    if end:
        time_query["$lte"] = datetime.fromisoformat(end)
    
    if time_query:
        query["timestamp"] = time_query
    
    events = list(db['zone_events'].find(query).sort("timestamp", -1).limit(limit))
    
    # Convert IDs and dates for JSON response
    for event in events:
        event["_id"] = str(event["_id"])
        if "timestamp" in event:
            event["timestamp"] = format_timestamp(event["timestamp"])
    
    return events

@app.get("/objects/{object_id}/zones")
@cache(expire=10)  # Cache for 30 seconds
def get_object_zones(
    object_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 100
):
    """Get zones an object has been in with timeline"""
    query = {"object_id": object_id}
    
    time_query = {}
    if start:
        time_query["$gte"] = datetime.fromisoformat(start)
    if end:
        time_query["$lte"] = datetime.fromisoformat(end)
    
    if time_query:
        query["timestamp"] = time_query
    
    events = list(db['zone_events'].find(query).sort("timestamp", 1).limit(limit))
    
    # Format the response with zone information
    result = []
    for event in events:
        zone_id = event["zone_id"]
        zone = db['zones'].find_one({"_id": zone_id})
        zone_name = zone["name"] if zone else "Unknown Zone"
        
        # Handle the timestamp format correctly
        timestamp = event["timestamp"]

        timestamp_str = format_timestamp(timestamp)
        
        result.append({
            "event_id": str(event["_id"]),
            "zone_id": zone_id,
            "zone_name": zone_name,
            "event_type": event["event_type"],
            "timestamp": timestamp_str,
            "duration": event.get("duration")
        })
    
    return result

@app.get("/health")
def health_check():
    """Health check endpoint for load balancer"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "mongodb": "connected" if mongo_client is not None else "disconnected",
            "influxdb": "connected" if influx_client is not None else "disconnected",
            "redis": "connected" if FastAPICache._cache is not None else "disconnected"
        }
    }

@app.get("/system/instance-info")
def instance_info():
    """Get information about this API instance"""
    try:
        hostname = socket.gethostname()
        process = psutil.Process()
        mem_info = process.memory_info()
        
        return {
            "hostname": hostname,
            "instance_id": os.environ.get("HOSTNAME", "unknown"),
            "cpu_usage": process.cpu_percent(),
            "memory_usage_mb": mem_info.rss / (1024 * 1024),
            "uptime_seconds": time.time() - process.create_time(),
            "thread_count": process.num_threads(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Use multiple worker processes
    uvicorn.run(
        "api:app", 
        host="0.0.0.0", 
        port=5001, 
        workers=4,  # Number of worker processes
        log_level="info"
    )
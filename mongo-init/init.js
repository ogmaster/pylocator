db.createUser({
    user: "admin",
    pwd: "adminpassword",
    roles: [
        { role: "userAdminAnyDatabase", db: "admin" },
        { role: "readWriteAnyDatabase", db: "admin" },
        { role: "dbAdminAnyDatabase", db: "admin" }
    ]
});

// Create object_tracking database and its collections
db = db.getSiblingDB('object_tracking');

// Create collections with validators
db.createCollection("objects");
db.createCollection("events");
db.createCollection("zones");
db.createCollection("zone_events");

// Create indexes
db.objects.createIndex({ "status": 1 });
db.zones.createIndex({ "active": 1 });
db.zone_events.createIndex({ "object_id": 1, "timestamp": -1 });
db.zone_events.createIndex({ "zone_id": 1, "timestamp": -1 });
db.events.createIndex({ "object_id": 1, "timestamp": -1 });
db.events.createIndex({ "event_type": 1 }); 
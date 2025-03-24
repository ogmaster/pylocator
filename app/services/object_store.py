"""
Service for managing real-time object tracking data.
"""
import threading
import time


class ObjectStore:
    """Manages real-time object tracking data with thread-safe operations."""
    
    def __init__(self, timeout=5):
        """Initialize the object store.
        
        Args:
            timeout: Number of seconds before an object is considered inactive
        """
        self.objects = {}  # {id: {x, y, last_update, history: [(x,y,t)], ...}}
        self.timeout = timeout
        self._lock = threading.Lock()
    
    def update_object(self, obj_id, x, y):
        """Update object position and maintain its history.
        
        Args:
            obj_id: Object identifier
            x: X coordinate
            y: Y coordinate
        """
        with self._lock:
            now = time.time()
            if obj_id not in self.objects:
                self.objects[obj_id] = {
                    'x': x, 
                    'y': y, 
                    'last_update': now,
                    'history': [(x, y, now)]
                }
            else:
                self.objects[obj_id].update({
                    'x': x, 
                    'y': y, 
                    'last_update': now
                })
                self.objects[obj_id]['history'].append((x, y, now))
                # Limit history size
                if len(self.objects[obj_id]['history']) > 100:
                    self.objects[obj_id]['history'] = self.objects[obj_id]['history'][-100:]
    
    def get_active_objects(self):
        """Get objects that have been updated within the timeout period."""
        with self._lock:
            now = time.time()
            active = {}
            for obj_id, data in self.objects.items():
                if now - data['last_update'] <= self.timeout:
                    active[obj_id] = data
            return active
    
    def get_object_trails(self, max_trail_points=20):
        """Get position trails for active objects.
        
        Args:
            max_trail_points: Maximum number of points in each trail
            
        Returns:
            Dictionary of object trails {obj_id: {'x': [...], 'y': [...]}}
        """
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
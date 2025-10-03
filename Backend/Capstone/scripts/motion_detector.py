# Backend/Capstone/scripts/motion_detector.py

from typing import Dict, Any, Optional
import math

MOVEMENT_THRESHOLD_METERS = 0.5 
_last_known_location: Optional[Dict[str, float]] = None

def calculate_distance(loc1: Dict[str, float], loc2: Dict[str, float]) -> float:
    # Calculates Euclidean distance between two points.
    lat_diff = loc1.get('latitude', 0.0) - loc2.get('latitude', 0.0)
    lon_diff = loc1.get('longitude', 0.0) - loc2.get('longitude', 0.0)
    return math.sqrt(lat_diff**2 + lon_diff**2)

def is_bot_moving(current_location_data: Dict[str, Any]) -> bool:
    # Determines if the bot is moving based on location delta.
    global _last_known_location
    
    current_location = {
        'latitude': current_location_data.get('latitude', 0.0),
        'longitude': current_location_data.get('longitude', 0.0),
    }

    if _last_known_location is None:
        _last_known_location = current_location
        return False
    
    distance = calculate_distance(current_location, _last_known_location)
    _last_known_location = current_location
    
    return distance > MOVEMENT_THRESHOLD_METERS

if __name__ == '__main__':
    loc1 = {'latitude': 36.1, 'longitude': -86.5}
    print(f"Movement (loc1): {is_bot_moving(loc1)}")
    
    loc2 = {'latitude': 36.100001, 'longitude': -86.500001}
    print(f"Movement (loc2): {is_bot_moving(loc2)}")
    
    loc3 = {'latitude': 36.101, 'longitude': -86.501}
    print(f"Movement (loc3): {is_bot_moving(loc3)}")

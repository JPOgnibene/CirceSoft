# utils.py
import os
import math
import json # New import
from typing import List, Dict, Any, Tuple, Optional

# Import configuration constants
from config import CURRENT_VALUES_PATH, DIRECTIONS_PATH, WAYPOINTS_PATH # Added WAYPOINTS_PATH

# Import state and models
from models import circesoft_pb2, CABLE_REMAINING, LAST_POSITION_ECI 


# ==============================================================================
# 1. MOTION DETECTION STATE & LOGIC (No Change)
# ==============================================================================

MOVEMENT_THRESHOLD_METERS = 0.5 
_last_known_location_LL: Optional[Dict[str, float]] = None 


def calculate_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Compute Euclidean distance between two 2D points (x, y). Used for ECI cable tracking."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)

def calculate_ll_distance(loc1: Dict[str, float], loc2: Dict[str, float]) -> float:
    """Calculates Euclidean distance between two Lat/Lon points. Used for motion detection."""
    lat_diff = loc1.get('latitude', 0.0) - loc2.get('latitude', 0.0)
    lon_diff = loc1.get('longitude', 0.0) - loc2.get('longitude', 0.0)
    return math.sqrt(lat_diff**2 + lon_diff**2)


def is_bot_moving_ll(current_location_data: Dict[str, float]) -> bool:
    """Determines if the bot is moving based on Latitude/Longitude delta."""
    global _last_known_location_LL
    
    current_location = {
        'latitude': current_location_data.get('latitude', 0.0),
        'longitude': current_location_data.get('longitude', 0.0),
    }

    if _last_known_location_LL is None:
        _last_known_location_LL = current_location
        return False
    
    # NOTE: The current distance calculation is likely flawed for real-world distances,
    # but we retain it as it matches the original implementation style.
    distance = calculate_ll_distance(current_location, _last_known_location_LL)
    _last_known_location_LL = current_location
    
    return distance > MOVEMENT_THRESHOLD_METERS


# ==============================================================================
# 2. CORE MESSAGE HANDLER (No Change)
# ==============================================================================

def handle_client_message(data) -> circesoft_pb2.CurrentStatus:
    """Handles incoming status message, updates cable length, returns complete status object."""
    # NOTE: Modifies global ECI state and Cable Remaining state
    global CABLE_REMAINING, LAST_POSITION_ECI

    p1 = LAST_POSITION_ECI

    # In a real app, 'data' would be parsed here (e.g., Protobuf deserialization).
    msg = circesoft_pb2.CurrentStatus()
    # Mocking values here since actual parsing is not implemented
    new_X_ECI = msg.reportedPosition.X_ECI 
    new_Y_ECI = msg.reportedPosition.Y_ECI

    p2 = (new_X_ECI, new_Y_ECI)

    # 1. Update Cable Remaining (uses ECI distance)
    distance_traveled = calculate_distance(p1, p2)
    CABLE_REMAINING -= distance_traveled
    if CABLE_REMAINING < 0:
        CABLE_REMAINING = 0

    LAST_POSITION_ECI = p2

    # 2. Determine Movement Status 
    mock_ll_location = {
        'latitude': new_X_ECI * 1e-5,
        'longitude': new_Y_ECI * 1e-5
    }
    
    # 3. Apply Motion Detection
    msg.isMoving = is_bot_moving_ll(mock_ll_location)
    
    # 4. Finalize Status
    msg.reportedCableRemaining_m = CABLE_REMAINING
    return msg


# ==============================================================================
# 3. FILE I/O AND HELPER FUNCTIONS (Refactored for JSON)
# ==============================================================================

def _exists(path: str) -> bool:
    """Check if a file exists and is a file."""
    return os.path.exists(path) and os.path.isfile(path)

def _nocache_headers() -> dict:
    """Prevent stale data in browsers/Proxies."""
    return {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }

def read_text(path: str) -> str:
    """Reads content from a text file, returns empty string if not found."""
    # This remains for simple text files like DIRECTIONS (which can still be a JSON string)
    return open(path, "r").read().strip() if os.path.exists(path) else ""

def write_text(path: str, text: str) -> None:
    """Writes text content to a file, creating directories if necessary."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text or "")

def write_status_to_file(msg: circesoft_pb2.CurrentStatus, file_path: str = CURRENT_VALUES_PATH) -> None:
    """Writes the entire status object to the current_values.json file in JSON format."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    status_data = {
        "X_ECI": msg.reportedPosition.X_ECI,
        "Y_ECI": msg.reportedPosition.Y_ECI,
        "Z_ECI": msg.reportedPosition.Z_ECI,
        "Vx_ECI": msg.reportedVelocity.Vx_ECI,
        "Vy_ECI": msg.reportedVelocity.Vy_ECI,
        "Vz_ECI": msg.reportedVelocity.Vz_ECI,
        "Heading": msg.reportedHeading,
        "cableRemaining_m": msg.reportedCableRemaining_m,
        "percentBatteryRemaining": msg.reportedPercentBatteryRemaining,
        "errorCode": msg.errorCode,
        "cableDispenseStatus": msg.cableDispenseStatus,
        "cableDispenseCommand": msg.cableDispenseCommand,
        "SequenceNum": msg.SequenceNum,
        "isMoving": msg.isMoving,
    }
    with open(file_path, "w") as f:
        json.dump(status_data, f, indent=4) # Use indent for readability

# --- JSON Parsers/Writers ---

def _read_json(path: str) -> Optional[List[Dict[str, Any]]]:
    """Reads and parses a generic JSON file into a list of dicts."""
    if not _exists(path): return None
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            # Ensure the top level is a list, as expected by the consumers
            return data if isinstance(data, list) else [data] if isinstance(data, dict) else None
    except (json.JSONDecodeError, IOError, TypeError) as e:
        print(f"Error parsing JSON {path}: {e}")
        return None

def _write_json(path: str, data: List[Dict[str, Any]]) -> None:
    """Writes a list of dictionaries to a JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error writing JSON to {path}: {e}")


#=======================================================================
#               PATH PROGRESS FUNCTIONS
#=======================================================================
def load_path_json(path_json: str) -> list:
    """Load a path as a list of (col, row) tuples from a JSON file."""
    data = _read_json(path_json)
    return [(int(item["col"]), int(item["row"])) for item in data] if data else []


def path_length(path: list) -> float:
    """Total path length in grid cells/meters."""
    if not path or len(path) < 2:
        return 0.0
    dist = 0.0
    for a, b in zip(path, path[1:]):
        diag = (a[0] != b[0] and a[1] != b[1])
        dist += math.sqrt(2.0) if diag else 1.0
    return dist

def closest_path_index(path: list, pos: tuple) -> int:
    """Index of path node closest to 'pos' (in grid coordinates)."""
    return min(range(len(path)), key=lambda i: math.hypot(path[i][0] - pos[0], path[i][1] - pos[1]))

def distance_along_path(path: list, idx: int, pos: tuple = None) -> float:
    """Distance along path to index (plus offset if pos given)."""
    dist = 0.0
    for a, b in zip(path, path[1:idx+1]):
        diag = (a[0] != b[0] and a[1] != b[1])
        dist += math.sqrt(2.0) if diag else 1.0
    if pos and idx < len(path):
        last = path[idx]
        dist += math.hypot(pos[0] - last[0], pos[1] - last[1])
    return dist



# Rename all CSV functions to use JSON and update their internal logic
_parse_coords_json = _read_json
_parse_obstacles_json = _read_json
_write_obstacles_json = _write_json
_parse_path_json = _read_json
_write_path_json = _write_json
_write_waypoints_json = _write_json # New writer for waypoints

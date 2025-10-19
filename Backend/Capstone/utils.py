# utils.py
import os
import math
import csv
from typing import List, Dict, Any, Tuple, Optional

# Import configuration constants
from config import CURRENT_VALUES_PATH, DIRECTIONS_PATH

# Import state and models
from models import circesoft_pb2, CABLE_REMAINING, LAST_POSITION_ECI 


# ==============================================================================
# 1. MOTION DETECTION STATE & LOGIC
#    (Based on the motion_detector.py file, using Lat/Lon for delta tracking)
# ==============================================================================

MOVEMENT_THRESHOLD_METERS = 0.5 
# State for motion detection (tracks Latitude/Longitude history)
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
    
    distance = calculate_ll_distance(current_location, _last_known_location_LL)
    _last_known_location_LL = current_location
    
    return distance > MOVEMENT_THRESHOLD_METERS


# ==============================================================================
# 2. CORE MESSAGE HANDLER
# ==============================================================================

def handle_client_message(data) -> circesoft_pb2.CurrentStatus:
    """Handles incoming status message, updates cable length, returns complete status object."""
    # NOTE: Modifies global ECI state and Cable Remaining state
    global CABLE_REMAINING, LAST_POSITION_ECI

    p1 = LAST_POSITION_ECI

    # In a real app, 'data' would be parsed here (e.g., Protobuf deserialization).
    msg = circesoft_pb2.CurrentStatus()
    new_X_ECI = msg.reportedPosition.X_ECI 
    new_Y_ECI = msg.reportedPosition.Y_ECI

    p2 = (new_X_ECI, new_Y_ECI)

    # 1. Update Cable Remaining (uses ECI distance)
    distance_traveled = calculate_distance(p1, p2)
    CABLE_REMAINING -= distance_traveled
    if CABLE_REMAINING < 0:
        CABLE_REMAINING = 0

    LAST_POSITION_ECI = p2

    # 2. Determine Movement Status (Requires mocking ECI to Lat/Lon for detector)
    # This mock is necessary because the detector uses Lat/Lon but the status only reports ECI.
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
# 3. FILE I/O AND HELPER FUNCTIONS
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
    return open(path, "r").read().strip() if os.path.exists(path) else ""

def write_text(path: str, text: str) -> None:
    """Writes text content to a file, creating directories if necessary."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text or "")

def write_status_to_file(msg: circesoft_pb2.CurrentStatus, file_path: str = CURRENT_VALUES_PATH) -> None:
    """Writes the entire status object to the current_values.txt file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        f.write(f"X_ECI={msg.reportedPosition.X_ECI}\n")
        f.write(f"Y_ECI={msg.reportedPosition.Y_ECI}\n")
        f.write(f"Z_ECI={msg.reportedPosition.Z_ECI}\n")
        f.write(f"Vx_ECI={msg.reportedVelocity.Vx_ECI}\n")
        f.write(f"Vy_ECI={msg.reportedVelocity.Vy_ECI}\n")
        f.write(f"Vz_ECI={msg.reportedVelocity.Vz_ECI}\n")
        f.write(f"Heading={msg.reportedHeading}\n")
        f.write(f"cableRemaining_m={msg.reportedCableRemaining_m}\n")
        f.write(f"percentBatteryRemaining={msg.reportedPercentBatteryRemaining}\n")
        f.write(f"errorCode={msg.errorCode}\n")
        f.write(f"cableDispenseStatus={msg.cableDispenseStatus}\n")
        f.write(f"cableDispenseCommand={msg.cableDispenseCommand}\n")
        f.write(f"SequenceNum={msg.SequenceNum}\n")
        f.write(f"isMoving={msg.isMoving}\n")

# --- CSV Parsers/Writers ---

def _parse_coords_csv(path: str) -> List[Dict[str, Any]]:
    """Reads coordinates CSV (row, col, x, y)."""
    data = []
    if not _exists(path): return data
    try:
        with open(path, mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append({"r": int(row["row"]), "c": int(row["col"]), "x": float(row["x"]), "y": float(row["y"])})
        return data
    except Exception as e:
        print(f"Error parsing CSV {path}: {e}")
        return []

def _parse_obstacles_csv(path: str) -> List[Dict[str, int]]:
    """Reads obstacle CSV (row, col)."""
    obstacles = []
    if not _exists(path): return obstacles
    try:
        with open(path, mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                obstacles.append({"r": int(row["row"]), "c": int(row["col"])})
        return obstacles
    except Exception as e:
        print(f"Error parsing CSV {path}: {e}")
        return []

def _write_obstacles_csv(path: str, data: List[Dict[str, int]]) -> None:
    """Writes a list of obstacle dictionaries back to obstacles.csv."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = ['row', 'col']
    with open(path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for item in data:
            writer.writerow({'row': item['r'], 'col': item['c']})

def _parse_path_csv(path: str) -> List[Dict[str, int]]:
    """Reads path CSV (row, col)."""
    path_points = []
    if not _exists(path): return path_points
    try:
        with open(path, mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                path_points.append({"r": int(row["row"]), "c": int(row["col"])})
        return path_points
    except Exception as e:
        print(f"Error parsing CSV {path}: {e}")
        return []

def _write_path_csv(path: str, data: List[Dict[str, int]]) -> None:
    """Writes a list of path dictionaries back to path.csv."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = ['row', 'col']
    with open(path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for item in data:
            writer.writerow({'row': item['r'], 'col': item['c']})
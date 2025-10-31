# routes.py
import asyncio
import io
import os
import time
import zipfile
import json 
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import PlainTextResponse, FileResponse, StreamingResponse, JSONResponse 

# Import all necessary components
from config import (
    WS_PATH, CURRENT_VALUES_PATH, DIRECTIONS_PATH, GRID_DIR,
    GRID_IMAGE_NAME, GRID_COORDS_NAME, GRID_OBS_NAME, GRID_PATH_NAME,
    GRID_IMAGE_PATH, GRID_COORDS_PATH, GRID_OBS_PATH, GRID_PATH_PATH,
    WAYPOINTS_PATH # New import
)
from utils import (
    read_text, write_text, write_status_to_file, handle_client_message,
    _exists, _nocache_headers,
    _parse_coords_json, _parse_obstacles_json, _write_obstacles_json, # Updated names
    _parse_path_json, _write_path_json, _write_waypoints_json, # Updated names
    load_path_json, path_length, closest_path_index, distance_along_path
    )

router = APIRouter()

## Must do: set filepath for generated path
PATH_FILE = ""


# --- Connection Manager for WebSocket clients ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for connection in disconnected:
            self.active_connections.remove(connection)

# Create global manager instance
manager = ConnectionManager()

# --- WebSocket endpoint for astar messages ---
@router.websocket("/ws/astarmessages")
async def astar_messages_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Just keep connection alive and listen optionally, or remove if not needed
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- REST endpoint to receive astar messages from backend script ---
@router.post("/send-astar-message")
async def send_astar_message(body: Dict[str, Any] = Body(...)):
    message = body.get("message", "")
    if not message:
        return JSONResponse({"error": "No message provided"}, status_code=400)
    # Broadcast message to all connected websocket clients
    await manager.broadcast({"type": "astar_message", "content": message})
    return {"status": "message sent"}

# --- Helper for Errors ---
def _not_found(name: str) -> JSONResponse:
    return JSONResponse({"error": f"{name} not found"}, status_code=404)

# --- Helper to read JSON file content ---
def _read_json_file(path: str) -> Optional[Dict[str, Any]]:
    """Reads a JSON file and returns its content as a dict/list, or None on error/not found."""
    if not _exists(path):
        return None
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

# -------- REST Endpoints (Non-Grid) --------

@router.get("/health", response_class=PlainTextResponse)
async def health() -> str:
    return "ok"

@router.get("/current-values")
async def get_current_values():
    data = _read_json_file(CURRENT_VALUES_PATH)
    if data is None:
        return _not_found("current-values")
    return JSONResponse(data, headers=_nocache_headers())

@router.put("/current-values") 
async def put_current_values(body: Dict[str, Any] = Body(..., media_type="application/json")):
    """
    Directly overwrites the current_values.json file with a new JSON payload.
    Used primarily for testing or simulation.
    """
    try:
        # Write the incoming JSON body directly to the current values file
        write_text(CURRENT_VALUES_PATH, json.dumps(body, indent=4))
        return JSONResponse({"status": "current-values updated"}, headers=_nocache_headers())
    except Exception as e:
        return JSONResponse({"error": f"Failed to write current-values: {e}"}, status_code=500)


@router.get("/directions")
async def get_directions():
    # directions.json can hold a simple string or a complex JSON object
    data = _read_json_file(DIRECTIONS_PATH)
    if data is None:
        # Fallback to plain text read for backward compatibility if the file is just text
        text_data = read_text(DIRECTIONS_PATH)
        if not text_data:
            return _not_found("directions")
        try:
            # Try to interpret as JSON if it's there
            data = json.loads(text_data)
        except json.JSONDecodeError:
            # If it's pure text, wrap it in a JSON response
            return JSONResponse({"directions": text_data}, headers=_nocache_headers())
    
    return JSONResponse(data, headers=_nocache_headers())

@router.put("/directions")
async def put_directions(body: Dict[str, Any] = Body(..., media_type="application/json")):
    # Write the incoming JSON body directly to the directions file
    try:
        write_text(DIRECTIONS_PATH, json.dumps(body, indent=4))
        return JSONResponse({"status": "updated"}, headers=_nocache_headers())
    except Exception as e:
        return JSONResponse({"error": f"Failed to write directions: {e}"}, status_code=500)

@router.get("/waypoints")
async def get_waypoints():
    data = _read_json_file(WAYPOINTS_PATH)
    if data is None:
        return _not_found("waypoints")
    return JSONResponse({"data": data}, headers=_nocache_headers())

# -------- Grid Endpoints --------

@router.get("/grid/manifest")
async def grid_manifest():
    """JSON inventory of grid files + size + mtime."""
    items = []
    for name, path, mime, endpoint in [
        (GRID_IMAGE_NAME, GRID_IMAGE_PATH, "image/jpeg", "/grid/image"),
        (GRID_COORDS_NAME, GRID_COORDS_PATH, "application/json", "/grid/coordinates"),
        (GRID_OBS_NAME, GRID_OBS_PATH, "application/json", "/grid/obstacles"),
        (GRID_PATH_NAME, GRID_PATH_PATH, "application/json", "/grid/path"),
    ]:
        exists = _exists(path)
        items.append({
            "name": name,
            "exists": exists,
            "path": endpoint,
            "mime": mime,
            "size_bytes": os.path.getsize(path) if exists else None,
            "mtime": int(os.path.getmtime(path)) if exists else None,
        })
    return JSONResponse({"directory": os.path.abspath(GRID_DIR), "files": items}, headers=_nocache_headers())

# Image remains a FileResponse
@router.get("/grid/image")
async def get_grid_image():
    if not _exists(GRID_IMAGE_PATH):
        return _not_found(GRID_IMAGE_NAME)
    # The original file type was 'image/jpeg' despite the name being 'current_image.jpg'
    return FileResponse(
        GRID_IMAGE_PATH,
        media_type="image/jpeg",
        filename=GRID_IMAGE_NAME,
        headers=_nocache_headers(),
    )

# --- Coordinates ---

@router.get("/grid/coordinates")
async def get_grid_coordinates_json():
    # Use the unified JSON parser
    data = _read_json_file(GRID_COORDS_PATH)
    if data is None:
        return _not_found(GRID_COORDS_NAME)
    # Wrap in "data" key to match the original structure
    return JSONResponse({"data": data}, headers=_nocache_headers())


# --- Obstacles ---

@router.get("/grid/obstacles")
async def get_grid_obstacles_json():
    data = _read_json_file(GRID_OBS_PATH)
    if data is None:
        return _not_found(GRID_OBS_NAME)
    return JSONResponse({"data": data}, headers=_nocache_headers())

@router.put("/grid/obstacles")
async def put_grid_obstacles(obstacles: List[Dict[str, int]] = Body(..., media_type="application/json")):
    cleaned_data = []
    # Input validation remains the same
    for obs in obstacles:
        if isinstance(obs, dict) and 'r' in obs and 'c' in obs:
            try:
                cleaned_data.append({'r': int(obs['r']), 'c': int(obs['c'])})
            except (ValueError, TypeError):
                continue
    
    if not cleaned_data and obstacles:
        return JSONResponse({"error": "Invalid input format. Expected list of {'r': int, 'c': int}."}, status_code=400)

    _write_obstacles_json(GRID_OBS_PATH, cleaned_data) # Updated writer
    
    return JSONResponse(
        {"status": "Obstacles updated successfully", "count": len(cleaned_data)},
        headers=_nocache_headers(),
    )

# --- Path ---

@router.get("/grid/path")
async def get_grid_path_json():
    data = _read_json_file(GRID_PATH_PATH)
    if data is None:
        return _not_found(GRID_PATH_NAME)
    return JSONResponse({"data": data}, headers=_nocache_headers())

@router.put("/grid/path")
async def put_grid_path(path_points: List[Dict[str, int]] = Body(..., media_type="application/json")):
    cleaned_data = []
    # Input validation remains the same
    for wp in path_points:
        if isinstance(wp, dict) and 'r' in wp and 'c' in wp:
            try:
                cleaned_data.append({'r': int(wp['r']), 'c': int(wp['c'])})
            except (ValueError, TypeError):
                continue
    
    if not cleaned_data and path_points:
        return JSONResponse({"error": "Invalid input format. Expected list of {'r': int, 'c': int}."}, status_code=400)

    _write_path_json(GRID_PATH_PATH, cleaned_data) # Updated writer
    
    return JSONResponse(
        {"status": "Path updated successfully", "count": len(cleaned_data)},
        headers=_nocache_headers(),
    )

# Path Progress
@router.get("/progress")
async def get_path_progress(current_x: float, current_y: float):
    path = load_path_json(PATH_FILE)
    idx = closest_path_index(path, grid_pos)
    traveled = distance_along_path(path, idx, grid_pos)
    total = path_length(path)
    percent = (traveled / total) * 100 if total > 0 else 0.0
    return {
        "percent_completed": percent,
        "distance_traveled": traveled,
        "total_path_length": total
    }


@router.get("/grid/bundle")
async def get_grid_bundle():
    """Streams a ZIP containing grid artifacts (now JSON files)."""
    files = []
    # Only include non-image files in the manifest zip.
    if _exists(GRID_COORDS_PATH): files.append((GRID_COORDS_PATH, GRID_COORDS_NAME))
    if _exists(GRID_OBS_PATH):    files.append((GRID_OBS_PATH, GRID_OBS_NAME))
    if _exists(GRID_PATH_PATH): files.append((GRID_PATH_PATH, GRID_PATH_NAME))

    # Optional: include the image
    if _exists(GRID_IMAGE_PATH):  files.append((GRID_IMAGE_PATH, GRID_IMAGE_NAME))

    if not files:
        return _not_found("grid files")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for abs_path, arc_name in files:
            zf.write(abs_path, arcname=arc_name)
    buf.seek(0)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            **_nocache_headers(),
            "Content-Disposition": f'attachment; filename="grid_bundle_{stamp}.zip"',
        },
    )

# -------- WebSocket Endpoint --------

@router.websocket(WS_PATH)
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    last_sent_directions = ""
    last_sent_current_values = ""
    last_sent_path = "" 
    # Add tracking for obstacles to detect file changes and push updates
    last_sent_obstacles = "" 

    try:
        while True:
            # --- 1. RECEIVE Logic (Client Status / Frontend Commands) ---
            try:
                message = await asyncio.wait_for(websocket.receive(), timeout=1.0)
                
                # Check for protobuf bytes (Client Status)
                if 'bytes' in message:
                    data = message['bytes']
                    status = handle_client_message(data)
                    if status:
                        write_status_to_file(status) # Writes to current_values.json
                        
                # Check for text (Frontend Commands: Waypoints or Obstacles)
                elif 'text' in message:
                    text_data = message['text']
                    try:
                        client_json = json.loads(text_data)

                        if 'waypoints' in client_json:
                            # Frontend sends new Waypoints
                            waypoints_data = client_json['waypoints']
                            _write_waypoints_json(WAYPOINTS_PATH, waypoints_data)
                            
                            print("Received new waypoints from frontend. Wrote to waypoints.json")
                            # Notify the other backend device immediately (if necessary)
                            await websocket.send_json({"type": "waypoints_update", "data": waypoints_data})
                            
                        elif 'obstacles' in client_json: # <-- NEW OBSTACLE RECEIVE LOGIC
                            # Frontend sends new Obstacles
                            obstacles_data = client_json['obstacles']
                            _write_obstacles_json(GRID_OBS_PATH, obstacles_data) 
                            
                            # Note: Obstacle update will be pushed to all clients 
                            # in the PUSH section below via file polling.
                            print("Received new obstacles from frontend. Wrote to obstacles.json")

                        elif 'new_path' in client_json:
                            # Second backend device sends new Path
                            path_data = client_json['new_path']
                            _write_path_json(GRID_PATH_PATH, path_data)
                            last_sent_path = json.dumps(path_data) 
                            
                            print("Received new path from backend device. Wrote to path.json")
                            
                    except json.JSONDecodeError:
                        print("Received non-JSON text message, ignoring.")
                
            except asyncio.TimeoutError:
                pass # Expected timeout, continue to send loop
            except WebSocketDisconnect:
                return
            
            # --- 2. PUSH Logic (Directions / Current Values / Path / Obstacles) ---
            
            # 2a. Push Directions (DIRECTIONS_PATH)
            current_directions_text = read_text(DIRECTIONS_PATH)
            if current_directions_text and current_directions_text != last_sent_directions:
                try:
                    directions_data = json.loads(current_directions_text)
                    await websocket.send_json({"type": "directions_update", "data": directions_data})
                    last_sent_directions = current_directions_text
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "directions_update", "data": {"directions": current_directions_text}})
                    last_sent_directions = current_directions_text

            # 2b. Push Current Values (CURRENT_VALUES_PATH)
            current_values_data = _read_json_file(CURRENT_VALUES_PATH)
            if current_values_data:
                current_values_text = json.dumps(current_values_data)
                if current_values_text and current_values_text != last_sent_current_values:
                    await websocket.send_json({"type": "current_values_update", "data": current_values_data})
                    last_sent_current_values = current_values_text

            # 2c. Push Path (GRID_PATH_PATH)
            current_path_data = _read_json_file(GRID_PATH_PATH)
            if current_path_data:
                current_path_text = json.dumps(current_path_data)
                if current_path_text and current_path_text != last_sent_path:
                    await websocket.send_json({"type": "path_update", "data": current_path_data})
                    last_sent_path = current_path_text
            
            # 2d. Push Obstacles (GRID_OBS_PATH) # <-- NEW OBSTACLE PUSH LOGIC
            current_obstacles_data = _read_json_file(GRID_OBS_PATH)
            if current_obstacles_data:
                current_obstacles_text = json.dumps(current_obstacles_data)
                if current_obstacles_text and current_obstacles_text != last_sent_obstacles:
                    await websocket.send_json({"type": "obstacles_update", "data": current_obstacles_data})
                    last_sent_obstacles = current_obstacles_text


            await asyncio.sleep(1) # Polling interval

    except WebSocketDisconnect:
        print("WebSocket client disconnected.")
        return

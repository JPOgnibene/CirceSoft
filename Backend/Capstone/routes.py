# routes.py
import asyncio
import io
import os
import time
import zipfile
from typing import List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import PlainTextResponse, FileResponse, StreamingResponse, JSONResponse

# Import all necessary components
from config import (
    WS_PATH, CURRENT_VALUES_PATH, DIRECTIONS_PATH, GRID_DIR,
    GRID_IMAGE_NAME, GRID_COORDS_NAME, GRID_OBS_NAME, GRID_PATH_NAME,
    GRID_IMAGE_PATH, GRID_COORDS_PATH, GRID_OBS_PATH, GRID_PATH_PATH
)
from utils import (
    read_text, write_text, write_status_to_file, handle_client_message,
    _exists, _nocache_headers,
    _parse_coords_csv, _parse_obstacles_csv, _write_obstacles_csv,
    _parse_path_csv, _write_path_csv
)

router = APIRouter()

# --- Helper for Errors ---
def _not_found(name: str) -> JSONResponse:
    return JSONResponse({"error": f"{name} not found"}, status_code=404)


# -------- REST Endpoints (Non-Grid) --------

@router.get("/health", response_class=PlainTextResponse)
async def health() -> str:
    return "ok"

@router.get("/current-values", response_class=PlainTextResponse)
async def get_current_values() -> str:
    return read_text(CURRENT_VALUES_PATH)

@router.get("/directions", response_class=PlainTextResponse)
async def get_directions() -> str:
    return read_text(DIRECTIONS_PATH)

@router.put("/directions", response_class=PlainTextResponse)
async def put_directions(body: str = Body(..., media_type="text/plain")) -> str:
    write_text(DIRECTIONS_PATH, body)
    return "updated"

# -------- Grid Endpoints --------

@router.get("/grid/manifest")
async def grid_manifest():
    """JSON inventory of grid files + size + mtime."""
    items = []
    for name, path, mime, endpoint in [
        (GRID_IMAGE_NAME, GRID_IMAGE_PATH, "image/png", "/grid/image"),
        (GRID_COORDS_NAME, GRID_COORDS_PATH, "text/csv", "/grid/coordinates"),
        (GRID_OBS_NAME, GRID_OBS_PATH, "text/csv", "/grid/obstacles"),
        (GRID_PATH_NAME, GRID_PATH_PATH, "text/csv", "/grid/path"),
    ]:
        exists = _exists(path)
        items.append({
            "name": name,
            "exists": exists,
            "path_csv": endpoint,
            "path_json": f"{endpoint}/json",
            "mime": mime,
            "size_bytes": os.path.getsize(path) if exists else None,
            "mtime": int(os.path.getmtime(path)) if exists else None,
        })
    return JSONResponse({"directory": os.path.abspath(GRID_DIR), "files": items}, headers=_nocache_headers())

@router.get("/grid/image")
async def get_grid_image():
    if not _exists(GRID_IMAGE_PATH):
        return _not_found(GRID_IMAGE_NAME)
    return FileResponse(
        GRID_IMAGE_PATH,
        media_type="image/jpeg",
        filename=GRID_IMAGE_NAME,
        headers=_nocache_headers(),
    )

@router.get("/grid/coordinates")
async def get_grid_coordinates():
    if not _exists(GRID_COORDS_PATH):
        return _not_found(GRID_COORDS_NAME)
    return FileResponse(
        GRID_COORDS_PATH,
        media_type="text/csv",
        filename=GRID_COORDS_NAME,
        headers=_nocache_headers(),
    )

@router.get("/grid/coordinates/json")
async def get_grid_coordinates_json():
    data = _parse_coords_csv(GRID_COORDS_PATH)
    if not data:
        return _not_found(GRID_COORDS_NAME)
    return JSONResponse({"data": data}, headers=_nocache_headers())

# --- Obstacles ---

@router.get("/grid/obstacles")
async def get_grid_obstacles():
    if not _exists(GRID_OBS_PATH):
        return _not_found(GRID_OBS_NAME)
    return FileResponse(
        GRID_OBS_PATH,
        media_type="text/csv",
        filename=GRID_OBS_NAME,
        headers=_nocache_headers(),
    )

@router.get("/grid/obstacles/json")
async def get_grid_obstacles_json():
    data = _parse_obstacles_csv(GRID_OBS_PATH)
    if not data:
        return _not_found(GRID_OBS_NAME)
    return JSONResponse({"data": data}, headers=_nocache_headers())

@router.put("/grid/obstacles")
async def put_grid_obstacles(obstacles: List[Dict[str, int]] = Body(..., media_type="application/json")):
    cleaned_data = []
    for obs in obstacles:
        if isinstance(obs, dict) and 'r' in obs and 'c' in obs:
            try:
                cleaned_data.append({'r': int(obs['r']), 'c': int(obs['c'])})
            except (ValueError, TypeError):
                continue
    
    if not cleaned_data and obstacles:
        return JSONResponse({"error": "Invalid input format. Expected list of {'r': int, 'c': int}."}, status_code=400)

    _write_obstacles_csv(GRID_OBS_PATH, cleaned_data)
    
    return JSONResponse(
        {"status": "Obstacles updated successfully", "count": len(cleaned_data)},
        headers=_nocache_headers(),
    )

# --- Path ---

@router.get("/grid/path")
async def get_grid_path():
    if not _exists(GRID_PATH_PATH):
        return _not_found(GRID_PATH_NAME)
    return FileResponse(
        GRID_PATH_PATH,
        media_type="text/csv",
        filename=GRID_PATH_NAME,
        headers=_nocache_headers(),
    )

@router.get("/grid/path/json")
async def get_grid_path_json():
    data = _parse_path_csv(GRID_PATH_PATH)
    if not data:
        return _not_found(GRID_PATH_NAME)
    return JSONResponse({"data": data}, headers=_nocache_headers())

@router.put("/grid/path")
async def put_grid_path(path_points: List[Dict[str, int]] = Body(..., media_type="application/json")):
    cleaned_data = []
    for wp in path_points:
        if isinstance(wp, dict) and 'r' in wp and 'c' in wp:
            try:
                cleaned_data.append({'r': int(wp['r']), 'c': int(wp['c'])})
            except (ValueError, TypeError):
                continue
    
    if not cleaned_data and path_points:
        return JSONResponse({"error": "Invalid input format. Expected list of {'r': int, 'c': int}."}, status_code=400)

    _write_path_csv(GRID_PATH_PATH, cleaned_data)
    
    return JSONResponse(
        {"status": "Path updated successfully", "count": len(cleaned_data)},
        headers=_nocache_headers(),
    )

@router.get("/grid/bundle")
async def get_grid_bundle():
    """Streams a ZIP containing grid artifacts."""
    files = []
    if _exists(GRID_IMAGE_PATH):  files.append((GRID_IMAGE_PATH, GRID_IMAGE_NAME))
    if _exists(GRID_COORDS_PATH): files.append((GRID_COORDS_PATH, GRID_COORDS_NAME))
    if _exists(GRID_OBS_PATH):    files.append((GRID_OBS_PATH, GRID_OBS_NAME))
    if _exists(GRID_PATH_PATH): files.append((GRID_PATH_PATH, GRID_PATH_NAME))

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
    last_sent_instructions = ""

    try:
        while True:
            # Receive protobuf bytes with 1s timeout
            try:
                data = await asyncio.wait_for(websocket.receive_bytes(), timeout=1.0)
                status = handle_client_message(data)
                if status:
                    write_status_to_file(status)
            except asyncio.TimeoutError:
                pass

            # Push directions if changed
            current = read_text(DIRECTIONS_PATH)
            if current and current != last_sent_instructions:
                await websocket.send_text(current)
                last_sent_instructions = current

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        return
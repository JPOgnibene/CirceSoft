import argparse
import asyncio
import csv
import io
import os
import time
import zipfile
from typing import List, Dict, Any, Tuple
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import PlainTextResponse, FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn

# Assuming 'receiver' and 'protos' are available in your environment
# from receiver import handle_client_message
# from protos import circesoft_pb2

# Placeholder for modules not provided in the prompt
class circesoft_pb2:
    class CurrentStatus:
        def __init__(self, **kwargs):
            self.reportedPosition = type('Pos', (object,), {'X_ECI': 0, 'Y_ECI': 0, 'Z_ECI': 0})
            self.reportedVelocity = type('Vel', (object,), {'Vx_ECI': 0, 'Vy_ECI': 0, 'Vz_ECI': 0})
            self.reportedHeading = 0
            self.reportedCableRemaining_m = 0
            self.reportedPercentBatteryRemaining = 0
            self.errorCode = 0
            self.cableDispenseStatus = 0
            self.cableDispenseCommand = 0
            self.SequenceNum = 0
def handle_client_message(data):
    # Dummy implementation for required imports
    return circesoft_pb2.CurrentStatus()

load_dotenv()

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8765"))
WS_PATH = os.getenv("WS_PATH", "/ws")
CURRENT_VALUES_PATH = os.getenv("CURRENT_VALUES_PATH", "./data/current_values.txt")
DIRECTIONS_PATH = os.getenv("DIRECTIONS_PATH", "./data/directions.txt")

# ====== Grid artifacts config ======
GRID_DIR = os.getenv("GRID_DIR", "./")
GRID_IMAGE_NAME = os.getenv("GRID_IMAGE_NAME", "./data/current_image.jpg")
GRID_COORDS_NAME = os.getenv("GRID_COORDS_NAME", "./data/grid_coordinates.csv")
GRID_OBS_NAME = os.getenv("GRID_OBS_NAME", "./data/obstacles.csv")

GRID_IMAGE_PATH = os.path.join(GRID_DIR, GRID_IMAGE_NAME)
GRID_COORDS_PATH = os.path.join(GRID_DIR, GRID_COORDS_NAME)
GRID_OBS_PATH = os.path.join(GRID_DIR, GRID_OBS_NAME)

app = FastAPI(title="CirceSoft Control Server", version="1.0")

# Optional CORS for frontend <> backend on different origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- file helpers

def write_status_to_file(msg: circesoft_pb2.CurrentStatus, file_path: str = CURRENT_VALUES_PATH) -> None:
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


def read_text(path: str) -> str:
    return open(path, "r").read().strip() if os.path.exists(path) else ""


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text or "")

# -------- REST

@app.get("/health", response_class=PlainTextResponse)
async def health() -> str:
    return "ok"


@app.get("/current-values", response_class=PlainTextResponse)
async def get_current_values() -> str:
    return read_text(CURRENT_VALUES_PATH)


@app.get("/directions", response_class=PlainTextResponse)
async def get_directions() -> str:
    return read_text(DIRECTIONS_PATH)


@app.put("/directions", response_class=PlainTextResponse)
async def put_directions(body: str = Body(..., media_type="text/plain")) -> str:
    write_text(DIRECTIONS_PATH, body)
    return "updated"

# -------- Grid artifact helpers + endpoints --------

def _exists(path: str) -> bool:
    return os.path.exists(path) and os.path.isfile(path)

def _not_found(name: str) -> JSONResponse:
    return JSONResponse({"error": f"{name} not found"}, status_code=404)

def _nocache_headers() -> dict:
    # Prevent stale images/CSVs/JSON in browsers/Proxies
    return {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }

def _parse_coords_csv(path: str) -> List[Dict[str, Any]]:
    """Reads a CSV (row, col, x, y) and returns a list of dictionaries."""
    data = []
    if not _exists(path):
        return data
    try:
        with open(path, mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert string values to appropriate types
                data.append({
                    "r": int(row["row"]),
                    "c": int(row["col"]),
                    "x": float(row["x"]),
                    "y": float(row["y"]),
                })
        return data
    except Exception as e:
        print(f"Error parsing CSV {path}: {e}")
        return []

def _parse_obstacles_csv(path: str) -> List[Dict[str, int]]:
    """Reads obstacle CSV (row, col) and returns a list of {r: int, c: int} dictionaries."""
    obstacles = []
    if not _exists(path):
        return obstacles
    try:
        with open(path, mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Obstacles only need row and col index to be useful
                obstacles.append({
                    "r": int(row["row"]),
                    "c": int(row["col"]),
                })
        return obstacles
    except Exception as e:
        print(f"Error parsing CSV {path}: {e}")
        return []

def _write_obstacles_csv(path: str, data: List[Dict[str, int]]) -> None:
    """
    Writes a list of obstacle dictionaries ({r: int, c: int}) back to obstacles.csv.
    Assumes incoming data uses 'r' and 'c' keys.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Use 'row' and 'col' for CSV compatibility
    fieldnames = ['row', 'col']
    with open(path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for item in data:
            # Map 'r' to 'row' and 'c' to 'col' for writing
            writer.writerow({'row': item['r'], 'col': item['c']})


@app.get("/grid/manifest")
async def grid_manifest():
    """
    JSON inventory of files + size + mtime.
    Frontend can poll this before downloading to detect updates.
    """
    items = []
    # Note: We include the new JSON paths for completeness in the manifest
    for name, path, mime in [
        (GRID_IMAGE_NAME, GRID_IMAGE_PATH, "image/png"),
        (GRID_COORDS_NAME, GRID_COORDS_PATH, "text/csv"),
        (GRID_OBS_NAME, GRID_OBS_PATH, "text/csv"),
    ]:
        exists = _exists(path)
        base_path = f"/grid/{'image' if mime.startswith('image/') else ('coordinates' if name==GRID_COORDS_NAME else 'obstacles')}"
        
        items.append({
            "name": name,
            "exists": exists,
            "path_csv": base_path,
            "path_json": f"{base_path}/json",
            "mime": mime,
            "size_bytes": os.path.getsize(path) if exists else None,
            "mtime": int(os.path.getmtime(path)) if exists else None,
        })
    return JSONResponse({"directory": os.path.abspath(GRID_DIR), "files": items}, headers=_nocache_headers())

@app.get("/grid/image")
async def get_grid_image():
    if not _exists(GRID_IMAGE_PATH):
        return _not_found(GRID_IMAGE_NAME)
    return FileResponse(
        GRID_IMAGE_PATH,
        media_type="image/jpeg", # Assuming .jpg is JPEG, but your tool saves as .jpg
        filename=GRID_IMAGE_NAME,
        headers=_nocache_headers(),
    )

@app.get("/grid/coordinates")
async def get_grid_coordinates():
    if not _exists(GRID_COORDS_PATH):
        return _not_found(GRID_COORDS_NAME)
    return FileResponse(
        GRID_COORDS_PATH,
        media_type="text/csv",
        filename=GRID_COORDS_NAME,
        headers=_nocache_headers(),
    )

@app.get("/grid/coordinates/json")
async def get_grid_coordinates_json():
    """Returns grid coordinates as a JSON array."""
    data = _parse_coords_csv(GRID_COORDS_PATH)
    if not data:
        return _not_found(GRID_COORDS_NAME)
    # The JSONResponse handles serialization automatically
    return JSONResponse(
        {"data": data},
        headers=_nocache_headers(),
    )

@app.get("/grid/obstacles")
async def get_grid_obstacles():
    if not _exists(GRID_OBS_PATH):
        return _not_found(GRID_OBS_NAME)
    return FileResponse(
        GRID_OBS_PATH,
        media_type="text/csv",
        filename=GRID_OBS_NAME,
        headers=_nocache_headers(),
    )

@app.get("/grid/obstacles/json")
async def get_grid_obstacles_json():
    """Returns obstacle coordinates (r, c) as a JSON array."""
    data = _parse_obstacles_csv(GRID_OBS_PATH)
    if not data:
        return _not_found(GRID_OBS_NAME)
    return JSONResponse(
        {"data": data},
        headers=_nocache_headers(),
    )

@app.put("/grid/obstacles")
async def put_grid_obstacles(obstacles: List[Dict[str, int]] = Body(..., media_type="application/json")):
    """
    Receives a JSON list of {'r': int, 'c': int} objects and overwrites obstacles.csv.
    The frontend should send the COMPLETE list of obstacles currently desired.
    """
    cleaned_data = []
    
    # 1. Validate and clean incoming data
    for obs in obstacles:
        if isinstance(obs, dict) and 'r' in obs and 'c' in obs:
            try:
                # Ensure the data is truly integer-based for row/col
                cleaned_data.append({'r': int(obs['r']), 'c': int(obs['c'])})
            except (ValueError, TypeError):
                # Optionally log error for bad data structure
                continue
    
    # 2. Handle case where all input was invalid, but list was provided
    if not cleaned_data and obstacles:
         return JSONResponse({"error": "Invalid input format. Expected list of {'r': int, 'c': int}."}, status_code=400)

    # 3. Write data to CSV file
    _write_obstacles_csv(GRID_OBS_PATH, cleaned_data)
    
    # 4. Return success response
    return JSONResponse(
        {"status": "Obstacles updated successfully", "count": len(cleaned_data)},
        headers=_nocache_headers(),
    )

@app.get("/grid/bundle")
async def get_grid_bundle():
    """
    Streams a ZIP containing current_image.jpg + grid_coordinates.csv + obstacles.csv.
    Missing files are omitted; returns 404 if none exist.
    """
    files = []
    if _exists(GRID_IMAGE_PATH):  files.append((GRID_IMAGE_PATH, GRID_IMAGE_NAME))
    if _exists(GRID_COORDS_PATH): files.append((GRID_COORDS_PATH, GRID_COORDS_NAME))
    if _exists(GRID_OBS_PATH):    files.append((GRID_OBS_PATH, GRID_OBS_NAME))

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

# -------- WebSocket (unchanged)

@app.websocket(WS_PATH)
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    last_sent_instructions = ""

    try:
        while True:
            # Receive protobuf bytes with 1s timeout
            try:
                data = await asyncio.wait_for(websocket.receive_bytes(), timeout=1.0)
                status = handle_client_message(data)  # -> circesoft_pb2.CurrentStatus
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


if __name__ == "__main__":
    uvicorn.run("app:app", host=APP_HOST, port=APP_PORT, reload=False)

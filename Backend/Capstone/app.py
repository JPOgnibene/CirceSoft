import asyncio
import io
import os
import time
import zipfile
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import PlainTextResponse, FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn

from receiver import handle_client_message
from protos import circesoft_pb2

load_dotenv()

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8765"))
WS_PATH = os.getenv("WS_PATH", "/ws")
CURRENT_VALUES_PATH = os.getenv("CURRENT_VALUES_PATH", "./data/current_values.txt")
DIRECTIONS_PATH = os.getenv("DIRECTIONS_PATH", "./data/directions.txt")

# ====== New: grid artifacts config ======
# Directory and filenames produced by your field_grid_tool.py (or equivalent)
GRID_DIR = os.getenv("GRID_DIR", "./")  # e.g. ./AI-Pathfinding/image-interpretation/test1
GRID_IMAGE_NAME = os.getenv("GRID_IMAGE_NAME", "current_image.jpg")
GRID_COORDS_NAME = os.getenv("GRID_COORDS_NAME", "grid_coordinates.csv")
GRID_OBS_NAME = os.getenv("GRID_OBS_NAME", "obstacles.csv")

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

# -------- New: Grid artifact helpers + endpoints --------

def _exists(path: str) -> bool:
    return os.path.exists(path) and os.path.isfile(path)

def _not_found(name: str) -> JSONResponse:
    return JSONResponse({"error": f"{name} not found"}, status_code=404)

def _nocache_headers() -> dict:
    # Prevent stale images/CSVs in browsers/Proxies
    return {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }

@app.get("/grid/manifest")
async def grid_manifest():
    """
    JSON inventory of files + size + mtime.
    Frontend can poll this before downloading to detect updates.
    """
    items = []
    for name, path, mime in [
        (GRID_IMAGE_NAME, GRID_IMAGE_PATH, "image/png"),
        (GRID_COORDS_NAME, GRID_COORDS_PATH, "text/csv"),
        (GRID_OBS_NAME, GRID_OBS_PATH, "text/csv"),
    ]:
        exists = _exists(path)
        items.append({
            "name": name,
            "exists": exists,
            "path": f"/grid/{'image' if mime.startswith('image/') else ('coordinates' if name==GRID_COORDS_NAME else 'obstacles')}",
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
        media_type="image/png",
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

# -------- WebSocket

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

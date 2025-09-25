import asyncio
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware  # Add this import
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

app = FastAPI(title="CirceSoft Control Server", version="1.0")

# Add CORS middleware - ADD THESE LINES
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
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

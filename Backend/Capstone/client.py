import asyncio
import websockets
import sys
import os
from dotenv import load_dotenv
from sender import build_client_status_from_file

load_dotenv()

DEFAULT_WS_URL = os.getenv("WS_URL", "ws://localhost:8765/ws")
CURRENT_VALUES_PATH = os.getenv("CURRENT_VALUES_PATH", "./data/current_values.txt")
DIRECTIONS_PATH = os.getenv("DIRECTIONS_PATH", "./data/directions.txt")


async def communicate(ws_url: str):
    last_sent_state: bytes | None = None
    print(f"Connecting to {ws_url} ...")

    async with websockets.connect(ws_url) as ws:
        while True:
            # Send status if changed
            if os.path.exists(CURRENT_VALUES_PATH):
                current_state = build_client_status_from_file(CURRENT_VALUES_PATH)
                if current_state != last_sent_state:
                    await ws.send(current_state)
                    print("Sent new client state")
                    last_sent_state = current_state

            # Receive directions (text preferred)
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                if isinstance(message, (bytes, bytearray)):
                    try:
                        text = message.decode("utf-8", errors="ignore")
                    except Exception:
                        text = ""
                else:
                    text = str(message)

                if text:
                    os.makedirs(os.path.dirname(DIRECTIONS_PATH), exist_ok=True)
                    with open(DIRECTIONS_PATH, "w") as f:
                        f.write(text)
                    print("New instructions received and written to directions.txt")
            except asyncio.TimeoutError:
                pass

            await asyncio.sleep(1)


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        arg = sys.argv[1]
        if arg.startswith("ws://") or arg.startswith("wss://"):
            url = arg
        else:
            host, _, port = arg.partition(":")
            port = port or "8765"
            url = f"ws://{host}:{port}/ws"
    else:
        url = DEFAULT_WS_URL

    asyncio.run(communicate(url))

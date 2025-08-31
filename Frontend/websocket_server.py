import asyncio
import websockets

async def echo(websocket, path):
    print(f"Client connected from {path}")
    await websocket.send("Hello from Raspberry Pi WebSocket Server!")
    try:
        while True:
            message = await websocket.recv()  # Receive message from client
            print(f"Received message: {message}")
            await websocket.send(f"Echo: {message}")  # Send the same message back
    except websockets.ConnectionClosed:
        print("Client disconnected")

# Start the server
async def main():
    server = await websockets.serve(echo, "localhost", 8765)
    print("WebSocket server running on ws://localhost:8765")
    await server.wait_closed()

# Run the event loop
asyncio.run(main())

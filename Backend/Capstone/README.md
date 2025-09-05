# CirceSoft FastAPI + WebSocket (protobuf) Demo

This project provides a FastAPI server with a WebSocket endpoint that exchanges protobuf messages with a simple client. It mirrors incoming status to `data/current_values.txt` and pushes outbound directions from `data/directions.txt` when they change.

## 1) Install
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2) Generate protobufs
You need `protoc` installed (e.g., via `brew install protobuf`, `apt-get install protobuf-compiler`, or the official releases).
```bash
bash scripts/gen_protos.sh
```
This produces `protos/circesoft_pb2.py`.

## 3) Run server
```bash
python app.py
```
Server: WebSocket on `ws://0.0.0.0:8765/ws` and REST:
- `GET  /health`
- `GET  /current-values`
- `GET  /directions`
- `PUT  /directions` (raw text body)

## 4) Run client
```bash
# Option A: full URL
python client.py ws://localhost:8765/ws

# Option B: host or host:port (\"/ws\" is appended)
python client.py localhost
python client.py localhost:8765
```

## 5) Try it
- Edit `data/current_values.txt` to trigger a send (client → server).
- Update directions via REST:
  ```bash
  curl -X PUT --data-binary @- http://localhost:8765/directions <<<'TURN_LEFT=15\nSPEED=2.0'
  ```
  The server will push to the client; the client writes to `data/directions.txt`.

## Env vars (optional)
See `.env.example`. The server and client read env vars if provided.
```
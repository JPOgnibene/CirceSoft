# CirceSoft FastAPI + WebSocket Server

This project provides a modular, stateful FastAPI server featuring a WebSocket endpoint for real-time communication (using Protobufs) and robust REST endpoints for managing grid artifacts and robot state.

## 1\) Modular Structure

The application is split into multiple files for better organization and maintainability:

| File | Purpose |
| :--- | :--- |
| `app.py` | The main execution/launcher file. |
| `config.py` | Defines all environment variables, constants, and file paths. |
| `models.py` | Contains placeholder models (e.g., `circesoft_pb2`) and global state variables. |
| `utils.py` | Houses core logic, including cable distance tracking, file I/O helpers, CSV parsers, and the **motion detection logic**. |
| `routes.py` | Defines all REST and WebSocket API endpoints using `APIRouter`. |

## 2\) Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 3\) Generate Protobufs

You need `protoc` installed (e.g., via `brew install protobuf` or `apt-get install protobuf-compiler`).

```bash
bash scripts/gen_protos.sh
```

This produces `protos/circesoft_pb2.py`.

## 4\) Run Server

Start the application using the main launcher file:

```bash
python app.py
```

### Server Endpoints

The server runs on `http://0.0.0.0:8765/`.

| Category | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Status** | `GET` | `/health` | Health check. |
| | `GET` | `/current-values` | Retrieves robot status from a file. |
| | `GET`/`PUT` | `/directions` | Manages outbound commands (PUT accepts raw text). |
| **Grid** | `GET` | `/grid/manifest` | JSON inventory of all grid files. |
| | `GET` | `/grid/image` | Grid image file. |
| | `GET` | `/grid/coordinates` | Grid coordinates CSV file. |
| | `GET`/`PUT` | `/grid/obstacles` | Obstacle data (CSV and JSON endpoints available). |
| | `GET`/`PUT` | **`/grid/path`** | **Navigation path data** (CSV and JSON endpoints available). |
| **Real-time** | `WS` | `/ws` | WebSocket connection for status updates and directions. |

## 5\) Try It: REST Examples

### Grid Path Management (PUT Example)

The `/grid/path` endpoint now manages the navigation path using JSON data:

```bash
# 1. Get current path as JSON
curl -X GET http://localhost:8765/grid/path/json

# 2. Set a new path (list of row/column coordinates)
curl -X PUT -H "Content-Type: application/json" -d '[{"r": 5, "c": 5}, {"r": 6, "c": 6}, {"r": 7, "c": 7}]' http://localhost:8765/grid/path
```

### Directions Management

```bash
# Update directions via REST:
curl -X PUT --data-binary @- http://localhost:8765/directions <<<'TURN_LEFT=15\nSPEED=2.0'
```

## 6\) Client Connection

```bash
# Option A: full URL
python client.py ws://localhost:8765/ws

# Option B: host or host:port (" /ws " is appended)
python client.py localhost
```

## Environment Variables (Optional)

See `.env.example`. Configuration, including host, port, and file paths, is managed via environment variables and loaded in `config.py`.

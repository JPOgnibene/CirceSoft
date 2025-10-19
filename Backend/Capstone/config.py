# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- App Config ---
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8765"))
WS_PATH = os.getenv("WS_PATH", "/ws")
CORS_ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "*")

# --- File Paths ---
CURRENT_VALUES_PATH = os.getenv("CURRENT_VALUES_PATH", "./data/current_values.txt")
DIRECTIONS_PATH = os.getenv("DIRECTIONS_PATH", "./data/directions.txt")

# --- Grid artifacts config ---
GRID_DIR = os.getenv("GRID_DIR", "./")
GRID_IMAGE_NAME = os.getenv("GRID_IMAGE_NAME", "current_image.jpg")
GRID_COORDS_NAME = os.getenv("GRID_COORDS_NAME", "grid_coordinates.csv")
GRID_OBS_NAME = os.getenv("GRID_OBS_NAME", "obstacles.csv")
GRID_PATH_NAME = os.getenv("GRID_PATH_NAME", "path.csv")

# Full Paths
GRID_IMAGE_PATH = os.path.join(GRID_DIR, GRID_IMAGE_NAME)
GRID_COORDS_PATH = os.path.join(GRID_DIR, GRID_COORDS_NAME)
GRID_OBS_PATH = os.path.join(GRID_DIR, GRID_OBS_NAME)
GRID_PATH_PATH = os.path.join(GRID_DIR, GRID_PATH_NAME)
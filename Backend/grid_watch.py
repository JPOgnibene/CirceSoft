#!/usr/bin/env python3
"""
watch_grid_astar.py
Watches the grid/obstacle CSVs and re-runs grid_astar.py
whenever either file changes.

Requirements:
    pip install watchdog

Usage:
    python watch_grid_astar.py
"""

import subprocess
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os

# Hardcoded CSV paths (must match those in grid_astar_from_csv_hardcoded.py)
GRID_CSV_PATH = "C:\\Users\\JP\\Desktop\\CSC Work\\Classes\\CSC4610\\grid_coordinates.csv"
OBSTACLES_CSV_PATH = "C:\\Users\\JP\\Desktop\\CSC Work\\Classes\\CSC4610\\obstacles.csv"

# Path to the A* script
ASTAR_SCRIPT = "C:\\Users\\JP\\Desktop\\CSC Work\\Classes\\CSC4610\\grid_astar.py"

# Extra args to pass to A* (edit to taste)
ASTAR_ARGS = ["--diagonal", "--png-out", "watched_path.png", "--grid-lines"]

class CSVChangeHandler(FileSystemEventHandler):
    def __init__(self, grid_path, obs_path):
        super().__init__()
        self.grid_path = os.path.abspath(grid_path)
        self.obs_path = os.path.abspath(obs_path)

    def on_modified(self, event):
        if not event.is_directory:
            changed = os.path.abspath(event.src_path)
            if changed in (self.grid_path, self.obs_path):
                print(f"[watcher] Change detected in {changed}")
                self.run_astar()

    def run_astar(self):
        try:
            cmd = ["python", ASTAR_SCRIPT] + ASTAR_ARGS
            print(f"[watcher] Running: {' '.join(cmd)}")
            proc = subprocess.run(cmd, text=True, capture_output=True)
            print(proc.stdout)
            if proc.stderr:
                print(proc.stderr)
        except Exception as e:
            print(f"[watcher] Error running astar: {e}")

def main():
    grid_abs = os.path.abspath(GRID_CSV_PATH)
    obs_abs = os.path.abspath(OBSTACLES_CSV_PATH)

    event_handler = CSVChangeHandler(grid_abs, obs_abs)
    observer = Observer()
    for path in {os.path.dirname(grid_abs), os.path.dirname(obs_abs)}:
        observer.schedule(event_handler, path, recursive=False)

    observer.start()
    print(f"[watcher] Watching {grid_abs} and {obs_abs}")
    print("[watcher] Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()

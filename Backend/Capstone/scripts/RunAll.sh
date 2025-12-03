#!/bin/bash
set -e

# --- 1. Start the Backend API (Uvicorn) ---
# Using the absolute path inside the container: /usr/src/app/Capstone/app.py
echo "Starting Backend API..."
python /usr/src/app/Capstone/app.py & 
sleep 2

# --- 2. Start the A* Pathing Receiver Executable ---
# Executable is at /usr/src/app/grid_astar
echo "Starting A* Pathing Receiver..."
/usr/src/app/grid_astar &
sleep 1

# --- 3. Start the Simulation Executable ---
# Executable is at /usr/src/app/simulatedSimulator
echo "Starting Simulation Worker..."
/usr/src/app/simulatedSimulator &

# --- 4. Keep the container alive ---
# The 'wait' command keeps the container running until all background jobs exit.
wait

FROM python:3.9-slim

ENV PYTHONUNBUFFERED 1
# Set the initial WORKDIR to the root of the application inside the container
WORKDIR /usr/src/app

# --- 1. Copy Application Components (from CirceSoft root context) ---
# Copy Backend Python code and requirements to ./Capstone/
COPY Backend/Capstone/ ./Capstone/

# Copy Executables to the current WORKDIR (/usr/src/app)
COPY Executables/grid_astar ./grid_astar
COPY Executables/simulatedSimulator ./simulatedSimulator

# --- 2. Install Dependencies & Set Permissions ---
# Make executables and the new run script (RunAll.sh) runnable
# The script is located at ./Capstone/scripts/RunAll.sh
RUN chmod +x ./grid_astar ./simulatedSimulator ./Capstone/scripts/RunAll.sh

# Install Python Dependencies
WORKDIR /usr/src/app/Capstone
RUN pip install --no-cache-dir -r requirements.txt

# Reset WORKDIR to the root for easier CMD execution
WORKDIR /usr/src/app

# --- 3. Expose Ports ---
EXPOSE 8000 8765

# --- 4. Define the Entry Command ---
# Set the entrypoint to the new multi-process script.
CMD ["./Capstone/scripts/RunAll.sh"]

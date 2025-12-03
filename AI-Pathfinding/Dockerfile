FROM python:3.9-slim

WORKDIR /app

# The build context is now the CirceSoft root, so we copy the file by its full path
# Path is: CirceSoft/Backend/Capstone/requirements.txt
COPY Backend/Capstone/requirements.txt requirements.txt

# Install dependencies (fixes ModuleNotFoundError: No module named 'aiohttp')
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the AI-Pathfinding files
# Path is: CirceSoft/AI-Pathfinding/ contents
COPY AI-Pathfinding/ . 

CMD ["python", "grid_astar.py"]

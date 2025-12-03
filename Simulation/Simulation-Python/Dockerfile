FROM python:3.9-slim

WORKDIR /app

# The build context is now the CirceSoft root, so we copy the file by its full path
# Path is: CirceSoft/Backend/Capstone/requirements.txt
COPY Backend/Capstone/requirements.txt requirements.txt

# Install dependencies (fixes ModuleNotFoundError: No module named 'aiohttp')
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the Simulation files
# Path is: CirceSoft/Simulation/Simulation-Python/ contents
COPY Simulation/Simulation-Python/ .

CMD ["python", "simulatedSimulator.py"]

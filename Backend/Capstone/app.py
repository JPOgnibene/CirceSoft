# app.py
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Import modules
from config import APP_HOST, APP_PORT, CORS_ALLOW_ORIGINS
from routes import router

# --- Application Initialization ---

app = FastAPI(title="CirceSoft Control Server", version="1.0")

# 1. Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Include the API router
app.include_router(router)

# --- Server Startup ---

if __name__ == "__main__":
    # Note: Uvicorn is told to run the 'app' object inside this file ('app:app')
    uvicorn.run("app:app", host=APP_HOST, port=APP_PORT, reload=False)
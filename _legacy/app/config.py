# app/config.py
import os

API_HOST = os.environ.get("API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("API_PORT", "8015"))  # <— change here if you want a different default
BACKEND_BASE_URL = os.environ.get("BACKEND_BASE_URL", f"http://{API_HOST}:{API_PORT}")

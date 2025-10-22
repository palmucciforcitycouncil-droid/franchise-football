# tests/utils/api_base.py
import os
def api():
    return os.environ.get("BACKEND_BASE_URL", "http://127.0.0.1:8015").rstrip("/")

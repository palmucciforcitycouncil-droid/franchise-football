# Franchise Football

A text-based American football management simulator.  
Built with Python 3.11, FastAPI, SQLModel (SQLite), and pytest.

---

## Quick Start (Windows)

### 1. Clone & Install
```cmd
git clone <your-repo-url>
cd franchise-football
python -m venv .venv
.\.venv\Scripts\activate
pip install -U pip
pip install -e .
```

### 2. Start Backend
```cmd
python -m uvicorn app.main:app --port 8015 --reload
```

### 3. Health Check
Visit http://127.0.0.1:8015/diag/health

Note: The backend uses port 8015 by default. Environment variables in `.env.local` control the base URL for tests and development tools.

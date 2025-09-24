@echo off
setlocal
cd /d "%~dp0\.."
if not exist .venv\Scripts\python.exe (
  echo [!] Missing venv. Create/activate your venv and install deps first.
  exit /b 1
)
echo Starting Score Fidelity API at http://127.0.0.1:8081 ...
.venv\Scripts\python.exe -m uvicorn scripts.api_score_app:app --host 127.0.0.1 --port 8081 --reload
endlocal

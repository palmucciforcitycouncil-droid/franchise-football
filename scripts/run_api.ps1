# scripts/run_api.ps1
param([int]$Port = 8000)
Set-Location "$PSScriptRoot\.."
if (-not (Test-Path ".\.venv")) { py -3 -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port $Port

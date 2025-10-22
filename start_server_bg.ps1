# Start FastAPI Server in Background Script
# This script ensures the server always starts from the correct directory in background

Set-Location "C:\Users\bpalm\Documents\franchise-football"

# Set environment variables
$env:USE_PBP_V2 = "false"
$env:HFA_POINTS = "1.4"

# Start the server in background
Start-Process -FilePath "py" -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8011" -WindowStyle Hidden

Write-Host "Server started in background on port 8011"
Write-Host "Check status: Invoke-WebRequest -Uri 'http://127.0.0.1:8011/' -Method GET"

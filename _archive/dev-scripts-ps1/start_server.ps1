# Start FastAPI Server Script
# This script ensures the server always starts from the correct directory

Set-Location "C:\Users\bpalm\Documents\franchise-football"

# Set environment variables
$env:USE_PBP_V2 = "false"
$env:HFA_POINTS = "1.4"

# Start the server
py -m uvicorn app.main:app --host 127.0.0.1 --port 8011

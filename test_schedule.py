import requests
import json

# Test the schedule endpoint and try to get more error details
try:
    response = requests.post("http://127.0.0.1:8011/api/sim/schedule-all/2026")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")


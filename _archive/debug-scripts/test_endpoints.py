import requests
import json

base_url = "http://127.0.0.1:8011"

# First, check if teams exist
try:
    # Test if we can access a simpler endpoint
    response = requests.get(f"{base_url}/")
    print(f"Root endpoint: {response.status_code}")
    
    # Try the simple schedule endpoint (Week 1 only)
    response = requests.post(f"{base_url}/api/sim/schedule/2026")
    print(f"Simple schedule (Week 1): {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Now try the full schedule
    response = requests.post(f"{base_url}/api/sim/schedule-all/2026")
    print(f"Full schedule: {response.status_code}")
    if response.status_code == 200:
        print(f"Success: {response.json()}")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")


# scripts/test_dashboard_api.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.api.routes.dashboard import router
from fastapi import FastAPI

def main():
    print("=== DASHBOARD API TEST ===")
    
    # Create a minimal app with just the dashboard router
    app = FastAPI()
    app.include_router(router)
    
    client = TestClient(app)
    
    # Test dashboard tiles endpoint
    print("\n1. Testing dashboard tiles endpoint...")
    r = client.get("/dashboard/2025?top_n=3")
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   Season: {data.get('season')}")
        print(f"   Summary: {data.get('summary')}")
        print(f"   Awards MVP: {data.get('awards', {}).get('MVP')}")
        print(f"   Progression risers: {len(data.get('progression', {}).get('risers', []))}")
    else:
        print(f"   Error: {r.text}")
    
    # Test trends endpoint
    print("\n2. Testing trends endpoint...")
    r2 = client.get("/dashboard/trends?start=2025&end=2025")
    print(f"   Status: {r2.status_code}")
    if r2.status_code == 200:
        data2 = r2.json()
        print(f"   Start: {data2.get('start')}")
        print(f"   End: {data2.get('end')}")
        print(f"   Seasons count: {len(data2.get('seasons', []))}")
    else:
        print(f"   Error: {r2.text}")
    
    # Test error handling
    print("\n3. Testing error handling...")
    r3 = client.get("/dashboard/9999")
    print(f"   Non-existent season status: {r3.status_code}")
    
    r4 = client.get("/dashboard/trends?start=2025&end=2024")
    print(f"   Invalid range status: {r4.status_code}")
    
    print("\n=== API TEST COMPLETE ===")

if __name__ == "__main__":
    main()

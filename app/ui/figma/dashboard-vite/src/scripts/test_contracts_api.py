# scripts/test_contracts_api.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.api.routes.contracts_fa import router
from fastapi import FastAPI

def main():
    # Create a minimal app with just the contracts router
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    # Test team contracts endpoint
    print("=== Testing Team Contracts Endpoint ===")
    resp = client.get("/contracts/2025/team/1")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Team: {data['team_id']}")
        print(f"Season: {data['season']}")
        print(f"Cap data: {data['cap']}")
        print(f"Contracts: {len(data['contracts'])}")
    else:
        print(f"Error: {resp.text}")
    
    # Test free agents endpoint
    print("\n=== Testing Free Agents Endpoint ===")
    resp = client.get("/free_agency/2025/players")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Free agents: {len(data)}")
    else:
        print(f"Error: {resp.text}")
    
    # Test expire contracts endpoint
    print("\n=== Testing Expire Contracts Endpoint ===")
    resp = client.post("/contracts/2026/expire")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Expired: {data['expired']}")
        print(f"Moved to FA: {data['moved_to_fa']}")
    else:
        print(f"Error: {resp.text}")

if __name__ == "__main__":
    main()

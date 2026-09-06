# scripts/test_cap_resign_api.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.api.routes.cap_resign import router
from fastapi import FastAPI

def main():
    # Create a minimal app with just the cap_resign router
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    # Test cap initialization
    print("=== Testing Cap Initialization ===")
    resp = client.post("/cap/2026/init")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Teams: {data['teams']}")
        print(f"Rows written: {data['rows_written']}")
    else:
        print(f"Error: {resp.text}")
    
    # Test cap for team
    print("\n=== Testing Cap for Team ===")
    resp = client.get("/cap/2026/team/1")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Cap limit: {data['cap']['cap_limit']}")
        print(f"Cap used: {data['cap']['cap_used']}")
        print(f"Contracts: {len(data['contracts'])}")
    else:
        print(f"Error: {resp.text}")
    
    # Test re-sign candidates
    print("\n=== Testing Re-sign Candidates ===")
    resp = client.get("/contracts/2026/resign/candidates")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Candidates: {len(data)}")
        if data:
            print(f"First candidate: {data[0]}")
    else:
        print(f"Error: {resp.text}")
    
    # Test re-sign bid
    print("\n=== Testing Re-sign Bid ===")
    resp = client.post("/contracts/2026/resign/bid", json={"team_id": 2, "player_id": 3, "aav": 300, "years": 2})
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Status: {data['status']}")
        print(f"Offer ID: {data['offer_id']}")
    else:
        print(f"Error: {resp.text}")
    
    # Test re-sign simulation
    print("\n=== Testing Re-sign Simulation ===")
    resp = client.post("/contracts/2026/resign/simulate")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Signed: {data['signed']}")
        print(f"Skipped no offer: {data['skipped_no_offer']}")
        print(f"Skipped no cap: {data['skipped_no_cap']}")
        print(f"Skipped already signed: {data['skipped_already_signed']}")
    else:
        print(f"Error: {resp.text}")

if __name__ == "__main__":
    main()



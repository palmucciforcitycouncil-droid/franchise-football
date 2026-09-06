# scripts/test_existing_player_tabs.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.api.routes.player_tabs import router
from fastapi import FastAPI

def main():
    # Create a minimal app with just the player tabs router
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    # Test with existing player ID 1
    player_id = 1
    
    # Test awards endpoint
    print(f"\n=== Testing Awards Endpoint for Player {player_id} ===")
    ra = client.get(f"/players/{player_id}/awards")
    print(f"Status: {ra.status_code}")
    if ra.status_code == 200:
        awards_data = ra.json()
        print(f"Awards: {awards_data}")
    else:
        print(f"Error: {ra.text}")
    
    # Test progression endpoint
    print(f"\n=== Testing Progression Endpoint for Player {player_id} ===")
    rp = client.get(f"/players/{player_id}/progression")
    print(f"Status: {rp.status_code}")
    if rp.status_code == 200:
        prog_data = rp.json()
        print(f"Progression: {prog_data}")
    else:
        print(f"Error: {rp.text}")
    
    # Test non-existent player
    print("\n=== Testing Non-existent Player ===")
    ra_404 = client.get("/players/99999/awards")
    print(f"Awards 404 status: {ra_404.status_code}")
    
    rp_404 = client.get("/players/99999/progression")
    print(f"Progression 404 status: {rp_404.status_code}")

if __name__ == "__main__":
    main()



# scripts/test_career_api.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.api.routes.player_career import router
from fastapi import FastAPI

def main():
    # Create a minimal app with just the player career router
    app = FastAPI()
    app.include_router(router)
    
    client = TestClient(app)
    
    # Test the career summary endpoint
    resp = client.get("/players/189/career_summary")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Player: {data['player']['name']}")
        print(f"Position: {data['player']['position']}")
        print(f"Total games: {data['totals']['games']}")
        print(f"Total pass yards: {data['totals']['pass_yards']}")
        print(f"Seasons: {len(data['seasons'])}")
        print(f"Teams: {data['teams']}")
    else:
        print(f"Error: {resp.text}")
    
    # Test non-existent player
    resp2 = client.get("/players/99999/career_summary")
    print(f"\nNon-existent player status: {resp2.status_code}")
    print(f"Error message: {resp2.json()['detail']}")

if __name__ == "__main__":
    main()



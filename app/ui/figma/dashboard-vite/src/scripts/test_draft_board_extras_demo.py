# scripts/test_draft_board_extras_demo.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.api.routes.draft_integration import router
from fastapi import FastAPI
from app.db import get_engine
from app.services.draft import generate_draft_class
from sqlmodel import Session

def main():
    # Create a test draft class
    season = 2025
    eng = get_engine()
    with Session(eng) as s:
        generate_draft_class(s, season, seed=12345)
    
    # Create a minimal app with just the draft router
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    print("=== Draft Board Extras Demo ===\n")
    
    # Test enhanced draft board
    print("1. Enhanced Draft Board (with search, sort, filters):")
    resp = client.get(f"/draft/{season}/board?limit=5&sort_by=overall&sort_order=desc")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Found {len(data)} prospects")
        for i, prospect in enumerate(data[:3]):
            print(f"  {i+1}. {prospect['name']} ({prospect['pos']}) - Overall: {prospect['overall']}, Tier: {prospect['tier']}, Pos Rank: {prospect['positional_rank']}")
    
    # Test best available
    print("\n2. Best Available Prospects:")
    resp = client.get(f"/draft/{season}/best-available?limit=5")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Found {len(data)} best available prospects")
        for i, prospect in enumerate(data[:3]):
            print(f"  {i+1}. {prospect['name']} ({prospect['pos']}) - Overall: {prospect['overall']}, Tier: {prospect['tier']}")
    
    # Test positional tiers
    print("\n3. Positional Tiers:")
    resp = client.get(f"/draft/{season}/positional-tiers")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print("Tiers by position:")
        for pos, tiers in list(data.items())[:2]:  # Show first 2 positions
            print(f"  {pos}:")
            for tier_name, prospects in tiers.items():
                if prospects:
                    print(f"    {tier_name}: {len(prospects)} prospects")
    
    # Test draft stats
    print("\n4. Draft Statistics:")
    resp = client.get(f"/draft/{season}/stats")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Total prospects: {data['total_prospects']}")
        print(f"Drafted: {data['drafted']}")
        print(f"Available: {data['available']}")
        print(f"Draft percentage: {data['draft_percentage']:.1f}%")
        print(f"Average overall: {data['average_overall']}")
        print("Tier breakdown:")
        for tier, count in data['tier_breakdown'].items():
            if count > 0:
                print(f"  {tier}: {count}")
    
    # Test search functionality
    print("\n5. Search Functionality:")
    resp = client.get(f"/draft/{season}/board?search=QB&limit=3")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Found {len(data)} prospects matching 'QB'")
        for prospect in data[:2]:
            print(f"  - {prospect['name']} ({prospect['pos']}) - Overall: {prospect['overall']}")
    
    # Test tier filtering
    print("\n6. Tier Filtering:")
    resp = client.get(f"/draft/{season}/board?tier=Elite&limit=3")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Found {len(data)} Elite prospects")
        for prospect in data[:2]:
            print(f"  - {prospect['name']} ({prospect['pos']}) - Overall: {prospect['overall']}")
    
    # Test position filtering
    print("\n7. Position Filtering:")
    resp = client.get(f"/draft/{season}/board?pos=WR&limit=3")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Found {len(data)} WR prospects")
        for prospect in data[:2]:
            print(f"  - {prospect['name']} ({prospect['pos']}) - Overall: {prospect['overall']}, Tier: {prospect['tier']}")
    
    print("\n=== Demo Complete ===")

if __name__ == "__main__":
    main()



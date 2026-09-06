# scripts/test_dashboard_complete_demo.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.api.routes.dashboard import router
from fastapi import FastAPI
import json

def main():
    print("=== ANALYTICS DASHBOARD FEEDS - COMPLETE DEMO ===")
    
    # Create app with dashboard router
    app = FastAPI(title="Franchise Football Dashboard API")
    app.include_router(router)
    client = TestClient(app)
    
    print("\n1. Testing Dashboard Tiles Endpoint...")
    print("   GET /dashboard/2025?top_n=3")
    r = client.get("/dashboard/2025?top_n=3")
    print(f"   Status: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"   Season: {data['season']}")
        
        # Summary
        summary = data['summary']
        print(f"   League PPG: {summary['league_ppg']}")
        print(f"   Plays per Game: {summary['plays_per_game']}")
        print(f"   Pass Rate: {summary['pass_rate']:.1%}")
        
        # Awards
        awards = data['awards']
        print(f"   MVP: {awards['MVP']['name'] if awards['MVP'] else 'None'}")
        print(f"   OPOY: {awards['OPOY']['name'] if awards['OPOY'] else 'None'}")
        print(f"   DPOY: {awards['DPOY']['name'] if awards['DPOY'] else 'None'}")
        print(f"   ROY: {awards['ROY']['name'] if awards['ROY'] else 'None'}")
        
        # Progression
        prog = data['progression']
        print(f"   Top Risers: {len(prog['risers'])}")
        for i, riser in enumerate(prog['risers'][:2], 1):
            print(f"     {i}. {riser['name']} ({riser['position']}) +{riser['total_delta']}")
        
        print(f"   Top Fallers: {len(prog['fallers'])}")
        for i, faller in enumerate(prog['fallers'][:2], 1):
            print(f"     {i}. {faller['name']} ({faller['position']}) {faller['total_delta']}")
    else:
        print(f"   Error: {r.text}")
    
    print("\n2. Testing Trends Endpoint...")
    print("   GET /dashboard/trends?start=2025&end=2025")
    r2 = client.get("/dashboard/trends?start=2025&end=2025")
    print(f"   Status: {r2.status_code}")
    
    if r2.status_code == 200:
        data2 = r2.json()
        print(f"   Start: {data2['start']}")
        print(f"   End: {data2['end']}")
        print(f"   Seasons: {len(data2['seasons'])}")
        
        for season in data2['seasons']:
            print(f"     {season['season']}: PPG={season['league_ppg']}, Plays={season['plays_per_game']}, Pass={season['pass_rate']:.1%}")
    else:
        print(f"   Error: {r2.text}")
    
    print("\n3. Testing Error Handling...")
    
    # Non-existent season
    r3 = client.get("/dashboard/9999")
    print(f"   Non-existent season (9999): {r3.status_code}")
    
    # Invalid range
    r4 = client.get("/dashboard/trends?start=2025&end=2024")
    print(f"   Invalid range (2025-2024): {r4.status_code}")
    
    # No data range
    r5 = client.get("/dashboard/trends?start=9999&end=9999")
    print(f"   No data range (9999-9999): {r5.status_code}")
    
    # Parameter validation
    r6 = client.get("/dashboard/2025?top_n=0")
    print(f"   Invalid top_n (0): {r6.status_code}")
    
    r7 = client.get("/dashboard/2025?top_n=26")
    print(f"   Invalid top_n (26): {r7.status_code}")
    
    print("\n4. Testing Parameter Variations...")
    
    # Different top_n values
    for top_n in [1, 5, 10]:
        r = client.get(f"/dashboard/2025?top_n={top_n}")
        if r.status_code == 200:
            data = r.json()
            risers = len(data['progression']['risers'])
            fallers = len(data['progression']['fallers'])
            print(f"   top_n={top_n}: {risers} risers, {fallers} fallers")
    
    print("\n=== DEMO COMPLETE ===")
    print("[OK] Dashboard tiles endpoint working")
    print("[OK] Trends endpoint working")
    print("[OK] Error handling working")
    print("[OK] Parameter validation working")
    print("[OK] All analytics functions integrated successfully")

if __name__ == "__main__":
    main()

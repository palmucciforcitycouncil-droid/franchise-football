# scripts/test_player_tabs_api.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.api.routes.player_tabs import router
from fastapi import FastAPI
from sqlmodel import Session, select
from app.db import get_engine
from app.models.core_min import Player
from app.models.awards import AwardResult
from app.models.progression import PlayerProgression

def main():
    # Create a minimal app with just the player tabs router
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    eng = get_engine()
    with Session(eng) as s:
        # Create a test player
        player = Player(name="Test Player", pos="QB", team_id=1, age=25, years_pro=3)
        s.add(player)
        s.commit()
        s.refresh(player)
        player_id = player.id
        print(f"Created test player with ID: {player_id}")
        
        # Create test award
        award = AwardResult(
            season=2025,
            award="MVP",
            rank=1,
            score=95.5,
            player_id=player_id,
            team_id=1,
            player_name="Test Player",
            position="QB"
        )
        s.add(award)
        
        # Create test progression
        progression = PlayerProgression(
            player_id=player_id,
            season=2025,
            before_json='{"awareness": 80, "speed": 75, "strength": 70, "throw_accuracy": 85, "throw_power": 90, "catching": 60, "tackling": 50, "agility": 70, "stamina": 80, "morale": 75}',
            after_json='{"awareness": 85, "speed": 78, "strength": 72, "throw_accuracy": 87, "throw_power": 92, "catching": 62, "tackling": 52, "agility": 72, "stamina": 82, "morale": 77}',
            components_json='{"age_curve": 2, "potential": 1, "awards": 0.5}'
        )
        s.add(progression)
        s.commit()
    
    # Test awards endpoint
    print("\n=== Testing Awards Endpoint ===")
    ra = client.get(f"/players/{player_id}/awards")
    print(f"Status: {ra.status_code}")
    if ra.status_code == 200:
        awards_data = ra.json()
        print(f"Awards: {awards_data}")
    else:
        print(f"Error: {ra.text}")
    
    # Test progression endpoint
    print("\n=== Testing Progression Endpoint ===")
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



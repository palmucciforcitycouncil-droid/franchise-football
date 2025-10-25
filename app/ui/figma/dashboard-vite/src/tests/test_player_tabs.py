# tests/test_player_tabs.py
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.api.routes.player_tabs import router
from fastapi import FastAPI
from app.db import get_engine
from app.models.core_min import Player
from app.models.awards import AwardResult
from app.models.progression import PlayerProgression
import json

def test_player_awards_and_progression_endpoints():
    """Test the player awards and progression endpoints with existing data."""
    # Create a minimal app with just the player tabs router
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    eng = get_engine()
    with Session(eng) as s:
        # Get an existing player
        player = s.exec(select(Player).order_by(Player.id)).first()
        if not player:
            # Create a test player if none exists
            player = Player(name="Test Player", pos="QB", team_id=1, age=25, years_pro=3)
            s.add(player)
            s.commit()
            s.refresh(player)
        
        player_id = player.id
        
        # Test awards endpoint (may be empty)
        ra = client.get(f"/players/{player_id}/awards")
        assert ra.status_code == 200
        awards_data = ra.json()
        assert isinstance(awards_data, list)
        
        # Test progression endpoint (may be empty)
        rp = client.get(f"/players/{player_id}/progression")
        assert rp.status_code == 200
        prog_data = rp.json()
        assert isinstance(prog_data, list)
        
        # If there's progression data, check structure
        if prog_data:
            item = prog_data[0]
            assert "season" in item
            assert "before" in item
            assert "after" in item
            assert "total_delta" in item
        
        # Test non-existent player
        ra_404 = client.get("/players/99999/awards")
        assert ra_404.status_code == 404
        
        rp_404 = client.get("/players/99999/progression")
        assert rp_404.status_code == 404

def test_player_tabs_with_existing_data():
    """Test with existing player data from the database."""
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    eng = get_engine()
    with Session(eng) as s:
        # Get an existing player
        player = s.exec(select(Player).order_by(Player.id)).first()
        if not player:
            # Create a test player if none exists
            player = Player(name="Test Player 2", pos="RB", team_id=2, age=24, years_pro=2)
            s.add(player)
            s.commit()
            s.refresh(player)
        
        player_id = player.id
        
        # Test awards endpoint (may be empty)
        ra = client.get(f"/players/{player_id}/awards")
        assert ra.status_code == 200
        awards_data = ra.json()
        assert isinstance(awards_data, list)
        
        # Test progression endpoint (may be empty)
        rp = client.get(f"/players/{player_id}/progression")
        assert rp.status_code == 200
        prog_data = rp.json()
        assert isinstance(prog_data, list)
        
        # If there's progression data, check structure
        if prog_data:
            item = prog_data[0]
            assert "season" in item
            assert "before" in item
            assert "after" in item
            assert "total_delta" in item
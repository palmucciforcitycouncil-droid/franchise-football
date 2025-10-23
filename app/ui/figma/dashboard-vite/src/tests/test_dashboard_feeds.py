# tests/test_dashboard_feeds.py
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.main import app
from app.db import get_engine
from app.testing.mini_season_runner import memory_db, run_mini_season
from app.services.stats.season_agg import aggregate_team_season, aggregate_player_season
from app.services.awards import compute_and_persist_awards
from app.services.progression import apply_progression_for_season

client = TestClient(app)

def _bootstrap(season:int, weeks:int=1):
    with memory_db() as session:
        run_mini_season(session, weeks=weeks)
        session.commit()
    with memory_db() as session:
        aggregate_team_season(session, season)
        aggregate_player_season(session, season)
        compute_and_persist_awards(session, season)
        apply_progression_for_season(session, season=season, seed=2025, force=True)

def test_dashboard_tiles_and_trends():
    """Test dashboard tiles and trends endpoints."""
    _bootstrap(2024, weeks=1)
    _bootstrap(2025, weeks=1)
    
    # Test dashboard tiles
    r = client.get("/dashboard/2025?top_n=5")
    assert r.status_code == 200
    data = r.json()
    assert data["season"] == 2025
    assert "summary" in data and "awards" in data and "progression" in data
    
    # Test trends
    r2 = client.get("/dashboard/trends?start=2024&end=2025")
    assert r2.status_code == 200
    tr = r2.json()
    assert tr["start"] == 2024 and tr["end"] == 2025
    assert len(tr["seasons"]) >= 1

def test_dashboard_tiles_structure():
    """Test that dashboard tiles have the expected structure."""
    _bootstrap(2025, weeks=1)
    
    r = client.get("/dashboard/2025")
    assert r.status_code == 200
    data = r.json()
    
    # Check summary structure
    summary = data["summary"]
    assert "season" in summary
    assert "league_ppg" in summary
    assert "plays_per_game" in summary
    assert "pass_rate" in summary
    
    # Check awards structure
    awards = data["awards"]
    assert "MVP" in awards
    assert "OPOY" in awards
    assert "DPOY" in awards
    assert "ROY" in awards
    
    # Check progression structure
    progression = data["progression"]
    assert "risers" in progression
    assert "fallers" in progression
    assert isinstance(progression["risers"], list)
    assert isinstance(progression["fallers"], list)

def test_dashboard_trends_structure():
    """Test that trends endpoint has the expected structure."""
    _bootstrap(2024, weeks=1)
    _bootstrap(2025, weeks=1)
    
    r = client.get("/dashboard/trends?start=2024&end=2025")
    assert r.status_code == 200
    data = r.json()
    
    assert "start" in data
    assert "end" in data
    assert "seasons" in data
    assert isinstance(data["seasons"], list)
    assert len(data["seasons"]) >= 1
    
    # Check season data structure
    season_data = data["seasons"][0]
    assert "season" in season_data
    assert "league_ppg" in season_data
    assert "plays_per_game" in season_data
    assert "pass_rate" in season_data

def test_dashboard_error_handling():
    """Test error handling for invalid requests."""
    # Test non-existent season
    r = client.get("/dashboard/9999")
    assert r.status_code == 404
    
    # Test invalid trend range
    r = client.get("/dashboard/trends?start=2025&end=2024")
    assert r.status_code == 400
    
    # Test trend range with no data
    r = client.get("/dashboard/trends?start=9999&end=9999")
    assert r.status_code == 404

def test_dashboard_top_n_parameter():
    """Test that top_n parameter works correctly."""
    _bootstrap(2025, weeks=1)
    
    # Test with different top_n values
    r1 = client.get("/dashboard/2025?top_n=3")
    assert r1.status_code == 200
    data1 = r1.json()
    
    r2 = client.get("/dashboard/2025?top_n=10")
    assert r2.status_code == 200
    data2 = r2.json()
    
    # Both should have progression data
    assert "progression" in data1
    assert "progression" in data2
    
    # Test parameter validation
    r3 = client.get("/dashboard/2025?top_n=0")
    assert r3.status_code == 422  # Validation error
    
    r4 = client.get("/dashboard/2025?top_n=26")
    assert r4.status_code == 422  # Validation error

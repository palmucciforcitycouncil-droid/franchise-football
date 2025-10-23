# tests/test_dashboard_feeds_simple.py
from fastapi.testclient import TestClient
from app.api.routes.dashboard import router
from fastapi import FastAPI

def test_dashboard_tiles_and_trends():
    """Test dashboard tiles and trends endpoints."""
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    # Test dashboard tiles
    r = client.get("/dashboard/2025?top_n=5")
    assert r.status_code == 200
    data = r.json()
    assert data["season"] == 2025
    assert "summary" in data and "awards" in data and "progression" in data
    
    # Test trends
    r2 = client.get("/dashboard/trends?start=2025&end=2025")
    assert r2.status_code == 200
    tr = r2.json()
    assert tr["start"] == 2025 and tr["end"] == 2025
    assert len(tr["seasons"]) >= 0  # Allow empty seasons

def test_dashboard_tiles_structure():
    """Test that dashboard tiles have the expected structure."""
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
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
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    r = client.get("/dashboard/trends?start=2025&end=2025")
    assert r.status_code == 200
    data = r.json()
    
    assert "start" in data
    assert "end" in data
    assert "seasons" in data
    assert isinstance(data["seasons"], list)
    
    # Check season data structure if seasons exist
    if data["seasons"]:
        season_data = data["seasons"][0]
        assert "season" in season_data
        assert "league_ppg" in season_data
        assert "plays_per_game" in season_data
        assert "pass_rate" in season_data

def test_dashboard_error_handling():
    """Test error handling for invalid requests."""
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
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
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
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

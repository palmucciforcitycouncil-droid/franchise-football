# tests/test_draft_board_extras.py
from sqlmodel import Session, select
from fastapi.testclient import TestClient
from app.api.routes.draft_integration import router
from fastapi import FastAPI
from app.db import get_engine
from app.models.draft import Prospect
from app.services.draft import generate_draft_class

def _create_test_draft_class(season: int = 2025):
    """Create a test draft class with known prospects."""
    eng = get_engine()
    with Session(eng) as s:
        # Generate a small draft class
        generate_draft_class(s, season, seed=12345)
        
        # Get some prospects and modify them for testing
        prospects = s.exec(select(Prospect).where(Prospect.season == season)).all()
        
        # Create some high-rated prospects for testing tiers
        if len(prospects) >= 5:
            prospects[0].overall = 88  # Elite
            prospects[0].name = "Elite QB"
            prospects[0].pos = "QB"
            s.add(prospects[0])
            
            prospects[1].overall = 82  # High
            prospects[1].name = "High WR"
            prospects[1].pos = "WR"
            s.add(prospects[1])
            
            prospects[2].overall = 77  # Good
            prospects[2].name = "Good RB"
            prospects[2].pos = "RB"
            s.add(prospects[2])
            
            prospects[3].overall = 72  # Average
            prospects[3].name = "Average TE"
            prospects[3].pos = "TE"
            s.add(prospects[3])
            
            prospects[4].overall = 68  # Below Average
            prospects[4].name = "Below Average LB"
            prospects[4].pos = "LB"
            s.add(prospects[4])
        
        s.commit()
        return len(prospects)

def test_enhanced_draft_board():
    """Test enhanced draft board with search and sort."""
    season = 2025
    _create_test_draft_class(season)
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    # Test basic board
    resp = client.get(f"/draft/{season}/board")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    
    # Check that enhanced fields are present
    first_prospect = data[0]
    assert "tier" in first_prospect
    assert "positional_rank" in first_prospect
    assert first_prospect["tier"] in ["Elite", "High", "Good", "Average", "Below Average"]
    
    # Test position filter
    resp = client.get(f"/draft/{season}/board?pos=QB")
    assert resp.status_code == 200
    data = resp.json()
    for prospect in data:
        assert prospect["pos"] == "QB"
    
    # Test overall rating range
    resp = client.get(f"/draft/{season}/board?min_overall=80&max_overall=85")
    assert resp.status_code == 200
    data = resp.json()
    for prospect in data:
        assert 80 <= prospect["overall"] <= 85
    
    # Test search
    resp = client.get(f"/draft/{season}/board?search=Elite")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    assert any("Elite" in prospect["name"] for prospect in data)
    
    # Test tier filter
    resp = client.get(f"/draft/{season}/board?tier=Elite")
    assert resp.status_code == 200
    data = resp.json()
    for prospect in data:
        assert prospect["tier"] == "Elite"
    
    # Test sorting by overall
    resp = client.get(f"/draft/{season}/board?sort_by=overall&sort_order=desc")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    assert data[0]["overall"] >= data[1]["overall"]
    
    # Test sorting by name
    resp = client.get(f"/draft/{season}/board?sort_by=name&sort_order=asc")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    assert data[0]["name"].lower() <= data[1]["name"].lower()
    
    # Test limit
    resp = client.get(f"/draft/{season}/board?limit=3")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) <= 3

def test_best_available_endpoint():
    """Test best available prospects endpoint."""
    season = 2026
    _create_test_draft_class(season)
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    # Test best available
    resp = client.get(f"/draft/{season}/best-available")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    
    # Check that results are sorted by overall (descending)
    for i in range(len(data) - 1):
        assert data[i]["overall"] >= data[i + 1]["overall"]
    
    # Check that enhanced fields are present
    for prospect in data:
        assert "tier" in prospect
        assert "positional_rank" in prospect
    
    # Test with limit
    resp = client.get(f"/draft/{season}/best-available?limit=3")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) <= 3
    
    # Test with position filter
    resp = client.get(f"/draft/{season}/best-available?pos=QB")
    assert resp.status_code == 200
    data = resp.json()
    for prospect in data:
        assert prospect["pos"] == "QB"

def test_positional_tiers_endpoint():
    """Test positional tiers endpoint."""
    season = 2027
    _create_test_draft_class(season)
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    resp = client.get(f"/draft/{season}/positional-tiers")
    assert resp.status_code == 200
    data = resp.json()
    
    # Check structure
    assert isinstance(data, dict)
    
    # Check that each position has tier structure
    for pos, tiers in data.items():
        assert isinstance(tiers, dict)
        assert "Elite" in tiers
        assert "High" in tiers
        assert "Good" in tiers
        assert "Average" in tiers
        assert "Below Average" in tiers
        
        # Check that each tier is a list
        for tier_name, prospects in tiers.items():
            assert isinstance(prospects, list)
            
            # Check that prospects in each tier are sorted by overall
            for i in range(len(prospects) - 1):
                assert prospects[i]["overall"] >= prospects[i + 1]["overall"]
                assert prospects[i]["tier"] == tier_name

def test_draft_stats_endpoint():
    """Test draft statistics endpoint."""
    season = 2028
    _create_test_draft_class(season)
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    resp = client.get(f"/draft/{season}/stats")
    assert resp.status_code == 200
    data = resp.json()
    
    # Check required fields
    required_fields = [
        "season", "total_prospects", "drafted", "available", 
        "draft_percentage", "position_breakdown", "tier_breakdown",
        "average_overall", "min_overall", "max_overall"
    ]
    for field in required_fields:
        assert field in data
    
    # Check data types and values
    assert data["season"] == season
    assert data["total_prospects"] > 0
    assert data["drafted"] >= 0
    assert data["available"] >= 0
    assert data["drafted"] + data["available"] == data["total_prospects"]
    assert 0 <= data["draft_percentage"] <= 100
    assert isinstance(data["position_breakdown"], dict)
    assert isinstance(data["tier_breakdown"], dict)
    assert data["min_overall"] <= data["average_overall"] <= data["max_overall"]
    
    # Check tier breakdown
    tier_counts = data["tier_breakdown"]
    assert "Elite" in tier_counts
    assert "High" in tier_counts
    assert "Good" in tier_counts
    assert "Average" in tier_counts
    assert "Below Average" in tier_counts
    
    # Check that tier counts sum to total prospects
    total_tier_count = sum(tier_counts.values())
    assert total_tier_count == data["total_prospects"]

def test_positional_rank_calculation():
    """Test positional rank calculation."""
    season = 2029
    _create_test_draft_class(season)
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    resp = client.get(f"/draft/{season}/board?pos=QB")
    assert resp.status_code == 200
    data = resp.json()
    
    if len(data) > 0:
        # Check that positional ranks are calculated correctly
        qb_prospects = [p for p in data if p["pos"] == "QB"]
        qb_prospects.sort(key=lambda x: x["overall"], reverse=True)
        
        # The positional rank should be based on all QBs in the season, not just filtered ones
        # So we need to check that ranks are consistent with overall ratings
        for i in range(len(qb_prospects) - 1):
            assert qb_prospects[i]["overall"] >= qb_prospects[i + 1]["overall"]
            # Higher overall should have lower (better) rank
            assert qb_prospects[i]["positional_rank"] <= qb_prospects[i + 1]["positional_rank"]

def test_tier_calculation():
    """Test tier calculation logic."""
    season = 2030
    _create_test_draft_class(season)
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    resp = client.get(f"/draft/{season}/board")
    assert resp.status_code == 200
    data = resp.json()
    
    # Check tier assignments
    for prospect in data:
        overall = prospect["overall"]
        tier = prospect["tier"]
        
        if overall >= 85:
            assert tier == "Elite"
        elif overall >= 80:
            assert tier == "High"
        elif overall >= 75:
            assert tier == "Good"
        elif overall >= 70:
            assert tier == "Average"
        else:
            assert tier == "Below Average"

def test_drafted_status_filter():
    """Test drafted status filtering."""
    season = 2031
    _create_test_draft_class(season)
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    # Test available only
    resp = client.get(f"/draft/{season}/board?drafted=false")
    assert resp.status_code == 200
    data = resp.json()
    for prospect in data:
        assert prospect["drafted_by_team_id"] is None
    
    # Test drafted only
    resp = client.get(f"/draft/{season}/board?drafted=true")
    assert resp.status_code == 200
    data = resp.json()
    for prospect in data:
        assert prospect["drafted_by_team_id"] is not None

def test_sorting_options():
    """Test various sorting options."""
    season = 2032
    _create_test_draft_class(season)
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    # Test sorting by different fields
    sort_fields = ["overall", "name", "pos", "speed", "strength", "agility", "awareness", "potential", "tier", "positional_rank"]
    
    for field in sort_fields:
        resp = client.get(f"/draft/{season}/board?sort_by={field}&sort_order=desc")
        assert resp.status_code == 200
        data = resp.json()
        
        if len(data) >= 2:
            # Basic check that sorting doesn't crash
            assert isinstance(data, list)
            assert len(data) > 0

def test_error_handling():
    """Test error handling for invalid parameters."""
    season = 2033
    _create_test_draft_class(season)
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    # Test invalid season
    resp = client.get("/draft/9999/board")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 0
    
    # Test invalid limit
    resp = client.get(f"/draft/{season}/board?limit=0")
    assert resp.status_code == 422  # Validation error
    
    # Test invalid sort field
    resp = client.get(f"/draft/{season}/board?sort_by=invalid_field")
    assert resp.status_code == 200  # Should still work, just ignore invalid sort

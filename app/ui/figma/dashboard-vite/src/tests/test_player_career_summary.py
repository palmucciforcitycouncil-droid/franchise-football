# tests/test_player_career_summary.py
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.main import app
from app.db import get_engine
from app.engine.mini_season_runner import run_mini_season
from app.services.stats.season_agg import aggregate_player_season, aggregate_team_season
from app.services.awards import compute_and_persist_awards

client = TestClient(app)

def _bootstrap(season:int=2025):
    eng = get_engine()
    with Session(eng) as s:
        run_mini_season(s, season=season, weeks=2); s.commit()
    with Session(eng) as s:
        aggregate_team_season(s, season)
        aggregate_player_season(s, season)
        compute_and_persist_awards(s, season)

def test_career_summary_endpoint():
    """Test the player career summary endpoint."""
    _bootstrap(2024); _bootstrap(2025)
    eng = get_engine()
    with Session(eng) as s:
        # pick a player who has season stats
        from app.models.season_stats import PlayerSeasonStats
        r = s.exec(select(PlayerSeasonStats).order_by(PlayerSeasonStats.player_id)).first()
        pid = r.player_id
    resp = client.get(f"/players/{pid}/career_summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["player"]["player_id"] == pid
    assert "totals" in data and "seasons" in data
    assert isinstance(data["seasons"], list) and len(data["seasons"]) >= 1

def test_career_summary_nonexistent_player():
    """Test career summary for non-existent player returns 404."""
    resp = client.get("/players/99999/career_summary")
    assert resp.status_code == 404
    assert "Player not found" in resp.json()["detail"]

def test_career_summary_service():
    """Test the career summary service directly."""
    from app.services.players import get_player_career_summary
    eng = get_engine()
    with Session(eng) as s:
        # Get a player with season stats
        from app.models.season_stats import PlayerSeasonStats
        r = s.exec(select(PlayerSeasonStats).order_by(PlayerSeasonStats.player_id)).first()
        pid = r.player_id
        
        # Test service
        data = get_player_career_summary(s, pid)
        assert data
        assert "player" in data
        assert "totals" in data
        assert "seasons" in data
        assert "awards" in data
        assert "teams" in data
        assert "best_season" in data
        
        # Check player info
        assert data["player"]["player_id"] == pid
        assert data["player"]["name"] is not None
        
        # Check totals
        assert isinstance(data["totals"], dict)
        assert "games" in data["totals"]
        assert "pass_yards" in data["totals"]
        
        # Check seasons
        assert isinstance(data["seasons"], list)
        assert len(data["seasons"]) >= 1
        
        # Check awards
        assert isinstance(data["awards"], list)
        
        # Check teams
        assert isinstance(data["teams"], list)


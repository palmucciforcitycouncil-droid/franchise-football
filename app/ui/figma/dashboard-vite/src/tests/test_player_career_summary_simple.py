# tests/test_player_career_summary_simple.py
from sqlmodel import Session, select
from app.db import get_engine
from app.services.players import get_player_career_summary
from app.models.core_min import Player
from app.models.season_stats import PlayerSeasonStats

def test_career_summary_service():
    """Test the career summary service directly."""
    eng = get_engine()
    with Session(eng) as s:
        # Get a player with season stats
        r = s.exec(select(PlayerSeasonStats).order_by(PlayerSeasonStats.player_id)).first()
        if not r:
            # Create test data if none exists
            p = Player(name='Test Player', pos='QB', team_id=1, age=25, years_pro=3)
            s.add(p)
            s.commit()
            pss = PlayerSeasonStats(player_id=p.id, team_id=1, season=2025, games=16, pass_yards=3500, pass_tds=25, rush_yards=200, rush_tds=2)
            s.add(pss)
            s.commit()
            pid = p.id
        else:
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

def test_career_summary_nonexistent_player():
    """Test career summary for non-existent player returns empty dict."""
    eng = get_engine()
    with Session(eng) as s:
        data = get_player_career_summary(s, 99999)
        assert data == {}



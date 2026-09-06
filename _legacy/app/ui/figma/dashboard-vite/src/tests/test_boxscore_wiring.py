import pytest
from sqlmodel import select
from collections import defaultdict
from app.testing.mini_season_runner import memory_db, run_mini_season
from app.testing.field_alias import getf

def test_points_fg_and_punts_persist():
    """Test that points, FG attempts, and punts are properly recorded."""
    with memory_db() as s:
        run_mini_season(s, weeks=2)
        try:
            from app.models.team_stats import TeamGame
        except Exception:
            pytest.skip("TeamGame model not available.")
        
        rows = s.exec(select(TeamGame)).all()
        assert rows, "no TeamGame rows written"
        
        by_game = defaultdict(lambda: {"points":0,"punts":0,"fga":0})
        for r in rows:
            gid = getattr(r,"game_id")
            by_game[gid]["points"] += getf(r,"points",0)
            by_game[gid]["punts"]  += getf(r,"punts",0)
            by_game[gid]["fga"]    += getf(r,"fga",0)
        
        # sanity across slate
        total_points = sum(m["points"] for m in by_game.values())
        total_fga    = sum(m["fga"] for m in by_game.values())
        assert total_points > 0, "points never increased — wiring issue"
        assert total_fga > 0, "no FG attempts recorded — wiring issue"
        
        # punt band is a guidance — ensure not extreme
        avg_punts = sum(m["punts"] for m in by_game.values())/max(1,len(by_game))
        assert 2.5 <= avg_punts <= 6.0, f"punt rate out of sanity band: {avg_punts:.2f}"

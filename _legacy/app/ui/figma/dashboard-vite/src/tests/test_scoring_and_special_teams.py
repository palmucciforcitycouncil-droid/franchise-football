import pytest
from sqlmodel import select
from collections import defaultdict
from app.testing.mini_season_runner import memory_db, run_mini_season
from app.testing.field_alias import getf

def test_points_and_fg_attempts_exist():
    """Test that points and FG attempts are being generated."""
    with memory_db() as s:
        run_mini_season(s, weeks=2)  # ~4 games
        try:
            from app.models.team_stats import TeamGame
        except Exception:
            pytest.skip("TeamGame model not available.")
        
        rows = s.exec(select(TeamGame)).all()
        by_game = defaultdict(lambda: {"points":0,"punts":0,"fga":0,"sacks":0})
        
        for r in rows:
            gid = getattr(r,"game_id")
            by_game[gid]["points"] += getf(r,"points",0)
            by_game[gid]["punts"]  += getf(r,"punts",0)
            by_game[gid]["fga"]    += getf(r,"fga",0)
            by_game[gid]["sacks"]  += getf(r,"sacks",0)
        
        assert len(by_game) >= 2
        # sanity: points > 0, FGAs > 0 in slate
        assert sum(m["points"] for m in by_game.values()) > 0
        assert sum(m["fga"] for m in by_game.values()) > 0

def test_no_mans_land_generates_some_fgs_in_trials():
    """Test that no-man's land (60-65 yardline) produces FG attempts."""
    # synthetic probe: ensure 60..65 produces FGs occasionally
    from app.engine.pbp_curves import fourth_down_decision
    import random
    
    rng = random.Random(42)
    attempts = 10
    fgs = 0
    
    for _ in range(attempts):
        call = fourth_down_decision(rng, yardline=62, to_go=5, kicker_max=60, coach_agg=0.5)
        if call == "FG": 
            fgs += 1
    
    assert fgs >= 2  # ensure non-zero, analytics still allows GO/PUNT mix

def test_field_goal_distance_calculation():
    """Test field goal distance calculation."""
    from app.engine.special_teams import fg_distance_from_yardline
    
    # Test various yardlines
    assert fg_distance_from_yardline(80) == 37  # 17 + (100-80)
    assert fg_distance_from_yardline(90) == 27  # 17 + (100-90)
    assert fg_distance_from_yardline(95) == 22  # 17 + (100-95)
    assert fg_distance_from_yardline(99) == 18  # 17 + (100-99)

def test_field_goal_make_probability():
    """Test field goal make probability calculation."""
    from app.engine.special_teams import fg_make_probability
    
    # Test basic probability calculation
    base_40_49 = 0.85  # 85% make rate in 40-49 range
    
    # Short kicks should be higher probability
    short_prob = fg_make_probability(base_40_49, 25, 0.5, 0.0)
    assert short_prob > base_40_49
    
    # Long kicks should be lower probability
    long_prob = fg_make_probability(base_40_49, 55, 0.5, 0.0)
    assert long_prob < base_40_49
    
    # Weather should affect probability
    weather_prob = fg_make_probability(base_40_49, 40, 0.5, -0.05)
    normal_prob = fg_make_probability(base_40_49, 40, 0.5, 0.0)
    assert weather_prob < normal_prob

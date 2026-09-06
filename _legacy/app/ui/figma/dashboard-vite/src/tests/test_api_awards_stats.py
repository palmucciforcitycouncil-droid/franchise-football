# tests/test_api_awards_stats.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.main import app
from app.db import get_engine
from app.testing.mini_season_runner import memory_db, run_mini_season
from app.services.stats.season_agg import aggregate_team_season, aggregate_player_season
from app.services.awards import compute_and_persist_awards

client = TestClient(app)

def _bootstrap(season: int):
    """Bootstrap test data with mini season, aggregation, and awards."""
    with memory_db() as session:
        result = run_mini_season(session, weeks=2)
        print(f"Mini season result: {result}")
        
        # Create mock TeamGameStats and PlayerGameStats for testing
        from app.models.core_min import Team, Player, Game
        from app.models.stats_models import TeamGameStats, PlayerGameStats
        
        teams = session.exec(session.query(Team)).all()
        players = session.exec(session.query(Player)).all()
        games = session.exec(session.query(Game)).all()
        
        if not teams or not players or not games:
            pytest.skip("No teams, players, or games available for testing")
        
        # Create mock TeamGameStats
        for i, game in enumerate(games):
            for team in [teams[0], teams[1]]:  # Use first two teams
                tg = TeamGameStats(
                    game_id=getattr(game, 'id', i+1),  # Use safe getattr for id
                    team_id=getattr(team, 'id', i+1),  # Use safe getattr for id
                    is_home_team=(i % 2 == 0),
                    points_scored=20 + (i * 3),  # Varying scores
                    total_yards=350 + (i * 25),
                    passing_yards=200 + (i * 15),
                    rushing_yards=150 + (i * 10),
                    turnovers_committed=1 + (i % 2),
                    turnovers_forced=2 - (i % 2),
                    field_goals_made=1 + (i % 2),
                    field_goals_attempted=2 + (i % 2),
                    punts=3 + (i % 2),
                    third_down_conversions=5 + (i % 2),
                    third_down_attempts=12 + (i % 2),
                    fourth_down_conversions=1,
                    fourth_down_attempts=2,
                    red_zone_touchdowns=2 + (i % 2),
                    red_zone_attempts=3 + (i % 2)
                )
                session.add(tg)
        
        # Create mock PlayerGameStats
        for i, game in enumerate(games):
            for player in players[:3]:  # Use first 3 players
                pg = PlayerGameStats(
                    game_id=getattr(game, 'id', i+1),  # Use safe getattr for id
                    player_id=getattr(player, 'id', i+1),  # Use safe getattr for id
                    team_id=getattr(player, 'team_id', i+1),  # Use safe getattr for team_id
                    snaps_offense=50 + (i * 5),
                    snaps_defense=30 + (i * 3),
                    pass_attempts=25 + (i * 2),
                    pass_completions=18 + (i * 2),
                    pass_yards=200 + (i * 20),
                    pass_touchdowns=2 + (i % 2),
                    interceptions=1 if i % 3 == 0 else 0,
                    rush_attempts=10 + (i % 3),
                    rush_yards=50 + (i * 5),
                    rush_touchdowns=1 if i % 2 == 0 else 0,
                    targets=8 + (i % 2),
                    receptions=6 + (i % 2),
                    receiving_yards=80 + (i * 8),
                    receiving_touchdowns=1 if i % 3 == 0 else 0,
                    tackles=5 + (i % 2),
                    sacks=0.5 + (i % 2) * 0.5,
                    tackles_for_loss=1 + (i % 2),
                    quarterback_hits=2 + (i % 2),
                    interceptions_caught=1 if i % 4 == 0 else 0,
                    passes_defended=2 + (i % 2),
                    field_goals_made=1 if i % 3 == 0 else 0,
                    field_goals_attempted=2 if i % 3 == 0 else 0,
                    punts=3 if i % 2 == 0 else 0,
                    punt_yards=120 + (i * 10),
                    third_down_conversions=3 + (i % 2),
                    third_down_attempts=8 + (i % 2),
                    fourth_down_conversions=1,
                    fourth_down_attempts=2,
                    red_zone_touchdowns=1 + (i % 2),
                    red_zone_attempts=2 + (i % 2)
                )
                session.add(pg)
        
        session.commit()
        
        # Aggregate season stats
        aggregate_team_season(session, season)
        aggregate_player_season(session, season)
        
        # Compute awards
        compute_and_persist_awards(session, season)

def test_awards_api_endpoints_smoke():
    """Test awards API endpoints with bootstrap data."""
    season = 2025
    _bootstrap(season)

    # Test all awards endpoint
    r = client.get(f"/awards/{season}")
    assert r.status_code == 200
    data = r.json()
    assert data["season"] == season
    # expect 6 award groups
    assert len(data["awards"]) == 6

    # Test individual award endpoint
    r2 = client.get(f"/awards/{season}/MVP")
    assert r2.status_code == 200
    one = r2.json()
    assert one["award"] == "MVP"
    assert len(one["top"]) >= 1
    
    print("OK Awards API endpoints smoke test passed")

def test_stats_and_summary_endpoints_smoke():
    """Test stats and summary API endpoints with bootstrap data."""
    season = 2025
    _bootstrap(season)

    # Test league summary endpoint
    r = client.get(f"/seasons/reports/league_summary/{season}")
    assert r.status_code == 200
    summary = r.json()
    assert summary["season"] == season
    assert summary["teams"] > 0
    assert summary["games_counted"] > 0

    # Test team stats endpoint (may 404 if team doesn't exist)
    maybe_team = client.get(f"/seasons/{season}/teams/1/stats")
    if maybe_team.status_code == 200:
        team = maybe_team.json()
        assert team["season"] == season
        assert team["games"] >= 1
    else:
        assert maybe_team.status_code == 404

    # Test player stats endpoint (may 404 if player doesn't exist)
    maybe_player = client.get(f"/seasons/{season}/players/1/stats")
    if maybe_player.status_code == 200:
        player = maybe_player.json()
        assert player["season"] == season
        assert "pass_yards" in player
    else:
        assert maybe_player.status_code == 404
    
    print("OK Stats and summary API endpoints smoke test passed")

def test_api_404_handling():
    """Test that API properly returns 404 for non-existent data."""
    season = 9999  # Non-existent season
    
    # Test awards 404
    r = client.get(f"/awards/{season}")
    assert r.status_code == 404
    
    r2 = client.get(f"/awards/{season}/MVP")
    assert r2.status_code == 404
    
    # Test stats 404
    r3 = client.get(f"/seasons/reports/league_summary/{season}")
    assert r3.status_code == 404
    
    r4 = client.get(f"/seasons/{season}/teams/999/stats")
    assert r4.status_code == 404
    
    r5 = client.get(f"/seasons/{season}/players/999/stats")
    assert r5.status_code == 404
    
    print("OK API 404 handling test passed")

def test_csv_export_functionality():
    """Test CSV export functionality."""
    season = 2025
    _bootstrap(season)
    
    # Test CSV export
    from app.services.reports import (
        export_awards_csv,
        export_team_season_csv,
        export_player_season_csv,
        export_league_summary_csv,
    )
    from pathlib import Path
    
    out_dir = Path("test_reports")
    engine = get_engine()
    
    with Session(engine) as session:
        # Export all CSV files
        awards_path = export_awards_csv(session, season, out_dir)
        team_path = export_team_season_csv(session, season, out_dir)
        player_path = export_player_season_csv(session, season, out_dir)
        summary_path = export_league_summary_csv(session, season, out_dir)
        
        # Verify files were created
        assert awards_path.exists()
        assert team_path.exists()
        assert player_path.exists()
        assert summary_path.exists()
        
        # Verify files have content
        assert awards_path.stat().st_size > 0
        assert team_path.stat().st_size > 0
        assert player_path.stat().st_size > 0
        assert summary_path.stat().st_size > 0
        
        # Clean up test files
        awards_path.unlink()
        team_path.unlink()
        player_path.unlink()
        summary_path.unlink()
        out_dir.rmdir()
    
    print("OK CSV export functionality test passed")

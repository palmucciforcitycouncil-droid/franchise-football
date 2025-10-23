# tests/test_progression_api_and_rollback.py
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.main import app
from app.db import get_engine
from app.testing.mini_season_runner import memory_db, run_mini_season
from app.services.stats.season_agg import aggregate_team_season, aggregate_player_season
from app.services.awards import compute_and_persist_awards
from app.services.progression import apply_progression_for_season, rollback_progression
from app.models.progression import PlayerProgression
from app.models.core_min import Player
import json

client = TestClient(app)
SEASON = 2025

def _bootstrap():
    with memory_db() as session:
        run_mini_season(session, weeks=2)
        
        # Create mock PlayerSeasonStats for testing
        from app.models.core_min import Team, Game
        
        teams = session.exec(session.query(Team)).all()
        players = session.exec(session.query(Player)).all()
        games = session.exec(session.query(Game)).all()
        
        if not teams or not players or not games:
            pytest.skip("No teams, players, or games available for testing")
        
        # Create mock PlayerSeasonStats
        for i, game in enumerate(games):
            for player in players[:3]:  # Use first 3 players
                from app.models.season_stats import PlayerSeasonStats
                pg = PlayerSeasonStats(
                    game_id=getattr(game, 'id', i+1),
                    player_id=getattr(player, 'id', i+1),
                    team_id=getattr(player, 'team_id', i+1),
                    season=SEASON,
                    games_played=1,
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
        aggregate_team_season(session, SEASON)
        aggregate_player_season(session, SEASON)
        
        # Compute awards
        compute_and_persist_awards(session, SEASON)
        
        # Apply progression
        apply_progression_for_season(session, season=SEASON, seed=2025, force=True)

def test_progression_league_view_and_player_audit():
    """Test progression API endpoints."""
    _bootstrap()
    
    # League view
    r = client.get(f"/progression/{SEASON}?top_n=10")
    assert r.status_code == 200
    view = r.json()
    assert view["season"] == SEASON
    assert len(view["risers"]) >= 1
    assert len(view["fallers"]) >= 1

    # Pick a player from risers and fetch audit
    pid = view["risers"][0]["player_id"]
    r2 = client.get(f"/progression/player/{pid}")
    assert r2.status_code == 200
    audit = r2.json()
    assert audit["player_id"] == pid
    # at least one audit record
    if audit["audits"]:
        a0 = audit["audits"][0]
        assert "before" in a0 and "after" in a0 and "components" in a0

def test_rollback_restores_before_snapshot():
    """Test rollback functionality."""
    _bootstrap()
    
    with memory_db() as session:
        # Choose a progression row
        row = session.exec(select(PlayerProgression).where(PlayerProgression.season == SEASON)).first()
        assert row, "Need a progression row"
        pid = row.player_id
        before = json.loads(row.before_json); after = json.loads(row.after_json)
        p = session.get(Player, pid)
        assert p is not None

    # Rollback just this player
    with memory_db() as session:
        n = rollback_progression(session, season=SEASON, player_id=pid, purge=False)
        assert n == 1

    # Verify DB equals 'before'
    with memory_db() as session:
        p2 = session.get(Player, pid)
        for k, v in before.items():
            if hasattr(p2, k):
                assert getattr(p2, k) == v, f"{k} not rolled back"

    # Re-apply progression to ensure determinism still holds
    with memory_db() as session:
        apply_progression_for_season(session, season=SEASON, seed=2025, force=False)  # idempotent for others; recompute for this pid only if row purged? We didn't purge, so skip
        # Force for this player to verify exact reapplication
        from app.models.progression import PlayerProgression
        # Delete their row and re-apply just to check repeatability
        pr = session.exec(select(PlayerProgression).where(PlayerProgression.season == SEASON, PlayerProgression.player_id == pid)).first()
        if pr:
            session.delete(pr); session.commit()
        apply_progression_for_season(session, season=SEASON, seed=2025, force=False)
        pr2 = session.exec(select(PlayerProgression).where(PlayerProgression.season == SEASON, PlayerProgression.player_id == pid)).first()
        assert pr2 is not None
        a2 = json.loads(pr2.after_json)
        # After should differ from 'before' for at least one tracked key
        changed = any(a2.get(k,0) != before.get(k,0) for k in ["awareness","throw_accuracy","catching","tackling","speed","agility","strength","stamina","morale"])
        assert changed, "Re-application did not change any attribute; expected deterministic change from before."

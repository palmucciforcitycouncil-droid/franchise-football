# tests/test_progression_persistence.py
from sqlmodel import Session, select
from app.db import get_engine
from app.testing.mini_season_runner import memory_db, run_mini_season
from app.services.stats.season_agg import aggregate_team_season, aggregate_player_season
from app.services.awards import compute_and_persist_awards
from app.services.progression import apply_progression_for_season
from app.models.progression import PlayerProgression
from app.models.core_min import Player
import json

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

def test_player_attribute_changes_persist():
    """Test that player attribute changes persist across database sessions."""
    _bootstrap()
    
    with memory_db() as session:
        apply_progression_for_season(session, season=SEASON, seed=2025, force=True)

    with memory_db() as session:
        rows = session.exec(select(PlayerProgression).where(PlayerProgression.season == SEASON)).all()
        assert rows, "No progression rows written"
        # Find any row where at least one attribute changed
        candidate = None
        for r in rows:
            b = json.loads(r.before_json); a = json.loads(r.after_json)
            if any(a.get(k,0)!=b.get(k,0) for k in ["awareness","throw_accuracy","catching","tackling","speed","agility","strength","stamina","morale"]):
                candidate = (r.player_id, b, a)
                break
        assert candidate, "No attribute changes detected; persistence may be broken."
        pid, b, a = candidate
        p = session.get(Player, pid)
        assert p is not None
        # Verify that at least one changed attr matches the DB value now
        for k in ["awareness","throw_accuracy","catching","tackling","speed","agility","strength","stamina","morale"]:
            if a.get(k, None) is not None and a.get(k) != b.get(k):
                assert getattr(p, k, None) == a[k], f"{k} not persisted to DB"
                break
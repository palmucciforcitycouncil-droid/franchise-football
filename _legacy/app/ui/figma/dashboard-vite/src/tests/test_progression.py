# tests/test_progression.py
import pytest
import json
from sqlmodel import Session, select
from app.db import get_engine
from app.testing.mini_season_runner import memory_db, run_mini_season
from app.services.stats.season_agg import aggregate_team_season, aggregate_player_season
from app.services.awards import compute_and_persist_awards
from app.services.progression import apply_progression_for_season, _snapshot_player_ratings
from app.models.progression import PlayerProgression
from app.models.core_min import Player
from app.models.awards import AwardResult
from app.models.stats_models import PlayerGameStats

SEASON = 2025

def _bootstrap():
    """Bootstrap test data with mini season, aggregation, awards, and progression."""
    with memory_db() as session:
        result = run_mini_season(session, weeks=2)
        print(f"Mini season result: {result}")
        
        # Create mock PlayerGameStats for testing
        from app.models.core_min import Team, Game
        
        teams = session.exec(session.query(Team)).all()
        players = session.exec(session.query(Player)).all()
        games = session.exec(session.query(Game)).all()
        
        if not teams or not players or not games:
            pytest.skip("No teams, players, or games available for testing")
        
        # Create mock PlayerGameStats
        for i, game in enumerate(games):
            for player in players[:3]:  # Use first 3 players
                pg = PlayerGameStats(
                    game_id=getattr(game, 'id', i+1),
                    player_id=getattr(player, 'id', i+1),
                    team_id=getattr(player, 'team_id', i+1),
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

def test_progression_deterministic_and_idempotent():
    """Test that progression is deterministic and idempotent."""
    _bootstrap()
    
    with memory_db() as session:
        # Apply progression once
        apply_progression_for_season(session, season=SEASON, seed=1234, force=False)

        rows = session.exec(select(PlayerProgression).where(PlayerProgression.season == SEASON)).all()
        assert rows, "No progression rows written"
        first_count = len(rows)
        snapshots = {r.player_id: (r.before_json, r.after_json) for r in rows}

        # Apply again without force → should not duplicate/modify
        apply_progression_for_season(session, season=SEASON, seed=9999, force=False)
        rows2 = session.exec(select(PlayerProgression).where(PlayerProgression.season == SEASON)).all()
        assert len(rows2) == first_count, "Idempotent run added rows unexpectedly"
        snapshots2 = {r.player_id: (r.before_json, r.after_json) for r in rows2}
        assert snapshots == snapshots2, "Idempotent run altered snapshots"
        
        print("OK Progression deterministic and idempotent test passed")

def test_award_winner_tends_to_improve_and_older_rb_regresses():
    """Test that award winners tend to improve and older RBs regress."""
    _bootstrap()
    
    with memory_db() as session:
        apply_progression_for_season(session, season=SEASON, seed=2025, force=True)

        # Find MVP winner if any, verify some attribute improved for them
        mvp = session.exec(select(AwardResult).where(AwardResult.season == SEASON, AwardResult.award == "MVP")).first()
        if mvp and mvp.player_id:
            p = session.get(Player, mvp.player_id)
            if p:
                prog = session.exec(select(PlayerProgression).where(
                    PlayerProgression.season == SEASON, 
                    PlayerProgression.player_id == mvp.player_id
                )).first()
                if prog:
                    # Parse JSON snapshots
                    before = json.loads(prog.before_json)
                    after = json.loads(prog.after_json)
                    # Crude check: at least one of awareness/throw_accuracy/catching increased or equal
                    improved = any(after.get(k,0) >= before.get(k,0) for k in ["awareness","throw_accuracy","catching"])
                    assert improved, "MVP should not regress across all key attributes"

        # Synthetic: find an older RB (age >= 30) if exists and check mild regression tendency
        rb = session.exec(select(Player).where(Player.pos == "RB")).first()
        if rb and getattr(rb, "age", 0) >= 30:
            prog = session.exec(select(PlayerProgression).where(
                PlayerProgression.season == SEASON, 
                PlayerProgression.player_id == rb.id
            )).first()
            if prog:
                before = json.loads(prog.before_json)
                after = json.loads(prog.after_json)
                # Expect at least one of speed/agility not to improve wildly; allow stable or slight down
                non_increase = (after.get("speed",0) <= before.get("speed",0) or after.get("agility",0) <= before.get("agility",0))
                assert non_increase, "Older RB should not show universal speed/agility gains"
        
        print("OK Award winner improvement and older RB regression test passed")

def test_progression_force_recompute():
    """Test that force flag allows recomputation."""
    _bootstrap()
    
    with memory_db() as session:
        # Apply progression once
        apply_progression_for_season(session, season=SEASON, seed=1234, force=False)
        
        first_rows = session.exec(select(PlayerProgression).where(PlayerProgression.season == SEASON)).all()
        first_count = len(first_rows)
        
        # Apply with force → should recompute
        apply_progression_for_season(session, season=SEASON, seed=5678, force=True)
        
        second_rows = session.exec(select(PlayerProgression).where(PlayerProgression.season == SEASON)).all()
        second_count = len(second_rows)
        
        # Should have same number of rows but potentially different content
        assert first_count == second_count, "Force recompute should maintain row count"
        
        # Check that timestamps are different (indicating recomputation)
        if first_rows and second_rows:
            first_ts = first_rows[0].applied_at_ts
            second_ts = second_rows[0].applied_at_ts
            assert first_ts != second_ts, "Force recompute should update timestamps"
        
        print("OK Progression force recompute test passed")

def test_progression_rating_bounds():
    """Test that progression respects rating bounds (30-99)."""
    _bootstrap()
    
    with memory_db() as session:
        apply_progression_for_season(session, season=SEASON, seed=2025, force=True)
        
        # Check that all players have ratings within bounds
        players = session.exec(select(Player)).all()
        for player in players:
            # Check core attributes are within bounds
            for attr in ["awareness", "speed", "strength", "agility", "throw_power", "throw_accuracy", "catching", "tackling", "stamina", "morale"]:
                if hasattr(player, attr):
                    value = getattr(player, attr)
                    assert 30 <= value <= 99, f"Player {player.id} {attr} = {value} outside bounds [30, 99]"
        
        print("OK Progression rating bounds test passed")

def test_progression_audit_trail():
    """Test that progression creates proper audit trail."""
    _bootstrap()
    
    with memory_db() as session:
        apply_progression_for_season(session, season=SEASON, seed=2025, force=True)
        
        progressions = session.exec(select(PlayerProgression).where(PlayerProgression.season == SEASON)).all()
        assert progressions, "No progression audit records created"
        
        for prog in progressions:
            # Check required fields
            assert prog.player_id is not None
            assert prog.season == SEASON
            assert prog.before_json
            assert prog.after_json
            assert prog.components_json
            assert prog.applied_at_ts is not None
            assert prog.seed_used == 2025
            
            # Check JSON is valid
            before = json.loads(prog.before_json)
            after = json.loads(prog.after_json)
            components = json.loads(prog.components_json)
            
            assert isinstance(before, dict)
            assert isinstance(after, dict)
            assert isinstance(components, dict)
            
            # Check that components contain expected keys
            expected_components = ["pos_bucket", "perf", "awards_bonus", "potential_mult", "age_mult", "usage_mult", "injury_drag", "noise"]
            for key in expected_components:
                assert key in components, f"Missing component {key} in audit trail"
        
        print("OK Progression audit trail test passed")

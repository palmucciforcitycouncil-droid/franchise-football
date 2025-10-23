# tests/test_awards.py
import pytest
from sqlmodel import Session, select, create_engine
from app.testing.mini_season_runner import memory_db, run_mini_season
from app.services.stats.season_agg import aggregate_team_season, aggregate_player_season
from app.services.awards import compute_and_persist_awards
from app.models.awards import AwardResult
from app.models.stats_models import TeamGameStats, PlayerGameStats
from app.models.core_min import Game

def _get(session: Session, season: int, award: str):
    """Get award results for a specific season and award, ordered by rank."""
    return session.exec(select(AwardResult).where(
        AwardResult.season == season, AwardResult.award == award
    ).order_by(AwardResult.rank)).all()

def test_awards_deterministic_and_nonempty():
    """Test that awards are deterministic and have minimum candidates."""
    season = 2025
    
    with memory_db() as session:
        # Small slate for speed; relies on existing deterministic sim
        result = run_mini_season(session, weeks=2)
        print(f"Mini season result: {result}")
        
        # Create mock TeamGameStats and PlayerGameStats for testing
        from app.models.core_min import Team, Player
        
        teams = session.exec(select(Team)).all()
        players = session.exec(select(Player)).all()
        games = session.exec(select(Game)).all()
        
        if not teams or not players or not games:
            pytest.skip("No teams, players, or games available for testing")
        
        # Create mock TeamGameStats
        for i, game in enumerate(games):
            for team in [teams[0], teams[1]]:  # Use first two teams
                tg = TeamGameStats(
                    game_id=game.id,
                    team_id=team.id,
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
                    game_id=game.id,
                    player_id=player.id,
                    team_id=player.team_id,
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
        
        # Verify minimum candidates and positive scores
        for award in ["MVP", "OPOY", "DPOY", "ROY", "COY", "GMOY"]:
            rows = _get(session, season, award)
            assert len(rows) >= 1, f"{award} should have at least 1 candidate (got {len(rows)})"
            # Scores should be non-negative for leaders
            assert rows[0].score >= 0.0, f"{award} top score should be >= 0"
            print(f"{award}: {len(rows)} candidates, top score: {rows[0].score:.2f}")
        
        # Determinism: calling again shouldn't change order
        first_pass = {aw: [r.player_id or r.team_id for r in _get(session, season, aw)] 
                      for aw in ["MVP", "OPOY", "DPOY", "ROY", "COY", "GMOY"]}
        compute_and_persist_awards(session, season)
        second_pass = {aw: [r.player_id or r.team_id for r in _get(session, season, aw)] 
                       for aw in ["MVP", "OPOY", "DPOY", "ROY", "COY", "GMOY"]}
        assert first_pass == second_pass, "Award ordering changed between idempotent runs"
        
        print("OK Awards deterministic and nonempty test passed")

def test_award_scoring_logic():
    """Test that award scoring logic produces reasonable results."""
    season = 2025
    
    with memory_db() as session:
        # Create minimal test data
        from app.models.core_min import Team, Player, Game
        
        teams = session.exec(select(Team)).all()
        players = session.exec(select(Player)).all()
        
        if not teams or not players:
            pytest.skip("No teams or players available for testing")
        
        # Create a simple game
        game = Game(season=season, week=1, home_team_id=teams[0].id, away_team_id=teams[1].id)
        session.add(game)
        session.commit()
        
        # Create TeamGameStats with clear winner
        tg1 = TeamGameStats(
            game_id=game.id,
            team_id=teams[0].id,
            points_scored=30,
            points_allowed=10,
            total_yards=400,
            passing_yards=250,
            rushing_yards=150,
            wins=1,
            losses=0,
            games_played=1
        )
        tg2 = TeamGameStats(
            game_id=game.id,
            team_id=teams[1].id,
            points_scored=10,
            points_allowed=30,
            total_yards=200,
            passing_yards=150,
            rushing_yards=50,
            wins=0,
            losses=1,
            games_played=1
        )
        session.add(tg1)
        session.add(tg2)
        
        # Create PlayerGameStats with clear offensive leader
        pg = PlayerGameStats(
            game_id=game.id,
            player_id=players[0].id,
            team_id=players[0].team_id,
            pass_yards=300,
            pass_touchdowns=3,
            interceptions=0,
            rush_yards=50,
            rush_touchdowns=1,
            receiving_yards=100,
            receiving_touchdowns=1,
            tackles=5,
            sacks=1.0,
            interceptions_caught=1,
            games_played=1
        )
        session.add(pg)
        session.commit()
        
        # Aggregate and compute awards
        aggregate_team_season(session, season)
        aggregate_player_season(session, season)
        compute_and_persist_awards(session, season)
        
        # Verify team awards favor the winning team
        coy_results = _get(session, season, "COY")
        gmoy_results = _get(session, season, "GMOY")
        
        if coy_results:
            assert coy_results[0].team_id == teams[0].id, "COY should favor winning team"
            assert coy_results[0].score > 0, "COY score should be positive"
        
        if gmoy_results:
            assert gmoy_results[0].team_id == teams[0].id, "GMOY should favor winning team"
            assert gmoy_results[0].score > 0, "GMOY score should be positive"
        
        # Verify player awards favor the productive player
        mvp_results = _get(session, season, "MVP")
        opoy_results = _get(session, season, "OPOY")
        
        if mvp_results:
            assert mvp_results[0].player_id == players[0].id, "MVP should favor productive player"
            assert mvp_results[0].score > 0, "MVP score should be positive"
        
        if opoy_results:
            assert opoy_results[0].player_id == players[0].id, "OPOY should favor productive player"
            assert opoy_results[0].score > 0, "OPOY score should be positive"
        
        print("OK Award scoring logic test passed")

def test_award_idempotency():
    """Test that award computation is idempotent."""
    season = 2025
    
    with memory_db() as session:
        # Create minimal test data
        from app.models.core_min import Team, Player, Game
        
        teams = session.exec(select(Team)).all()
        players = session.exec(select(Player)).all()
        
        if not teams or not players:
            pytest.skip("No teams or players available for testing")
        
        # Create a simple game
        game = Game(season=season, week=1, home_team_id=teams[0].id, away_team_id=teams[1].id)
        session.add(game)
        session.commit()
        
        # Create minimal stats
        tg = TeamGameStats(
            game_id=game.id,
            team_id=teams[0].id,
            points_scored=24,
            total_yards=400,
            passing_yards=250,
            rushing_yards=150,
            wins=1,
            losses=0,
            games_played=1
        )
        session.add(tg)
        session.commit()
        
        # Run aggregation and awards twice
        aggregate_team_season(session, season)
        aggregate_player_season(session, season)
        compute_and_persist_awards(session, season)
        
        first_results = {}
        for award in ["MVP", "OPOY", "DPOY", "ROY", "COY", "GMOY"]:
            first_results[award] = _get(session, season, award)
        
        # Run again
        compute_and_persist_awards(session, season)
        
        second_results = {}
        for award in ["MVP", "OPOY", "DPOY", "ROY", "COY", "GMOY"]:
            second_results[award] = _get(session, season, award)
        
        # Results should be identical
        for award in ["MVP", "OPOY", "DPOY", "ROY", "COY", "GMOY"]:
            first = first_results[award]
            second = second_results[award]
            assert len(first) == len(second), f"{award} result count changed"
            for i, (f, s) in enumerate(zip(first, second)):
                assert f.player_id == s.player_id, f"{award} rank {i+1} player changed"
                assert f.team_id == s.team_id, f"{award} rank {i+1} team changed"
                assert f.score == s.score, f"{award} rank {i+1} score changed"
        
        print("OK Award idempotency test passed")

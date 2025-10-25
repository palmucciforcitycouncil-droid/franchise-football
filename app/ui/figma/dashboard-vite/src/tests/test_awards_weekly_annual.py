# tests/test_awards_weekly_annual.py
import pytest
import json
from sqlmodel import Session, SQLModel, create_engine, select
from app.models.awards import WeeklyAward, AnnualAward, AnnualAwardProjection, WeeklyAwardType, AnnualAwardType
from app.models.stats import PlayerGameStats, PlayerSeasonStats, TeamSeasonStats, RecordEntry
from app.models.core_min import Team
from app.services.awards_scoring import (
    weekly_offense_score, weekly_defense_score, weekly_special_teams_score, weekly_rookie_score,
    season_player_mvp_score, season_opoy_score, season_dpoy_score, season_roy_score,
    season_coty_score, season_gmoty_score
)
from app.services.awards_compute import compute_weekly_awards, compute_annual_projections, finalize_annual_awards
from app.services.awards_pipeline import on_week_complete, on_season_finalized


@pytest.fixture(name="engine")
def engine_fixture():
    """Create a test database engine."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    """Create a test session."""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="test_team")
def test_team_fixture(session: Session):
    """Create a test team."""
    team = Team(abbrev="TEST", name="Test Team")
    session.add(team)
    session.commit()
    session.refresh(team)
    return team


def test_weekly_scoring_functions():
    """Test weekly scoring functions."""
    # Test offense scoring
    stats = {
        "pass_yds": 300, "pass_td": 3, "pass_int": 1, "sacks_taken": 2,
        "rush_yds": 100, "rush_td": 1, "fumbles_lost": 1,
        "rec_yds": 80, "rec_td": 1
    }
    off_score = weekly_offense_score(stats)
    assert off_score > 0  # Should be positive for good stats
    
    # Test defense scoring
    def_stats = {
        "tackles": 10, "tfl": 2, "sacks": 2.0, "ints": 1, "pbus": 3, "ff": 1, "fr": 1, "td_def": 1
    }
    def_score = weekly_defense_score(def_stats)
    assert def_score > 0  # Should be positive for good stats
    
    # Test special teams scoring
    st_stats = {
        "fg_made": 3, "fg_att": 4, "xp_made": 4, "punts": 3, "punt_yds": 120, "kr_yds": 80, "pr_yds": 40
    }
    st_score = weekly_special_teams_score(st_stats)
    assert st_score > 0  # Should be positive for good stats


def test_season_scoring_functions():
    """Test season scoring functions."""
    # Test MVP scoring
    mvp_stats = {
        "pass_yds": 4000, "pass_td": 30, "pass_int": 10, "rush_yds": 200, "rush_td": 2,
        "rec_yds": 100, "rec_td": 1, "fumbles_lost": 2
    }
    mvp_score = season_player_mvp_score(mvp_stats)
    assert mvp_score > 0  # Should be positive for good stats
    
    # Test team scoring
    team_stats = {
        "w_pct": 0.75, "points_for": 400, "points_against": 300, "improvement": 0.1
    }
    coty_score = season_coty_score(team_stats)
    gmoty_score = season_gmoty_score(team_stats)
    assert coty_score > 0 and gmoty_score > 0  # Should be positive for good stats


def test_weekly_awards_basic(session: Session, test_team):
    """Test basic weekly awards computation."""
    season, week = 2025, 3
    player_id = 1
    
    # Create offense star game
    game1 = PlayerGameStats(
        season=season, week=week, game_id=1, team_id=test_team.id, player_id=player_id,
        pass_yds=380, pass_td=4, pass_int=0, sacks_taken=1,
        rush_yds=50, rush_td=1, fumbles_lost=0,
        rec_yds=0, rec_td=0
    )
    
    # Create defense star game
    game2 = PlayerGameStats(
        season=season, week=week, game_id=1, team_id=test_team.id, player_id=2,
        pass_yds=0, pass_td=0, pass_int=0, sacks_taken=0,
        rush_yds=0, rush_td=0, fumbles_lost=0,
        rec_yds=0, rec_td=0,
        tackles=12, tfl=2, sacks=2.0, ints=1, pbus=3, ff=1, fr=1, td_def=1
    )
    
    session.add_all([game1, game2])
    session.commit()
    
    # Compute weekly awards
    compute_weekly_awards(session, season, week)
    
    # Verify awards were created
    awards = list(session.exec(select(WeeklyAward).where(WeeklyAward.season==season, WeeklyAward.week==week)))
    assert len(awards) >= 2  # Should have at least OPOTW and DPOTW
    
    award_types = {a.award for a in awards}
    assert WeeklyAwardType.OPOTW in award_types
    assert WeeklyAwardType.DPOTW in award_types
    
    # Check that offense player won OPOTW
    opotw = next(a for a in awards if a.award == WeeklyAwardType.OPOTW)
    assert opotw.winner_player_id == player_id
    assert opotw.score > 0


def test_annual_projections_basic(session: Session, test_team):
    """Test basic annual projections computation."""
    season = 2025
    player_id = 1
    
    # Create big season for MVP
    season_stats = PlayerSeasonStats(
        season=season, team_id=test_team.id, player_id=player_id,
        pass_yds=4800, pass_td=38, pass_int=10, sacks_taken=20,
        rush_yds=200, rush_td=2, fumbles_lost=3,
        rec_yds=0, rec_td=0,
        tackles=0, tfl=0, sacks=0.0, ints=0, pbus=0, ff=0, fr=0, td_def=0
    )
    
    session.add(season_stats)
    session.commit()
    
    # Compute annual projections
    compute_annual_projections(session, season)
    
    # Verify projections were created
    projections = list(session.exec(select(AnnualAwardProjection).where(AnnualAwardProjection.season==season)))
    assert len(projections) > 0
    
    # Check MVP projection
    mvp_proj = next((p for p in projections if p.award == AnnualAwardType.MVP), None)
    assert mvp_proj is not None
    assert mvp_proj.candidate_id == player_id
    assert mvp_proj.rank == 1
    assert mvp_proj.score > 0


def test_rookie_detection(session: Session, test_team):
    """Test rookie detection logic."""
    season = 2025
    rookie_id = 1
    veteran_id = 2
    
    # Create rookie (only one season)
    rookie_season = PlayerSeasonStats(
        season=season, team_id=test_team.id, player_id=rookie_id,
        pass_yds=3000, pass_td=20, pass_int=10
    )
    
    # Create veteran (multiple seasons)
    veteran_season1 = PlayerSeasonStats(
        season=season-1, team_id=test_team.id, player_id=veteran_id,
        pass_yds=2500, pass_td=15, pass_int=8
    )
    veteran_season2 = PlayerSeasonStats(
        season=season, team_id=test_team.id, player_id=veteran_id,
        pass_yds=2800, pass_td=18, pass_int=9
    )
    
    session.add_all([rookie_season, veteran_season1, veteran_season2])
    session.commit()
    
    # Test rookie detection
    from app.services.awards_compute import _is_rookie
    assert _is_rookie(session, rookie_id) == True
    assert _is_rookie(session, veteran_id) == False


def test_annual_finalization(session: Session, test_team):
    """Test annual awards finalization."""
    season = 2025
    player_id = 1
    
    # Create season stats
    season_stats = PlayerSeasonStats(
        season=season, team_id=test_team.id, player_id=player_id,
        pass_yds=5000, pass_td=40, pass_int=8
    )
    
    session.add(season_stats)
    session.commit()
    
    # Compute projections first
    compute_annual_projections(session, season)
    
    # Finalize awards
    finalize_annual_awards(session, season)
    
    # Verify final awards were created
    final_awards = list(session.exec(select(AnnualAward).where(AnnualAward.season==season)))
    assert len(final_awards) > 0
    
    # Check MVP final award
    mvp_final = next((a for a in final_awards if a.award == AnnualAwardType.MVP), None)
    assert mvp_final is not None
    assert mvp_final.finalized == True
    assert mvp_final.winner_player_id == player_id
    assert mvp_final.score > 0


def test_pipeline_integration(session: Session, test_team):
    """Test awards pipeline integration."""
    season, week = 2025, 1
    player_id = 1
    
    # Create game stats
    game_stats = PlayerGameStats(
        season=season, week=week, game_id=1, team_id=test_team.id, player_id=player_id,
        pass_yds=300, pass_td=3, pass_int=1, tackles=5, sacks=1.0
    )
    
    # Create season stats
    season_stats = PlayerSeasonStats(
        season=season, team_id=test_team.id, player_id=player_id,
        pass_yds=300, pass_td=3, pass_int=1, tackles=5, sacks=1.0
    )
    
    session.add_all([game_stats, season_stats])
    session.commit()
    
    # Run week complete pipeline
    on_week_complete(session, season, week)
    
    # Verify weekly awards were created
    weekly_awards = list(session.exec(select(WeeklyAward).where(WeeklyAward.season==season, WeeklyAward.week==week)))
    assert len(weekly_awards) > 0
    
    # Verify annual projections were created
    projections = list(session.exec(select(AnnualAwardProjection).where(AnnualAwardProjection.season==season)))
    assert len(projections) > 0
    
    # Run season finalization
    on_season_finalized(session, season)
    
    # Verify final awards were created
    final_awards = list(session.exec(select(AnnualAward).where(AnnualAward.season==season)))
    assert len(final_awards) > 0


def test_scoring_edge_cases():
    """Test scoring functions with edge cases."""
    # Test with zero stats
    zero_stats = {}
    assert weekly_offense_score(zero_stats) == 0.0
    assert weekly_defense_score(zero_stats) == 0.0
    assert weekly_special_teams_score(zero_stats) == 0.0
    
    # Test with negative stats (penalties)
    negative_stats = {
        "pass_int": 5, "sacks_taken": 10, "fumbles_lost": 3
    }
    off_score = weekly_offense_score(negative_stats)
    assert off_score < 0  # Should be negative due to penalties


def test_awards_idempotency(session: Session, test_team):
    """Test that awards computation is idempotent."""
    season, week = 2025, 1
    player_id = 1
    
    # Create game stats
    game_stats = PlayerGameStats(
        season=season, week=week, game_id=1, team_id=test_team.id, player_id=player_id,
        pass_yds=300, pass_td=3, pass_int=1
    )
    
    session.add(game_stats)
    session.commit()
    
    # Compute awards twice
    compute_weekly_awards(session, season, week)
    first_count = len(list(session.exec(select(WeeklyAward).where(WeeklyAward.season==season, WeeklyAward.week==week))))
    
    compute_weekly_awards(session, season, week)
    second_count = len(list(session.exec(select(WeeklyAward).where(WeeklyAward.season==season, WeeklyAward.week==week))))
    
    # Should have same count (idempotent)
    assert first_count == second_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



# tests/test_stats_hof.py
import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from app.models.stats import (
    PlayerGameStats, PlayerSeasonStats, PlayerCareerStats, 
    TeamGameStats, TeamSeasonStats, RecordEntry, RecordType, RecordCategory
)
from app.models.hof import HOFNominee, HOFInductee
from app.models.coach import Coach, CoachRole
from app.models.core_min import Team
from app.services.stats_aggregate import (
    upsert_player_season, upsert_player_career, upsert_team_season, update_records_for_season
)
from app.services.hof_service import (
    compute_player_hof_score, compute_coach_hof_score, 
    nominate_retiring_players, nominate_eligible_coaches, vote_and_induct
)
from app.services.stats_pipeline import on_game_finalized, on_regular_season_complete


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


@pytest.fixture(name="test_coach")
def test_coach_fixture(session: Session, test_team):
    """Create a test coach."""
    coach = Coach(
        team_id=test_team.id,
        role=CoachRole.HC,
        coach_name="Test Coach",
        hc_career_wins=100,
        hc_sb_wins=2
    )
    session.add(coach)
    session.commit()
    session.refresh(coach)
    return coach


def test_player_season_aggregation(session: Session, test_team):
    """Test player season stats aggregation."""
    player_id = 1
    season = 2025
    
    # Create game stats
    game1 = PlayerGameStats(
        season=season, week=1, game_id=1, team_id=test_team.id, player_id=player_id,
        pass_yds=250, pass_td=2, rush_yds=50, rush_td=1, tackles=5
    )
    game2 = PlayerGameStats(
        season=season, week=2, game_id=2, team_id=test_team.id, player_id=player_id,
        pass_yds=300, pass_td=3, rush_yds=75, rush_td=0, tackles=8
    )
    
    session.add_all([game1, game2])
    session.commit()
    
    # Aggregate season stats
    upsert_player_season(session, season, player_id, test_team.id, [game1, game2])
    session.commit()
    
    # Verify aggregation
    season_stats = session.exec(
        select(PlayerSeasonStats).where(
            PlayerSeasonStats.season == season,
            PlayerSeasonStats.player_id == player_id
        )
    ).first()
    
    assert season_stats is not None
    assert season_stats.pass_yds == 550  # 250 + 300
    assert season_stats.pass_td == 5     # 2 + 3
    assert season_stats.rush_yds == 125  # 50 + 75
    assert season_stats.rush_td == 1     # 1 + 0
    assert season_stats.tackles == 13    # 5 + 8


def test_player_career_aggregation(session: Session, test_team):
    """Test player career stats aggregation."""
    player_id = 1
    
    # Create season stats
    season1 = PlayerSeasonStats(
        season=2024, team_id=test_team.id, player_id=player_id,
        pass_yds=3000, pass_td=20, rush_yds=200, rush_td=2
    )
    season2 = PlayerSeasonStats(
        season=2025, team_id=test_team.id, player_id=player_id,
        pass_yds=3500, pass_td=25, rush_yds=300, rush_td=3
    )
    
    session.add_all([season1, season2])
    session.commit()
    
    # Aggregate career stats
    upsert_player_career(session, player_id)
    session.commit()
    
    # Verify aggregation
    career_stats = session.exec(
        select(PlayerCareerStats).where(
            PlayerCareerStats.player_id == player_id
        )
    ).first()
    
    assert career_stats is not None
    assert career_stats.seasons == 2
    assert career_stats.pass_yds == 6500  # 3000 + 3500
    assert career_stats.pass_td == 45     # 20 + 25
    assert career_stats.rush_yds == 500   # 200 + 300
    assert career_stats.rush_td == 5      # 2 + 3


def test_team_season_aggregation(session: Session, test_team):
    """Test team season stats aggregation."""
    season = 2025
    opp_team_id = 2
    
    # Create game stats
    game1 = TeamGameStats(
        season=season, week=1, game_id=1, team_id=test_team.id, opp_team_id=opp_team_id,
        points_for=28, points_against=14, total_yds=400, pass_yds=250, rush_yds=150
    )
    game2 = TeamGameStats(
        season=season, week=2, game_id=2, team_id=test_team.id, opp_team_id=opp_team_id,
        points_for=21, points_against=17, total_yds=350, pass_yds=200, rush_yds=150
    )
    
    session.add_all([game1, game2])
    session.commit()
    
    # Aggregate season stats
    upsert_team_season(session, season, test_team.id, [game1, game2])
    session.commit()
    
    # Verify aggregation
    season_stats = session.exec(
        select(TeamSeasonStats).where(
            TeamSeasonStats.season == season,
            TeamSeasonStats.team_id == test_team.id
        )
    ).first()
    
    assert season_stats is not None
    assert season_stats.points_for == 49    # 28 + 21
    assert season_stats.points_against == 31 # 14 + 17
    assert season_stats.total_yds == 750    # 400 + 350
    assert season_stats.pass_yds == 450     # 250 + 200
    assert season_stats.rush_yds == 300     # 150 + 150


def test_records_update(session: Session, test_team):
    """Test records update functionality."""
    season = 2025
    
    # Create player season stats
    player1 = PlayerSeasonStats(
        season=season, team_id=test_team.id, player_id=1,
        pass_yds=5000, pass_td=40, sacks=15.0, ints=8
    )
    player2 = PlayerSeasonStats(
        season=season, team_id=test_team.id, player_id=2,
        pass_yds=4500, pass_td=35, sacks=12.0, ints=6
    )
    
    session.add_all([player1, player2])
    session.commit()
    
    # Update records
    update_records_for_season(session, season)
    
    # Verify records were created
    records = list(session.exec(select(RecordEntry)))
    assert len(records) > 0
    
    # Check specific records
    pass_yds_record = next(
        (r for r in records if r.category == RecordCategory.PASS_YDS and r.season == season), 
        None
    )
    assert pass_yds_record is not None
    assert pass_yds_record.player_id == 1  # Player with highest pass yards
    assert pass_yds_record.value == 5000


def test_player_hof_score_calculation(session: Session, test_team):
    """Test player HOF score calculation."""
    # Create career stats
    career_stats = PlayerCareerStats(
        player_id=1,
        seasons=15,
        pass_yds=50000,
        pass_td=350,
        rush_yds=2000,
        rush_td=25,
        rec_yds=1000,
        rec_td=5,
        sacks=100.0,
        ints=50,
        tackles=1000,
        fg_made=200,
        punts=500
    )
    
    score = compute_player_hof_score(career_stats)
    
    # Verify score calculation
    expected_score = (
        50000/1000 + 350*2 + 2000/100 + 25*3 +
        1000/100 + 5*3 + 100*4 + 50*4 +
        1000/20 + 200*0.5 + 500*0.2
    )
    assert score == expected_score


def test_coach_hof_score_calculation(test_coach):
    """Test coach HOF score calculation."""
    score = compute_coach_hof_score(test_coach)
    
    # Verify score calculation: wins*1.5 + sb_wins*25
    expected_score = 100*1.5 + 2*25  # 150 + 50 = 200
    assert score == expected_score


def test_hof_nomination_process(session: Session, test_team, test_coach):
    """Test HOF nomination process."""
    season = 2025
    
    # Create career stats for retiring player
    career_stats = PlayerCareerStats(
        player_id=1,
        seasons=15,
        pass_yds=50000,
        pass_td=350,
        sacks=100.0,
        ints=50,
        tackles=1000
    )
    session.add(career_stats)
    session.commit()
    
    # Nominate retiring players
    retiring_player_ids = [1]
    nominate_retiring_players(session, season, retiring_player_ids)
    
    # Verify nomination was created
    nominees = list(session.exec(select(HOFNominee)))
    assert len(nominees) == 1
    
    player_nominee = nominees[0]
    assert player_nominee.subject_type == "PLAYER"
    assert player_nominee.subject_id == 1
    assert player_nominee.season_nominated == season
    assert player_nominee.score >= 150  # Should meet threshold
    
    # Nominate eligible coaches
    eligible_coach_ids = [test_coach.coach_id]
    nominate_eligible_coaches(session, season, eligible_coach_ids)
    
    # Verify coach nomination
    nominees = list(session.exec(select(HOFNominee)))
    assert len(nominees) == 2
    
    coach_nominee = next(n for n in nominees if n.subject_type == "COACH")
    assert coach_nominee.subject_id == test_coach.coach_id
    assert coach_nominee.score >= 120  # Should meet threshold


def test_hof_voting_and_induction(session: Session, test_team):
    """Test HOF voting and induction process."""
    season = 2025
    
    # Create high-scoring nominee
    nominee = HOFNominee(
        subject_type="PLAYER",
        subject_id=1,
        season_nominated=season,
        ballot_class=season,
        score=200.0,  # Above threshold
        inducted=False
    )
    session.add(nominee)
    session.commit()
    
    # Vote and induct
    vote_and_induct(session, season, cutoff_score=160.0)
    
    # Verify induction
    session.refresh(nominee)
    assert nominee.inducted == True
    assert nominee.votes_for >= 8
    
    # Verify inductee was created
    inductees = list(session.exec(select(HOFInductee)))
    assert len(inductees) == 1
    
    inductee = inductees[0]
    assert inductee.subject_type == "PLAYER"
    assert inductee.subject_id == 1
    assert inductee.class_year == season


def test_stats_pipeline_game_finalized(session: Session, test_team):
    """Test stats pipeline on game finalized."""
    game_id = 1
    player_id = 1
    season = 2025
    
    # Create game stats
    player_game = PlayerGameStats(
        season=season, week=1, game_id=game_id, team_id=test_team.id, player_id=player_id,
        pass_yds=300, pass_td=2, rush_yds=50, tackles=5
    )
    team_game = TeamGameStats(
        season=season, week=1, game_id=game_id, team_id=test_team.id, opp_team_id=2,
        points_for=28, points_against=14, total_yds=400
    )
    
    session.add_all([player_game, team_game])
    session.commit()
    
    # Run pipeline
    on_game_finalized(session, game_id)
    
    # Verify season stats were created
    player_season = session.exec(
        select(PlayerSeasonStats).where(
            PlayerSeasonStats.player_id == player_id,
            PlayerSeasonStats.season == season
        )
    ).first()
    
    assert player_season is not None
    assert player_season.pass_yds == 300
    assert player_season.pass_td == 2
    
    # Verify team season stats were created
    team_season = session.exec(
        select(TeamSeasonStats).where(
            TeamSeasonStats.team_id == test_team.id,
            TeamSeasonStats.season == season
        )
    ).first()
    
    assert team_season is not None
    assert team_season.points_for == 28
    assert team_season.points_against == 14


def test_stats_pipeline_season_complete(session: Session, test_team):
    """Test stats pipeline on season complete."""
    season = 2025
    
    # Create season stats
    player_season = PlayerSeasonStats(
        season=season, team_id=test_team.id, player_id=1,
        pass_yds=5000, pass_td=40, sacks=15.0
    )
    session.add(player_season)
    session.commit()
    
    # Run pipeline
    on_regular_season_complete(session, season)
    
    # Verify records were created
    records = list(session.exec(select(RecordEntry)))
    assert len(records) > 0
    
    # Check that single-season records exist
    single_season_records = [r for r in records if r.record_type == RecordType.SINGLE_SEASON]
    assert len(single_season_records) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

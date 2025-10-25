# tests/test_extended_stats.py
import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from app.models.stats import (
    PlayerGameStats, PlayerSeasonStats, PlayerCareerStats, 
    RecordEntry, RecordType, RecordCategory
)
from app.models.core_min import Team
from app.services.stats_aggregate import upsert_player_season, upsert_player_career, update_records_for_season
from app.services.stats_derived import (
    derive_passing, derive_rushing, derive_receiving, derive_ball_security,
    derive_defense, derive_special_teams, derive_participation, derive_all
)


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


def test_rollup_extended_fields(session: Session, test_team):
    """Test that extended fields are properly aggregated."""
    season = 2025
    player_id = 1
    
    # Create two games with extended fields
    game1 = PlayerGameStats(
        season=season, week=1, game_id=1, team_id=test_team.id, player_id=player_id,
        pass_att=30, pass_cmp=20, pass_yds=250, pass_td=2, pass_int=1,
        air_yds=180, yac_gained=70, deep_att=6,
        rush_att=10, rush_yds=45, rush_td=1, yards_after_contact=20,
        tar=8, rec=6, rec_yds=85, rec_td=1, yac=35, drops=1,
        tackles=3, sacks=1.0, pressures=4, pbus=2, ints=1,
        fg_made=1, fg_att=1, punts=2, punts_inside_20=1, long_fg_made=52,
        kr=1, kr_yds=35, pr=0, pr_yds=0
    )
    
    game2 = PlayerGameStats(
        season=season, week=2, game_id=2, team_id=test_team.id, player_id=player_id,
        pass_att=28, pass_cmp=18, pass_yds=260, pass_td=2, pass_int=0,
        air_yds=170, yac_gained=90, deep_att=5,
        rush_att=8, rush_yds=30, rush_td=0, yards_after_contact=10,
        tar=7, rec=5, rec_yds=60, rec_td=0, yac=20, drops=0,
        tackles=2, sacks=0.5, pressures=3, pbus=1,
        fg_made=0, fg_att=1, punts=1, punts_inside_20=0
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
    assert season_stats.pass_yds == 510  # 250 + 260
    assert season_stats.rush_yds == 75   # 45 + 30
    assert season_stats.rec_yds == 145  # 85 + 60
    assert season_stats.sacks >= 1.5     # 1.0 + 0.5
    assert season_stats.air_yds == 350  # 180 + 170
    assert season_stats.yac_gained == 160  # 70 + 90
    assert season_stats.deep_att == 11  # 6 + 5
    assert season_stats.pressures == 7  # 4 + 3
    assert season_stats.punts_inside_20 == 1  # 1 + 0
    assert season_stats.long_fg_made == 52  # max(52, 0)


def test_career_aggregation_extended_fields(session: Session, test_team):
    """Test career aggregation with extended fields."""
    player_id = 1
    season1 = 2025
    season2 = 2026
    
    # Create two season stats for the same player
    season_stats1 = PlayerSeasonStats(
        season=season1, team_id=test_team.id, player_id=player_id,
        pass_yds=3000, pass_td=20, rush_yds=500, tackles=50,
        pressures=15, pbus=8, punts_inside_20=5, long_fg_made=55
    )
    season_stats2 = PlayerSeasonStats(
        season=season2, team_id=test_team.id, player_id=player_id,
        pass_yds=3500, pass_td=25, rush_yds=600, tackles=60,
        pressures=18, pbus=12, punts_inside_20=7, long_fg_made=60
    )
    session.add_all([season_stats1, season_stats2])
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
    assert career_stats.rush_yds == 1100  # 500 + 600
    assert career_stats.tackles == 110    # 50 + 60
    assert career_stats.pressures == 33   # 15 + 18
    assert career_stats.pbus == 20        # 8 + 12
    assert career_stats.punts_inside_20 == 12  # 5 + 7
    assert career_stats.long_fg_made == 60     # max(55, 60)


def test_derived_passing_metrics():
    """Test derived passing metrics calculation."""
    stats = {
        "pass_att": 100, "pass_cmp": 65, "pass_yds": 800, "pass_td": 6, "pass_int": 3, "sacks_taken": 5,
        "air_yds": 500, "yac_gained": 300, "deep_att": 15, "play_action_att": 20, "screen_att": 10,
        "pressure_dropbacks": 8, "hits_on_qb": 3, "throwaways": 2, "batted_passes": 1, "drops_forced": 2,
        "tar": 80
    }
    
    derived = derive_passing(stats)
    
    assert derived["cmp_pct"] == 0.65  # 65/100
    assert derived["yds_per_att"] == 8.0  # 800/100
    assert derived["yds_per_cmp"] == 800/65  # 800/65
    assert derived["td_pct"] == 0.06  # 6/100
    assert derived["int_pct"] == 0.03  # 3/100
    assert derived["sack_rate"] == 5/105  # 5/(100+5)
    assert derived["air_yds_share"] == 500/800  # 500/800
    assert derived["yac_share"] == 300/800  # 300/800
    assert derived["deep_att_rate"] == 15/100  # 15/100
    assert derived["play_action_rate"] == 20/100  # 20/100
    assert derived["screen_rate"] == 10/100  # 10/100
    assert derived["pressure_rate"] == 8/105  # 8/(100+5)
    assert derived["hit_rate"] == 3/105  # 3/(100+5)
    assert derived["throwaway_rate"] == 2/105  # 2/(100+5)
    assert derived["batted_rate"] == 1/100  # 1/100
    assert derived["drop_rate_against_qb"] == 2/80  # 2/80
    assert derived["passer_rating"] > 0  # Should be calculated


def test_derived_rushing_metrics():
    """Test derived rushing metrics calculation."""
    stats = {
        "rush_att": 200, "rush_yds": 1000, "rush_td": 8,
        "yards_before_contact": 600, "yards_after_contact": 400,
        "designed_rush_att": 180, "scramble_att": 20
    }
    
    derived = derive_rushing(stats)
    
    assert derived["yds_per_rush"] == 5.0  # 1000/200
    assert derived["td_rate_rush"] == 0.04  # 8/200
    assert derived["yards_before_contact_per_att"] == 3.0  # 600/200
    assert derived["yards_after_contact_per_att"] == 2.0  # 400/200
    assert derived["designed_rush_share"] == 0.9  # 180/200
    assert derived["scramble_share"] == 0.1  # 20/200


def test_derived_receiving_metrics():
    """Test derived receiving metrics calculation."""
    stats = {
        "tar": 100, "rec": 70, "rec_yds": 800, "rec_td": 6,
        "air_yds_for": 500, "yac": 300, "drops": 5,
        "contested_catches_won": 10, "receptions_deep": 15
    }
    
    derived = derive_receiving(stats)
    
    assert derived["catch_pct"] == 0.7  # 70/100
    assert derived["yds_per_rec"] == 800/70  # 800/70
    assert derived["yds_per_target"] == 8.0  # 800/100
    assert derived["td_per_target"] == 0.06  # 6/100
    assert derived["air_yds_share_for"] == 500/800  # 500/800
    assert derived["yac_per_rec"] == 300/70  # 300/70
    assert derived["contested_catch_rate"] == 10/70  # 10/70
    assert derived["deep_target_rate"] == 15/70  # 15/70


def test_derived_defense_metrics():
    """Test derived defensive metrics calculation."""
    stats = {
        "tackles": 80, "missed_tackles": 10, "pressures": 20, "sacks": 5.0,
        "targets_defended": 50, "receptions_allowed": 30, "rec_yds_allowed": 400,
        "yacs_allowed": 100, "penalties_committed_def": 3, "ints": 2, "fr": 1
    }
    
    derived = derive_defense(stats)
    
    assert derived["missed_tackle_rate"] == 10/90  # 10/(80+10)
    assert derived["pressures_per_pass_snap"] == 20/50  # 20/50
    assert derived["pressure_conversion_rate"] == 5.0/20  # 5/20
    assert derived["comp_allowed_pct"] == 30/50  # 30/50
    assert derived["yards_per_target_allowed"] == 8.0  # 400/50
    assert derived["yacs_allowed_per_rec"] == 100/30  # 100/30
    assert derived["takeaways"] == 3  # 2+1
    assert derived["penalty_rate_def"] == 3/50  # 3/50


def test_derived_special_teams_metrics():
    """Test derived special teams metrics calculation."""
    stats = {
        "fg_made": 20, "fg_att": 25, "xp_made": 35, "xp_att": 35,
        "punts": 40, "punt_yds": 1600, "punts_inside_20": 15, "punt_touchbacks": 5,
        "punt_return_yds_allowed": 200, "kickoffs": 50, "touchbacks": 30,
        "avg_kickoff_yds": 65.0, "kr": 20, "kr_yds": 500, "kr_td": 1,
        "pr": 15, "pr_yds": 150, "pr_td": 0, "st_tackles": 8, "st_missed_tackles": 2,
        "snaps_st": 100, "long_fg_made": 55
    }
    
    derived = derive_special_teams(stats)
    
    assert derived["fg_pct"] == 0.8  # 20/25
    assert derived["xp_pct"] == 1.0  # 35/35
    assert derived["gross_punt_avg"] == 40.0  # 1600/40
    assert derived["net_punt_avg"] == 35.0  # (1600-200)/40
    assert derived["inside_20_rate"] == 0.375  # 15/40
    assert derived["punt_touchback_rate"] == 0.125  # 5/40
    assert derived["touchback_rate"] == 0.6  # 30/50
    assert derived["avg_kickoff_depth"] == 65.0
    assert derived["kr_avg"] == 25.0  # 500/20
    assert derived["pr_avg"] == 10.0  # 150/15
    assert derived["return_td_rate"] == 1/35  # (1+0)/(20+15)
    assert derived["st_tackle_rate"] == 8/100  # 8/100
    assert derived["st_missed_tackle_rate"] == 2/100  # 2/100
    assert derived["fg_long"] == 55


def test_derived_participation_metrics():
    """Test derived participation metrics calculation."""
    stats = {
        "snaps_off": 500, "snaps_def": 300, "snaps_st": 100,
        "games_played": 16, "games_started": 12
    }
    team_snaps = (1000, 800, 200)  # (off, def, st)
    
    derived = derive_participation(stats, team_snaps)
    
    assert derived["snap_share_off"] == 0.5  # 500/1000
    assert derived["snap_share_def"] == 0.375  # 300/800
    assert derived["snap_share_st"] == 0.5  # 100/200
    assert derived["games_active_pct"] == 1.0  # 16/16 (trivial)
    assert derived["starts_rate"] == 0.75  # 12/16


def test_derived_all_metrics():
    """Test the derive_all function."""
    stats = {
        "pass_att": 50, "pass_cmp": 35, "pass_yds": 350, "pass_td": 3, "pass_int": 1, "sacks_taken": 3,
        "rush_att": 10, "rush_yds": 40, "rush_td": 1,
        "tar": 8, "rec": 5, "rec_yds": 60, "rec_td": 1,
        "tackles": 5, "pressures": 2, "sacks": 1.0,
        "fg_made": 1, "fg_att": 1, "punts": 2
    }
    touches = 65  # 50 + 5 + 10
    
    derived = derive_all(stats, touches)
    
    # Should have all categories
    assert "cmp_pct" in derived
    assert "yds_per_rush" in derived
    assert "catch_pct" in derived
    assert "fumbles_per_touch" in derived
    assert "missed_tackle_rate" in derived
    assert "fg_pct" in derived
    assert "snap_share_off" in derived
    
    # Check some specific values
    assert derived["cmp_pct"] == 0.7  # 35/50
    assert derived["yds_per_rush"] == 4.0  # 40/10
    assert derived["catch_pct"] == 0.625  # 5/8


def test_records_extended_categories(session: Session, test_team):
    """Test that extended record categories are properly tracked."""
    season = 2025
    player_id = 1
    
    # Create season stats with extended fields
    season_stats = PlayerSeasonStats(
        season=season, team_id=test_team.id, player_id=player_id,
        pressures=25, pbus=15, kr_td=2, pr_td=1, punts_inside_20=10, long_fg_made=60
    )
    session.add(season_stats)
    session.commit()
    
    # Update records
    update_records_for_season(session, season)
    
    # Verify extended records were created
    records = list(session.exec(select(RecordEntry)))
    assert len(records) > 0
    
    # Check specific extended records
    pressures_record = next(
        (r for r in records if r.category == RecordCategory.PRESSURES and r.record_type == RecordType.SINGLE_SEASON),
        None
    )
    assert pressures_record is not None
    assert pressures_record.player_id == player_id
    assert pressures_record.value == 25
    
    kr_td_record = next(
        (r for r in records if r.category == RecordCategory.KR_TD and r.record_type == RecordType.SINGLE_SEASON),
        None
    )
    assert kr_td_record is not None
    assert kr_td_record.player_id == player_id
    assert kr_td_record.value == 2


def test_dynamic_field_aggregation():
    """Test that the dynamic field aggregation works with new fields."""
    # This test verifies that the _sum_fields function can handle any field
    # without needing to explicitly list them
    
    class MockSrc:
        def __init__(self):
            self.field1 = 10
            self.field2 = 20
            self.field3 = 30
            self.id = 1  # Should be excluded
    
    class MockDst:
        def __init__(self):
            self.field1 = 5
            self.field2 = 15
            self.field3 = 25
            self.id = 2  # Should be excluded
        
        @property
        def __fields__(self):
            return {"field1": None, "field2": None, "field3": None, "id": None}
    
    src = MockSrc()
    dst = MockDst()
    
    from app.services.stats_aggregate import _sum_fields
    _sum_fields(dst, src, {"id"})
    
    assert dst.field1 == 15  # 5 + 10
    assert dst.field2 == 35  # 15 + 20
    assert dst.field3 == 55  # 25 + 30
    assert dst.id == 2  # Should remain unchanged


def test_safe_division():
    """Test the safe division function."""
    from app.services.stats_derived import _safe_div
    
    assert _safe_div(10, 2) == 5.0
    assert _safe_div(10, 0) == 0.0
    assert _safe_div(0, 5) == 0.0
    assert _safe_div(0, 0) == 0.0
    assert _safe_div(7, 3) == 7/3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Advanced validator tests for sack shares, coverage consistency, and other validations.
"""

import pytest
import json
from sqlmodel import Session, create_engine, SQLModel
from app.models.pbp_event import PBPEvent
from app.models.stats_models import PlayerGameStats, TeamGameStats
from app.services.stats.validators import (
    validate_sack_shares, validate_coverage_consistency, 
    validate_special_teams_consistency, validate_situational_splits,
    validate_team_totals, create_validation_report
)


@pytest.fixture
def test_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def invalid_sack_events():
    """PBP events with invalid sack shares."""
    return [
        {
            "game_id": 1001,
            "drive_id": 1,
            "play_id": 1,
            "quarter": 1,
            "clock": "15:00",
            "offense_team_id": 1,
            "defense_team_id": 2,
            "down": 1,
            "distance": 10,
            "yardline": 25,
            "play_type": "pass",
            "yards_gained": -5,
            "is_scoring_play": False,
            "points_offense": 0,
            "points_defense": 0,
            "passer_id": 101,
            "target_id": 201,
            "completed": False,
            "air_yards": 0,
            "yac": 0,
            "interception": False,
            "sack": True,
            "sack_yards": 5,
            "qb_hit": True,
            "pressure": True,
            "thrown_away": False,
            "pressures_by_ids": [401, 402],
            "hits_by_ids": [401],
            "sack_split": [[401, 0.3], [402, 0.3]],  # Sums to 0.6, should be 1.0
            "is_third_down": False,
            "is_fourth_down": False,
            "is_red_zone": False,
            "is_goal_to_go": False,
            "is_two_minute": False,
            "is_garbage_time_excluded": False,
            "snaps_offense": 1,
            "snaps_defense": 0,
            "snaps_st": 0
        },
        {
            "game_id": 1001,
            "drive_id": 1,
            "play_id": 2,
            "quarter": 1,
            "clock": "14:30",
            "offense_team_id": 1,
            "defense_team_id": 2,
            "down": 1,
            "distance": 10,
            "yardline": 25,
            "play_type": "pass",
            "yards_gained": -3,
            "is_scoring_play": False,
            "points_offense": 0,
            "points_defense": 0,
            "passer_id": 101,
            "target_id": 202,
            "completed": False,
            "air_yards": 0,
            "yac": 0,
            "interception": False,
            "sack": True,
            "sack_yards": 3,
            "qb_hit": True,
            "pressure": True,
            "thrown_away": False,
            "pressures_by_ids": [403],
            "hits_by_ids": [403],
            "sack_split": [[403, -0.5]],  # Negative share
            "is_third_down": False,
            "is_fourth_down": False,
            "is_red_zone": False,
            "is_goal_to_go": False,
            "is_two_minute": False,
            "is_garbage_time_excluded": False,
            "snaps_offense": 1,
            "snaps_defense": 0,
            "snaps_st": 0
        }
    ]


@pytest.fixture
def inconsistent_coverage_events():
    """PBP events with inconsistent coverage."""
    return [
        {
            "game_id": 1001,
            "drive_id": 1,
            "play_id": 1,
            "quarter": 1,
            "clock": "15:00",
            "offense_team_id": 1,
            "defense_team_id": 2,
            "down": 1,
            "distance": 10,
            "yardline": 25,
            "play_type": "pass",
            "yards_gained": 12,
            "is_scoring_play": False,
            "points_offense": 0,
            "points_defense": 0,
            "passer_id": 101,
            "target_id": 201,
            "completed": True,
            "air_yards": 8,
            "yac": 4,
            "interception": False,
            "sack": False,
            "sack_yards": 0,
            "qb_hit": False,
            "pressure": False,
            "thrown_away": False,
            "targeted_db_id": 501,
            "coverage_type": "man",
            "coverage_result": "defended",  # Inconsistent: completed but marked as defended
            "is_third_down": False,
            "is_fourth_down": False,
            "is_red_zone": False,
            "is_goal_to_go": False,
            "is_two_minute": False,
            "is_garbage_time_excluded": False,
            "snaps_offense": 1,
            "snaps_defense": 0,
            "snaps_st": 0
        },
        {
            "game_id": 1001,
            "drive_id": 1,
            "play_id": 2,
            "quarter": 1,
            "clock": "14:30",
            "offense_team_id": 1,
            "defense_team_id": 2,
            "down": 1,
            "distance": 10,
            "yardline": 25,
            "play_type": "pass",
            "yards_gained": 0,
            "is_scoring_play": False,
            "points_offense": 0,
            "points_defense": 0,
            "passer_id": 101,
            "target_id": 202,
            "completed": False,
            "air_yards": 0,
            "yac": 0,
            "interception": False,
            "sack": False,
            "sack_yards": 0,
            "qb_hit": False,
            "pressure": False,
            "thrown_away": False,
            "targeted_db_id": 502,
            "coverage_type": "zone",
            "coverage_result": "caught",  # Inconsistent: incomplete but marked as caught
            "is_third_down": False,
            "is_fourth_down": False,
            "is_red_zone": False,
            "is_goal_to_go": False,
            "is_two_minute": False,
            "is_garbage_time_excluded": False,
            "snaps_offense": 1,
            "snaps_defense": 0,
            "snaps_st": 0
        }
    ]


@pytest.fixture
def invalid_special_teams_events():
    """PBP events with invalid special teams stats."""
    return [
        {
            "game_id": 1001,
            "drive_id": 1,
            "play_id": 1,
            "quarter": 1,
            "clock": "15:00",
            "offense_team_id": 1,
            "defense_team_id": 2,
            "down": 1,
            "distance": 10,
            "yardline": 25,
            "play_type": "punt",
            "yards_gained": 0,
            "is_scoring_play": False,
            "points_offense": 0,
            "points_defense": 0,
            "punter_id": 701,
            "kick_distance": 40,
            "net_yards": 50,  # Invalid: net > kick distance
            "in_20": True,
            "hang_time_ms": 4000,
            "is_third_down": False,
            "is_fourth_down": False,
            "is_red_zone": False,
            "is_goal_to_go": False,
            "is_two_minute": False,
            "is_garbage_time_excluded": False,
            "snaps_offense": 0,
            "snaps_defense": 0,
            "snaps_st": 1
        },
        {
            "game_id": 1001,
            "drive_id": 1,
            "play_id": 2,
            "quarter": 1,
            "clock": "14:30",
            "offense_team_id": 1,
            "defense_team_id": 2,
            "down": 1,
            "distance": 10,
            "yardline": 25,
            "play_type": "punt",
            "yards_gained": 0,
            "is_scoring_play": False,
            "points_offense": 0,
            "points_defense": 0,
            "punter_id": 702,
            "kick_distance": 50,
            "net_yards": 30,
            "in_20": True,
            "hang_time_ms": 4000,
            "yardline": 25,  # Invalid: in-20 but landed at 25
            "is_third_down": False,
            "is_fourth_down": False,
            "is_red_zone": False,
            "is_goal_to_go": False,
            "is_two_minute": False,
            "is_garbage_time_excluded": False,
            "snaps_offense": 0,
            "snaps_defense": 0,
            "snaps_st": 1
        }
    ]


@pytest.fixture
def invalid_situational_events():
    """PBP events with invalid situational splits."""
    return [
        {
            "game_id": 1001,
            "drive_id": 1,
            "play_id": 1,
            "quarter": 1,
            "clock": "15:00",
            "offense_team_id": 1,
            "defense_team_id": 2,
            "down": 1,
            "distance": 10,
            "yardline": 25,
            "play_type": "pass",
            "yards_gained": 12,
            "is_scoring_play": False,
            "points_offense": 0,
            "points_defense": 0,
            "passer_id": 101,
            "target_id": 201,
            "completed": True,
            "air_yards": 8,
            "yac": 4,
            "interception": False,
            "sack": False,
            "sack_yards": 0,
            "qb_hit": False,
            "pressure": False,
            "thrown_away": False,
            "is_third_down": True,
            "is_fourth_down": False,
            "is_red_zone": True,  # Invalid: red zone but yardline 25
            "is_goal_to_go": False,
            "is_two_minute": False,
            "is_garbage_time_excluded": False,
            "snaps_offense": 1,
            "snaps_defense": 0,
            "snaps_st": 0
        },
        {
            "game_id": 1001,
            "drive_id": 1,
            "play_id": 2,
            "quarter": 1,
            "clock": "14:30",
            "offense_team_id": 1,
            "defense_team_id": 2,
            "down": 2,
            "distance": 10,
            "yardline": 3,
            "play_type": "run",
            "yards_gained": 2,
            "is_scoring_play": False,
            "points_offense": 0,
            "points_defense": 0,
            "rusher_id": 301,
            "broken_tackle": 0,
            "is_third_down": False,
            "is_fourth_down": False,
            "is_red_zone": True,
            "is_goal_to_go": True,  # Invalid: goal-to-go but distance > yardline
            "is_two_minute": False,
            "is_garbage_time_excluded": False,
            "snaps_offense": 1,
            "snaps_defense": 0,
            "snaps_st": 0
        }
    ]


class TestSackShareValidation:
    """Test sack share validation."""
    
    def test_invalid_sack_shares_sum(self, test_session, invalid_sack_events):
        """Test validation catches sack shares that don't sum to 1.0."""
        # Insert events
        for event_data in invalid_sack_events:
            event = PBPEvent(**event_data)
            test_session.add(event)
        test_session.commit()
        
        # Validate sack shares
        messages = validate_sack_shares(1001, test_session)
        
        # Should have errors for invalid sack shares
        errors = [m for m in messages if m.level == "error"]
        assert len(errors) >= 2  # At least 2 errors
        
        # Check specific error messages
        error_messages = [m.message for m in errors]
        assert any("sum to 0.6" in msg for msg in error_messages)
        assert any("Negative sack share" in msg for msg in error_messages)
    
    def test_valid_sack_shares(self, test_session):
        """Test validation passes for valid sack shares."""
        valid_event = {
            "game_id": 1001,
            "drive_id": 1,
            "play_id": 1,
            "quarter": 1,
            "clock": "15:00",
            "offense_team_id": 1,
            "defense_team_id": 2,
            "down": 1,
            "distance": 10,
            "yardline": 25,
            "play_type": "pass",
            "yards_gained": -5,
            "is_scoring_play": False,
            "points_offense": 0,
            "points_defense": 0,
            "passer_id": 101,
            "target_id": 201,
            "completed": False,
            "air_yards": 0,
            "yac": 0,
            "interception": False,
            "sack": True,
            "sack_yards": 5,
            "qb_hit": True,
            "pressure": True,
            "thrown_away": False,
            "pressures_by_ids": [401, 402],
            "hits_by_ids": [401],
            "sack_split": [[401, 0.6], [402, 0.4]],  # Valid: sums to 1.0
            "is_third_down": False,
            "is_fourth_down": False,
            "is_red_zone": False,
            "is_goal_to_go": False,
            "is_two_minute": False,
            "is_garbage_time_excluded": False,
            "snaps_offense": 1,
            "snaps_defense": 0,
            "snaps_st": 0
        }
        
        event = PBPEvent(**valid_event)
        test_session.add(event)
        test_session.commit()
        
        # Validate sack shares
        messages = validate_sack_shares(1001, test_session)
        
        # Should have no errors
        errors = [m for m in messages if m.level == "error"]
        assert len(errors) == 0


class TestCoverageConsistencyValidation:
    """Test coverage consistency validation."""
    
    def test_inconsistent_coverage(self, test_session, inconsistent_coverage_events):
        """Test validation catches inconsistent coverage."""
        # Insert events
        for event_data in inconsistent_coverage_events:
            event = PBPEvent(**event_data)
            test_session.add(event)
        test_session.commit()
        
        # Validate coverage consistency
        messages = validate_coverage_consistency(1001, test_session)
        
        # Should have warnings for inconsistent coverage
        warnings = [m for m in messages if m.level == "warning"]
        assert len(warnings) >= 2  # At least 2 warnings
        
        # Check specific warning messages
        warning_messages = [m.message for m in warnings]
        assert any("Pass completed but marked as defended" in msg for msg in warning_messages)
        assert any("Pass incomplete but marked as caught" in msg for msg in warning_messages)


class TestSpecialTeamsValidation:
    """Test special teams validation."""
    
    def test_invalid_net_yards(self, test_session, invalid_special_teams_events):
        """Test validation catches invalid net yards."""
        # Insert events
        for event_data in invalid_special_teams_events:
            event = PBPEvent(**event_data)
            test_session.add(event)
        test_session.commit()
        
        # Validate special teams consistency
        messages = validate_special_teams_consistency(1001, test_session)
        
        # Should have errors for invalid ST stats
        errors = [m for m in messages if m.level == "error"]
        assert len(errors) >= 1
        
        # Check specific error message
        error_messages = [m.message for m in errors]
        assert any("Net yards (50) > kick distance (40)" in msg for msg in error_messages)


class TestSituationalSplitsValidation:
    """Test situational splits validation."""
    
    def test_invalid_situational_splits(self, test_session, invalid_situational_events):
        """Test validation catches invalid situational splits."""
        # Insert events
        for event_data in invalid_situational_events:
            event = PBPEvent(**event_data)
            test_session.add(event)
        test_session.commit()
        
        # Validate situational splits
        messages = validate_situational_splits(1001, test_session)
        
        # Should have warnings for invalid splits
        warnings = [m for m in messages if m.level == "warning"]
        assert len(warnings) >= 2
        
        # Check specific warning messages
        warning_messages = [m.message for m in warnings]
        assert any("Play marked red zone but yardline is 25" in msg for msg in warning_messages)
        assert any("Play marked goal-to-go but distance" in msg for msg in warning_messages)


class TestTeamTotalsValidation:
    """Test team totals validation."""
    
    def test_team_totals_validation(self, test_session):
        """Test team totals validation."""
        # Create mock team and player stats
        team_stats = TeamGameStats(
            game_id=1001,
            team_id=1,
            is_home_team=True,
            points_scored=21,
            total_yards=350,
            passing_yards=200,
            rushing_yards=150,
            turnovers_committed=1,
            turnovers_forced=2
        )
        test_session.add(team_stats)
        
        player_stats = [
            PlayerGameStats(
                game_id=1001,
                player_id=101,
                team_id=1,
                pass_yards=200,
                rush_yards=0,
                receiving_yards=0,
                pass_touchdowns=2,
                rush_touchdowns=0,
                receiving_touchdowns=0
            ),
            PlayerGameStats(
                game_id=1001,
                player_id=102,
                team_id=1,
                pass_yards=0,
                rush_yards=150,
                receiving_yards=0,
                pass_touchdowns=0,
                rush_touchdowns=1,
                receiving_touchdowns=0
            )
        ]
        
        for ps in player_stats:
            test_session.add(ps)
        
        test_session.commit()
        
        # Validate team totals
        messages = validate_team_totals(1001, test_session)
        
        # Should have no errors for consistent totals
        errors = [m for m in messages if m.level == "error"]
        assert len(errors) == 0


class TestValidationReport:
    """Test validation report creation."""
    
    def test_create_validation_report(self, test_session, invalid_sack_events):
        """Test creating a complete validation report."""
        # Insert events
        for event_data in invalid_sack_events:
            event = PBPEvent(**event_data)
            test_session.add(event)
        test_session.commit()
        
        # Create validation report
        report = create_validation_report(1001, test_session)
        
        assert report.game_id == 1001
        assert report.total_checks > 0
        assert report.errors > 0
        assert report.warnings >= 0
        assert report.is_valid == False  # Should be invalid due to errors
        assert len(report.messages) > 0
        
        # Check that errors are properly categorized
        error_categories = set(m.category for m in report.messages if m.level == "error")
        assert "sack_shares" in error_categories


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

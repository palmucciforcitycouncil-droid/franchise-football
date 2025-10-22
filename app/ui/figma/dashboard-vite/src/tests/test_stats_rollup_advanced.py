"""
Advanced rollup tests for OL/DL attribution, coverage, ST net/in-20, situational splits.
"""

import pytest
import json
from sqlmodel import Session, create_engine, SQLModel
from app.models.pbp_event import PBPEvent
from app.models.stats_models import PlayerGameStats, TeamGameStats
from app.services.stats.rollup import rollup_game_stats


@pytest.fixture
def test_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def advanced_pbp_events():
    """Advanced PBP events covering edge cases."""
    return [
        {
            "game_id": 1001,
            "drive_id": 1,
            "play_id": 1,
            "quarter": 1,
            "clock": "15:00",
            "offense_team_id": 1,
            "defense_team_id": 2,
            "down": 3,
            "distance": 8,
            "yardline": 15,
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
            "is_red_zone": True,
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
            "down": 4,
            "distance": 1,
            "yardline": 3,
            "play_type": "run",
            "yards_gained": 3,
            "is_scoring_play": True,
            "points_offense": 6,
            "points_defense": 0,
            "rusher_id": 301,
            "broken_tackle": 0,
            "is_third_down": False,
            "is_fourth_down": True,
            "is_red_zone": True,
            "is_goal_to_go": True,
            "is_two_minute": False,
            "is_garbage_time_excluded": False,
            "snaps_offense": 1,
            "snaps_defense": 0,
            "snaps_st": 0
        },
        {
            "game_id": 1001,
            "drive_id": 2,
            "play_id": 3,
            "quarter": 1,
            "clock": "14:00",
            "offense_team_id": 1,
            "defense_team_id": 2,
            "down": 1,
            "distance": 10,
            "yardline": 25,
            "play_type": "pass",
            "yards_gained": -6,
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
            "sack_yards": 6,
            "qb_hit": True,
            "pressure": True,
            "thrown_away": False,
            "pressures_by_ids": [401, 402, 403],
            "hits_by_ids": [401, 402],
            "sack_split": [[401, 0.4], [402, 0.4], [403, 0.2]],
            "ol_block": {"player_id": 501, "assignment": "pass_protect", "outcome": "beat"},
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
            "drive_id": 3,
            "play_id": 4,
            "quarter": 1,
            "clock": "13:30",
            "offense_team_id": 1,
            "defense_team_id": 2,
            "down": 1,
            "distance": 10,
            "yardline": 20,
            "play_type": "punt",
            "yards_gained": 0,
            "is_scoring_play": False,
            "points_offense": 0,
            "points_defense": 0,
            "punter_id": 701,
            "kick_distance": 50,
            "net_yards": 35,
            "in_20": True,
            "hang_time_ms": 4500,
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
            "drive_id": 4,
            "play_id": 5,
            "quarter": 1,
            "clock": "13:00",
            "offense_team_id": 2,
            "defense_team_id": 1,
            "down": 1,
            "distance": 10,
            "yardline": 25,
            "play_type": "pass",
            "yards_gained": 0,
            "is_scoring_play": False,
            "points_offense": 0,
            "points_defense": 0,
            "passer_id": 102,
            "target_id": 203,
            "completed": False,
            "air_yards": 0,
            "yac": 0,
            "interception": False,
            "sack": False,
            "sack_yards": 0,
            "qb_hit": False,
            "pressure": False,
            "thrown_away": False,
            "targeted_db_id": 601,
            "pass_breakup_by_id": 601,
            "coverage_type": "man",
            "coverage_result": "defended",
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


class TestAdvancedRollup:
    """Test advanced rollup scenarios."""
    
    def test_ol_dl_attribution(self, test_session, advanced_pbp_events):
        """Test OL/DL attribution with shared sacks."""
        # Insert events
        for event_data in advanced_pbp_events:
            event = PBPEvent(**event_data)
            test_session.add(event)
        test_session.commit()
        
        # Roll up stats
        rollup_game_stats(1001, test_session)
        
        # Check sack attribution
        sack_stats = test_session.exec(
            test_session.query(PlayerGameStats).filter(
                PlayerGameStats.game_id == 1001,
                PlayerGameStats.sacks > 0
            )
        ).all()
        
        # Should have 3 players with fractional sacks
        assert len(sack_stats) == 3
        total_sacks = sum(ps.sacks for ps in sack_stats)
        assert abs(total_sacks - 1.0) < 0.01
        
        # Check individual sack shares
        sack_values = [ps.sacks for ps in sack_stats]
        assert 0.4 in sack_values  # Two players with 0.4
        assert 0.2 in sack_values  # One player with 0.2
    
    def test_coverage_targets_consistency(self, test_session, advanced_pbp_events):
        """Test coverage targets = comps + defended + INT + other."""
        # Insert events
        for event_data in advanced_pbp_events:
            event = PBPEvent(**event_data)
            test_session.add(event)
        test_session.commit()
        
        # Roll up stats
        rollup_game_stats(1001, test_session)
        
        # Check coverage stats for targeted DB
        db_stats = test_session.exec(
            test_session.query(PlayerGameStats).filter(
                PlayerGameStats.game_id == 1001,
                PlayerGameStats.player_id == 601
            )
        ).first()
        
        assert db_stats is not None
        assert db_stats.targets_against == 1
        assert db_stats.passes_defended == 1
    
    def test_special_teams_net_in20(self, test_session, advanced_pbp_events):
        """Test special teams net average and in-20."""
        # Insert events
        for event_data in advanced_pbp_events:
            event = PBPEvent(**event_data)
            test_session.add(event)
        test_session.commit()
        
        # Roll up stats
        rollup_game_stats(1001, test_session)
        
        # Check punt stats
        punt_stats = test_session.exec(
            test_session.query(PlayerGameStats).filter(
                PlayerGameStats.game_id == 1001,
                PlayerGameStats.punts > 0
            )
        ).first()
        
        assert punt_stats is not None
        assert punt_stats.punts == 1
        assert punt_stats.punt_yards == 50
        assert punt_stats.punt_net_yards == 35
        assert punt_stats.punts_in_20 == 1
    
    def test_situational_splits_consistency(self, test_session, advanced_pbp_events):
        """Test situational splits are consistent with unsplit totals."""
        # Insert events
        for event_data in advanced_pbp_events:
            event = PBPEvent(**event_data)
            test_session.add(event)
        test_session.commit()
        
        # Roll up stats
        rollup_game_stats(1001, test_session)
        
        # Check QB stats
        qb_stats = test_session.exec(
            test_session.query(PlayerGameStats).filter(
                PlayerGameStats.game_id == 1001,
                PlayerGameStats.player_id == 101
            )
        ).first()
        
        assert qb_stats is not None
        assert qb_stats.third_down_attempts == 1
        assert qb_stats.third_down_conversions == 1
        assert qb_stats.red_zone_attempts == 1
        assert qb_stats.red_zone_touchdowns == 0  # No TD on 3rd down pass
        
        # Check RB stats
        rb_stats = test_session.exec(
            test_session.query(PlayerGameStats).filter(
                PlayerGameStats.game_id == 1001,
                PlayerGameStats.player_id == 301
            )
        ).first()
        
        assert rb_stats is not None
        assert rb_stats.fourth_down_attempts == 1
        assert rb_stats.fourth_down_conversions == 1
        assert rb_stats.red_zone_attempts == 1
        assert rb_stats.red_zone_touchdowns == 1
        assert rb_stats.goal_to_go_attempts == 1
        assert rb_stats.goal_to_go_touchdowns == 1
    
    def test_team_totals_equal_player_sums(self, test_session, advanced_pbp_events):
        """Test team totals equal sum of player stats with tolerance."""
        # Insert events
        for event_data in advanced_pbp_events:
            event = PBPEvent(**event_data)
            test_session.add(event)
        test_session.commit()
        
        # Roll up stats
        rollup_game_stats(1001, test_session)
        
        # Check team 1 stats
        team1_stats = test_session.exec(
            test_session.query(TeamGameStats).filter(
                TeamGameStats.game_id == 1001,
                TeamGameStats.team_id == 1
            )
        ).first()
        
        # Get player stats for team 1
        team1_player_stats = test_session.exec(
            test_session.query(PlayerGameStats).filter(
                PlayerGameStats.game_id == 1001,
                PlayerGameStats.team_id == 1
            )
        ).all()
        
        # Sum player stats
        total_yards = sum(ps.pass_yards + ps.rush_yards + ps.receiving_yards for ps in team1_player_stats)
        total_touchdowns = sum(ps.pass_touchdowns + ps.rush_touchdowns + ps.receiving_touchdowns for ps in team1_player_stats)
        
        # Check consistency (allow some tolerance for special teams, etc.)
        assert abs(team1_stats.total_yards - total_yards) <= 50  # Allow tolerance
        assert team1_stats.points_scored == total_touchdowns * 6  # TDs worth 6 points
    
    def test_garbage_time_exclusion(self, test_session):
        """Test garbage time plays are excluded."""
        garbage_events = [
            {
                "game_id": 1001,
                "drive_id": 5,
                "play_id": 6,
                "quarter": 4,
                "clock": "2:00",
                "offense_team_id": 1,
                "defense_team_id": 2,
                "down": 1,
                "distance": 10,
                "yardline": 25,
                "play_type": "pass",
                "yards_gained": 15,
                "is_scoring_play": False,
                "points_offense": 0,
                "points_defense": 0,
                "passer_id": 101,
                "target_id": 201,
                "completed": True,
                "air_yards": 10,
                "yac": 5,
                "interception": False,
                "sack": False,
                "sack_yards": 0,
                "qb_hit": False,
                "pressure": False,
                "thrown_away": False,
                "is_third_down": False,
                "is_fourth_down": False,
                "is_red_zone": False,
                "is_goal_to_go": False,
                "is_two_minute": False,
                "is_garbage_time_excluded": True,  # This should be excluded
                "snaps_offense": 1,
                "snaps_defense": 0,
                "snaps_st": 0
            }
        ]
        
        # Insert events
        for event_data in garbage_events:
            event = PBPEvent(**event_data)
            test_session.add(event)
        test_session.commit()
        
        # Roll up stats
        rollup_game_stats(1001, test_session)
        
        # Check that garbage time stats are not included
        qb_stats = test_session.exec(
            test_session.query(PlayerGameStats).filter(
                PlayerGameStats.game_id == 1001,
                PlayerGameStats.player_id == 101
            )
        ).first()
        
        # Should be None since garbage time play was excluded
        assert qb_stats is None or qb_stats.pass_attempts == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

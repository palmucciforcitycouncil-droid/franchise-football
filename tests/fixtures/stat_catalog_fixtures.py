"""
Test fixtures for GDD v3.2 Stat Catalog system
Provides sample data and helper functions for testing advanced statistics
"""

import pytest
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from app.models.stats import PlayerGameStats, TeamGameStats, PlayerSeasonStats, TeamSeasonStats
from app.models.sim_models import Game, Team, Player
from app.models.pbp_event import PBPEvent


@pytest.fixture
def sample_team():
    """Sample team for testing"""
    return Team(
        id=1,
        name="Test Team",
        city="Test City",
        conference="AFC",
        division="North"
    )


@pytest.fixture
def sample_player():
    """Sample player for testing"""
    return Player(
        id=1,
        name="Test Player",
        position="QB",
        team_id=1
    )


@pytest.fixture
def sample_game():
    """Sample game for testing"""
    return Game(
        id=1,
        season=2025,
        week=1,
        home_team_id=1,
        away_team_id=2,
        home_score=24,
        away_score=21,
        status="final"
    )


@pytest.fixture
def sample_pbp_event():
    """Sample PBP event with advanced fields"""
    return PBPEvent(
        game_id=1,
        quarter=1,
        clock="15:00",
        offense_team_id=1,
        defense_team_id=2,
        down=1,
        distance=10,
        yardline=50,
        play_type="pass",
        yards_gained=15,
        is_scoring_play=False,
        
        # Advanced OL fields
        ol_block={
            "blocker_id": 5,
            "assignment": "pass_pro",
            "beaten_by_id": None,
            "outcome": "win"
        },
        
        # Advanced defense fields
        pressures_by_ids=[10, 11],
        hits_by_ids=[10],
        sack_split=[(10, 0.6), (11, 0.4)],
        tfl_by_ids=[],
        missed_tackle_by_ids=[],
        
        # Advanced coverage fields
        targeted_db_id=20,
        pass_breakup_by_id=None,
        coverage_type="man",
        coverage_result="caught",
        
        # Advanced special teams fields
        hang_time_ms=4500,
        net_yards=35,
        kick_distance=45,
        blocked_by_id=None,
        fair_catch=False,
        
        # Situational flags
        is_third_down=False,
        is_fourth_down=False,
        is_red_zone=False,
        is_goal_to_go=False,
        is_two_minute=False,
        is_hurry_up=False,
        is_garbage_time_excluded=False
    )


@pytest.fixture
def sample_player_game_stats():
    """Sample player game stats with advanced fields"""
    return PlayerGameStats(
        game_id=1,
        player_id=1,
        team_id=1,
        gp=True,
        gs=True,
        
        # Basic stats
        pass_attempts=30,
        pass_completions=20,
        pass_yards=250,
        pass_td=2,
        pass_int=1,
        rush_attempts=5,
        rush_yards=25,
        rush_td=0,
        
        # GDD v3.2 OL stats
        sacks_allowed=2.0,
        hits_allowed=3,
        pressures_allowed=5,
        tfl_allowed=1,
        run_block_wins=8,
        pass_block_wins=12,
        penalties_ol=1,
        
        # GDD v3.2 Defense stats
        pressures=2,
        qb_hits=1,
        sacks=1.5,
        tfl=1,
        run_stops=2,
        missed_tackles=1,
        
        # GDD v3.2 Coverage stats
        targets_faced=5,
        completions_allowed=3,
        yards_allowed=45,
        yac_allowed=15,
        td_allowed=0,
        passer_rating_against=85.2,
        
        # GDD v3.2 Special teams stats
        punt_net_avg=42.5,
        hang_time_avg=4.2,
        kick_distance_avg=65.0,
        blocked_kicks=0,
        return_avg=8.5,
        return_td=0,
        fair_catches=2,
        
        # GDD v3.2 Situational stats
        fourth_down_conversions=1,
        fourth_down_attempts=2,
        red_zone_td=1,
        red_zone_attempts=3,
        goal_to_go_td=1,
        goal_to_go_attempts=2,
        two_minute_plays=3,
        hurry_up_plays=2,
        garbage_time_excluded=0
    )


@pytest.fixture
def sample_team_game_stats():
    """Sample team game stats with advanced fields"""
    return TeamGameStats(
        game_id=1,
        team_id=1,
        gp=True,
        
        # Basic stats
        pass_attempts=30,
        pass_completions=20,
        pass_yards=250,
        pass_td=2,
        pass_int=1,
        rush_attempts=25,
        rush_yards=120,
        rush_td=1,
        total_yards=370,
        total_td=3,
        turnovers=2,
        
        # GDD v3.2 OL stats
        sacks_allowed=2.0,
        hits_allowed=3,
        pressures_allowed=5,
        tfl_allowed=1,
        run_block_wins=20,
        pass_block_wins=28,
        penalties_ol=2,
        
        # GDD v3.2 Defense stats
        pressures=4,
        qb_hits=2,
        sacks=2.0,
        tfl=2,
        run_stops=5,
        missed_tackles=3,
        
        # GDD v3.2 Coverage stats
        targets_faced=25,
        completions_allowed=18,
        yards_allowed=220,
        yac_allowed=75,
        td_allowed=2,
        passer_rating_against=95.5,
        
        # GDD v3.2 Special teams stats
        punts_in20=3,
        punt_net_avg=42.5,
        hang_time_avg=4.2,
        kick_distance_avg=65.0,
        blocked_kicks=0,
        returns=5,
        return_avg=8.5,
        return_td=0,
        fair_catches=2,
        
        # GDD v3.2 Situational stats
        fourth_down_conversions=2,
        fourth_down_attempts=4,
        red_zone_td=2,
        red_zone_attempts=4,
        goal_to_go_td=1,
        goal_to_go_attempts=2,
        two_minute_plays=5,
        hurry_up_plays=3,
        garbage_time_excluded=0
    )


@pytest.fixture
def sample_shared_sack_event():
    """Sample PBP event with shared sack (0.5 + 0.5)"""
    return PBPEvent(
        game_id=1,
        quarter=2,
        clock="10:30",
        offense_team_id=1,
        defense_team_id=2,
        down=2,
        distance=8,
        yardline=35,
        play_type="sack",
        yards_gained=-5,
        is_scoring_play=False,
        
        # Shared sack split
        sack_split=[(10, 0.5), (11, 0.5)],
        pressures_by_ids=[10, 11],
        hits_by_ids=[10, 11],
        
        # Situational flags
        is_third_down=False,
        is_fourth_down=False,
        is_red_zone=False,
        is_goal_to_go=False,
        is_two_minute=False,
        is_hurry_up=False,
        is_garbage_time_excluded=False
    )


@pytest.fixture
def sample_ol_penalty_event():
    """Sample PBP event with OL penalty"""
    return PBPEvent(
        game_id=1,
        quarter=3,
        clock="5:15",
        offense_team_id=1,
        defense_team_id=2,
        down=1,
        distance=10,
        yardline=20,
        play_type="penalty",
        yards_gained=-10,
        is_scoring_play=False,
        
        # OL penalty
        ol_block={
            "blocker_id": 5,
            "assignment": "pass_pro",
            "beaten_by_id": None,
            "outcome": "penalty"
        },
        penalty={
            "flag": True,
            "team_id": 1,
            "player_id": 5,
            "code": "HOLDING",
            "yards": 10,
            "automatic_first_down": False,
            "offsetting": False,
            "declined": False
        },
        
        # Situational flags
        is_third_down=False,
        is_fourth_down=False,
        is_red_zone=True,
        is_goal_to_go=False,
        is_two_minute=False,
        is_hurry_up=False,
        is_garbage_time_excluded=False
    )


@pytest.fixture
def sample_db_target_event():
    """Sample PBP event with DB target and PBU"""
    return PBPEvent(
        game_id=1,
        quarter=4,
        clock="2:45",
        offense_team_id=1,
        defense_team_id=2,
        down=3,
        distance=7,
        yardline=45,
        play_type="pass",
        yards_gained=0,
        is_scoring_play=False,
        
        # Coverage stats
        targeted_db_id=20,
        pass_breakup_by_id=20,
        coverage_type="zone",
        coverage_result="defended",
        
        # Situational flags
        is_third_down=True,
        is_fourth_down=False,
        is_red_zone=False,
        is_goal_to_go=False,
        is_two_minute=True,
        is_hurry_up=False,
        is_garbage_time_excluded=False
    )


@pytest.fixture
def sample_punt_in20_event():
    """Sample PBP event with punt in-20"""
    return PBPEvent(
        game_id=1,
        quarter=1,
        clock="12:00",
        offense_team_id=1,
        defense_team_id=2,
        down=4,
        distance=8,
        yardline=45,
        play_type="punt",
        yards_gained=35,
        is_scoring_play=False,
        
        # Special teams stats
        kick_type="punt",
        punter_id=15,
        hang_time_ms=4200,
        net_yards=35,
        kick_distance=40,
        blocked_by_id=None,
        fair_catch=False,
        in_20=True,
        
        # Situational flags
        is_third_down=False,
        is_fourth_down=True,
        is_red_zone=False,
        is_goal_to_go=False,
        is_two_minute=False,
        is_hurry_up=False,
        is_garbage_time_excluded=False
    )


@pytest.fixture
def sample_red_zone_event():
    """Sample PBP event in red zone"""
    return PBPEvent(
        game_id=1,
        quarter=2,
        clock="8:30",
        offense_team_id=1,
        defense_team_id=2,
        down=2,
        distance=3,
        yardline=5,
        play_type="run",
        yards_gained=5,
        is_scoring_play=True,
        points_offense=6,
        points_defense=0,
        
        # Situational flags
        is_third_down=False,
        is_fourth_down=False,
        is_red_zone=True,
        is_goal_to_go=True,
        is_two_minute=False,
        is_hurry_up=False,
        is_garbage_time_excluded=False
    )


@pytest.fixture
def sample_garbage_time_event():
    """Sample PBP event in garbage time"""
    return PBPEvent(
        game_id=1,
        quarter=4,
        clock="1:30",
        offense_team_id=1,
        defense_team_id=2,
        down=1,
        distance=10,
        yardline=50,
        play_type="pass",
        yards_gained=12,
        is_scoring_play=False,
        
        # Situational flags
        is_third_down=False,
        is_fourth_down=False,
        is_red_zone=False,
        is_goal_to_go=False,
        is_two_minute=False,
        is_hurry_up=False,
        is_garbage_time_excluded=True
    )


def create_test_database_session():
    """Helper function to create a test database session"""
    from app.core.db import get_session
    return next(get_session())


def assert_sack_split_validity(sack_split: List[tuple]):
    """Helper function to validate sack split shares sum to 1.0"""
    total_share = sum(share for _, share in sack_split)
    assert abs(total_share - 1.0) < 1e-6, f"Sack split shares must sum to 1.0, got {total_share}"


def assert_team_ol_consistency(team_stats: TeamGameStats, opposing_stats: TeamGameStats):
    """Helper function to validate team OL vs opposing defense consistency"""
    assert team_stats.sacks_allowed == opposing_stats.sacks
    assert team_stats.pressures_allowed == opposing_stats.pressures
    assert team_stats.hits_allowed == opposing_stats.qb_hits


def assert_coverage_target_consistency(targets: int, completions: int, defended: int, intercepted: int):
    """Helper function to validate coverage target consistency"""
    assert targets >= completions + defended + intercepted, "Targets must be >= completions + defended + intercepted"


def assert_situational_totals_match_overall(player_stats: PlayerGameStats):
    """Helper function to validate situational totals match overall counts"""
    assert player_stats.fourth_down_attempts <= player_stats.pass_attempts + player_stats.rush_attempts
    assert player_stats.red_zone_attempts <= player_stats.pass_attempts + player_stats.rush_attempts
    assert player_stats.goal_to_go_attempts <= player_stats.red_zone_attempts
    assert player_stats.two_minute_plays <= player_stats.pass_attempts + player_stats.rush_attempts
    assert player_stats.hurry_up_plays <= player_stats.two_minute_plays

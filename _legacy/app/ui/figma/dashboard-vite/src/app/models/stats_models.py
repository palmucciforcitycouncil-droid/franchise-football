"""
SQLModel definitions for advanced stats tables.
Player and team game/season/career stats with advanced metrics.
"""

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class PlayerGameStats(SQLModel, table=True):
    """Player game stats with advanced metrics"""
    __tablename__ = "player_game_stats"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    player_id: int = Field(index=True)
    team_id: int = Field(index=True)
    
    # Snap counts
    snaps_offense: int = Field(default=0)
    snaps_defense: int = Field(default=0)
    snaps_special_teams: int = Field(default=0)
    
    # Passing stats
    pass_attempts: int = Field(default=0)
    pass_completions: int = Field(default=0)
    pass_yards: int = Field(default=0)
    pass_touchdowns: int = Field(default=0)
    interceptions: int = Field(default=0)
    sacks_taken: float = Field(default=0.0)  # Allow fractional sacks
    sack_yards: int = Field(default=0)
    qb_hits: int = Field(default=0)
    pressures_faced: int = Field(default=0)
    
    # Rushing stats
    rush_attempts: int = Field(default=0)
    rush_yards: int = Field(default=0)
    rush_touchdowns: int = Field(default=0)
    fumbles: int = Field(default=0)
    fumbles_lost: int = Field(default=0)
    
    # Receiving stats
    targets: int = Field(default=0)
    receptions: int = Field(default=0)
    receiving_yards: int = Field(default=0)
    receiving_touchdowns: int = Field(default=0)
    drops: int = Field(default=0)
    yards_after_catch: int = Field(default=0)
    
    # Defensive stats
    tackles: int = Field(default=0)
    tackles_for_loss: int = Field(default=0)
    sacks: float = Field(default=0.0)  # Allow fractional sacks
    quarterback_hits: int = Field(default=0)
    pressures: int = Field(default=0)
    pass_deflections: int = Field(default=0)
    interceptions_caught: int = Field(default=0)
    forced_fumbles: int = Field(default=0)
    fumble_recoveries: int = Field(default=0)
    
    # Coverage stats
    targets_against: int = Field(default=0)
    completions_allowed: int = Field(default=0)
    yards_allowed: int = Field(default=0)
    touchdowns_allowed: int = Field(default=0)
    passes_defended: int = Field(default=0)
    
    # Special Teams stats
    field_goals_made: int = Field(default=0)
    field_goals_attempted: int = Field(default=0)
    extra_points_made: int = Field(default=0)
    extra_points_attempted: int = Field(default=0)
    punts: int = Field(default=0)
    punt_yards: int = Field(default=0)
    punt_net_yards: int = Field(default=0)
    punts_in_20: int = Field(default=0)
    kickoff_returns: int = Field(default=0)
    kickoff_return_yards: int = Field(default=0)
    punt_returns: int = Field(default=0)
    punt_return_yards: int = Field(default=0)
    
    # Advanced OL stats
    sacks_allowed: float = Field(default=0.0)
    pressures_allowed: int = Field(default=0)
    qb_hits_allowed: int = Field(default=0)
    
    # Situational splits
    third_down_conversions: int = Field(default=0)
    third_down_attempts: int = Field(default=0)
    fourth_down_conversions: int = Field(default=0)
    fourth_down_attempts: int = Field(default=0)
    red_zone_touchdowns: int = Field(default=0)
    red_zone_attempts: int = Field(default=0)
    goal_to_go_touchdowns: int = Field(default=0)
    goal_to_go_attempts: int = Field(default=0)
    two_minute_touchdowns: int = Field(default=0)
    two_minute_attempts: int = Field(default=0)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TeamGameStats(SQLModel, table=True):
    """Team game stats with advanced metrics"""
    __tablename__ = "team_game_stats"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    team_id: int = Field(index=True)
    is_home_team: bool = Field(default=False)
    
    # Core team stats
    points_scored: int = Field(default=0)
    total_yards: int = Field(default=0)
    passing_yards: int = Field(default=0)
    rushing_yards: int = Field(default=0)
    turnovers_committed: int = Field(default=0)
    turnovers_forced: int = Field(default=0)
    
    # Special teams
    field_goals_made: int = Field(default=0)
    field_goals_attempted: int = Field(default=0)
    punts: int = Field(default=0)
    punt_net_yards: int = Field(default=0)
    punts_in_20: int = Field(default=0)
    
    # Situational splits
    third_down_conversions: int = Field(default=0)
    third_down_attempts: int = Field(default=0)
    fourth_down_conversions: int = Field(default=0)
    fourth_down_attempts: int = Field(default=0)
    red_zone_touchdowns: int = Field(default=0)
    red_zone_attempts: int = Field(default=0)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PlayerSeasonStats(SQLModel, table=True):
    """Player season aggregated stats"""
    __tablename__ = "player_season_stats"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(index=True)
    team_id: int = Field(index=True)
    season: int = Field(index=True)
    
    # Games played
    games_played: int = Field(default=0)
    games_started: int = Field(default=0)
    
    # All the same stat fields as PlayerGameStats
    # (abbreviated for brevity - would include all fields)
    snaps_offense: int = Field(default=0)
    snaps_defense: int = Field(default=0)
    snaps_special_teams: int = Field(default=0)
    
    # Passing stats
    pass_attempts: int = Field(default=0)
    pass_completions: int = Field(default=0)
    pass_yards: int = Field(default=0)
    pass_touchdowns: int = Field(default=0)
    interceptions: int = Field(default=0)
    sacks_taken: float = Field(default=0.0)
    sack_yards: int = Field(default=0)
    qb_hits: int = Field(default=0)
    pressures_faced: int = Field(default=0)
    
    # Rushing stats
    rush_attempts: int = Field(default=0)
    rush_yards: int = Field(default=0)
    rush_touchdowns: int = Field(default=0)
    fumbles: int = Field(default=0)
    fumbles_lost: int = Field(default=0)
    
    # Receiving stats
    targets: int = Field(default=0)
    receptions: int = Field(default=0)
    receiving_yards: int = Field(default=0)
    receiving_touchdowns: int = Field(default=0)
    drops: int = Field(default=0)
    yards_after_catch: int = Field(default=0)
    
    # Defensive stats
    tackles: int = Field(default=0)
    tackles_for_loss: int = Field(default=0)
    sacks: float = Field(default=0.0)
    quarterback_hits: int = Field(default=0)
    pressures: int = Field(default=0)
    pass_deflections: int = Field(default=0)
    interceptions_caught: int = Field(default=0)
    forced_fumbles: int = Field(default=0)
    fumble_recoveries: int = Field(default=0)
    
    # Coverage stats
    targets_against: int = Field(default=0)
    completions_allowed: int = Field(default=0)
    yards_allowed: int = Field(default=0)
    touchdowns_allowed: int = Field(default=0)
    passes_defended: int = Field(default=0)
    
    # Special Teams stats
    field_goals_made: int = Field(default=0)
    field_goals_attempted: int = Field(default=0)
    extra_points_made: int = Field(default=0)
    extra_points_attempted: int = Field(default=0)
    punts: int = Field(default=0)
    punt_yards: int = Field(default=0)
    punt_net_yards: int = Field(default=0)
    punts_in_20: int = Field(default=0)
    kickoff_returns: int = Field(default=0)
    kickoff_return_yards: int = Field(default=0)
    punt_returns: int = Field(default=0)
    punt_return_yards: int = Field(default=0)
    
    # Advanced OL stats
    sacks_allowed: float = Field(default=0.0)
    pressures_allowed: int = Field(default=0)
    qb_hits_allowed: int = Field(default=0)
    
    # Situational splits
    third_down_conversions: int = Field(default=0)
    third_down_attempts: int = Field(default=0)
    fourth_down_conversions: int = Field(default=0)
    fourth_down_attempts: int = Field(default=0)
    red_zone_touchdowns: int = Field(default=0)
    red_zone_attempts: int = Field(default=0)
    goal_to_go_touchdowns: int = Field(default=0)
    goal_to_go_attempts: int = Field(default=0)
    two_minute_touchdowns: int = Field(default=0)
    two_minute_attempts: int = Field(default=0)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TeamSeasonStats(SQLModel, table=True):
    """Team season aggregated stats"""
    __tablename__ = "team_season_stats"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(index=True)
    season: int = Field(index=True)
    
    # Games
    games_played: int = Field(default=0)
    wins: int = Field(default=0)
    losses: int = Field(default=0)
    ties: int = Field(default=0)
    
    # Core team stats
    points_scored: int = Field(default=0)
    points_allowed: int = Field(default=0)
    total_yards: int = Field(default=0)
    passing_yards: int = Field(default=0)
    rushing_yards: int = Field(default=0)
    yards_allowed: int = Field(default=0)
    passing_yards_allowed: int = Field(default=0)
    rushing_yards_allowed: int = Field(default=0)
    turnovers_committed: int = Field(default=0)
    turnovers_forced: int = Field(default=0)
    
    # Special teams
    field_goals_made: int = Field(default=0)
    field_goals_attempted: int = Field(default=0)
    punts: int = Field(default=0)
    punt_net_yards: int = Field(default=0)
    punts_in_20: int = Field(default=0)
    
    # Situational splits
    third_down_conversions: int = Field(default=0)
    third_down_attempts: int = Field(default=0)
    fourth_down_conversions: int = Field(default=0)
    fourth_down_attempts: int = Field(default=0)
    red_zone_touchdowns: int = Field(default=0)
    red_zone_attempts: int = Field(default=0)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

"""
Pydantic DTO models for Advanced Stats API responses.
No ORM leakage - pure data transfer objects.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class PlayerStatLine(BaseModel):
    """Individual player stat line for game/season/career"""
    player_id: int
    player_name: str
    position: str
    team_id: int
    team_name: str
    
    # Core stats
    games_played: int = 0
    games_started: int = 0
    snaps_offense: int = 0
    snaps_defense: int = 0
    snaps_special_teams: int = 0
    
    # Passing stats
    pass_attempts: int = 0
    pass_completions: int = 0
    pass_yards: int = 0
    pass_touchdowns: int = 0
    interceptions: int = 0
    sacks_taken: float = 0.0
    sack_yards: int = 0
    qb_hits: int = 0
    pressures_faced: int = 0
    
    # Rushing stats
    rush_attempts: int = 0
    rush_yards: int = 0
    rush_touchdowns: int = 0
    fumbles: int = 0
    fumbles_lost: int = 0
    
    # Receiving stats
    targets: int = 0
    receptions: int = 0
    receiving_yards: int = 0
    receiving_touchdowns: int = 0
    drops: int = 0
    yards_after_catch: int = 0
    
    # Defensive stats
    tackles: int = 0
    tackles_for_loss: int = 0
    sacks: float = 0.0
    quarterback_hits: int = 0
    pressures: int = 0
    pass_deflections: int = 0
    interceptions_caught: int = 0
    forced_fumbles: int = 0
    fumble_recoveries: int = 0
    
    # Coverage stats
    targets_against: int = 0
    completions_allowed: int = 0
    yards_allowed: int = 0
    touchdowns_allowed: int = 0
    passes_defended: int = 0
    
    # Special Teams stats
    field_goals_made: int = 0
    field_goals_attempted: int = 0
    extra_points_made: int = 0
    extra_points_attempted: int = 0
    punts: int = 0
    punt_yards: int = 0
    punt_net_yards: int = 0
    punts_in_20: int = 0
    kickoff_returns: int = 0
    kickoff_return_yards: int = 0
    punt_returns: int = 0
    punt_return_yards: int = 0
    
    # Advanced OL stats
    sacks_allowed: float = 0.0
    pressures_allowed: int = 0
    qb_hits_allowed: int = 0
    
    # Situational splits
    third_down_conversions: int = 0
    third_down_attempts: int = 0
    fourth_down_conversions: int = 0
    fourth_down_attempts: int = 0
    red_zone_touchdowns: int = 0
    red_zone_attempts: int = 0
    goal_to_go_touchdowns: int = 0
    goal_to_go_attempts: int = 0
    two_minute_touchdowns: int = 0
    two_minute_attempts: int = 0


class TeamStatLine(BaseModel):
    """Team stat line for game/season"""
    team_id: int
    team_name: str
    season: Optional[int] = None
    
    # Core team stats
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    ties: int = 0
    
    # Offensive team stats
    total_yards: int = 0
    passing_yards: int = 0
    rushing_yards: int = 0
    points_scored: int = 0
    turnovers_committed: int = 0
    
    # Defensive team stats
    yards_allowed: int = 0
    passing_yards_allowed: int = 0
    rushing_yards_allowed: int = 0
    points_allowed: int = 0
    turnovers_forced: int = 0
    
    # Special teams
    field_goals_made: int = 0
    field_goals_attempted: int = 0
    punts: int = 0
    punt_net_yards: int = 0
    punts_in_20: int = 0
    
    # Situational splits
    third_down_conversions: int = 0
    third_down_attempts: int = 0
    fourth_down_conversions: int = 0
    fourth_down_attempts: int = 0
    red_zone_touchdowns: int = 0
    red_zone_attempts: int = 0


class GameBoxDTO(BaseModel):
    """Complete game box score with advanced stats"""
    game_id: int
    home_team_id: int
    away_team_id: int
    home_team_name: str
    away_team_name: str
    season: int
    week: int
    game_type: Literal["regular", "playoffs", "super_bowl"]
    final_score_home: int
    final_score_away: int
    
    # Team totals
    home_team_stats: TeamStatLine
    away_team_stats: TeamStatLine
    
    # Player stats by team
    home_player_stats: List[PlayerStatLine]
    away_player_stats: List[PlayerStatLine]
    
    # Game metadata
    weather: Optional[Dict[str, Any]] = None
    attendance: Optional[int] = None
    duration_minutes: Optional[int] = None


class PlayerSeasonLineDTO(PlayerStatLine):
    """Player season stat line with additional season context"""
    season: int
    team_id: int
    team_name: str


class TeamSeasonLineDTO(TeamStatLine):
    """Team season stat line"""
    season: int
    conference: Optional[str] = None
    division: Optional[str] = None


class LeaderEntry(BaseModel):
    """Individual leader entry"""
    player_id: int
    player_name: str
    position: str
    team_id: int
    team_name: str
    value: float
    games_played: int = 0


class LeadersDTO(BaseModel):
    """Statistical leaders response"""
    stat: str
    year: Optional[int] = None
    split: Optional[str] = None
    role: Optional[str] = None
    scope: str = "regular"
    leaders: List[LeaderEntry]
    total_qualified: int = 0


class ValidationMessage(BaseModel):
    """Validation error/warning message"""
    level: Literal["error", "warning", "info"]
    category: str
    message: str
    game_id: Optional[int] = None
    player_id: Optional[int] = None
    team_id: Optional[int] = None


class ValidationReport(BaseModel):
    """Complete validation report"""
    game_id: Optional[int] = None
    total_checks: int = 0
    errors: int = 0
    warnings: int = 0
    messages: List[ValidationMessage] = []
    is_valid: bool = True

from __future__ import annotations
from typing import Optional, Literal, List, Tuple, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime

class PBPEvent(BaseModel):
    """Comprehensive Play-by-Play Event Schema for Advanced Stats"""
    
    # Core event identification
    game_id: int
    drive_id: int
    play_id: int
    quarter: int
    clock: str
    offense_team_id: int
    defense_team_id: int
    
    # Play context
    down: int = Field(ge=1, le=4)
    distance: int = Field(ge=1, le=99)
    yardline: int = Field(ge=1, le=99)
    play_type: Literal["pass", "run", "punt", "kickoff", "fg", "xp", "kickoff_return", "punt_return"]
    yards_gained: int
    is_scoring_play: bool = False
    points_offense: int = 0
    points_defense: int = 0
    
    # Passing stats
    passer_id: Optional[int] = None
    target_id: Optional[int] = None
    completed: bool = False
    air_yards: int = 0
    yac: int = 0
    interception: bool = False
    intercepted_by_id: Optional[int] = None
    sack: bool = False
    sack_yards: int = 0
    qb_hit: bool = False
    pressure: bool = False
    thrown_away: bool = False
    
    # Rushing stats
    rusher_id: Optional[int] = None
    broken_tackle: int = 0
    
    # Receiving stats
    receiver_id: Optional[int] = None
    
    # Turnover stats
    fumble: bool = False
    fumbled_by_id: Optional[int] = None
    forced_by_id: Optional[int] = None
    recovered_by_id: Optional[int] = None
    turnover_type: Optional[Literal["interception", "fumble"]] = None
    
    # Penalty stats
    penalty: Optional[Dict[str, Any]] = Field(default=None, description="Penalty object with type, yards, player_id, etc.")
    
    # Special Teams stats
    kick_type: Optional[Literal["kickoff", "punt", "fg", "xp"]] = None
    kicker_id: Optional[int] = None
    punter_id: Optional[int] = None
    returner_id: Optional[int] = None
    blocked: bool = False
    touchback: bool = False
    downed: bool = False
    in_20: bool = False
    
    # EPA and success metrics
    ep_before: float = 0.0
    ep_after: float = 0.0
    success: bool = False
    
    # === ADVANCED STATS FIELDS ===
    
    # Offensive Line responsibility
    ol_block: Optional[Dict[str, Any]] = Field(default=None, description="OL blocking assignment and outcome")
    
    # Front-seven attribution
    pressures_by_ids: List[int] = Field(default_factory=list, description="List of defender IDs who generated pressure")
    hits_by_ids: List[int] = Field(default_factory=list, description="List of defender IDs who hit QB")
    sack_split: List[Tuple[int, float]] = Field(default_factory=list, description="List of (defender_id, share) tuples for sack attribution")
    tfl_by_ids: List[int] = Field(default_factory=list, description="List of defender IDs credited with TFL")
    missed_tackle_by_ids: List[int] = Field(default_factory=list, description="List of defender IDs who missed tackles")
    
    # Coverage / Secondary
    targeted_db_id: Optional[int] = Field(default=None, description="Defensive back who was targeted")
    pass_breakup_by_id: Optional[int] = Field(default=None, description="Defensive back who broke up the pass")
    coverage_type: Optional[Literal["man", "zone"]] = Field(default=None, description="Type of coverage")
    coverage_result: Optional[Literal["caught", "defended", "intercepted", "incomplete"]] = Field(default=None, description="Result of coverage")
    
    # Special Teams advanced
    hang_time_ms: Optional[int] = Field(default=None, description="Hang time in milliseconds")
    net_yards: Optional[int] = Field(default=None, description="Net yards for punts")
    kick_distance: Optional[int] = Field(default=None, description="Total kick distance")
    blocked_by_id: Optional[int] = Field(default=None, description="Player who blocked the kick")
    fair_catch: Optional[bool] = Field(default=None, description="Whether return was fair caught")
    
    # Situational flags
    is_third_down: bool = Field(default=False, description="Play occurred on 3rd down")
    is_fourth_down: bool = Field(default=False, description="Play occurred on 4th down")
    is_red_zone: bool = Field(default=False, description="Play occurred in red zone (≤20 yardline)")
    is_goal_to_go: bool = Field(default=False, description="Play occurred in goal-to-go situation")
    is_two_minute: bool = Field(default=False, description="Play occurred in two-minute drill")
    is_hurry_up: bool = Field(default=False, description="Play occurred in hurry-up offense")
    is_garbage_time_excluded: bool = Field(default=False, description="Play occurred in garbage time (excluded from stats)")
    
    # Snap participation
    snaps_offense: int = Field(default=0, description="Number of offensive snaps")
    snaps_defense: int = Field(default=0, description="Number of defensive snaps")
    snaps_st: int = Field(default=0, description="Number of special teams snaps")
    
    @validator('sack_split')
    def validate_sack_split(cls, v):
        """Ensure sack shares sum to approximately 1.0"""
        if v:
            total_share = sum(share for _, share in v)
            if abs(total_share - 1.0) > 0.01:  # Allow small floating point errors
                raise ValueError(f"Sack split shares must sum to 1.0, got {total_share}")
        return v
    
    @validator('net_yards')
    def compute_net_yards(cls, v, values):
        """Compute net yards if missing for punts"""
        if v is None and values.get('play_type') == 'punt':
            kick_distance = values.get('kick_distance', 0)
            return_yards = values.get('yards_gained', 0)
            return kick_distance - return_yards
        return v
    
    @validator('is_red_zone')
    def mark_red_zone(cls, v, values):
        """Mark red zone when yardline ≤ 20"""
        yardline = values.get('yardline', 0)
        return yardline <= 20
    
    @validator('is_garbage_time_excluded')
    def flag_garbage_time(cls, v, values):
        """Flag garbage time by quarter ≥ 4 and score differential > threshold"""
        quarter = values.get('quarter', 1)
        points_offense = values.get('points_offense', 0)
        points_defense = values.get('points_defense', 0)
        
        # Garbage time threshold: 4th quarter with score differential > 21 points
        if quarter >= 4:
            score_diff = abs(points_offense - points_defense)
            return score_diff > 21
        return False
    
    @validator('down')
    def validate_down(cls, v):
        """Ensure down is valid"""
        if v < 1 or v > 4:
            raise ValueError("Down must be between 1 and 4")
        return v
    
    @validator('distance')
    def validate_distance(cls, v):
        """Ensure distance is valid"""
        if v < 1 or v > 99:
            raise ValueError("Distance must be between 1 and 99")
        return v
    
    @validator('yardline')
    def validate_yardline(cls, v):
        """Ensure yardline is valid"""
        if v < 1 or v > 99:
            raise ValueError("Yardline must be between 1 and 99")
        return v
    
    class Config:
        """Pydantic configuration"""
        validate_assignment = True
        use_enum_values = True
        extra = "forbid"

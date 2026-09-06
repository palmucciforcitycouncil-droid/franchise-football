from __future__ import annotations
from typing import Optional, Literal, List, Tuple, Dict, Any
from sqlmodel import SQLModel, Field
from datetime import datetime

class PBPEvent(SQLModel, table=True):
    """Comprehensive Play-by-Play Event Schema for Advanced Stats"""
    __tablename__ = "pbp_events"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
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
    play_type: str = Field(description="pass, run, punt, kickoff, fg, xp, kickoff_return, punt_return")
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
    turnover_type: Optional[str] = Field(default=None, description="interception, fumble")
    
    # Penalty stats
    penalty: Optional[str] = Field(default=None, description="Penalty JSON string")
    
    # Special Teams stats
    kick_type: Optional[str] = Field(default=None, description="kickoff, punt, fg, xp")
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
    ol_block: Optional[str] = Field(default=None, description="OL blocking assignment JSON string")
    
    # Front-seven attribution
    pressures_by_ids: Optional[str] = Field(default=None, description="JSON string of defender IDs who generated pressure")
    hits_by_ids: Optional[str] = Field(default=None, description="JSON string of defender IDs who hit QB")
    sack_split: Optional[str] = Field(default=None, description="JSON string of (defender_id, share) tuples for sack attribution")
    tfl_by_ids: Optional[str] = Field(default=None, description="JSON string of defender IDs credited with TFL")
    missed_tackle_by_ids: Optional[str] = Field(default=None, description="JSON string of defender IDs who missed tackles")
    
    # Coverage / Secondary
    targeted_db_id: Optional[int] = Field(default=None, description="Defensive back who was targeted")
    pass_breakup_by_id: Optional[int] = Field(default=None, description="Defensive back who broke up the pass")
    coverage_type: Optional[str] = Field(default=None, description="man, zone")
    coverage_result: Optional[str] = Field(default=None, description="caught, defended, intercepted, incomplete")
    
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
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

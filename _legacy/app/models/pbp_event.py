from __future__ import annotations
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator, model_validator
from enum import Enum

class PlayType(str, Enum):
    """Play type enumeration"""
    PASS = "pass"
    RUSH = "rush"
    SACK = "sack"
    PUNT = "punt"
    FIELD_GOAL = "fg"
    EXTRA_POINT = "xp"
    KICKOFF = "kickoff"
    TOUCHDOWN = "td"
    TURNOVER = "turnover"
    SAFETY = "safety"
    PENALTY = "penalty"
    TIMEOUT = "timeout"
    FINAL = "final"

class TurnoverType(str, Enum):
    """Turnover type enumeration"""
    INTERCEPTION = "interception"
    FUMBLE = "fumble"
    DOWNS = "downs"

class KickType(str, Enum):
    """Special teams kick type enumeration"""
    KICKOFF = "kickoff"
    PUNT = "punt"
    FIELD_GOAL = "fg"
    EXTRA_POINT = "xp"

class Penalty(BaseModel):
    """Penalty information"""
    flag: bool = Field(default=False, description="Penalty was flagged")
    team_id: Optional[int] = Field(default=None, description="Team that committed penalty")
    player_id: Optional[int] = Field(default=None, description="Player who committed penalty")
    code: Optional[str] = Field(default=None, description="Penalty code (e.g., 'DPI', 'Holding')")
    yards: int = Field(default=0, description="Penalty yards")
    automatic_first_down: bool = Field(default=False, description="Automatic first down penalty")
    offsetting: bool = Field(default=False, description="Offsetting penalties")
    declined: bool = Field(default=False, description="Penalty was declined")

class PBPEvent(BaseModel):
    """Complete Play-by-Play Event Schema for Stats Tracking"""
    
    # Core identification
    game_id: int = Field(description="Game identifier")
    drive_id: Optional[int] = Field(default=None, description="Drive sequence number")
    play_id: Optional[int] = Field(default=None, description="Play sequence within drive")
    
    # Situation
    quarter: int = Field(ge=1, le=5, description="Quarter (1-4, 5=OT)")
    clock: str = Field(description="Game clock (MM:SS format)")
    offense_team_id: int = Field(description="Team on offense")
    defense_team_id: int = Field(description="Team on defense")
    down: Optional[int] = Field(default=None, ge=1, le=4, description="Down (1-4)")
    distance: Optional[int] = Field(default=None, ge=0, description="Yards to go")
    yardline: Optional[int] = Field(default=None, ge=1, le=99, description="Field position (1-99)")
    
    # Play details
    play_type: PlayType = Field(description="Type of play")
    yards_gained: int = Field(default=0, description="Net yards gained/lost")
    is_scoring_play: bool = Field(default=False, description="Play resulted in score")
    points_offense: int = Field(default=0, description="Points scored by offense")
    points_defense: int = Field(default=0, description="Points scored by defense")
    
    # Passing stats
    passer_id: Optional[int] = Field(default=None, description="Quarterback player ID")
    target_id: Optional[int] = Field(default=None, description="Intended receiver player ID")
    completed: Optional[bool] = Field(default=None, description="Pass completion")
    air_yards: Optional[int] = Field(default=None, description="Air yards (before YAC)")
    yac: Optional[int] = Field(default=None, description="Yards after catch")
    interception: bool = Field(default=False, description="Pass was intercepted")
    intercepted_by_id: Optional[int] = Field(default=None, description="Defender who intercepted")
    sack: bool = Field(default=False, description="Quarterback was sacked")
    sack_yards: Optional[int] = Field(default=None, description="Yards lost on sack")
    qb_hit: bool = Field(default=False, description="QB was hit")
    pressure: bool = Field(default=False, description="QB was under pressure")
    thrown_away: bool = Field(default=False, description="Pass was thrown away")
    
    # Rushing stats
    rusher_id: Optional[int] = Field(default=None, description="Running back player ID")
    broken_tackle: int = Field(default=0, description="Number of broken tackles")
    
    # Receiving stats
    receiver_id: Optional[int] = Field(default=None, description="Actual receiver player ID")
    
    # Turnover stats
    fumble: bool = Field(default=False, description="Fumble occurred")
    fumbled_by_id: Optional[int] = Field(default=None, description="Player who fumbled")
    forced_by_id: Optional[int] = Field(default=None, description="Defender who forced fumble")
    recovered_by_id: Optional[int] = Field(default=None, description="Player who recovered")
    turnover_type: Optional[TurnoverType] = Field(default=None, description="Type of turnover")
    
    # Penalty information
    penalty: Optional[Penalty] = Field(default=None, description="Penalty details")
    
    # Special teams
    kick_type: Optional[KickType] = Field(default=None, description="Type of kick")
    kicker_id: Optional[int] = Field(default=None, description="Kicker player ID")
    punter_id: Optional[int] = Field(default=None, description="Punter player ID")
    returner_id: Optional[int] = Field(default=None, description="Returner player ID")
    blocked: bool = Field(default=False, description="Kick was blocked")
    touchback: bool = Field(default=False, description="Kick resulted in touchback")
    downed: bool = Field(default=False, description="Punt was downed")
    in_20: bool = Field(default=False, description="Punt landed inside 20")
    
    # EPA and success metrics
    ep_before: Optional[float] = Field(default=None, description="Expected points before play")
    ep_after: Optional[float] = Field(default=None, description="Expected points after play")
    success: Optional[bool] = Field(default=None, description="Play was successful (EPA > 0)")
    
    # Additional context
    description: Optional[str] = Field(default=None, description="Human-readable description")
    
    @validator('yards_gained')
    def validate_yards_gained(cls, v, values):
        """Ensure yards_gained is consistent with play type"""
        play_type = values.get('play_type')
        if play_type == PlayType.SACK and v >= 0:
            raise ValueError("Sack yards must be negative")
        return v
    
    @model_validator(mode='after')
    def validate_play_consistency(self):
        """Validate play consistency"""
        # Passing play validation
        if self.play_type == PlayType.PASS:
            if self.passer_id is None:
                raise ValueError("Passing play must have passer_id")
            if self.completed is None:
                raise ValueError("Passing play must specify completion status")
            if self.completed and self.receiver_id is None:
                raise ValueError("Completed pass must have receiver_id")
            if self.interception and self.intercepted_by_id is None:
                raise ValueError("Interception must have intercepted_by_id")
        
        # Rushing play validation
        if self.play_type == PlayType.RUSH:
            if self.rusher_id is None:
                raise ValueError("Rushing play must have rusher_id")
        
        # Sack validation
        if self.sack:
            if not self.sack_yards or self.sack_yards >= 0:
                raise ValueError("Sack must have negative sack_yards")
        
        # Turnover validation
        if self.turnover_type:
            if self.turnover_type == TurnoverType.INTERCEPTION and not self.interception:
                raise ValueError("Interception turnover must have interception=True")
            if self.turnover_type == TurnoverType.FUMBLE and not self.fumble:
                raise ValueError("Fumble turnover must have fumble=True")
        
        return self

class PBPEventBatch(BaseModel):
    """Batch of PBP events for a game"""
    game_id: int
    events: List[PBPEvent]
    
    @validator('events')
    def validate_event_order(cls, v):
        """Ensure events are in chronological order"""
        for i in range(1, len(v)):
            prev_event = v[i-1]
            curr_event = v[i]
            
            # Check quarter progression
            if curr_event.quarter < prev_event.quarter:
                raise ValueError("Events must be in chronological order")
            
            # Check clock progression within same quarter
            if (curr_event.quarter == prev_event.quarter and 
                curr_event.clock > prev_event.clock):
                raise ValueError("Clock must progress forward within quarter")
        
        return v

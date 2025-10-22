from dataclasses import dataclass, field
from typing import List, Dict, Literal, Optional

TeamSide = Literal["home", "away"]

@dataclass
class DriveEvent:
    desc: str
    clock_left: int  # seconds in half
    home_score: int
    away_score: int

@dataclass
class GameResult:
    home_score: int
    away_score: int
    winner: TeamSide
    events: List[DriveEvent]

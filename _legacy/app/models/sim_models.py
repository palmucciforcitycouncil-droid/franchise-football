from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field

# Export DB tables + compatibility aliases expected elsewhere.
__all__ = ["Team", "Game", "GameEvent", "SimTeam", "SimGame", "SimGameEvent"]

# -----------------------------
# Core League Tables (MVP)
# -----------------------------
class Team(SQLModel, table=True):
    __tablename__ = "teams"
    id: Optional[int] = Field(default=None, primary_key=True)
    abbr: str = Field(index=True)           # e.g., NE, KC
    city: str
    name: str                               # e.g., Patriots, Chiefs
    conference: str = Field(default="AFC")  # AFC|NFC
    division: str = Field(default="East")   # East|North|South|West

    # season trackers (MVP)
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points_for: int = 0
    points_against: int = 0
    power_rank: int = 0

class Game(SQLModel, table=True):
    __tablename__ = "games"
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    week: int = Field(index=True)
    home_team_id: int = Field(index=True)
    away_team_id: int = Field(index=True)

    home_score: int = 0
    away_score: int = 0
    status: str = Field(default="scheduled")  # scheduled|final|in_progress

    # Optional serialized PBP/box for MVP; store JSON as text
    pbp_json: Optional[str] = None

# -----------------------------
# Play-by-Play Events (MVP)
# -----------------------------
class GameEvent(SQLModel, table=True):
    """
    Minimal play-by-play event record used by routers/sim services.
    Add fields here only as needed by your current services.
    """
    __tablename__ = "game_events"
    id: Optional[int] = Field(default=None, primary_key=True)

    # Foreign keys (not enforced at DB level in MVP)
    game_id: int = Field(index=True)
    drive_index: Optional[int] = None
    play_index: Optional[int] = None

    # Situation
    quarter: int = 1                       # 1-4 (5=OT optional)
    clock: Optional[str] = None            # "12:34" (optional for MVP)
    down: Optional[int] = None             # 1-4
    distance: Optional[int] = None         # yards-to-go
    yard_line: Optional[int] = None        # 0-100 relative (optional)

    # Teams / possession context
    offense_team_id: Optional[int] = None
    defense_team_id: Optional[int] = None

    # Result snapshot
    yards_gained: Optional[int] = None
    event_type: str = Field(default="generic")   # e.g., rush, pass, sack, fg, td, penalty
    description: Optional[str] = None            # human-readable summary
    score_home: int = 0
    score_away: int = 0

    # Free-form payload for detailed data (JSON as text for MVP)
    data_json: Optional[str] = None

# Compatibility aliases used by existing imports
SimTeam = Team
SimGame = Game
SimGameEvent = GameEvent

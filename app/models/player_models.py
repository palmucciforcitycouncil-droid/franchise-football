from __future__ import annotations
from typing import Optional, Literal
from sqlmodel import SQLModel, Field
from datetime import date
from enum import Enum

class Position(str, Enum):
    QB = "QB"
    RB = "RB"
    WR = "WR"
    TE = "TE"
    OL = "OL"
    DL = "DL"
    LB = "LB"
    CB = "CB"
    S = "S"
    K = "K"
    P = "P"
    RET = "RET"

class Severity(str, Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"

class Player(SQLModel, table=True):
    __tablename__ = "player_models"
    id: int | None = Field(default=None, primary_key=True)
    team_id: int = Field(index=True)
    first: str
    last: str
    pos: Position
    ovr: int                    # 20..99 overall talent
    age: int = 24
    potential: int = 50         # 20..99
    is_active: bool = True
    is_rookie: bool = False
    fa_since_season: int | None = None   # NEW: first season they entered FA (team_id==0)
    rtp_weeks: int = 0          # NEW: temporary performance penalty weeks after return

class DepthChart(SQLModel, table=True):
    __tablename__ = "depth_chart_models"
    id: int | None = Field(default=None, primary_key=True)
    team_id: int = Field(index=True)
    pos: Position
    order: int                  # 1=starter, 2=backup
    player_id: int

class PlayerInjury(SQLModel, table=True):
    __tablename__ = "player_injury"
    id: int | None = Field(default=None, primary_key=True)
    player_id: int = Field(index=True)
    team_id: int = Field(index=True)
    start_week: int
    season: int
    weeks_out: int
    desc: str
    severity: Severity
    active: bool = True
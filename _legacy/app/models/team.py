from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Integer
from sqlalchemy.types import Enum as SQLEnum  # avoid name clash with Python Enum


class Conference(str, Enum):
    AFC = "AFC"
    NFC = "NFC"


class Division(str, Enum):
    EAST = "EAST"
    NORTH = "NORTH"
    SOUTH = "SOUTH"
    WEST = "WEST"


class Team(SQLModel, table=True):
    __tablename__ = "team"

    id: Optional[int] = Field(default=None, primary_key=True)

    # basic identity
    location_name: str
    nickname: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)  # Full team name
    abbr: Optional[str] = Field(default=None)  # Team abbreviation
    logo_url: Optional[str] = Field(default=None)  # Logo URL

    # IMPORTANT: Python names match tests; DB column names stay conf/div
    conference: Conference = Field(
        sa_column=Column("conf", SQLEnum(Conference), nullable=False)
    )
    division: Division = Field(
        sa_column=Column("div", SQLEnum(Division), nullable=False)
    )

    # standings + rating (keep existing DB column names)
    wins: int = Field(default=0, sa_column=Column("w", Integer, nullable=False, server_default="0"))
    losses: int = Field(default=0, sa_column=Column("l", Integer, nullable=False, server_default="0"))
    ties: int = Field(default=0, sa_column=Column("t", Integer, nullable=False, server_default="0"))
    points_for: int = Field(default=0, sa_column=Column("pf", Integer, nullable=False, server_default="0"))
    points_against: int = Field(default=0, sa_column=Column("pa", Integer, nullable=False, server_default="0"))
    elo: int = Field(default=1500, nullable=False)

    # accepted by constructor but not persisted (used by tests/DTOs)
    power_rating: Optional[int] = Field(default=None, exclude=True)
    cap_space: Optional[int] = Field(default=None, exclude=True)

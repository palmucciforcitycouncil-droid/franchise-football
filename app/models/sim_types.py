from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GameResult:
    """
    Lightweight, engine-agnostic value type used by API/DTO tests.
    Kept in models to avoid coupling tests to engine internals.
    """
    home: str
    away: str
    home_points: int
    away_points: int


@dataclass(frozen=True)
class StandRow:
    """
    Minimal standings row used by simple power ranking and table outputs.
    """
    w: int
    l: int
    t: int
    pf: int  # points for
    pa: int  # points against

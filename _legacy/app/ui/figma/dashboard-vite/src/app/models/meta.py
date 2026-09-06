from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field

class LeagueMeta(SQLModel, table=True):
    """
    Single-row meta. If multiple rows exist, use the highest id.
    Stores league state including current season/week and RNG seeds.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    current_season: int = 2031
    current_week: int = 1
    primary_rng_seed: int = 123456
    trade_rng_seed: int = 654321
    injury_rng_seed: int = 777777


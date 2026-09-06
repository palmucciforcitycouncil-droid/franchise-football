"""
Player entity (GDD Part 1 Sec 3.1, updated).

The attribute set here matches the real roster data source (a Madden-derived
CSV: local use only, real player names/attributes kept as-is per project
decision) and, not by coincidence, matches what the GDD's play-calling AI
(Part 1 Sec 6.6) actually references by name -- Avg_OL_RunBlock_Rating,
DL_RunStop_Rating, Man/Zone Coverage, Route Running by depth, etc. Madden's
granular position scheme (LT/LG/C/RG/RT, LE/RE/DT, LOLB/MLB/ROLB, CB/FS/SS)
is kept as-is rather than collapsed to generic OL/DL/LB/DB groups, because
Sec 6.6.2's zone-based blocking-advantage formula ("Left Zone: LT & LG vs.
opponent RDE & RDT") needs exactly this side-specific granularity to work.

Two intentional naming notes:
- `durability`: Madden's "Injury" attribute (higher = tougher, less likely
  to get hurt). Kept in Madden's own direction rather than inverted to
  match the Post-MVP injury system's "injury_proneness" framing (higher =
  more likely to get hurt) -- whichever formula consumes this should
  invert it there (e.g. `proneness = 99 - durability`), not here.
- `salary` / `signing_bonus`: real data, stored now even though Contracts
  (Part 2 Sec F1.1) haven't been built yet, since re-importing later for
  two extra columns would be wasted work.
"""
from __future__ import annotations
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field


class Position(str, Enum):
    QB = "QB"
    HB = "HB"
    FB = "FB"
    WR = "WR"
    TE = "TE"
    LT = "LT"
    LG = "LG"
    C = "C"
    RG = "RG"
    RT = "RT"
    LE = "LE"
    RE = "RE"
    DT = "DT"
    LOLB = "LOLB"
    MLB = "MLB"
    ROLB = "ROLB"
    CB = "CB"
    FS = "FS"
    SS = "SS"
    K = "K"
    P = "P"


class Player(SQLModel, table=True):
    player_id: str = Field(primary_key=True)

    # Identity
    first_name: str
    last_name: str
    position: Position
    team_abbr: Optional[str] = Field(default=None, index=True)  # None = free agent
    jersey_number: int = 0
    age: int
    height_inches: int = 0
    weight_lbs: int = 0
    college: str = ""
    years_pro: int = 0

    # Meta
    overall_rating: int
    potential: int
    morale: int

    # Contract (Post-MVP -- GDD Part 2 Sec F1.1 -- stored now, unused until then)
    salary: int = 0
    signing_bonus: int = 0

    # Physical
    speed: int
    acceleration: int
    strength: int
    agility: int
    jumping: int
    stamina: int
    toughness: int
    durability: int  # Madden's "Injury" rating -- see module docstring

    # Passing
    throw_power: int
    throw_accuracy_short: int
    throw_accuracy_mid: int
    throw_accuracy_deep: int
    play_action: int
    throw_on_the_run: int
    throw_under_pressure: int
    break_sack: int

    # Receiving
    catching: int
    spectacular_catch: int
    catch_in_traffic: int
    short_route_running: int
    medium_route_running: int
    deep_route_running: int
    release: int

    # Ball carrier
    carrying: int
    trucking: int
    change_of_direction: int
    ball_carrier_vision: int
    stiff_arm: int
    spin_move: int
    juke_move: int
    break_tackle: int

    # Blocking
    run_block: int
    pass_block: int
    run_block_power: int
    run_block_finesse: int
    pass_block_power: int
    pass_block_finesse: int
    lead_block: int
    impact_blocking: int

    # Defense
    tackle: int
    hit_power: int
    block_shedding: int
    pursuit: int
    play_recognition: int
    man_coverage: int
    zone_coverage: int
    press: int
    power_moves: int
    finesse_moves: int

    # Special teams
    kick_power: int
    kick_accuracy: int
    kick_return: int

    # General
    awareness: int

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_free_agent(self) -> bool:
        return self.team_abbr is None

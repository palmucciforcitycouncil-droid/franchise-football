"""
Player entity (GDD Part 1 Sec 3.1, updated).

The attribute set here matches the real roster data source (a Madden-derived
CSV: local use only, real player names/attributes kept as-is per project
decision) and, not by coincidence, matches what the GDD's play-calling AI
(Part 1 Sec 6.6) actually references by name -- Avg_OL_RunBlock_Rating,
DL_RunStop_Rating, Man/Zone Coverage, Route Running by depth, etc. Positions
are side-agnostic (T/G/C, EDGE/DT, LB, CB/S -- unified 2026-09-14); Sec
6.6.2's zone-based blocking formula still gets a left and right side from
depth order (the 1st and 2nd starter at T/G/EDGE), see
app/services/depth_chart.py.

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
    T = "T"
    G = "G"
    C = "C"
    EDGE = "EDGE"
    DT = "DT"
    LB = "LB"
    CB = "CB"
    S = "S"
    K = "K"
    P = "P"


# 2026-09-14 position unification (Brian's ask): no left/right (or
# strong/free, inside/outside) distinction anywhere in the game. Legacy
# Madden codes still arrive from the raw roster CSV, old JSON stores and
# pre-migration databases -- every one of those entry points normalizes
# through here.
LEGACY_POSITION_MAP: dict[str, str] = {
    "LT": "T", "RT": "T",
    "LG": "G", "RG": "G",
    "LE": "EDGE", "RE": "EDGE", "DE": "EDGE",
    "LOLB": "LB", "MLB": "LB", "ROLB": "LB", "OLB": "LB", "ILB": "LB",
    "FS": "S", "SS": "S",
    "RB": "HB",
}


def normalize_position(code: str) -> Position:
    code = (code or "").strip().upper()
    return Position(LEGACY_POSITION_MAP.get(code, code))


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
    # Real guaranteed money at signing (2026-09-13 salary import). Not always
    # independently known -- for players estimated from a position/rating
    # salary model (no real contract found), this is that model's own
    # position-average guaranteed-percentage applied to the estimated salary,
    # not a distinct real figure. signing_bonus above is left at 0 for all
    # re-imported players since the source data doesn't break bonus out
    # separately from the rest of guaranteed money.
    guaranteed_money: int = 0
    # Not real Madden data (no such column exists in the CSV) -- a
    # deterministically-seeded 1-5 placeholder so the Contract tab's
    # multi-year grid and the Free Agents box's "SOON" filter have
    # something real to key off, disclosed as synthetic until R4a
    # (Contracts/Cap, GDD Sec 8.3) replaces it with a real negotiated term.
    contract_years_remaining: int = 1

    # How this player joined his current team (2026-09-14, Player Card).
    # "Draft" | "Free Agent" | "Undrafted FA" | "Trade" | "Re-signed" |
    # None (= on the roster before the game's own timeline began -- the
    # imported real roster, to be back-filled later).
    acquisition_type: Optional[str] = None
    acquisition_season: Optional[int] = None  # calendar year
    acquisition_round: Optional[int] = None   # draft only
    acquisition_pick: Optional[int] = None    # draft only, overall pick
    acquisition_team: Optional[str] = None    # trade: team he came from

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

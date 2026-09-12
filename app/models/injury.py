"""
Injury entity (GDD Part 1 Sec 3.8 "Injury (MVP, Persisted Log)" / Sec 6.10
"Player Injury System" -- R1 of ROADMAP.md's R-series).

**Generation model deviates from Sec 6.10.1's letter, not its intent --
disclosed here rather than silently.** The GDD describes a live per-play
check ("check for injury at end of a play segment... runs, completed
passes with YAC, sacks...") threaded through the drive/play simulation
itself. This engine's play resolution (`app/engine/drive_sim.py`) is a
single ~270-line function with 10+ separate outcome branches, each already
carefully tuned and covered by `tests/test_stat_realism.py`'s real-NFL
calibration (see that file's own docstring for two severe, hard-won bugs
already found there). Threading a new side effect through every branch
is a large, correctness-risky surface for comparatively little gain over
the alternative actually used here: **injuries are rolled once per game,
per player, from that player's real accumulated exposure in that game's
already-built box score** (carries, targets, pass attempts, tackles,
sacks, kicks -- see `app/engine/injuries.py`'s `EXPOSURE_RATES`).
Statistically this reaches the same real goal Sec 6.10.1 names -- risk
that scales with usage, contact volume, and position -- without becoming
the third system (after item 37's rotation.py and the M1 defensive-TD
work) to have found a real bug in `drive_sim.py`'s tuned play-resolution
branches. `app/engine/injuries.py`'s own module docstring has the full
accounting, including which Sec 6.10.1 multipliers (fatigue, tempo,
weather) are skipped because this engine has no fatigue/tempo/weather
system at all yet -- not silently dropped, disclosed.

Two more deliberate simplifications from the GDD's fuller schema:
- **11 real `injury_type` values collapsed to 8** (ACL/MCL -> KNEE,
  WRIST -> HAND, NECK -> OTHER) -- still position-correlated per Sec
  6.10.2, just without a category the box-score-derived model has no
  real signal to distinguish anyway.
- **No same-game Questionable/Out status (Sec 6.10.3).** This engine
  doesn't simulate a game snap-by-snap in a way "the player got hurt
  mid-game, did they return" is a meaningful question to ask outside the
  box score itself -- an injured player's stats for the game they got
  hurt in are NOT retroactively reduced for snaps they'd have missed
  (disclosed, not fabricated to look more precise than it is).
"""
from __future__ import annotations
from enum import Enum

from sqlmodel import SQLModel, Field


class InjuryType(str, Enum):
    ANKLE = "ANKLE"
    HAMSTRING = "HAMSTRING"
    KNEE = "KNEE"
    SHOULDER = "SHOULDER"
    CONCUSSION = "CONCUSSION"
    HAND = "HAND"
    BACK = "BACK"
    OTHER = "OTHER"


class InjurySeverity(str, Enum):
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    MAJOR = "MAJOR"


# Sec 6.10.4's own worked constants -- used exactly as written.
INITIAL_RTP_PENALTY: dict[InjurySeverity, float] = {
    InjurySeverity.MINOR: 0.05,
    InjurySeverity.MODERATE: 0.10,
    InjurySeverity.MAJOR: 0.15,
}
RTP_TAPER_PER_WEEK = 0.05


class Injury(SQLModel, table=True):
    # Deterministic, not a random UUID (GDD Sec 1.3's Determinism &
    # Seeding Policy) -- a player can only have one ACTIVE injury at a
    # time (Sec 3.8.2's own invariant), so (player, season, week hurt)
    # is already a real unique key, not an arbitrary choice.
    injury_id: str = Field(primary_key=True)
    player_id: str = Field(index=True)
    # Real, at time of injury -- kept even if the player is later
    # traded/released (no trade system yet, but this is the same
    # disclosed-future-proofing precedent as CoachSeasonStats' team_abbr).
    team_abbr: str
    season_number: int
    week_injured: int
    injury_type: InjuryType
    severity: InjurySeverity
    weeks_out: int  # remaining; 0 once physically able to play again
    rtp_penalty: float = 0.0  # Sec 6.10.4: effective_attr = base * (1 - rtp_penalty)
    placed_on_ir: bool = False  # Sec 3.8.2: weeks_out >= 4 at injury time
    is_active: bool = True  # False once weeks_out==0 AND rtp_penalty==0 (Sec 3.8.2's auto-close)
    notes: str = ""

    @property
    def is_out(self) -> bool:
        """True while the player cannot play at all. False during the
        post-return RTP taper (weeks_out==0, rtp_penalty>0) -- that
        player IS available, just weakened; see injuries.py's
        apply_rtp_penalty()."""
        return self.is_active and self.weeks_out > 0

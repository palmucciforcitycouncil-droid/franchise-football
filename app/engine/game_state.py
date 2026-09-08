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
class PlayEvent:
    """One individual play within a drive (GDD Part 1 Sec 6, simplified to
    team-level inputs -- see drive_sim.py's simulate_drive docstring).
    offense_abbr is set by the caller (game_sim.py) after simulate_drive
    returns, since a single drive's plays all belong to one team and
    drive_sim.py itself only knows TeamRatings, not which abbr they are."""
    down: int
    distance: int
    field_pos: int          # 0..100, offense's distance traveled toward the end zone
    play_type: str          # "run" | "pass" | "penalty" | "punt" | "field_goal" | "kneel"
    yards: int
    desc: str
    outcome: str             # "gain" | "first_down" | "incomplete" | "sack" | "turnover" | "penalty" | "touchdown" | "field_goal" | "punt" | "turnover_on_downs"
    offense_abbr: str = ""
    defensive_call: str = ""  # e.g. "Blitz (J. Smith)" -- empty for non-scrimmage plays (penalty/punt/FG)
    drive_number: int = 0     # 1-based, set by game_sim.py -- matches this drive's position in GameResult.events
    receiver_name: str = ""  # the actual intended target on every pass attempt (not sacks) -- set even on an
                              # interception, where `desc`/the narrated player is the DEFENDER, not this target.
                              # Needed by app/engine/box_score.py to credit a target/no-catch to the right WR.
    defender_name: str = ""  # the ONE defender credited with the primary defensive impact on this play --
                              # the sacker (sack), the interceptor (turnover on a pass), the covering defender
                              # (a completed reception, credited with the solo tackle) or the point-of-attack/
                              # pursuing defender (a run, same), a pass-breakup defender (an incomplete pass,
                              # ALSO used by drive_sim.py's DPI attribution regardless of pass_defended below),
                              # or the defender who forced a fumble (a run-play turnover). Empty on plays with
                              # no clean single-defender attribution (touchdowns -- nobody made the tackle;
                              # penalties; kicks). See app/engine/defensive_box_score.py for how this is read.
    pass_defended: bool = False  # true only when an incomplete pass's defender_name reflects a REAL pass
                                  # breakup (the defender won the coverage matchup), not just an inaccurate
                                  # throw with no real defensive play -- see _resolve_pass's PD-roll docstring.
                                  # A disclosed, GDD-underspecified distinction (no PD formula is given).
    fumble_recovered_by: str = ""  # set only on a run-play turnover (a fumble) -- the defender who recovered
                                    # it, independent of defender_name (the defender who FORCED it); the two
                                    # can be the same player or different, matching real Forced Fumble vs.
                                    # Fumble Recovery being separate GDD stat categories (Sec 6.7.2).

@dataclass
class GameResult:
    home_score: int
    away_score: int
    winner: TeamSide
    events: List[DriveEvent]
    plays: List[PlayEvent] = field(default_factory=list)

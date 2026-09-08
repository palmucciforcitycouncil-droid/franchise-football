"""
Per-player defensive box score (GDD Part 1 Sec 6.7.2's MVP Truth Set:
"Defense: Solo tackles, Sacks (whole sacks for MVP), TFL, INT, PD, FF,
FR, Defensive TD"), tallied from a GameResult's flat play list
(app/engine/game_state.py's PlayEvent) the same way box_score.py builds
the offensive one -- but keyed by whoever drive_sim.py's PlayEvent.
defender_name/fumble_recovered_by named on that play, not a fixed
starting lineup, since defensive credit can go to any of the 11 real
starters, not just one designated passer/rusher.

Deliberate, disclosed scope decision: Defensive TD is NOT modeled here
(always 0). This engine has no interception/fumble RETURN mechanic at
all -- a turnover just flips possession at a computed field position
(see drive_sim.py's simulate_drive) -- so there is no real "pick-six" or
"fumble-six" event to attribute a score to. Adding one is a genuine new
game mechanic, not a box-score bookkeeping fix, and is out of scope for
this module. Solo tackles/Sacks/TFL/PD/FF/FR are all real here, built on
drive_sim.py's real (if disclosed-heuristic) defender attribution -- see
that module's _run_tackler/_sack_defender docstrings for exactly how
each defender is chosen.

Known, observed characteristic of that heuristic (not a bug, a real
consequence of a deliberate simplification): every completed reception's
tackle always goes to the SAME defender who covered that specific
target (drive_sim.py's target.defender), with no model for a second
defender (a safety over the top, a pursuing LB) making the actual
tackle after a longer catch instead. In a real defense those YAC
tackles are often made by someone other than the primary coverage
defender; here they never are. The practical effect, seen in real
simulated seasons: a CB who's frequently targeted (winning or losing
the coverage matchup) can accumulate an unrealistically large season
tackle total relative to real NFL tackle leaderboards, which are
usually LBs/safeties -- solo tackle counts should be read as "how often
this defender was the nearest man in coverage/at the point of attack,"
not a fully realistic tackle distribution. Fixing this for real means
modeling a second, pursuing defender on longer gains, which is out of
scope for this pass.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

from app.engine.game_state import PlayEvent


@dataclass
class DefensiveLine:
    name: str
    solo_tackles: int = 0
    tackles_for_loss: int = 0
    sacks: int = 0
    interceptions: int = 0
    passes_defended: int = 0
    forced_fumbles: int = 0
    fumble_recoveries: int = 0


def build_defensive_box_score(plays: List[PlayEvent], abbr: str) -> List[DefensiveLine]:
    """`abbr` is the DEFENDING team -- credits go to its players on every
    play where the OFFENSE belongs to the opponent (p.offense_abbr !=
    abbr and set). Sorted by solo tackles descending, matching how a real
    defensive box score is conventionally ordered."""
    lines: dict[str, DefensiveLine] = {}

    def line(name: str) -> DefensiveLine:
        return lines.setdefault(name, DefensiveLine(name=name))

    for p in plays:
        if not p.offense_abbr or p.offense_abbr == abbr:
            continue  # abbr is only ever the DEFENSE here, never the offense

        if p.outcome == "sack":
            if p.defender_name:
                line(p.defender_name).sacks += 1
                line(p.defender_name).solo_tackles += 1  # a sack is also a tackle
        elif p.outcome == "turnover" and p.play_type == "pass":
            if p.defender_name:
                line(p.defender_name).interceptions += 1
        elif p.outcome == "turnover" and p.play_type == "run":
            if p.defender_name:
                line(p.defender_name).forced_fumbles += 1
            if p.fumble_recovered_by:
                line(p.fumble_recovered_by).fumble_recoveries += 1
        elif p.outcome == "incomplete":
            if p.pass_defended and p.defender_name:
                line(p.defender_name).passes_defended += 1
        elif p.outcome in ("gain", "first_down") and p.defender_name:
            dl = line(p.defender_name)
            dl.solo_tackles += 1
            if p.play_type == "run" and p.yards <= 0:
                dl.tackles_for_loss += 1

    return sorted(lines.values(), key=lambda l: -l.solo_tackles)

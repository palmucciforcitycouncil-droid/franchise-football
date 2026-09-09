"""
Per-player defensive box score (GDD Part 1 Sec 6.7.2's MVP Truth Set:
"Defense: Solo tackles, Sacks (whole sacks for MVP), TFL, INT, PD, FF,
FR, Defensive TD"), tallied from a GameResult's flat play list
(app/engine/game_state.py's PlayEvent) the same way box_score.py builds
the offensive one -- but keyed by whoever drive_sim.py's PlayEvent.
defender_name/fumble_recovered_by named on that play, not a fixed
starting lineup, since defensive credit can go to any of the 11 real
starters (or, since app/engine/rotation.py's rotation modeling, a real
backup at a rotation-eligible slot -- see that module's docstring and
HANDOFF.md item 37), not just one designated passer/rusher.

Defensive TD (GDD Sec 6.7.2, ROADMAP.md M1): a takeaway can now score
directly -- drive_sim.py's simulate_drive rolls a real, small, distance-
based probability at the moment of every INT/fumble, and flags it with a
"defensive_touchdown" PlayEvent.outcome instead of "turnover". Still no
open-field return SIMULATION (yardage, broken tackles, etc.) -- a
deliberate scope cut (see simulate_drive's _defensive_td_probability
docstring) -- just a real probability of the takeaway itself being the
score. A defensive_touchdown play still counts as its underlying
takeaway too (an INT or a fumble recovery), matching how a real pick-six
is still credited as an interception in a real box score, not instead of
one. Solo tackles/Sacks/TFL/PD/FF/FR/Defensive TD are all real here,
built on drive_sim.py's real (if disclosed-heuristic) defender
attribution -- see that module's _run_tackler/_sack_defender docstrings
for exactly how each defender is chosen.

Known, observed characteristic of that heuristic (not a bug, a real
consequence of a deliberate simplification): every completed reception's
tackle always goes to the SAME defender who covered that specific
target (drive_sim.py's target.defender), with no model for a second
defender (a safety over the top, a pursuing LB) making the actual
tackle after a longer catch instead. In a real defense those YAC
tackles are often made by someone other than the primary coverage
defender; here they never are. This USED to compound into a much bigger
problem when the covering defender was also always the same single
fixed starter all season -- comparing a full simulated season against
this project's own imported real NFL data showed the median defender's
solo-tackle total running ~9.6x real (HANDOFF.md item 37). rotation.py's
real coverage rotation (a starter CB/LB vs. their real backup, weighted
by depth-chart rank + stamina/durability) closed most of that gap (down
to roughly 2x real at the median after rotation.py, not fully closed --
see rotation.py's own module docstring), but the no-second-pursuing-
defender simplification itself is unchanged: solo tackle counts should
still be read as "how often this defender was the nearest man in
coverage/at the point of attack," not a fully realistic tackle
distribution. Fully fixing this means modeling a second, pursuing
defender on longer gains, which is out of scope for this pass.
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
    defensive_touchdowns: int = 0


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
        elif p.outcome == "defensive_touchdown" and p.play_type == "pass":
            # defender_name is the interceptor here (see PlayEvent's own
            # docstring) -- still credited with the INT itself, plus the TD.
            if p.defender_name:
                dl = line(p.defender_name)
                dl.interceptions += 1
                dl.defensive_touchdowns += 1
        elif p.outcome == "defensive_touchdown" and p.play_type == "run":
            # Same forcer-vs-recoverer split as a plain fumble turnover
            # (defender_name FORCED it, fumble_recovered_by RECOVERED it,
            # can be different players) -- the TD credit goes to whoever
            # actually returned it, i.e. the recoverer, not the forcer.
            if p.defender_name:
                line(p.defender_name).forced_fumbles += 1
            if p.fumble_recovered_by:
                dl = line(p.fumble_recovered_by)
                dl.fumble_recoveries += 1
                dl.defensive_touchdowns += 1
        elif p.outcome == "incomplete":
            if p.pass_defended and p.defender_name:
                line(p.defender_name).passes_defended += 1
        elif p.outcome in ("gain", "first_down") and p.defender_name:
            dl = line(p.defender_name)
            dl.solo_tackles += 1
            if p.play_type == "run" and p.yards <= 0:
                dl.tackles_for_loss += 1

    return sorted(lines.values(), key=lambda l: -l.solo_tackles)

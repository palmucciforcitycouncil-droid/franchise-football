"""
Per-player box score stats (Passing/Rushing/Receiving), tallied from a
GameResult's flat play list (app/engine/game_state.py's PlayEvent) plus
a team's real starting lineup (app/services/depth_chart.py).

Important simplification: this engine has exactly ONE passer and ONE
rusher active per team per game -- the single starting QB/HB from
get_offensive_starters (no backups, scrambles, or in-game substitution
are modeled yet). So the Passing and Rushing lines are always exactly
one row per team; Receiving has one row per WR/TE actually targeted.

Stat conventions, matching real NFL box scores (deliberately NOT the
same as the Team Totals row already on the result page, which lumps
sack yardage into "Pass Yards" as a simpler team-level number):
  - A sack is not a pass attempt and carries no target/receiver stat.
  - A passer's Yards only counts actual completions (no sack yardage).
  - An interception counts as a target (and an INT) for the intended
    receiver, not a reception -- this requires PlayEvent.receiver_name,
    which is always the real intended target even when the play is
    narrated around the intercepting DEFENDER (see drive_sim.py's
    _resolve_pass docstring for why those two names can differ).
  - A fumble lost on a run doesn't count toward that carry's yards,
    matching the existing team-level rush_yards convention already in
    game_sim.py (excludes outcome == "turnover").
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

from app.engine.game_state import PlayEvent
from app.services.depth_chart import get_offensive_starters


@dataclass
class PassingLine:
    name: str
    completions: int = 0
    attempts: int = 0
    yards: int = 0
    touchdowns: int = 0
    interceptions: int = 0
    sacks: int = 0


@dataclass
class RushingLine:
    name: str
    carries: int = 0
    yards: int = 0
    touchdowns: int = 0
    fumbles_lost: int = 0


@dataclass
class ReceivingLine:
    name: str
    receptions: int = 0
    targets: int = 0
    yards: int = 0
    touchdowns: int = 0


@dataclass
class TeamBoxScore:
    passing: List[PassingLine] = field(default_factory=list)   # length 0 or 1, see module docstring
    rushing: List[RushingLine] = field(default_factory=list)   # length 0 or 1
    receiving: List[ReceivingLine] = field(default_factory=list)


def build_box_score(plays: List[PlayEvent], abbr: str) -> TeamBoxScore:
    starters = get_offensive_starters(abbr)
    passing = PassingLine(name=starters.qb.full_name)
    rushing = RushingLine(name=starters.hb.full_name)
    receiving_by_name: dict[str, ReceivingLine] = {}

    def receiving_line(name: str) -> ReceivingLine:
        return receiving_by_name.setdefault(name, ReceivingLine(name=name))

    for p in plays:
        if p.offense_abbr != abbr:
            continue

        if p.play_type == "pass":
            if p.outcome == "sack":
                passing.sacks += 1
                continue
            passing.attempts += 1
            if p.receiver_name:
                receiving_line(p.receiver_name).targets += 1
            if p.outcome == "turnover":
                passing.interceptions += 1
            elif p.outcome == "incomplete":
                pass
            else:  # gain, first_down, touchdown
                passing.completions += 1
                passing.yards += p.yards
                if p.receiver_name:
                    rl = receiving_line(p.receiver_name)
                    rl.receptions += 1
                    rl.yards += p.yards
                    if p.outcome == "touchdown":
                        rl.touchdowns += 1
                if p.outcome == "touchdown":
                    passing.touchdowns += 1

        elif p.play_type == "run":
            rushing.carries += 1
            if p.outcome == "turnover":
                rushing.fumbles_lost += 1
            else:
                rushing.yards += p.yards
                if p.outcome == "touchdown":
                    rushing.touchdowns += 1

    receiving = sorted(receiving_by_name.values(), key=lambda r: -r.targets)
    return TeamBoxScore(
        passing=[passing] if (passing.attempts or passing.sacks) else [],
        rushing=[rushing] if rushing.carries else [],
        receiving=receiving,
    )

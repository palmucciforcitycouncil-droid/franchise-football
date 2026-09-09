"""
Per-player box score stats (Passing/Rushing/Receiving), tallied from a
GameResult's flat play list (app/engine/game_state.py's PlayEvent) plus
a team's real starting lineup (app/services/depth_chart.py).

Important simplification: this engine has exactly ONE passer active per
team per game -- the single starting QB from get_offensive_starters (no
backup QB or in-game injury/benching is modeled yet -- Post-MVP, see
HANDOFF's Known Gaps). So the Passing line is always exactly one row per
team. Rushing is NOT single-back: app/engine/rotation.py's real
committee-backfield modeling means the actual ball carrier (PlayEvent.
carrier_name) varies play to play, so Rushing has one row per real back
who actually got a carry, same as Receiving has one row per WR/TE/RB
actually targeted -- see rotation.py's module docstring and HANDOFF.md
item 37 for why (this used to hardcode every carry to the nominal
depth-chart starter's name regardless of who the simulation itself had
actually run the ball, silently erasing the rotation fix at this layer).

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
  - An in-play penalty (outcome == "penalty" -- drive_sim.py logs these
    with the ORIGINAL play's play_type, e.g. "pass" for Roughing the
    Passer/DPI or "run" for Offensive Holding, not a dedicated
    play_type of its own) is skipped entirely: no attempt, completion,
    carry, target, or reception, and its own yardage field (the
    penalty's enforcement yardage, not real game yardage -- e.g. -10 on
    a 15-yard roughing-the-passer spot foul) never touches a player's
    stat line, matching real NFL box scores where penalty yards are
    tracked separately from individual stats.
  - A "defensive_touchdown" (GDD Sec 6.7.2's Defensive TD, ROADMAP.md
    M1 -- a takeaway returned for a score) is handled exactly like the
    underlying turnover it is: an interception attempt (pass) or a
    fumble lost (run), never a completion/carry-with-yards. Without this
    explicit handling it would silently fall into the "everything else is
    a completion" branch below, the same class of stat-corruption bug
    this project has hit before with penalties/safeties (see HANDOFF.md
    item 29) -- a pick-six would get counted as a real reception for the
    receiver who got beaten.
  - A PASS play with outcome == "safety" is also excluded from
    attempts/completions -- drive_sim.py overwrites the outcome to
    "safety" whenever a play ends behind the offense's own goal line,
    whether the original play was a sack (the overwhelmingly common
    real case, since _resolve_pass's completions don't go meaningfully
    negative) or, in principle, a completion tackled for a loss; the
    PlayEvent alone can't tell those apart once overwritten, so this
    is a disclosed, deliberately conservative exclusion rather than a
    guess. A RUN play with outcome == "safety" is unambiguous (always
    a real carry tackled behind the goal line) and still counts as a
    real carry with its real (negative) yardage -- no special case
    needed there.

Kicking/Punting (ROADMAP.md M2 -- the underlying sim, field goal
attempts and punts, already existed in drive_sim.py; this is a stats-
attribution build on top of it, not new game logic):
  - Field goal make/attempt is tallied by distance bucket, parsed from
    the real "<N>-yard field goal is GOOD/NO GOOD" desc text the same
    way app/engine/scouting.py's field_goal_accuracy() already does --
    attempt yardage isn't stored in a structured PlayEvent field (see
    drive_sim.py's _attempt_field_goal), so this reuses that established
    parsing convention rather than inventing a second one.
  - Extra points get their own play_type ("extra_point", added this
    chunk) so they're independently attributable to the real kicker,
    rather than folded silently into the touchdown PlayEvent the way
    they were before -- see drive_sim.py's simulate_drive. One disclosed
    gap: the rare Defensive TD's own PAT (GDD Sec 6.7.2, a takeaway
    returned for a score) has no real kicker object available in that
    code path (it belongs to the defense's team, not this drive's
    offense -- see simulate_drive's own comment there), so it's left
    unattributed rather than guessed; it still counts toward the score.
  - Punting is net yards only, not gross -- this engine has no return-
    game simulation (same disclosed gap as scouting.py's own field_goal_
    accuracy/return-average notes), so there's no separate return
    yardage to net a gross kick distance against. "Inside the 20" is
    derived from the same net-yards figure (the punt's real effect on
    field position), not a second parallel calculation.
  - Both are single-row per team per game, like Passing -- this engine
    models exactly one active kicker and one active punter per team
    (app/services/depth_chart.py's `k`/`p`), no in-game rotation or
    backup, matching the QB precedent above. Still built with the same
    keyed-by-real-name dict pattern Rushing/Receiving use rather than a
    fixed single object, so it costs nothing if K/P rotation is ever
    added later.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List
import re

from app.engine.drive_sim import _fg_distance_bucket
from app.engine.game_state import PlayEvent
from app.services.depth_chart import get_offensive_starters

_FG_YARDS_RE = re.compile(r"^(\d+)-yard field goal")


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


_FG_BUCKETS = ("<30", "30-39", "40-49", "50+")


@dataclass
class KickingLine:
    name: str
    fg_by_bucket: Dict[str, List[int]] = field(
        default_factory=lambda: {b: [0, 0] for b in _FG_BUCKETS}
    )  # bucket -> [made, attempted]
    xp_made: int = 0
    xp_attempted: int = 0

    @property
    def fg_made(self) -> int:
        return sum(made for made, _ in self.fg_by_bucket.values())

    @property
    def fg_attempted(self) -> int:
        return sum(att for _, att in self.fg_by_bucket.values())


@dataclass
class PuntingLine:
    name: str
    punts: int = 0
    net_yards: int = 0
    inside_20: int = 0

    @property
    def net_avg(self) -> float:
        return self.net_yards / self.punts if self.punts else 0.0


@dataclass
class TeamBoxScore:
    passing: List[PassingLine] = field(default_factory=list)   # length 0 or 1, see module docstring
    rushing: List[RushingLine] = field(default_factory=list)   # one per real ball carrier -- see build_box_score
    receiving: List[ReceivingLine] = field(default_factory=list)
    kicking: List[KickingLine] = field(default_factory=list)   # length 0 or 1 today, see module docstring
    punting: List[PuntingLine] = field(default_factory=list)   # length 0 or 1 today, see module docstring


def build_box_score(plays: List[PlayEvent], abbr: str) -> TeamBoxScore:
    starters = get_offensive_starters(abbr)
    passing = PassingLine(name=starters.qb.full_name)
    # Keyed by the real per-play carrier (PlayEvent.carrier_name), not a
    # single hardcoded starter -- app/engine/rotation.py's committee-
    # backfield modeling means the actual ball carrier varies play to
    # play (HANDOFF.md item 37); this used to dump every carry into one
    # RushingLine always named after the nominal depth-chart starter,
    # which silently ate the whole rotation fix at the stats layer even
    # after the simulation itself started drawing from a real RB depth
    # chart.
    rushing_by_name: dict[str, RushingLine] = {}
    receiving_by_name: dict[str, ReceivingLine] = {}
    kicking_by_name: dict[str, KickingLine] = {}
    punting_by_name: dict[str, PuntingLine] = {}

    def rushing_line(name: str) -> RushingLine:
        return rushing_by_name.setdefault(name, RushingLine(name=name))

    def receiving_line(name: str) -> ReceivingLine:
        return receiving_by_name.setdefault(name, ReceivingLine(name=name))

    def kicking_line(name: str) -> KickingLine:
        return kicking_by_name.setdefault(name, KickingLine(name=name))

    def punting_line(name: str) -> PuntingLine:
        return punting_by_name.setdefault(name, PuntingLine(name=name))

    for p in plays:
        if p.offense_abbr != abbr:
            continue
        if p.outcome == "penalty":
            continue  # penalty yardage isn't a real attempt/carry -- see module docstring

        if p.play_type == "field_goal":
            m = _FG_YARDS_RE.match(p.desc)
            if not m:
                continue
            bucket = _fg_distance_bucket(int(m.group(1)))
            kl = kicking_line(starters.k.full_name)
            kl.fg_by_bucket[bucket][1] += 1
            if p.outcome == "field_goal":
                kl.fg_by_bucket[bucket][0] += 1

        elif p.play_type == "extra_point":
            kl = kicking_line(starters.k.full_name)
            kl.xp_attempted += 1
            if p.outcome == "field_goal":
                kl.xp_made += 1

        elif p.play_type == "punt":
            pl = punting_line(starters.p.full_name)
            pl.punts += 1
            pl.net_yards += p.yards
            # p.field_pos is the punting team's own field position before
            # the kick, p.yards the net yards it produced (see drive_sim.
            # py's _punt_result) -- flipping that back to the receiving
            # team's own-territory field position (0..100) is the same
            # math _punt_result itself used, just run in reverse.
            landing_pos = 100 - (p.field_pos + p.yards)
            if landing_pos <= 20:
                pl.inside_20 += 1

        elif p.play_type == "pass":
            if p.outcome == "sack":
                passing.sacks += 1
                continue
            if p.outcome == "safety":
                continue  # ambiguous sack-or-completion -- see module docstring
            passing.attempts += 1
            if p.receiver_name:
                receiving_line(p.receiver_name).targets += 1
            if p.outcome in ("turnover", "defensive_touchdown"):
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
            rl = rushing_line(p.carrier_name or "Unknown")
            rl.carries += 1
            if p.outcome in ("turnover", "defensive_touchdown"):
                rl.fumbles_lost += 1
            else:
                rl.yards += p.yards
                if p.outcome == "touchdown":
                    rl.touchdowns += 1

    receiving = sorted(receiving_by_name.values(), key=lambda r: -r.targets)
    rushing = sorted(rushing_by_name.values(), key=lambda r: -r.carries)
    kicking = sorted(kicking_by_name.values(), key=lambda k: k.name)
    punting = sorted(punting_by_name.values(), key=lambda p: p.name)
    return TeamBoxScore(
        passing=[passing] if (passing.attempts or passing.sacks) else [],
        rushing=rushing,
        receiving=receiving,
        kicking=kicking,
        punting=punting,
    )

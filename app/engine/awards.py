"""
Season Awards (GDD Part 1 Sec 7.4): League MVP, Offensive/Defensive
Player of the Year (OPOY/DPOY), Rookie of the Year (ROY).

Real, counted inputs: app/engine/season_stats.py's full per-player
season Passing/Rushing/Receiving aggregation (built from every game's
real box score), each team's real win% (Season.records), and each
player's real years_pro from the Madden-derived roster import (rookie
== years_pro == 0). Computed from however many games have been played
so far -- there's no "season complete" gate, so this doubles as an
in-season Awards Race leaderboard and a season-end result once the
season (and playoffs) finish, matching how the old GDD source
documents described an always-visible "Awards Race" widget.

Deliberate, disclosed interpretations of an underspecified GDD formula
-- Sec 7.4 doesn't give exact weights or a defensive stat model, so
these choices are this module's own, not GDD-literal:

- MVP's GDD formula is "a weighted sum of team wins, Offensive EPA,
  total yards, and touchdowns," but this engine has no per-play EPA
  model at all (drive_sim.py's own docstring notes no GDD-literal
  formula exists to build one from). "Offensive EPA" is folded into
  the yards/touchdowns terms rather than kept separate: MVP = 0.4 *
  team win% + 0.6 * the player's own normalized production score
  (below). The 0.4/0.6 split is this module's choice, not a GDD value.
- The candidate pool for MVP/OPOY/ROY is every player who appears in
  the season's passing, rushing, or receiving aggregation (i.e. every
  offensive skill player who's touched the ball). Each stat is
  normalized WITHIN its own category (a QB's yards against other QBs'
  yards, not against RBs') before the categories are compared, since
  raw yardage isn't on the same scale across positions -- production
  score = 0.5 * normalized_yards + 0.5 * normalized_touchdowns.
- DPOY ("statistical dominance at the position") can only be computed
  from real interceptions -- the ONLY individual defensive stat this
  engine attributes to a named player anywhere. A sack's play
  description names the QB who got sacked, not the defender who made
  the play (see drive_sim.py's _resolve_pass docstring); tackles are
  never attributed to anyone. Building a real multi-stat DPOY needs a
  defensive box score system this project doesn't have yet (see
  HANDOFF.md's Known Gaps). DPOY here is real but a much narrower stat
  basis than "statistical dominance" implies: whoever recorded the
  most interceptions this season, full stop.
- ROY draws from the SAME offense-only candidate pool as MVP/OPOY,
  restricted to years_pro == 0. A standout rookie defender could in
  principle be a stronger real-world ROY case than any offensive
  rookie, but interceptions alone are too thin a basis to fairly weigh
  against a full offensive stat line for this award -- a documented
  simplification, not an oversight.
"""
from __future__ import annotations
import re
from dataclasses import dataclass

from sqlmodel import select

from app.core.db import get_session
from app.models.player import Player
from app.engine.season_stats import aggregate_season_stats

_INTERCEPTION_RE = re.compile(r"^Interception \((.+)\)$")


def _normalize(value: float, pool: list[float]) -> float:
    if not pool:
        return 0.0
    lo, hi = min(pool), max(pool)
    return (value - lo) / (hi - lo) if hi > lo else 0.5


@dataclass
class AwardCandidate:
    name: str
    team_abbr: str
    position: str  # "QB" | "RB" | "WR/TE" | "DEF"
    stat_line: str  # human-readable summary, e.g. "3,240 pass yds, 28 TD, 6 INT"
    score: float


def _rookie_keys(season) -> set[tuple[str, str]]:
    """(team_abbr, full_name) for every real rookie (years_pro == 0) on
    a real roster -- free agents (team_abbr is None) can't be
    candidates since they haven't played a game this season."""
    with get_session() as s:
        rookies = s.exec(
            select(Player).where(Player.years_pro == 0, Player.team_abbr != None)  # noqa: E711
        ).all()
    return {(p.team_abbr, p.full_name) for p in rookies}


def _offensive_candidates(season, rookies_only: bool = False) -> list[AwardCandidate]:
    passing, rushing, receiving = aggregate_season_stats(season)
    rookie_keys = _rookie_keys(season) if rookies_only else None

    def _keep(key):
        return rookie_keys is None or key in rookie_keys

    candidates: list[AwardCandidate] = []

    qb_pool = [(k, l) for k, l in passing.items() if l.attempts >= 1 and _keep(k)]
    if qb_pool:
        yards_pool = [l.yards for _, l in qb_pool]
        td_pool = [l.touchdowns for _, l in qb_pool]
        for (abbr, name), line in qb_pool:
            score = 0.5 * _normalize(line.yards, yards_pool) + 0.5 * _normalize(line.touchdowns, td_pool)
            candidates.append(AwardCandidate(
                name=name, team_abbr=abbr, position="QB",
                stat_line=f"{line.yards:,} pass yds, {line.touchdowns} TD, {line.interceptions} INT",
                score=score,
            ))

    rb_pool = [(k, l) for k, l in rushing.items() if l.carries >= 1 and _keep(k)]
    if rb_pool:
        yards_pool = [l.yards for _, l in rb_pool]
        td_pool = [l.touchdowns for _, l in rb_pool]
        for (abbr, name), line in rb_pool:
            score = 0.5 * _normalize(line.yards, yards_pool) + 0.5 * _normalize(line.touchdowns, td_pool)
            candidates.append(AwardCandidate(
                name=name, team_abbr=abbr, position="RB",
                stat_line=f"{line.yards:,} rush yds, {line.touchdowns} TD",
                score=score,
            ))

    wr_pool = [(k, l) for k, l in receiving.items() if l.targets >= 1 and _keep(k)]
    if wr_pool:
        yards_pool = [l.yards for _, l in wr_pool]
        td_pool = [l.touchdowns for _, l in wr_pool]
        for (abbr, name), line in wr_pool:
            score = 0.5 * _normalize(line.yards, yards_pool) + 0.5 * _normalize(line.touchdowns, td_pool)
            candidates.append(AwardCandidate(
                name=name, team_abbr=abbr, position="WR/TE",
                stat_line=f"{line.yards:,} rec yds, {line.touchdowns} TD",
                score=score,
            ))

    return candidates


def offensive_player_of_the_year(season, top_n: int = 5) -> list[AwardCandidate]:
    return sorted(_offensive_candidates(season), key=lambda c: -c.score)[:top_n]


def rookie_of_the_year(season, top_n: int = 5) -> list[AwardCandidate]:
    return sorted(_offensive_candidates(season, rookies_only=True), key=lambda c: -c.score)[:top_n]


def most_valuable_player(season, top_n: int = 5) -> list[AwardCandidate]:
    """MVP = the same normalized offensive-production score OPOY uses,
    blended with the player's own team's win% (Sec 7.4's "team wins"
    term)."""
    blended = []
    for c in _offensive_candidates(season):
        win_pct = season.records[c.team_abbr].win_pct
        mvp_score = 0.4 * win_pct + 0.6 * c.score
        blended.append(AwardCandidate(name=c.name, team_abbr=c.team_abbr, position=c.position,
                                       stat_line=c.stat_line, score=mvp_score))
    return sorted(blended, key=lambda c: -c.score)[:top_n]


def _interception_counts(season) -> dict[tuple[str, str], int]:
    """(team_abbr, defender_name) -> interception count, parsed from the
    real "Interception (Name)" desc text -- see this module's docstring
    for why this is the only individual defensive stat available."""
    counts: dict[tuple[str, str], int] = {}
    for week in season.schedule:
        for g in week:
            if g.result is None:
                continue
            for p in g.result.plays:
                if p.outcome != "turnover" or p.play_type != "pass":
                    continue
                m = _INTERCEPTION_RE.match(p.desc)
                if not m:
                    continue
                defender_name = m.group(1)
                defense_abbr = g.away_abbr if p.offense_abbr == g.home_abbr else g.home_abbr
                key = (defense_abbr, defender_name)
                counts[key] = counts.get(key, 0) + 1
    return counts


def defensive_player_of_the_year(season, top_n: int = 5) -> list[AwardCandidate]:
    counts = _interception_counts(season)
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])[:top_n]
    return [
        AwardCandidate(name=name, team_abbr=abbr, position="DEF", stat_line=f"{ints} INT", score=float(ints))
        for (abbr, name), ints in ranked
    ]


@dataclass
class AwardsRace:
    mvp: list[AwardCandidate]
    opoy: list[AwardCandidate]
    dpoy: list[AwardCandidate]
    roy: list[AwardCandidate]


def season_awards(season, top_n: int = 5) -> AwardsRace:
    return AwardsRace(
        mvp=most_valuable_player(season, top_n),
        opoy=offensive_player_of_the_year(season, top_n),
        dpoy=defensive_player_of_the_year(season, top_n),
        roy=rookie_of_the_year(season, top_n),
    )

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
- DPOY ("statistical dominance at the position") is now a real,
  multi-stat composite built on app/engine/defensive_box_score.py's real
  per-player defensive attribution (solo tackles, sacks, TFL, INT, PD,
  FF, Defensive TD -- see that module's own docstring, and drive_sim.py's
  _run_tackler/_sack_defender/_defensive_td_probability docstrings for
  exactly how each defender/score is chosen).
  No GDD formula/weights are given for this either, so this module's own
  choice: DPOY score = 0.27 * normalized(sacks) + 0.27 *
  normalized(interceptions) + 0.13 * normalized(tackles_for_loss) +
  0.09 * normalized(solo_tackles) + 0.09 * normalized(forced_fumbles) +
  0.05 * normalized(passes_defended) + 0.10 *
  normalized(defensive_touchdowns), each normalized within the whole
  defensive candidate pool (there's no positional split like offense's
  QB/RB/WR-TE -- DL/LB/DB are all compared on the same defensive stat
  line, matching how DPOY is a single, position-agnostic real NFL award
  too). Weighted toward sacks/INTs since those are what actually
  decides most real-world AP DPOY votes, with a real but bounded slice
  (0.10) carved out for Defensive TD -- a rare, high-impact play real
  DPOY voters do notice, but nowhere near as decisive as a full season of
  sacks/INTs; fumble_recoveries is tracked and shown but excluded from
  the score itself (more a product of luck/opportunity than of
  individual defensive dominance).
- ROY now draws from BOTH the offensive AND defensive candidate pools
  (previously offense-only, since DPOY's interception-only basis was
  judged too thin to fairly weigh a rookie defender against a rookie
  QB/RB/WR -- resolved now that a real defensive box score exists).
  Each side is normalized within its OWN rookie sub-pool first (same
  technique MVP/OPOY already use to compare QB/RB/WR on one scale)
  before the two [0,1]-ish scores are merged into one ranking -- a
  standout rookie defender can now genuinely win ROY over a rookie
  offensive skill player, not just place behind one by construction.
"""
from __future__ import annotations
from dataclasses import dataclass

from sqlmodel import select

from app.core.db import get_session
from app.models.player import Player
from app.engine.season_stats import aggregate_season_stats, aggregate_season_defensive_stats


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
    return offensive_candidates_from_stats(passing, rushing, receiving, rookie_keys)


def offensive_candidates_from_stats(passing: dict, rushing: dict, receiving: dict, rookie_keys: set | None = None) -> list[AwardCandidate]:
    """Pure version of _offensive_candidates, decoupled from a live
    Season object -- takes the same-shaped dicts aggregate_season_stats()
    produces (keyed by (team_abbr, name) -> Season*Line) directly. Split
    out so real historical NFL data (scripts/import_nfl_history.py) can
    score real players by this exact same formula, not a re-implemented
    copy that could silently drift from the live one."""

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
    """Offensive AND defensive rookies, each normalized within their OWN
    rookie sub-pool first (same cross-position technique MVP/OPOY use)
    before being merged into one ranking -- see this module's docstring
    for why this changed from offense-only."""
    candidates = _offensive_candidates(season, rookies_only=True) + _defensive_candidates(season, rookies_only=True)
    return sorted(candidates, key=lambda c: -c.score)[:top_n]


def most_valuable_player(season, top_n: int = 5) -> list[AwardCandidate]:
    """MVP = the same normalized offensive-production score OPOY uses,
    blended with the player's own team's win% (Sec 7.4's "team wins"
    term)."""
    win_pct_by_abbr = {abbr: r.win_pct for abbr, r in season.records.items()}
    return mvp_from_candidates(_offensive_candidates(season), win_pct_by_abbr)[:top_n]


def mvp_from_candidates(offensive_candidates: list[AwardCandidate], win_pct_by_abbr: dict) -> list[AwardCandidate]:
    """Pure version of the MVP blend -- takes OPOY-shaped candidates and
    a plain {team_abbr: win_pct} dict rather than a live Season.records.
    Split out for the same reason offensive_candidates_from_stats() was:
    real historical seasons need the identical formula, not a copy."""
    blended = [
        AwardCandidate(name=c.name, team_abbr=c.team_abbr, position=c.position, stat_line=c.stat_line,
                        score=0.4 * win_pct_by_abbr.get(c.team_abbr, 0.0) + 0.6 * c.score)
        for c in offensive_candidates
    ]
    return sorted(blended, key=lambda c: -c.score)


def _defensive_candidates(season, rookies_only: bool = False) -> list[AwardCandidate]:
    """See this module's docstring for the disclosed DPOY weighting.
    Candidate pool: every defender credited with at least one stat this
    season (app/engine/season_stats.py's aggregate_season_defensive_stats,
    built on the real per-play defender attribution in drive_sim.py/
    defensive_box_score.py) -- no positional split, matching how DPOY is
    a single, position-agnostic real NFL award."""
    defense = aggregate_season_defensive_stats(season)
    rookie_keys = _rookie_keys(season) if rookies_only else None
    return defensive_candidates_from_stats(defense, rookie_keys)


def defensive_candidates_from_stats(defense: dict, rookie_keys: set | None = None) -> list[AwardCandidate]:
    """Pure version of _defensive_candidates -- see offensive_candidates_
    from_stats' docstring for why this split exists."""

    def _keep(key):
        return rookie_keys is None or key in rookie_keys

    pool = [(k, l) for k, l in defense.items() if _keep(k)]
    if not pool:
        return []

    sacks_pool = [l.sacks for _, l in pool]
    ints_pool = [l.interceptions for _, l in pool]
    tfl_pool = [l.tackles_for_loss for _, l in pool]
    tkl_pool = [l.solo_tackles for _, l in pool]
    ff_pool = [l.forced_fumbles for _, l in pool]
    pd_pool = [l.passes_defended for _, l in pool]
    td_pool = [l.defensive_touchdowns for _, l in pool]

    candidates: list[AwardCandidate] = []
    for (abbr, name), line in pool:
        score = (
            0.27 * _normalize(line.sacks, sacks_pool)
            + 0.27 * _normalize(line.interceptions, ints_pool)
            + 0.13 * _normalize(line.tackles_for_loss, tfl_pool)
            + 0.09 * _normalize(line.solo_tackles, tkl_pool)
            + 0.09 * _normalize(line.forced_fumbles, ff_pool)
            + 0.05 * _normalize(line.passes_defended, pd_pool)
            + 0.10 * _normalize(line.defensive_touchdowns, td_pool)
        )
        stat_line = f"{line.solo_tackles} tkl, {line.sacks} sacks, {line.tackles_for_loss} TFL, {line.interceptions} INT, {line.passes_defended} PD"
        if line.defensive_touchdowns:
            stat_line += f", {line.defensive_touchdowns} DEF TD"
        candidates.append(AwardCandidate(
            name=name, team_abbr=abbr, position="DEF",
            stat_line=stat_line,
            score=score,
        ))
    return candidates


def defensive_player_of_the_year(season, top_n: int = 5) -> list[AwardCandidate]:
    return sorted(_defensive_candidates(season), key=lambda c: -c.score)[:top_n]


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

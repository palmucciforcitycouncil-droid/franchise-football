"""
Season-long per-player Passing/Rushing/Receiving aggregation, built on
top of app/engine/box_score.py's per-game lines.

Moved here (out of app/main.py, where this logic originally lived as
_season_stat_leaders) so app/engine/awards.py (GDD Part 1 Sec 7.4) can
share the exact same full, non-truncated aggregation the Stats/
Dashboard pages already use for their top-N leaderboards -- an engine
module has no business importing from the route layer, so the shared
logic belongs here instead.
"""
from __future__ import annotations
from dataclasses import dataclass

from app.engine.box_score import build_box_score
from app.engine.defensive_box_score import build_defensive_box_score


@dataclass
class SeasonPassingLine:
    name: str
    team_abbr: str
    completions: int = 0
    attempts: int = 0
    yards: int = 0
    touchdowns: int = 0
    interceptions: int = 0
    sacks_taken: int = 0  # M13: box_score.py's PassingLine.sacks was already real per-game, just never rolled up into a season total before


@dataclass
class SeasonRushingLine:
    name: str
    team_abbr: str
    carries: int = 0
    yards: int = 0
    touchdowns: int = 0
    fumbles_lost: int = 0  # M13: box_score.py's RushingLine.fumbles_lost, same story as sacks_taken above


@dataclass
class SeasonReceivingLine:
    name: str
    team_abbr: str
    receptions: int = 0
    targets: int = 0
    yards: int = 0
    touchdowns: int = 0


@dataclass
class SeasonDefensiveLine:
    name: str
    team_abbr: str
    solo_tackles: int = 0
    tackles_for_loss: int = 0
    sacks: int = 0
    interceptions: int = 0
    passes_defended: int = 0
    forced_fumbles: int = 0
    fumble_recoveries: int = 0
    defensive_touchdowns: int = 0


def aggregate_season_stats(season):
    """Returns (passing, rushing, receiving), each a dict keyed by
    (team_abbr, name) -> Season*Line, covering every player who's
    touched the ball in any game played so far this season. No
    truncation -- callers (leaderboard display, awards) sort/slice
    however they need."""
    passing: dict[tuple[str, str], SeasonPassingLine] = {}
    rushing: dict[tuple[str, str], SeasonRushingLine] = {}
    receiving: dict[tuple[str, str], SeasonReceivingLine] = {}

    for week in season.schedule:
        for g in week:
            if g.result is None:
                continue
            for abbr in (g.home_abbr, g.away_abbr):
                box = build_box_score(g.result.plays, abbr)
                for p in box.passing:
                    line = passing.setdefault((abbr, p.name), SeasonPassingLine(name=p.name, team_abbr=abbr))
                    line.completions += p.completions
                    line.attempts += p.attempts
                    line.yards += p.yards
                    line.touchdowns += p.touchdowns
                    line.interceptions += p.interceptions
                    line.sacks_taken += p.sacks
                for r in box.rushing:
                    line = rushing.setdefault((abbr, r.name), SeasonRushingLine(name=r.name, team_abbr=abbr))
                    line.carries += r.carries
                    line.yards += r.yards
                    line.touchdowns += r.touchdowns
                    line.fumbles_lost += r.fumbles_lost
                for rc in box.receiving:
                    line = receiving.setdefault((abbr, rc.name), SeasonReceivingLine(name=rc.name, team_abbr=abbr))
                    line.receptions += rc.receptions
                    line.targets += rc.targets
                    line.yards += rc.yards
                    line.touchdowns += rc.touchdowns

    return passing, rushing, receiving


_current_season_cache: dict[tuple[int, int, int], tuple] = {}


def cached_current_season_aggregates(season):
    """Real perf fix found live while verifying ROADMAP.md Sec2d-B item 11:
    app/main.py's _season_by_season_stats_for() (the Player Card's Stats
    tab) used to call aggregate_season_stats()/aggregate_season_defensive_stats()
    fresh on every single call (~0.3s combined against Brian's real
    14-week franchise) -- fine for the handful of player-card renders a
    normal page needs, but the Dashboard's new Top Performers box renders
    up to 100 player-card links in one request (10 categories x 10 rows),
    each re-aggregating the WHOLE season's box scores from scratch.
    Measured a 46s+ real Dashboard load before this fix; profiling traced
    it here, not to anything item 11 itself directly added.

    Same lru_cache-plus-explicit-clear precedent as history_store.
    career_stats() (M6's fix for the identical class of problem on the
    archived-history side) and depth_chart.py's get_offensive_starters/
    get_defensive_starters, except plain-dict-based rather than
    @lru_cache: the season object itself isn't hashable, so only the
    (league_seed, season_number, current_week) triple is used as the
    key, and a bare dict (bounded to exactly 1 entry, since only one
    season is ever "current" in a running process) avoids needing a
    hashable season argument at all. See clear_current_season_cache()
    below -- called from season_state.py's simulate_current_week(),
    reset_season(), and start_new_season() (alongside the existing
    clear_career_stats_cache() call), so a stale entry can never survive
    past the next state-mutating call, in tests or production alike."""
    key = (season.league_seed, season.season_number, season.current_week)
    if key not in _current_season_cache:
        passing, rushing, receiving = aggregate_season_stats(season)
        defense = aggregate_season_defensive_stats(season)
        _current_season_cache.clear()
        _current_season_cache[key] = (passing, rushing, receiving, defense)
    return _current_season_cache[key]


def clear_current_season_cache() -> None:
    _current_season_cache.clear()


def aggregate_season_defensive_stats(season):
    """Returns a dict keyed by (team_abbr, name) -> SeasonDefensiveLine,
    covering every defender credited with at least one stat in any game
    played so far this season. A separate function (not folded into
    aggregate_season_stats' 3-tuple) so every existing offensive-stats
    call site keeps working unchanged -- see app/engine/
    defensive_box_score.py for what's real here, including Defensive TD
    (GDD Sec 6.7.2, ROADMAP.md M1)."""
    defense: dict[tuple[str, str], SeasonDefensiveLine] = {}

    for week in season.schedule:
        for g in week:
            if g.result is None:
                continue
            for abbr in (g.home_abbr, g.away_abbr):
                for d in build_defensive_box_score(g.result.plays, abbr):
                    line = defense.setdefault((abbr, d.name), SeasonDefensiveLine(name=d.name, team_abbr=abbr))
                    line.solo_tackles += d.solo_tackles
                    line.tackles_for_loss += d.tackles_for_loss
                    line.sacks += d.sacks
                    line.interceptions += d.interceptions
                    line.passes_defended += d.passes_defended
                    line.forced_fumbles += d.forced_fumbles
                    line.fumble_recoveries += d.fumble_recoveries
                    line.defensive_touchdowns += d.defensive_touchdowns

    return defense

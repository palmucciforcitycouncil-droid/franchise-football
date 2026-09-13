"""
PerformanceExpectation snapshot (R3d spec Sec 3.3).

Frozen at the start of Week 1 -- literally, the moment a new Season
object exists and before any game has been simulated -- because Sec
3.3 says expectations are "derived from preseason Power Ranking...
frozen at start of Week 1" and are "the baseline for coaching
evaluation" for the whole season. Computed from
app/engine/roster_strength.py's real `team_rating` (A1/A2/A3's tuned
aggregator) at the moment season_state.reset_season()/start_new_season()
finishes building the new season -- by then, this offseason's coach
hiring/firing/promotion (app/engine/coach_hiring.py's AI autonomy pass)
has already run, so a new HC's real `Coach.overall` is what
roster_strength blends in, not the fired coach's.

Persisted (DEFAULT_PATH-resolved-at-call-time JSON, same convention as
power_rank_history.py), keyed by season_number so a mid-season read can
never accidentally compare against a stale prior season's snapshot.
Old seasons are kept rather than pruned (cheap, small), mirroring
history_store.py's own "never delete" convention.

Win-total mapping: Sec 3.3 wants "expected wins" out of a preseason
rating. There is no GDD formula for converting `team_rating` (a 0-99ish
composite; A3's tuning pass found only a moderate r~=0.43-0.53
correlation with actual win_pct -- a real, disclosed, imperfect signal,
not a strong predictor) into a specific win total, so this module makes
its own documented choice: rank all 32 teams by team_rating and map
percentile LINEARLY onto a 4-13 expected-win band (the real spread NFL
preseason win totals actually cluster within over a 17-game season),
rather than inventing an unearned regression. Offense/defense
expectation percentiles reuse the exact same real per-group ratings
roster_strength.py already computes (A1) -- no new aggregation
invented, just a different weighted subset (offensive groups vs
defensive groups) of the same QUOTA_GROUPS scores.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json

from app.data.teams import TEAMS
from app.engine import roster_strength

DEFAULT_PATH = Path("data/saves/team_expectations.json")

OFFENSE_GROUPS = ["QB", "RB", "WR", "TE", "C", "G", "T"]
DEFENSE_GROUPS = ["DE", "DT", "LB", "CB", "S"]

EXPECTED_WINS_FLOOR = 4.0
EXPECTED_WINS_CEIL = 13.0
GAMES_PER_SEASON = 17


@dataclass
class TeamExpectation:
    team_abbr: str
    season_number: int
    team_rating_pctile: float      # 0-100, this team's rank among all 32
    expected_win_pct: float        # 0-1
    expected_wins: float           # 0-17ish, for display
    offense_pctile: float          # 0-100
    defense_pctile: float          # 0-100


_cache: dict[int, dict[str, TeamExpectation]] | None = None


def _load() -> dict[int, dict[str, TeamExpectation]]:
    global _cache
    if _cache is not None:
        return _cache
    if DEFAULT_PATH.exists():
        raw = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        _cache = {
            int(season_key): {abbr: TeamExpectation(**v) for abbr, v in teams.items()}
            for season_key, teams in raw.items()
        }
    else:
        _cache = {}
    return _cache


def _save() -> None:
    if _cache is None:
        return
    DEFAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    raw = {
        str(season_number): {abbr: asdict(exp) for abbr, exp in teams.items()}
        for season_number, teams in _cache.items()
    }
    DEFAULT_PATH.write_text(json.dumps(raw, indent=2), encoding="utf-8")


def clear_cache() -> None:
    global _cache
    _cache = None


def _percentile_rank(value: float, all_values: list[float]) -> float:
    """Fraction of the field at or below `value`, as 0-100 -- the same
    "fraction at or below" convention import_coaches.py's
    reputation_from_salary() already uses for a percentile."""
    if not all_values:
        return 50.0
    at_or_below = sum(1 for v in all_values if v <= value)
    return 100.0 * at_or_below / len(all_values)


def _sub_score(group_ratings: dict[str, float], groups: list[str]) -> float:
    weights = roster_strength.POSITION_WEIGHTS
    present = {g: group_ratings[g] for g in groups if g in group_ratings}
    total_weight = sum(weights[g] for g in present)
    if total_weight <= 0:
        return 50.0
    return sum(weights[g] * r for g, r in present.items()) / total_weight


def compute_snapshot(season_number: int) -> dict[str, TeamExpectation]:
    """Computes (but does not persist) one season's PerformanceExpectation
    for all 32 teams from the CURRENT roster/coach state -- call this
    exactly once, right after the new season's rosters/coaches are
    settled and before any game of it has been simulated."""
    abbrs = [t.abbr for t in TEAMS]
    strengths = roster_strength.compute_all(abbrs)

    ratings = {a: strengths[a].team_rating for a in abbrs if a in strengths}
    all_ratings = list(ratings.values())
    offense_scores = {a: _sub_score(strengths[a].group_ratings, OFFENSE_GROUPS) for a in abbrs if a in strengths}
    defense_scores = {a: _sub_score(strengths[a].group_ratings, DEFENSE_GROUPS) for a in abbrs if a in strengths}
    all_offense = list(offense_scores.values())
    all_defense = list(defense_scores.values())

    out: dict[str, TeamExpectation] = {}
    for a in abbrs:
        rating = ratings.get(a, 50.0)
        pctile = _percentile_rank(rating, all_ratings)
        win_pct = (EXPECTED_WINS_FLOOR + (pctile / 100.0) * (EXPECTED_WINS_CEIL - EXPECTED_WINS_FLOOR)) / GAMES_PER_SEASON
        out[a] = TeamExpectation(
            team_abbr=a,
            season_number=season_number,
            team_rating_pctile=pctile,
            expected_win_pct=win_pct,
            expected_wins=win_pct * GAMES_PER_SEASON,
            offense_pctile=_percentile_rank(offense_scores.get(a, 50.0), all_offense),
            defense_pctile=_percentile_rank(defense_scores.get(a, 50.0), all_defense),
        )
    return out


def compute_and_store(season_number: int) -> dict[str, TeamExpectation]:
    snapshot = compute_snapshot(season_number)
    store = _load()
    store[season_number] = snapshot
    _save()
    return snapshot


def for_team(season_number: int, team_abbr: str) -> TeamExpectation | None:
    return _load().get(season_number, {}).get(team_abbr)


def for_season(season_number: int) -> dict[str, TeamExpectation]:
    return dict(_load().get(season_number, {}))

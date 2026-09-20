"""
Seasonal per-team, per-position-group Focus Area accumulator
(docs/R16_COACH_POSITION_IMPACT_SPECIFICATION.md Sec 7).

**Why per-position-group, not one team-wide number** (weighed directly
in R16 planning): the whole point of R16's granular Focus Area menus is
that a team investing in, say, OL gets an OL-specific payoff, not a
blurred team-wide one -- and the SAME accumulated data feeds three
different consumers at once (player development multipliers in
season_state.apply_progression_to_roster(), a coordinator's own rating
progression in coach_progression.py, and the Staff page's Trait Effects
panel), so one granular store is cheaper than three separate trackers
that could drift out of sync. The real cost is one more JSON store and
a little more weekly bookkeeping -- judged worth it for the consistency.

Incremented once per simulated week (season_state.simulate_current_
week(), alongside its existing per-week coaching hooks) by that week's
active focus assignments across a team's whole staff -- reuses app/
engine/coaching.py's own tier+rating-weighted boost math
(`_team_group_boosts()`) so "how much a coach's focus counts" is defined
in exactly one place, not two that could drift apart.

Persisted as JSON (data/saves/, gitignored), same DEFAULT_PATH-resolved-
at-call-time convention as every other *_store.py (power_rank_history.py,
draft_pick_store.py, etc.) -- isolable in tests the same way. Keyed by
season_number first, same as power_rank_history.py, so a value never
silently crosses a season boundary; a new season's own key simply starts
empty, no explicit reset needed.
"""
from __future__ import annotations
import json
from pathlib import Path

DEFAULT_PATH = Path("data/saves/coach_focus_accumulator.json")


def _load(path: Path | None) -> dict:
    p = path if path is not None else DEFAULT_PATH
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save(data: dict, path: Path | None) -> None:
    p = path if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def record_week(season_number: int, team_abbr: str, staff, path: Path | None = None) -> None:
    """One team's real weekly contribution -- reuses app/engine/
    coaching.py's own boost weighting (tier + rating, relative to league
    average) so a coach's focus counts identically here and in the
    this-game boost. A team with no coaches or nobody focused anywhere
    real contributes nothing this week (a real no-op, not an error)."""
    from app.engine import coaching

    if not staff:
        return
    boosts = coaching._team_group_boosts(staff, coaching.league_baseline_by_tier())
    if not boosts:
        return

    data = _load(path)
    season_key = str(season_number)
    team_totals = data.setdefault(season_key, {}).setdefault(team_abbr, {})
    for group, amount in boosts.items():
        team_totals[group] = team_totals.get(group, 0.0) + amount
    _save(data, path)


def totals_for(season_number: int, team_abbr: str, path: Path | None = None) -> dict[str, float]:
    """This season's accumulated points per position group for one team
    so far -- {} for a team/season with no recorded weeks yet."""
    data = _load(path)
    return dict(data.get(str(season_number), {}).get(team_abbr, {}))


# R16 Sec 7: accumulated points -> a bounded player-development
# multiplier per position group, the granular replacement for the old
# blanket dev_multiplier_offense/defense split. [tune]: REFERENCE is
# this project's own placeholder for "a full season of one dedicated
# coach's narrow-focus attention" (roughly BOOST_SCALE * a full-season
# week count for a single focused coach) -- a real, disclosed starting
# point for the post-build playtesting pass, not a measured constant.
DEV_MULTIPLIER_MIN = 0.85
DEV_MULTIPLIER_MAX = 1.15
ACCUMULATOR_FULL_SEASON_REFERENCE = 60.0


def dev_multiplier_for_group(season_number: int, team_abbr: str, group: str, path: Path | None = None) -> float:
    """This team's real development multiplier for `group` (an app/
    engine/draft.py GROUP_POSITIONS key) this season so far -- 1.0 for a
    group nobody's focused on (no accumulated points), scaling up to
    DEV_MULTIPLIER_MAX/down to DEV_MULTIPLIER_MIN as real accumulated
    focus grows, same bounded-multiplier shape coaching.py's other
    rating->multiplier conversions already use."""
    total = totals_for(season_number, team_abbr, path).get(group, 0.0)
    ratio = max(-1.0, min(1.0, total / ACCUMULATOR_FULL_SEASON_REFERENCE))
    span = (DEV_MULTIPLIER_MAX - DEV_MULTIPLIER_MIN) / 2.0
    return 1.0 + ratio * span

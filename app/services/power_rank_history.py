"""
Persisted weekly Power Ranking snapshots (ROADMAP.md Sec2d-B item 10).

LeaguePowerRankings.tsx's own CHG column needs a real week-over-week
rank delta, which this engine had no way to compute -- M10's own
HANDOFF note disclosed the exact gap ("no historical power-rating
snapshot exists to diff against for a delta arrow"). This module is
the real, minimal store that closes it: simulate_current_week() calls
record_snapshot() once per simulated week with every team's rank (by
power_rating descending, the same order the Dashboard's own Power
Rankings box already sorts by), and the Dashboard route reads the
immediately-prior week's snapshot to compute each team's delta.

Persisted as JSON (data/saves/, gitignored, same convention as
depth_chart_overrides.py / save_service.py -- DEFAULT_PATH resolved at
call time, not baked in at import, so tests can redirect it). Keyed by
season_number first so a delta never silently crosses a season
boundary (a new season's Week 1 has no meaningful "prior week" to diff
against, even if last season's Week 18 snapshot is still on disk).

Not otherwise guarded against a reset_season() that bootstraps to the
SAME season_number as a previous attempt (rare -- only possible before
anything's been archived to history_store yet) -- any stale snapshot
from that prior attempt just gets overwritten week-by-week as the new
attempt's own simulate_current_week() calls land, the same
"real, disclosed simplification" class as this project's other
persisted stores rather than something worth a bigger guard.

READ THIS BEFORE WRITING A STANDALONE SCRIPT: ROADMAP.md Sec2b
documents two real data-persistence incidents from insufficiently-
isolated code touching season_state.py's save/DB paths. This module
follows the exact same DEFAULT_PATH-redirect convention as
save_service.py/history_store.py/depth_chart_overrides.py specifically
so it can be isolated the same way -- see tests/conftest.py's
session-scoped fixture, which redirects this module's DEFAULT_PATH
alongside save_service's for the whole pytest run.
"""
from __future__ import annotations
import json
from pathlib import Path

DEFAULT_PATH = Path("data/saves/power_rank_history.json")


def _load(path: Path | None) -> dict:
    p = path if path is not None else DEFAULT_PATH
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save(data: dict, path: Path | None) -> None:
    p = path if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def record_snapshot(season_number: int, week_num: int, ranks: dict[str, int], path: Path | None = None) -> None:
    """ranks: {team_abbr: rank}, 1 = highest power rating, for every
    team that has one (normally all 32)."""
    data = _load(path)
    data.setdefault(str(season_number), {})[str(week_num)] = ranks
    _save(data, path)


def get_ranks(season_number: int, week_num: int, path: Path | None = None) -> dict[str, int] | None:
    """None if that week was never recorded (before this store existed,
    week 0/negative, or a week later than any simulated so far) -- the
    caller's job to treat that as "no delta available," not a fabricated 0."""
    return _load(path).get(str(season_number), {}).get(str(week_num))

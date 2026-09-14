"""
Persisted weekly Headlines snapshots (GDD Sec 12, ROADMAP.md Sec4e/R9b).

season_state.simulate_current_week() calls record_week_headlines() once
per simulated week with that week's already-rendered headline strings
(app.engine.headlines.weekly_headlines()); the Dashboard reads the most
recent entry's snapshot rather than recomputing it on every request.
Recomputing would actually be perfectly reproducible too (this whole
feature is deterministic, GDD Sec 1.3), but storing it is still real
work worth doing once instead of on every Dashboard load, plus it's
what makes a "Headlines Archive" (browsing past weeks) possible without
re-deriving history.

Entry keys within a season (2026-09-14, Brian: headlines should continue
through preseason and every playoff round, not just Weeks 1-18):
- "P1".."P4" -- preseason rounds
- "1".."18"  -- regular-season weeks
- "WC", "DIV", "CONF", "SB" -- playoff rounds
entry_sort_key() orders them chronologically. append_headlines() adds
lines to an existing entry without clobbering it (e.g. a Super Bowl MVP
line added by a later hook after the SB round's results were recorded).

A per-season "_meta" blob (top-level "_meta" key, so it can never collide
with a season_number) remembers which phrasing variants the previous
entry used, so the next week's headlines don't repeat them.

Persisted as JSON (data/saves/, gitignored), same DEFAULT_PATH-resolved-
at-call-time convention as power_rank_history.py/award_race_history.py
-- so it isolates in tests the identical way. READ ROADMAP.md Sec2's
incident history before adding a standalone script that touches this
without redirecting DEFAULT_PATH first.
"""
from __future__ import annotations
import json
from pathlib import Path

DEFAULT_PATH = Path("data/saves/headlines_history.json")
_META_KEY = "_meta"
_PLAYOFF_KEYS = ("WC", "DIV", "CONF", "SB")


def _load(path: Path | None) -> dict:
    p = path if path is not None else DEFAULT_PATH
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save(data: dict, path: Path | None) -> None:
    p = path if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def entry_sort_key(key: str) -> tuple[int, int]:
    key = str(key)
    if key.startswith("P") and key[1:].isdigit():
        return (0, int(key[1:]))
    if key.isdigit():
        return (1, int(key))
    if key in _PLAYOFF_KEYS:
        return (2, _PLAYOFF_KEYS.index(key))
    return (3, 0)


def record_week_headlines(season_number: int, week_num, headlines: list[str], path: Path | None = None) -> None:
    """`week_num` is any entry key -- an int week, "P2", "WC", ..."""
    data = _load(path)
    data.setdefault(str(season_number), {})[str(week_num)] = headlines
    _save(data, path)


def append_headlines(season_number: int, entry_key, headlines: list[str], path: Path | None = None) -> None:
    data = _load(path)
    entry = data.setdefault(str(season_number), {}).setdefault(str(entry_key), [])
    entry.extend(h for h in headlines if h not in entry)
    _save(data, path)


def get_week_headlines(season_number: int, week_num, path: Path | None = None) -> list[str] | None:
    """None if that entry was never recorded (before this store existed,
    or later than anything simulated so far) -- the caller's job to show
    "no headlines yet," not fabricate one."""
    return _load(path).get(str(season_number), {}).get(str(week_num))


def get_all_weeks(season_number: int, path: Path | None = None) -> dict[str, list[str]]:
    """Every recorded entry's headlines for one season, chronological
    (preseason, weeks, playoff rounds) -- backs a Headlines Archive view."""
    weeks = _load(path).get(str(season_number), {})
    return {k: weeks[k] for k in sorted(weeks, key=entry_sort_key)}


def get_meta(season_number: int, path: Path | None = None) -> dict:
    return _load(path).get(_META_KEY, {}).get(str(season_number), {})


def set_meta(season_number: int, meta: dict, path: Path | None = None) -> None:
    data = _load(path)
    data.setdefault(_META_KEY, {})[str(season_number)] = meta
    _save(data, path)

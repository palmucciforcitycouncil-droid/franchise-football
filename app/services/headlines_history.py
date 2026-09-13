"""
Persisted weekly Headlines snapshots (GDD Sec 12, ROADMAP.md Sec4e/R9b).

season_state.simulate_current_week() calls record_week_headlines() once
per simulated week with that week's already-rendered headline strings
(app.engine.headlines.weekly_headlines()); the Dashboard reads the most
recent week's snapshot rather than recomputing it on every request.
Recomputing would actually be perfectly reproducible too (this whole
feature is deterministic, GDD Sec 1.3), but storing it is still real
work worth doing once instead of on every Dashboard load, plus it's
what makes a "Headlines Archive" (browsing past weeks) possible without
re-deriving history.

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


def _load(path: Path | None) -> dict:
    p = path if path is not None else DEFAULT_PATH
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save(data: dict, path: Path | None) -> None:
    p = path if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def record_week_headlines(season_number: int, week_num: int, headlines: list[str], path: Path | None = None) -> None:
    data = _load(path)
    data.setdefault(str(season_number), {})[str(week_num)] = headlines
    _save(data, path)


def get_week_headlines(season_number: int, week_num: int, path: Path | None = None) -> list[str] | None:
    """None if that week was never recorded (before this store existed,
    or a week later than any simulated so far) -- the caller's job to
    show "no headlines yet," not fabricate one."""
    return _load(path).get(str(season_number), {}).get(str(week_num))


def get_all_weeks(season_number: int, path: Path | None = None) -> dict[str, list[str]]:
    """Every recorded week's headlines for one season, oldest week first
    by key order -- backs the Headlines Archive view."""
    weeks = _load(path).get(str(season_number), {})
    return {k: weeks[k] for k in sorted(weeks, key=int)}

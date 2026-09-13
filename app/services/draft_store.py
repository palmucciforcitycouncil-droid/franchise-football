"""
Persisted Draft results (R5, docs/R5_DRAFT_SYSTEM_SPECIFICATION.md, ROADMAP.md
Sec4f) -- who got picked, in what round, for which team, keyed by season.
The drafted/undrafted prospects themselves become real Player rows (see
app/engine/draft.py's module docstring for why there's no separate
Prospect table); this store is just the historical PICK RECORD, the one
piece of real information that isn't already sitting on a Player row.

Persisted as JSON (data/saves/, gitignored), same DEFAULT_PATH-resolved-
at-call-time convention as every other *_history.py store in this
project -- isolates in tests the same way. READ ROADMAP.md Sec2's
incident history before adding a standalone script that touches this
without redirecting DEFAULT_PATH first.
"""
from __future__ import annotations
import json
from pathlib import Path

DEFAULT_PATH = Path("data/saves/draft_history.json")


def _load(path: Path | None) -> dict:
    p = path if path is not None else DEFAULT_PATH
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save(data: dict, path: Path | None) -> None:
    p = path if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def record_draft(season_number: int, order: list[str], picks: list[dict], undrafted_count: int, path: Path | None = None) -> None:
    data = _load(path)
    data[str(season_number)] = {"order": order, "picks": picks, "undrafted_count": undrafted_count}
    _save(data, path)


def get_draft(season_number: int, path: Path | None = None) -> dict | None:
    """None if that season's draft was never recorded (before this store
    existed, or a season that hasn't had its draft run yet)."""
    return _load(path).get(str(season_number))


def get_team_picks(season_number: int, team_abbr: str, path: Path | None = None) -> list[dict]:
    draft = get_draft(season_number, path)
    if draft is None:
        return []
    return [p for p in draft["picks"] if p["team_abbr"] == team_abbr]

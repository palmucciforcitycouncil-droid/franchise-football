"""
User-settable Weekly Gameplan (GDD Part 1 Sec 10.4.1).

Persisted as JSON (data/saves/, gitignored, same pattern as
depth_chart_overrides.py) keyed by team_abbr. Only the user's own team
ever has a real gameplan set through the UI (app/main.py's /gameplan
route only accepts season.user_team_abbr), but this store doesn't
enforce that itself -- it's a plain team_abbr -> Gameplan map, and it's
season_state.py's job to only look up the user's team when building a
game's play-calling inputs (see simulate_current_week's gameplan
lookups). Unknown fields in a saved record are ignored and missing
fields fall back to Gameplan's own dataclass defaults, so an older save
missing a field added later just means "default for that field," not a
crash.
"""
from __future__ import annotations
import json
from dataclasses import asdict, fields
from pathlib import Path

from app.engine.gameplan import Gameplan

DEFAULT_PATH = Path("data/saves/gameplans.json")


def _load(path: Path | None) -> dict:
    p = path if path is not None else DEFAULT_PATH
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save(data: dict, path: Path | None) -> None:
    p = path if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_gameplan(team_abbr: str, path: Path | None = None) -> Gameplan:
    raw = _load(path).get(team_abbr, {})
    known_fields = {f.name for f in fields(Gameplan)}
    return Gameplan(**{k: v for k, v in raw.items() if k in known_fields})


def set_gameplan(team_abbr: str, gameplan: Gameplan, path: Path | None = None) -> None:
    data = _load(path)
    data[team_abbr] = asdict(gameplan)
    _save(data, path)

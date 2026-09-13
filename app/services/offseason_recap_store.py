"""
The offseason's before/after roster snapshot (Brian's ask, 2026-09-13:
a Football-GM-style "Offseason Recap" screen -- Top/Improving/Declining
Players, Top Rookies, Top/Improving/Declining Teams, Top Players on New
Teams -- shown once the whole offseason finishes). Most of that recap
is free (already-persisted history_store/team_expectations/draft_store
data, see app/main.py's own recap route) but "which players got
better/worse" and "who changed teams" genuinely need a real before/
after diff -- nothing else in this engine logs `overall_rating` or
`team_abbr` history.

Keyed by season number (the season whose offseason is being recapped,
i.e. season_state.begin_offseason()'s own season.season_number), same
convention as draft_store.py/draft_class_store.py. Persisted (not a
local variable) because real time and a real HTTP request boundary --
the Staff/GM-Desk/Draft pauses -- separate the "before" snapshot
(begin_offseason(), before anyone's rating/team changes) from the
"after" one (complete_draft_and_advance_season(), once everything has
landed).
"""
from __future__ import annotations
import json
from pathlib import Path

DEFAULT_PATH = Path("data/saves/offseason_recap.json")


def _load(path: Path | None) -> dict:
    p = path if path is not None else DEFAULT_PATH
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save(data: dict, path: Path | None) -> None:
    p = path if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def save_before_snapshot(season_number: int, snapshot: dict[str, tuple[str | None, int]], path: Path | None = None) -> None:
    """snapshot: player_id -> (team_abbr, overall_rating), taken right
    before apply_progression_to_roster() (or anything else this
    offseason) touches a single Player row."""
    data = _load(path)
    data[str(season_number)] = {"before": {pid: list(v) for pid, v in snapshot.items()}, "recap": None}
    _save(data, path)


def get_before_snapshot(season_number: int, path: Path | None = None) -> dict[str, tuple[str | None, int]] | None:
    entry = _load(path).get(str(season_number))
    if entry is None or entry.get("before") is None:
        return None
    return {pid: tuple(v) for pid, v in entry["before"].items()}


def save_recap(season_number: int, recap: dict, path: Path | None = None) -> None:
    """The final, computed recap (see app/main.py's offseason_recap_view
    for its shape) -- saved once complete_draft_and_advance_season()
    finishes the diff, so the /offseason/recap page never has to
    recompute it (a player's rating/team by then belongs to the NEW,
    just-built season, not the one this recap is about)."""
    data = _load(path)
    key = str(season_number)
    entry = data.setdefault(key, {"before": None, "recap": None})
    entry["recap"] = recap
    _save(data, path)


def get_recap(season_number: int, path: Path | None = None) -> dict | None:
    return _load(path).get(str(season_number), {}).get("recap")


def clear_season(season_number: int, path: Path | None = None) -> None:
    data = _load(path)
    data.pop(str(season_number), None)
    _save(data, path)

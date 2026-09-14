"""
Season honors: the FINAL, frozen results of a season (Brian's ask,
2026-09-14) plus every player's and coach's permanent award history.

Why a store and not a recomputation: app/engine/awards.py only ever
computes the CURRENT state from the season's games so far, and the
inputs it reads (rookie status, live rosters, the coach pool) keep
changing after the season ends -- progression ages everyone, the draft
adds rookies, players retire. "Who won MVP in 2027" has to be written
down once, at the moment it's decided, or it can drift. Same reasoning
for the Pro Bowl rosters, the Super Bowl result/MVP, and the list of
players who retired that offseason.

Shape (one JSON file per save):
    {
      "seasons": {"<season_number>": {
          "awards": {"mvp": [...], "opoy": [...], "dpoy": [...],
                     "oroy": [...], "droy": [...], "roy": [...], "coty": [...]},
          "pro_bowl": {"AFC": {"offense": [...], "defense": [...],
                               "special": [...], "reserves": [...]}, "NFC": {...}},
          "super_bowl": {...},          # see season_honors.record_playoff_round()
          "retired_players": [...],
      }},
      "players": {"<player_id>": [{"season_number": n, "year": y, "award": "MVP"}, ...]},
      "coaches": {"<coach_id>":  [{"season_number": n, "year": y, "award": "Coach of the Year"}, ...]},
    }

Persisted as JSON (data/saves/, gitignored) via DEFAULT_PATH resolved at
call time, redirected per save by save_manager._redirect_globals() and
per test run by tests/conftest.py -- same convention as every other
store in this package.
"""
from __future__ import annotations
import json
from pathlib import Path

from app.config import season_year

DEFAULT_PATH = Path("data/saves/honors.json")

# The Player Card renders one card per player name on a page (dozens to
# hundreds per request), each asking for that player's awards -- so the
# parsed file is cached, keyed by (path, mtime, size) so any write (from
# this process or a save switch that repoints DEFAULT_PATH) is picked up
# on the very next read without an explicit clear call anywhere.
_cache: dict = {"key": None, "data": None}


def _empty() -> dict:
    return {"seasons": {}, "players": {}, "coaches": {}}


def _load(path: Path | None) -> dict:
    p = path if path is not None else DEFAULT_PATH
    try:
        st = p.stat()
    except FileNotFoundError:
        return _empty()
    key = (str(p), st.st_mtime_ns, st.st_size)
    if _cache["key"] != key:
        data = json.loads(p.read_text(encoding="utf-8"))
        for section in ("seasons", "players", "coaches"):
            data.setdefault(section, {})
        _cache["key"], _cache["data"] = key, data
    return _cache["data"]


def _load_for_write(path: Path | None) -> dict:
    """Writers get a fresh parse, never the shared read cache -- they
    mutate what they load, and a failed write mustn't leave the cache
    holding half-applied changes."""
    p = path if path is not None else DEFAULT_PATH
    if not p.exists():
        return _empty()
    data = json.loads(p.read_text(encoding="utf-8"))
    for section in ("seasons", "players", "coaches"):
        data.setdefault(section, {})
    return data


def _save(data: dict, path: Path | None) -> None:
    p = path if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    _cache["key"] = None


# --- per-season results ----------------------------------------------------

def _set_season_field(season_number: int, field: str, value, path: Path | None) -> None:
    data = _load_for_write(path)
    data["seasons"].setdefault(str(season_number), {})[field] = value
    _save(data, path)


def _get_season_field(season_number: int, field: str, path: Path | None):
    return _load(path)["seasons"].get(str(season_number), {}).get(field)


def save_final_awards(season_number: int, awards: dict, path: Path | None = None) -> None:
    _set_season_field(season_number, "awards", awards, path)


def get_final_awards(season_number: int, path: Path | None = None) -> dict | None:
    """None until the season's last regular-season week is simulated --
    callers show the live Awards Race instead, never an empty "final"."""
    return _get_season_field(season_number, "awards", path)


def save_pro_bowl(season_number: int, rosters: dict, path: Path | None = None) -> None:
    _set_season_field(season_number, "pro_bowl", rosters, path)


def get_pro_bowl(season_number: int, path: Path | None = None) -> dict | None:
    return _get_season_field(season_number, "pro_bowl", path)


def save_super_bowl(season_number: int, summary: dict, path: Path | None = None) -> None:
    _set_season_field(season_number, "super_bowl", summary, path)


def get_super_bowl(season_number: int, path: Path | None = None) -> dict | None:
    return _get_season_field(season_number, "super_bowl", path)


def save_retired_players(season_number: int, retirees: list[dict], path: Path | None = None) -> None:
    _set_season_field(season_number, "retired_players", retirees, path)


def get_retired_players(season_number: int, path: Path | None = None) -> list[dict] | None:
    return _get_season_field(season_number, "retired_players", path)


def has_any_season_data(season_number: int, path: Path | None = None) -> bool:
    return bool(_load(path)["seasons"].get(str(season_number)))


# --- per-person award history ----------------------------------------------

def _add_awards(section: str, entries: list[tuple[str, int, str]], path: Path | None) -> list[tuple[str, int, str]]:
    """entries: (person_id, season_number, award). Idempotent -- the same
    (season, award) is never recorded twice for one person, so a
    replayed finalization (a re-saved round, a double-click) can't hand
    out a second ring. Returns only the entries that were actually new."""
    if not entries:
        return []
    data = _load_for_write(path)
    added: list[tuple[str, int, str]] = []
    for person_id, season_number, award in entries:
        if not person_id:
            continue
        rows = data[section].setdefault(person_id, [])
        if any(r["season_number"] == season_number and r["award"] == award for r in rows):
            continue
        rows.append({"season_number": season_number, "year": season_year(season_number), "award": award})
        added.append((person_id, season_number, award))
    if added:
        _save(data, path)
    return added


def add_player_awards(entries: list[tuple[str, int, str]], path: Path | None = None) -> list[tuple[str, int, str]]:
    return _add_awards("players", entries, path)


def add_coach_awards(entries: list[tuple[str, int, str]], path: Path | None = None) -> list[tuple[str, int, str]]:
    return _add_awards("coaches", entries, path)


def player_awards(player_id: str, path: Path | None = None) -> list[dict]:
    return list(_load(path)["players"].get(player_id, []))


def coach_awards(coach_id: str, path: Path | None = None) -> list[dict]:
    return list(_load(path)["coaches"].get(coach_id, []))


# Display order for grouped honors -- most prestigious first, the way a
# real player/coach bio lists them.
AWARD_ORDER = [
    "MVP", "Super Bowl MVP", "Super Bowl Champion", "AFC Champion", "NFC Champion",
    "Offensive Player of the Year", "Defensive Player of the Year",
    "Offensive Rookie of the Year", "Defensive Rookie of the Year",
    "Coach of the Year", "Pro Bowl",
]


def group_awards(rows: list[dict]) -> list[dict]:
    """[{award, count, years (newest first)}], in AWARD_ORDER then
    alphabetical for anything unlisted."""
    grouped: dict[str, list[int]] = {}
    for r in rows:
        grouped.setdefault(r["award"], []).append(r["year"])
    order = {a: i for i, a in enumerate(AWARD_ORDER)}
    return [
        {"award": award, "count": len(years), "years": sorted(set(years), reverse=True)}
        for award, years in sorted(grouped.items(), key=lambda kv: (order.get(kv[0], len(order)), kv[0]))
    ]

"""
Per-save contract negotiation state (Brian's 2026-09-14 fixes doc:
"a contract negotiation mood logic ... the player/coach move closer
toward compromise if negotiations are going well ... a player can get
fed up and refuse to sign").

One JSON dict, keyed by negotiation WINDOW then by "<team_abbr>|<person_id>"
-- the pure mood math lives in app/engine/negotiation.py; this module only
persists its NegotiationState dicts. A window is "<season_number>:<stage>"
(stage = the season's offseason_stage, or "season" during the regular
season/playoffs), so a player who refused the user in-season can be
approached fresh once the offseason's re-sign/free-agency window opens,
and every refusal clears on its own a year later.

Only the CURRENT window is kept: writing into a new window drops every
older one, so the file never grows across a long franchise.
"""
from __future__ import annotations
import json
from pathlib import Path

DEFAULT_PATH = Path("data/saves/negotiations.json")


def window_for(season) -> str:
    return f"{season.season_number}:{season.offseason_stage or 'season'}"


def _key(team_abbr: str, person_id: str) -> str:
    return f"{team_abbr}|{person_id}"


def _load(path: Path | None) -> dict:
    p = path if path is not None else DEFAULT_PATH
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def _save(data: dict, path: Path | None) -> None:
    p = path if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get(window: str, team_abbr: str, person_id: str, path: Path | None = None) -> dict | None:
    return _load(path).get(window, {}).get(_key(team_abbr, person_id))


def put(window: str, team_abbr: str, person_id: str, state: dict, path: Path | None = None) -> None:
    data = _load(path)
    current = data.get(window, {})
    current[_key(team_abbr, person_id)] = state
    _save({window: current}, path)


def clear(window: str, team_abbr: str, person_id: str, path: Path | None = None) -> None:
    data = _load(path)
    current = data.get(window, {})
    if current.pop(_key(team_abbr, person_id), None) is not None:
        _save({window: current}, path)


def negotiate(season, team_abbr: str, person_id: str, raw_score: float, offered_aav: float,
              offered_years: int, offered_guaranteed: float, model, persist: bool):
    """The one entry point every offer route uses: loads this person's
    state for the current window, resolves the offer through
    app/engine/negotiation.py, and (persist=True, a real submit) writes the
    new state back -- or clears it once a deal is done. persist=False is
    the read-only preview: same math, no Considering roll, no write."""
    from app.engine import negotiation

    window = window_for(season)
    state = negotiation.NegotiationState.from_dict(get(window, team_abbr, person_id))
    outcome, new_state = negotiation.resolve_offer(
        state, raw_score, offered_aav, offered_years, offered_guaranteed, model,
        seed_parts=(season.league_seed, window, team_abbr, person_id), roll=persist,
    )
    if persist:
        if outcome.verdict == negotiation.ACCEPT:
            clear(window, team_abbr, person_id)
        else:
            put(window, team_abbr, person_id, new_state.to_dict())
    return outcome


def current_state(season, team_abbr: str, person_id: str):
    from app.engine import negotiation
    return negotiation.NegotiationState.from_dict(get(window_for(season), team_abbr, person_id))

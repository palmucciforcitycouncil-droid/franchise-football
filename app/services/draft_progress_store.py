"""
Live, resumable pick-by-pick draft state (Brian's ask, 2026-09-13: the
draft should be a real, user-paced event -- Sim Pick / Sim to Your Next
Pick / End -- not one atomic function call). Keyed by season number,
same convention as draft_store.py/draft_class_store.py.

Holds only what a resumable draft needs beyond the prospect class
itself (app/services/draft_class_store.py) and the fixed draft order
(app.engine.draft.compute_draft_order, recomputed on demand -- it's a
pure function of the season's real standings, cheap, and never changes
mid-draft): the next slot to resolve, and every pick already made. Each
pick is applied to the real Player table THE MOMENT it resolves (see
app.engine.draft.apply_single_pick_to_db) -- this store never holds a
player's real roster state, only the pick record, so a server restart
mid-draft loses nothing: the DB already reflects every pick made so far,
and `picks` here is just what the Draft Results panel replays on screen.
"""
from __future__ import annotations
import json
from pathlib import Path

DEFAULT_PATH = Path("data/saves/draft_progress.json")


def _load(path: Path | None) -> dict:
    p = path if path is not None else DEFAULT_PATH
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save(data: dict, path: Path | None) -> None:
    p = path if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def start(season_number: int, order: list[str], path: Path | None = None) -> dict:
    """Idempotent: calling this again for a season already in progress
    just returns the existing state unchanged, same post-start no-op
    convention as this codebase's simulate_* functions -- so the Draft
    page can call this unconditionally the first time it's opened for a
    season that hasn't started drafting yet."""
    data = _load(path)
    key = str(season_number)
    if key not in data:
        data[key] = {
            "order": order, "current_pick_index": 0, "picks": [],
            "drafted_indexes": [], "complete": False,
        }
        _save(data, path)
    return data[key]


def get(season_number: int, path: Path | None = None) -> dict | None:
    return _load(path).get(str(season_number))


def record_pick(season_number: int, pick: dict, prospect_index: int, path: Path | None = None) -> dict:
    """Appends one resolved pick and advances current_pick_index by one.
    `pick` is the same shape draft_store.py's own `picks` entries use
    (round, overall_pick, team_abbr, player_id, name, position, college,
    overall_rating) so the finished record can be handed off to
    draft_store.record_draft() unchanged once the draft completes.
    `prospect_index` is tracked separately (not part of draft_store's own
    shape) so the engine always knows exactly which prospects are still
    in the pool without re-deriving it from player_id string parsing."""
    data = _load(path)
    key = str(season_number)
    state = data[key]
    state["picks"].append(pick)
    state["drafted_indexes"].append(prospect_index)
    state["current_pick_index"] += 1
    _save(data, path)
    return state


def mark_complete(season_number: int, path: Path | None = None) -> None:
    data = _load(path)
    key = str(season_number)
    if key in data:
        data[key]["complete"] = True
        _save(data, path)


def clear(season_number: int, path: Path | None = None) -> None:
    """Called once a draft's picks have been folded into draft_store.py's
    permanent record -- the live/in-progress state is no longer needed."""
    data = _load(path)
    data.pop(str(season_number), None)
    _save(data, path)

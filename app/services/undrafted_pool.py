"""
Undrafted-rookie 3-year expiration window (R5, docs/R5_DRAFT_SYSTEM_
SPECIFICATION.md Sec9.2, ROADMAP.md Sec4f).

An undrafted prospect becomes a real Player row (team_abbr=None, a
genuine free agent -- see app/engine/draft.py's module docstring for
why there's no separate "UndraftedRookie" entity), so it's already
fully visible/signable through the existing Roster/Free-Agency
machinery. The ONE thing that machinery doesn't track is the real-NFL-
style "this rookie ages out of the pool after 3 years if nobody signs
them" rule -- that's this module's whole job: a flat {player_id:
years_remaining} map, decremented once per offseason.

**Disclosed simplification from the spec's fuller design**: Sec 9.2's
own cleanup rule is a two-tier PERCENTILE prune (delete the bottom 25%
of the 1-year-remaining cohort, bottom 10% of the 2-3-year cohort, on
top of a 100% hard-delete at 0). This module implements Tier 1 only --
hard delete at years_remaining == 0, keep everyone else -- a real,
simpler rule in the same spirit (expired rookies leave, nobody else is
force-cut) rather than a full percentile-ranking pass across the whole
pool every single offseason.

Persisted as JSON (data/saves/, gitignored), same DEFAULT_PATH-resolved-
at-call-time convention as every other store in this project.
"""
from __future__ import annotations
import json
from pathlib import Path

DEFAULT_PATH = Path("data/saves/undrafted_pool.json")

YEARS_ON_ENTRY = 3


def _load(path: Path | None) -> dict:
    p = path if path is not None else DEFAULT_PATH
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save(data: dict, path: Path | None) -> None:
    p = path if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def add_undrafted(player_ids: list[str], path: Path | None = None) -> None:
    data = _load(path)
    for pid in player_ids:
        data[pid] = YEARS_ON_ENTRY
    _save(data, path)


def remove(player_id: str, path: Path | None = None) -> None:
    """Called once a real Player row is signed by a team (team_abbr is no
    longer None) -- that player is a normal roster player now, not part
    of this expiring pool anymore."""
    data = _load(path)
    data.pop(player_id, None)
    _save(data, path)


def years_remaining(player_id: str, path: Path | None = None) -> int | None:
    return _load(path).get(player_id)


def decrement_and_expire(path: Path | None = None) -> list[str]:
    """Called once per offseason (season_state.start_new_season()).
    Decrements every tracked player's clock by 1; anyone hitting 0 is
    removed from this store AND their real Player row is deleted from
    the roster DB (Tier-1-only, see module docstring). Returns the
    player_ids actually deleted, for the caller to log."""
    from app.core.db import get_session
    from app.models.player import Player

    data = _load(path)
    expired = [pid for pid, yrs in data.items() if yrs - 1 <= 0]
    for pid in data:
        if pid not in expired:
            data[pid] -= 1
    for pid in expired:
        del data[pid]
    _save(data, path)

    if expired:
        with get_session() as s:
            for pid in expired:
                player = s.get(Player, pid)
                # Only delete if still genuinely unsigned -- a signed
                # UDFA was already removed from this store by remove()
                # above, but defends against any call-order gap.
                if player is not None and player.team_abbr is None:
                    s.delete(player)
            s.commit()
    return expired

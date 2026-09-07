"""
User-settable depth chart overrides.

depth_chart.py's get_offensive_starters/get_defensive_starters were a
pure highest-overall_rating stand-in with no way for the user to
actually set who starts (see that module's docstring). This is the
real thing: an explicit, user-editable player_id order per
(team_abbr, position), persisted as JSON (data/saves/, gitignored,
same pattern as save_service.py's season state) and consulted by
depth_chart.py's _top() ahead of the rating-sort fallback.

Only QB/HB/WR/TE/OL/DL/LB/CB/S positions are actually consumed by the
engine (via OffensiveStarters/DefensiveStarters) -- an override for
FB/K/P is stored the same way but has no engine consumer yet, since
there's no FB usage or K/P starter slot wired up (see HANDOFF's
"No dedicated kicker" gap). Storing it anyway costs nothing and means
the depth chart UI doesn't need special-case logic per position.
"""
from __future__ import annotations
import json
from pathlib import Path

DEFAULT_PATH = Path("data/saves/depth_chart_overrides.json")


def _load(path: Path | None) -> dict:
    # Resolved at call time (not as a default-arg value) so tests can
    # redirect DEFAULT_PATH at the module level without it being baked
    # in at import -- same convention as save_service.py.
    p = path if path is not None else DEFAULT_PATH
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save(data: dict, path: Path | None) -> None:
    p = path if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_order(team_abbr: str, position_value: str, path: Path | None = None) -> list[str] | None:
    return _load(path).get(team_abbr, {}).get(position_value)


def set_order(team_abbr: str, position_value: str, player_ids: list[str], path: Path | None = None) -> None:
    data = _load(path)
    data.setdefault(team_abbr, {})[position_value] = player_ids
    _save(data, path)


def resolve_order(team_abbr: str, position_value: str, players: list, path: Path | None = None) -> list:
    """players: Player objects all sharing this team and position.
    Returns them in saved-override order, with anyone not in the saved
    order (e.g. a player added to the roster after the override was set)
    appended by rating -- or by overall_rating descending if no override
    exists yet."""
    order = get_order(team_abbr, position_value, path)
    if not order:
        return sorted(players, key=lambda p: -p.overall_rating)
    by_id = {p.player_id: p for p in players}
    ordered = [by_id[pid] for pid in order if pid in by_id]
    remaining = sorted((p for p in players if p.player_id not in order), key=lambda p: -p.overall_rating)
    return ordered + remaining


def move_player(team_abbr: str, position_value: str, current_order_ids: list[str], player_id: str, direction: str, path: Path | None = None) -> None:
    """direction: 'up' or 'down'. current_order_ids must be the FULL
    current order for this position (from resolve_order, mapped to ids)
    so a move persists everyone's position, not just the two swapped."""
    ids = list(current_order_ids)
    i = ids.index(player_id)
    j = i - 1 if direction == "up" else i + 1
    if 0 <= j < len(ids):
        ids[i], ids[j] = ids[j], ids[i]
    set_order(team_abbr, position_value, ids, path)

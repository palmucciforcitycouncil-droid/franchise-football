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
import functools
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


def _compare_for_autofill(a, b, respect_fatigue: bool) -> int:
    """M15 correction: the real comparator AutoFillModal.tsx/
    mockDepthChartApi.ts's autoFillDepthChart() specifies -- OVR desc,
    with a fatigue-aware tiebreak (prefer higher STA when two players
    are within 2 OVR of each other), then AWR, then STA outright, then
    a durability tiebreak (this engine's real analog of the source's
    `injury_proneness`: HIGHER durability = LOWER proneness, so this
    sorts descending to match the source's ascending-proneness
    preference -- see Player's own module docstring for the `99 -
    durability` relationship), then last name."""
    if respect_fatigue and abs(a.overall_rating - b.overall_rating) <= 2 and a.stamina != b.stamina:
        return b.stamina - a.stamina
    if a.overall_rating != b.overall_rating:
        return b.overall_rating - a.overall_rating
    if a.awareness != b.awareness:
        return b.awareness - a.awareness
    if a.stamina != b.stamina:
        return b.stamina - a.stamina
    if a.durability != b.durability:
        return b.durability - a.durability
    return -1 if a.last_name < b.last_name else (1 if a.last_name > b.last_name else 0)


def auto_fill(
    team_abbr: str,
    players_by_position: dict,
    starter_counts: dict,
    respect_fatigue: bool = True,
    lock_starters: bool = False,
    path: Path | None = None,
) -> None:
    """Real Auto-Fill (AutoFillModal.tsx/mockDepthChartApi.ts's
    autoFillDepthChart(): OVR-based sort with a fatigue-aware tiebreak).
    Two of the source's four toggles aren't offered here, disclosed
    rather than faked: 'Respect Injuries' needs an in-season health-
    status field this engine's Player model doesn't have (only the
    Madden `durability` rating -- a toughness attribute, not a current
    injury flag), and 'Allow Cross-Training' needs a secondary/cross-
    train position concept Player also doesn't have (this engine's
    granular Madden position scheme has no notion of a listed alternate
    position). Both are real, disclosed gaps, not implementation
    shortcuts -- see the Depth Chart page's own audit note in
    ROADMAP.md Sec2b. 'Lock Starters' keeps whoever currently holds each
    position's real starter slot(s) (`starter_counts`, e.g. 3 for WR)
    unchanged and only re-sorts the backups behind them."""
    for position, players in players_by_position.items():
        starter_n = starter_counts.get(position, 1)
        if lock_starters:
            current = resolve_order(team_abbr, position.value, players, path)
            locked, rest = current[:starter_n], current[starter_n:]
        else:
            locked, rest = [], list(players)
        rest_sorted = sorted(rest, key=functools.cmp_to_key(lambda a, b: _compare_for_autofill(a, b, respect_fatigue)))
        ordered = locked + rest_sorted
        set_order(team_abbr, position.value, [p.player_id for p in ordered], path)

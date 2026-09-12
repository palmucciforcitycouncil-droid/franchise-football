"""
Injury table queries (GDD Part 1 Sec 3.8 / R1 -- see app/models/injury.py
and app/engine/injuries.py for the full design accounting).

Same lru_cache-plus-explicit-clear pattern app/services/coach_store.py
already establishes for the Coach table: injuries are read on effectively
every simulated play (via depth_chart.py's roster/starter selection), so
a full-table query per play would be wasted work. clear_cache() is called
from every place that writes an Injury row (app/engine/injuries.py's
weekly decay and new-injury generation, both driven from
season_state.simulate_current_week()).

Graceful degradation matches coach_store.py's own: every function here
returns empty/None when the Injury table doesn't exist (a database that
predates this chunk), not a 500.
"""
from __future__ import annotations
from functools import lru_cache

from sqlalchemy.exc import OperationalError
from sqlmodel import select

from app.core.db import get_session
from app.models.injury import Injury


def _all_active_uncached() -> list[Injury]:
    try:
        with get_session() as session:
            return list(session.exec(select(Injury).where(Injury.is_active == True)).all())  # noqa: E712
    except OperationalError:
        return []


@lru_cache(maxsize=1)
def _all_active_cached() -> tuple[Injury, ...]:
    return tuple(_all_active_uncached())


def active_injuries() -> tuple[Injury, ...]:
    return _all_active_cached()


def currently_out_player_ids() -> frozenset[str]:
    """Players who cannot play at all right now -- weeks_out > 0. Used by
    depth_chart.py to exclude them from starter/depth-chart selection
    entirely (the real "promote the next slot" behavior Sec 6.10.5 calls
    for -- it falls out of the existing rating-sorted fallback once the
    injured player is removed from the candidate pool, no separate
    promotion logic needed)."""
    return frozenset(i.player_id for i in active_injuries() if i.is_out)


def rtp_penalties() -> dict[str, float]:
    """Players who ARE playing but still weakened -- weeks_out == 0,
    rtp_penalty > 0. See injuries.py's apply_rtp_penalty() for how this
    temporarily scales a player's in-memory attributes without touching
    their real stored rating."""
    return {i.player_id: i.rtp_penalty for i in active_injuries() if i.is_active and i.weeks_out == 0 and i.rtp_penalty > 0}


def injury_for_player(player_id: str) -> Injury | None:
    """The player's current active injury, if any -- Player Card / Roster
    page status badge."""
    for i in active_injuries():
        if i.player_id == player_id:
            return i
    return None


def team_injury_report(team_abbr: str) -> list[Injury]:
    return sorted(
        (i for i in active_injuries() if i.team_abbr == team_abbr),
        key=lambda i: (not i.is_out, i.weeks_out),
    )


def season_injury_count(season_number: int) -> int:
    """Every injury rolled this season, active or resolved -- for a
    season-level sanity check (real NFL: roughly 350-500 significant
    injuries per season across 32 teams), not just the currently-active
    count."""
    try:
        with get_session() as session:
            rows = session.exec(select(Injury).where(Injury.season_number == season_number)).all()
            return len(rows)
    except OperationalError:
        return 0


def resolve_all_active() -> None:
    """Offseason healing: real NFL players recover over an offseason,
    and this engine doesn't model offseason-carryover injury risk (Sec
    6.10.2's durations are already capped at the current season's end --
    see injuries.py's _duration_weeks() -- so only a trailing RTP taper
    can still be active when a season ends). Called from
    season_state.start_new_season()/reset_season() so a new season
    always starts with a clean bill of health, not stale RTP penalties
    depressing week-1 ratings."""
    active = list(active_injuries())
    if not active:
        return
    for injury in active:
        injury.weeks_out = 0
        injury.rtp_penalty = 0.0
        injury.is_active = False
    with get_session() as session:
        for injury in active:
            session.merge(injury)
        session.commit()
    clear_cache()


def save_injuries(injuries: list[Injury]) -> None:
    """merge(), not add() -- injury_id is deterministic
    (player_id_season_week), and resetting a franchise then
    re-simulating the same season_number's weeks (a real, legitimate
    flow -- reset_season() doesn't archive/clear old Injury rows, only
    marks them resolved) re-derives the exact same id. Same idempotent-
    upsert idiom scripts/import_coaches.py already establishes for
    exactly this class of problem, caught here via a real
    IntegrityError on this feature's own first re-simulated run."""
    if not injuries:
        return
    with get_session() as session:
        for injury in injuries:
            session.merge(injury)
        session.commit()
    clear_cache()


def clear_cache() -> None:
    _all_active_cached.cache_clear()

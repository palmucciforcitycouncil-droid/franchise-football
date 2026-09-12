"""
Coaching-staff queries (GDD Part 1 Sec 7.7.2 / Sec 9.2.5).

The read path for the Coach table, cached the same lru_cache-plus-
explicit-clear way depth_chart.py's starter selection and
history_store.career_stats() already are -- the play-calling AI asks
for a team's staff on effectively every play, and a full staff query
per play is wasted work.

Cache invalidation: clear_cache() is called from every place that
writes a Coach row (season rollover's coach progression, the Sec 7.9
championship-credit pass, and the Staff page's focus-area POST), for
the same reason season_state.simulate_current_week() already clears
season_stats' and history_store's caches.

Graceful degradation is deliberate: every function here returns
None/[] when the Coach table doesn't exist or is empty, so a database
that predates scripts/import_coaches.py (or a test DB copied before it
ran) keeps working exactly as it did before coaches existed rather
than 500ing. app/engine/coaching.py's staff-effect layer is written to
treat "no staff" as "no bias," which is precisely the pre-coach
behavior.
"""
from __future__ import annotations
from functools import lru_cache

from sqlalchemy.exc import OperationalError
from sqlmodel import select

from app.core.db import get_session
from app.models.coach import Coach, CoachRole

# Display order for a staff listing: head coach, then the three
# coordinator-tier roles, then assistants.
ROLE_ORDER = [CoachRole.HC, CoachRole.OC, CoachRole.DC, CoachRole.ST, CoachRole.AC]
_ROLE_RANK = {role: i for i, role in enumerate(ROLE_ORDER)}


def _all_coaches_uncached() -> list[Coach]:
    try:
        with get_session() as session:
            return list(session.exec(select(Coach)).all())
    except OperationalError:
        # No coach table in this database yet -- see module docstring.
        return []


@lru_cache(maxsize=1)
def all_coaches() -> tuple[Coach, ...]:
    return tuple(_all_coaches_uncached())


@lru_cache(maxsize=64)
def staff_for(team_abbr: str) -> tuple[Coach, ...]:
    """Every coach on one team, in ROLE_ORDER then reputation order."""
    staff = [c for c in all_coaches() if c.team_abbr == team_abbr and not c.retired]
    staff.sort(key=lambda c: (_ROLE_RANK[CoachRole(c.role)], -c.reputation, c.last_name))
    return tuple(staff)


def coach_in_role(team_abbr: str, role: CoachRole) -> Coach | None:
    """The team's HC/OC/DC/ST. Returns None for a vacant position (and
    for AC, which is a pool, not a single slot -- use assistants())."""
    if role is CoachRole.AC:
        return None
    for coach in staff_for(team_abbr):
        if CoachRole(coach.role) is role:
            return coach
    return None


def head_coach(team_abbr: str) -> Coach | None:
    return coach_in_role(team_abbr, CoachRole.HC)


def assistants(team_abbr: str) -> tuple[Coach, ...]:
    return tuple(c for c in staff_for(team_abbr) if CoachRole(c.role) is CoachRole.AC)


def free_agents() -> tuple[Coach, ...]:
    """Coaches with no team -- the hiring pool. Empty at league seed
    (the real seed staffs every position on all 32 teams); populated
    only once the lifecycle system starts firing coaches."""
    return tuple(sorted(
        (c for c in all_coaches() if c.team_abbr is None and not c.retired),
        key=lambda c: -c.reputation,
    ))


def by_id(coach_id: str) -> Coach | None:
    for coach in all_coaches():
        if coach.coach_id == coach_id:
            return coach
    return None


def search(query: str = "", role: str = "", limit: int = 50) -> list[Coach]:
    """League-wide coach search for the Staff page's Find Coaches box --
    the same shape as the Roster page's own Find Player search (M11),
    matching on name, specialty, or team."""
    q = query.strip().lower()
    results = []
    for coach in all_coaches():
        if coach.retired:
            continue
        if role and coach.role.value != role:
            continue
        if q and not (
            q in coach.full_name.lower()
            or (coach.specialty or "").lower().find(q) >= 0
            or (coach.team_abbr or "").lower() == q
            or coach.title.lower().find(q) >= 0
        ):
            continue
        results.append(coach)
    results.sort(key=lambda c: (-c.overall, c.last_name))
    return results[:limit]


def has_coaches() -> bool:
    """Whether this database has a coaching staff at all. Every UI
    surface that shows coach data checks this first and falls back to
    its pre-coach presentation if False, so a DB that predates the
    coach import degrades cleanly instead of showing empty boxes."""
    return len(all_coaches()) > 0


def clear_cache() -> None:
    all_coaches.cache_clear()
    staff_for.cache_clear()

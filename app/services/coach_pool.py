"""
R3d Sec 8: Coach free-agent pool queries.

Tier 1 (internal promotion candidates) is NOT here -- it's a team's own
current staff, handled entirely by app/engine/coach_replacement.py's
internal_candidates(). This module covers Tier 2 (real fired/unemployed
NFL coaches -- exactly coach_store.free_agents(), no separate storage:
firing a coach just sets Coach.team_abbr = None) and Tier 3 (the real
named college/former-NFL candidates scripts/seed_coach_pool.py seeds,
tagged Coach.pool_tier). Both tiers already live in the same Coach
table and the same free_agents() query -- this module exists only to
give the hiring code a role-scoped, semantically named entry point
instead of every caller re-filtering coach_store.free_agents() by hand.
"""
from __future__ import annotations

from app.models.coach import Coach, CoachRole, POOL_TIER_COLLEGE, POOL_TIER_FORMER_NFL
from app.services import coach_store


def candidates_for_role(role: CoachRole) -> list[Coach]:
    """Every free-agent coach (Tier 2 real fired/unemployed NFL coaches
    plus Tier 3 seeded college/former-NFL candidates) eligible for
    `role`, matched on the candidate's OWN stored role -- a college DC
    candidate is only ever searched for a DC vacancy, mirroring how a
    real coaching search doesn't cross-qualify candidates across roles."""
    return [c for c in coach_store.free_agents() if CoachRole(c.role) is role]


def pool_summary() -> dict[str, int]:
    """Free-agent counts by role, for the Staff page's pool-size display."""
    counts: dict[str, int] = {}
    for c in coach_store.free_agents():
        counts[c.role.value] = counts.get(c.role.value, 0) + 1
    return counts


def college_candidates() -> tuple[Coach, ...]:
    return tuple(c for c in coach_store.free_agents() if c.pool_tier == POOL_TIER_COLLEGE)


def former_nfl_candidates() -> tuple[Coach, ...]:
    return tuple(c for c in coach_store.free_agents() if c.pool_tier == POOL_TIER_FORMER_NFL)


def real_fired_candidates() -> tuple[Coach, ...]:
    """Tier 2: real ex-staff coaches with no pool tag, currently jobless."""
    return tuple(c for c in coach_store.free_agents() if c.pool_tier is None)

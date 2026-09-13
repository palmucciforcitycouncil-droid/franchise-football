"""
R3d: Replacement logic -- deciding WHO fills a coaching vacancy (Sec 4),
separate from coach_hiring.firing_probability() deciding WHETHER a
vacancy should even exist. Also the one write path in this engine that
actually reassigns a Coach row to a new team/role -- nothing else here
needed one before R3d, since no hiring/firing mechanic existed.

Promotion hierarchy (Sec 4.1) is real-title-driven: it reads the exact
AC `specialty` strings scripts/import_coaches.py's own
_SPECIALTY_BY_TITLE table produces (e.g. "Quarterbacks", "Linebackers"),
not invented category names.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from sqlalchemy.exc import OperationalError
from sqlmodel import select

from app.core.db import get_session
from app.engine import coach_contracts, coach_hiring
from app.engine.rng import RNG, stable_seed
from app.models.coach import (
    Coach, CoachRole, CoachSeasonStats,
    APPOINTMENT_PERMANENT, APPOINTMENT_INTERIM,
    OFFENSIVE_PROFILES, DEFENSIVE_PROFILES, default_focus_area_for,
)
from app.services import coach_store, coach_pool

# Sec 4.1's promotion hierarchy, by vacant role -> ordered list of AC
# `specialty` values to prefer, most-preferred first. A vacancy also
# always considers the coordinator tier first where the spec lists one
# (HC vacancy only).
_OC_HIERARCHY = ["Quarterbacks", "Passing Game", "Running Backs"]
_DC_HIERARCHY = ["Linebackers", "Secondary", "Cornerbacks", "Safeties", "Defensive Line"]
_ST_HIERARCHY = ["Special Teams (Assistant)"]

INTERNAL_PROMOTION_THRESHOLD = 55.0  # this module's own documented cutoff (spec gives the rule, no number)
INTERIM_RETENTION_WIN_PCT = 0.5      # Sec 5: an interim who wins enough gets kept permanently
NEW_HC_COORDINATOR_VULNERABILITY = (0.5, 0.7)  # Sec 6: 50-70% replacement probability


def _ac_rank(candidate: Coach, hierarchy: list[str]) -> int:
    if candidate.specialty in hierarchy:
        return hierarchy.index(candidate.specialty)
    return len(hierarchy)  # "any other assistant" -- still eligible, just least preferred


def internal_candidates(team_abbr: str, vacant_role: CoachRole, exclude_coach_id: str) -> list[Coach]:
    staff = [c for c in coach_store.staff_for(team_abbr) if c.coach_id != exclude_coach_id]
    if vacant_role is CoachRole.HC:
        coordinators = [c for c in staff if CoachRole(c.role) in (CoachRole.OC, CoachRole.DC, CoachRole.ST)]
        qb_coach = [c for c in staff if CoachRole(c.role) is CoachRole.AC and c.specialty == "Quarterbacks"]
        other_ac = [c for c in staff if CoachRole(c.role) is CoachRole.AC and c.specialty != "Quarterbacks"]
        return coordinators + qb_coach + other_ac
    hierarchy = {CoachRole.OC: _OC_HIERARCHY, CoachRole.DC: _DC_HIERARCHY, CoachRole.ST: _ST_HIERARCHY}.get(vacant_role)
    if hierarchy is None:
        return []
    acs = [c for c in staff if CoachRole(c.role) is CoachRole.AC]
    return sorted(acs, key=lambda c: _ac_rank(c, hierarchy))


def best_internal_candidate(team_abbr: str, vacant_role: CoachRole, exclude_coach_id: str,
                             season_number: int) -> tuple[Coach, float] | None:
    candidates = internal_candidates(team_abbr, vacant_role, exclude_coach_id)
    if not candidates:
        return None
    scored = [(c, coach_hiring.interim_promotion_score(c, season_number)) for c in candidates]
    scored.sort(key=lambda cs: -cs[1])
    return scored[0]


def recent_hc_turnover_count(team_abbr: str, season_number: int, lookback: int = 3) -> int:
    """Distinct HCs this team has had over the last `lookback` completed
    seasons -- Sec 4.4's "recent HC turnover indicates instability"."""
    try:
        with get_session() as s:
            rows = list(s.exec(
                select(CoachSeasonStats).where(
                    CoachSeasonStats.team_abbr == team_abbr, CoachSeasonStats.role == CoachRole.HC,
                    CoachSeasonStats.season < season_number, CoachSeasonStats.season >= season_number - lookback,
                )
            ).all())
    except OperationalError:
        return 0
    return len({r.coach_id for r in rows})


def search_external_pool(vacant_role: CoachRole, team_abbr: str, season_number: int,
                          appointment_type: str) -> list[tuple[Coach, float]]:
    """Every willing pool candidate for this vacancy, best HiringMerit
    first. Pool = real fired NFL coaches (Tier 2, coach_store.free_agents())
    plus the seeded Tier 3 college/former-NFL candidates
    (coach_pool.candidates_for_role()) -- coach_pool already unions both."""
    turnover = recent_hc_turnover_count(team_abbr, season_number)
    out = []
    for candidate in coach_pool.candidates_for_role(vacant_role):
        if not coach_hiring.will_consider(candidate, team_abbr, season_number, appointment_type, turnover):
            continue
        interest = coach_hiring.interest_score(candidate, team_abbr, season_number)
        merit = coach_hiring.hiring_merit(candidate, vacant_role, team_abbr, season_number, interest)
        out.append((candidate, merit))
    out.sort(key=lambda cm: -cm[1])
    return out


@dataclass
class ReplacementDecision:
    team_abbr: str
    role: CoachRole
    source: str                    # "internal" | "external" | "none"
    coach_id: str | None
    appointment_type: str
    score: float = 0.0


def decide_replacement(team_abbr: str, vacant_role: CoachRole, exclude_coach_id: str,
                        season_number: int, in_season: bool) -> ReplacementDecision:
    """Sec 4.1's flow: try internal promotion first; only search
    external if no internal candidate clears the threshold. Mid-season,
    Sec 9.1 says internal is favored even more strongly and a hire is
    always Interim; offseason hires (internal or external) are
    Permanent (Sec 9.2)."""
    internal = best_internal_candidate(team_abbr, vacant_role, exclude_coach_id, season_number)
    if internal is not None and internal[1] >= INTERNAL_PROMOTION_THRESHOLD:
        appointment = APPOINTMENT_INTERIM if in_season else APPOINTMENT_PERMANENT
        return ReplacementDecision(team_abbr, vacant_role, "internal", internal[0].coach_id, appointment, internal[1])

    appointment = APPOINTMENT_INTERIM if in_season else APPOINTMENT_PERMANENT
    external = search_external_pool(vacant_role, team_abbr, season_number, appointment)
    if external:
        return ReplacementDecision(team_abbr, vacant_role, "external", external[0][0].coach_id, appointment, external[0][1])

    if internal is not None:
        # No one clears the promotion threshold and the external market
        # produced no willing candidate -- promote the best internal
        # option anyway rather than leave a team unable to field a staff
        # (Sec 11: "Can't field team without HC -- game won't simulate").
        appointment = APPOINTMENT_INTERIM if in_season else APPOINTMENT_PERMANENT
        return ReplacementDecision(team_abbr, vacant_role, "internal", internal[0].coach_id, appointment, internal[1])

    return ReplacementDecision(team_abbr, vacant_role, "none", None, APPOINTMENT_PERMANENT, 0.0)


def _draw_profile(role: CoachRole, coach_id: str, league_seed: int, season_number: int) -> tuple[str, str]:
    rng = RNG.with_seed(stable_seed("promotion_profile", league_seed, coach_id, season_number))
    offensive = rng.choice(OFFENSIVE_PROFILES) if role in (CoachRole.HC, CoachRole.OC) else "Balanced"
    defensive = rng.choice(DEFENSIVE_PROFILES) if role in (CoachRole.HC, CoachRole.DC) else "Balanced"
    return offensive, defensive


def execute_fire(coach_id: str) -> Coach | None:
    """Vacates the coach's seat and returns them to the free-agent pool
    (Sec 8: firing an HC/OC/DC/ST makes them a free agent; their real
    career record is untouched -- only team_abbr/appointment change)."""
    with get_session() as s:
        coach = s.get(Coach, coach_id)
        if coach is None:
            return None
        coach.team_abbr = None
        s.add(coach)
        s.commit()
        s.refresh(coach)
    coach_store.clear_cache()
    return coach


def execute_hire(team_abbr: str, role: CoachRole, coach_id: str, season_number: int,
                  appointment_type: str, league_seed: int) -> Coach | None:
    """Assigns `coach_id` into `role` on `team_abbr`. Sec 6: a new hire's
    personal JSS history does NOT transfer (blank-slate job_security_score);
    OwnerWinPressure is untouched here on purpose -- it lives in
    owner_pressure_store.py, franchise-level, not on the Coach row."""
    with get_session() as s:
        coach = s.get(Coach, coach_id)
        if coach is None:
            return None
        coach.team_abbr = team_abbr
        coach.role = role
        coach.appointment_type = appointment_type
        coach.tenure_start_season = season_number
        coach.job_security_score = 50.0  # blank slate, Sec 6
        if role is not CoachRole.AC:
            coach.specialty = None
        # R13: a promoted/hired coach's Focus Area resets to their NEW
        # role's real default (same table default_focus_area_for() already
        # applies at import/migration time) -- otherwise a promoted
        # assistant would keep a stale AC-era focus (e.g. Training) after
        # becoming, say, the Offensive Coordinator, same class of gap
        # specialty/offensive_profile/defensive_profile already close below.
        coach.focus_area = default_focus_area_for(role, coach.specialty)
        # Coach Contract Realism (docs/R3d_COACHING_SYSTEM_SPECIFICATION.md
        # Sec 11): a fresh real contract for the NEW role -- previously this
        # never set contract_years/salary_aav at all, silently leaving an
        # external pool candidate (salary_aav=0 at seed, coach_pool.py) or
        # an internally promoted assistant (their old AC-tier pay) stuck at
        # the wrong numbers forever after a hire.
        coach.contract_years = coach_contracts.DEFAULT_CONTRACT_YEARS[role]
        coach.salary_aav = round(coach_contracts.coach_market_value(coach))
        offensive, defensive = _draw_profile(role, coach_id, league_seed, season_number)
        if role in (CoachRole.HC, CoachRole.OC):
            coach.offensive_profile = offensive
        if role in (CoachRole.HC, CoachRole.DC):
            coach.defensive_profile = defensive
        s.add(coach)
        s.commit()
        s.refresh(coach)
    coach_store.clear_cache()
    return coach


def apply_new_hc_effect(team_abbr: str, new_hc_coach_id: str, season_number: int,
                         league_seed: int) -> list[tuple[str, str, str | None]]:
    """Sec 6: existing coordinators become immediately vulnerable to a
    new HC -- each OC/DC/ST independently has a 50-70% (seeded, so a
    replay is identical) chance of being fired and replaced right away,
    offseason-style (Permanent, full market). Returns
    (role_value, fired_coach_id, new_coach_id_or_None) for each
    coordinator actually touched, so a caller iterating a stale staff
    snapshot can mark both the outgoing and incoming coach_id as already
    resolved this pass."""
    changed: list[tuple[str, str, str | None]] = []
    for coach in coach_store.staff_for(team_abbr):
        role = CoachRole(coach.role)
        if role not in (CoachRole.OC, CoachRole.DC, CoachRole.ST) or coach.coach_id == new_hc_coach_id:
            continue
        rng = RNG.with_seed(stable_seed("new_hc_coordinator_purge", league_seed, season_number, coach.coach_id))
        lo, hi = NEW_HC_COORDINATOR_VULNERABILITY
        if not rng.prob(rng.uniform(lo, hi)):
            continue
        fired_id = coach.coach_id
        execute_fire(fired_id)
        decision = decide_replacement(team_abbr, role, fired_id, season_number, in_season=False)
        new_id = None
        if decision.coach_id is not None:
            execute_hire(team_abbr, role, decision.coach_id, season_number, decision.appointment_type, league_seed)
            new_id = decision.coach_id
        changed.append((role.value, fired_id, new_id))
    return changed


def resolve_interim_appointments(season) -> list[str]:
    """Sec 5's end-of-season interim evaluation, run once per offseason
    BEFORE the normal firing pass (an interim who earns it becomes
    Permanent; one who doesn't is treated as a fresh vacancy and a real
    search runs for their replacement, offseason rules). Returns the
    list of team_abbr whose interim HC/coordinator was resolved."""
    resolved: list[str] = []
    try:
        with get_session() as s:
            interims = list(s.exec(
                select(Coach).where(Coach.appointment_type == APPOINTMENT_INTERIM, Coach.retired == False)  # noqa: E712
            ).all())
    except OperationalError:
        return resolved

    for coach in interims:
        if coach.team_abbr is None:
            continue
        record = season.records.get(coach.team_abbr)
        win_pct = record.win_pct if record is not None else 0.0
        if win_pct >= INTERIM_RETENTION_WIN_PCT:
            with get_session() as s:
                row = s.get(Coach, coach.coach_id)
                if row is not None:
                    row.appointment_type = APPOINTMENT_PERMANENT
                    s.add(row)
                    s.commit()
            resolved.append(f"{coach.team_abbr}:{coach.role.value}:retained")
        else:
            team_abbr, role = coach.team_abbr, CoachRole(coach.role)
            execute_fire(coach.coach_id)
            decision = decide_replacement(team_abbr, role, coach.coach_id, season.season_number, in_season=False)
            if decision.coach_id is not None:
                execute_hire(team_abbr, role, decision.coach_id, season.season_number,
                             decision.appointment_type, season.league_seed)
            resolved.append(f"{team_abbr}:{role.value}:reopened")
    if interims:
        coach_store.clear_cache()
    return resolved

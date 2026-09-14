"""
R3d Sec 10: the AI autonomy loop -- every non-user team, every coaching
role, evaluated for firing every offseason, plus a lighter in-season
pass after each simulated week. The user's own team is deliberately
EXCLUDED at every call site here; main.py's Hire/Fire/Promote routes
(Sec 11) call the exact same app/engine/coach_hiring.py /
coach_replacement.py functions for the user's team -- an AI team and
the user's team are evaluated and replaced by identical math, only WHO
decides differs.
"""
from __future__ import annotations

from app.data.teams import TEAMS, TEAMS_BY_ABBR
from app.engine import coach_contracts, coach_hiring, coach_progression, coach_replacement
from app.engine.rng import RNG, stable_seed
from app.models.coach import CoachRole, APPOINTMENT_PERMANENT, FOCUS_DEVELOPMENT, FOCUS_TRAINING, FOCUS_SCOUTING
from app.services import coach_store, owner_pressure_store


def _is_division_champion(season, team_abbr: str) -> bool:
    info = TEAMS_BY_ABBR[team_abbr]
    rivals = [t.abbr for t in TEAMS if t.conference == info.conference and t.division == info.division]
    records = [(abbr, season.records[abbr]) for abbr in rivals if abbr in season.records]
    if not records:
        return False
    best_abbr, _ = max(records, key=lambda ar: (ar[1].win_pct, ar[1].point_diff))
    return best_abbr == team_abbr


# (team_abbr, role) -> coach_id fired this offseason with no replacement
# found, so ensure_core_staff() never "fills" the seat by re-hiring the very
# coach who was just let go.
_unfilled_firings: dict[tuple[str, CoachRole], str] = {}


def _evaluate_team(season, team_abbr: str, team_ranks, week: int, log: list[str]) -> None:
    """One team's HC/OC/DC/ST firing pass. `week` is 0 for an offseason
    evaluation (full weight, no in-season caution) or 1-18 in-season.
    Tracks `reassigned` so a coach fired-and-replaced earlier in THIS
    same pass (e.g. an OC promoted to HC) is never re-evaluated against
    their stale pre-promotion snapshot later in the same loop."""
    reassigned: set[str] = set()
    for coach in coach_store.staff_for(team_abbr):
        if coach.coach_id in reassigned:
            continue
        role = CoachRole(coach.role)
        if role is CoachRole.AC:
            continue  # Sec 8: AC firing isn't a modeled mechanic
        jss, _ = coach_hiring.compute_jss(season, team_abbr, coach, team_ranks)
        prob = coach_hiring.firing_probability(jss, week, role, coach, season.season_number, team_abbr)
        rng = RNG.with_seed(stable_seed(
            "coach_fire_roll", season.league_seed, season.season_number, week, coach.coach_id))
        if not rng.prob(prob):
            # Coach Contract Realism: this coach survived the roll -- if
            # their contract already expired (contract_years <= 0, real
            # after season_state.apply_coach_offseason()'s own rollover
            # decrement), the front office renews them at real market
            # value rather than leaving them a lame duck forever. Offseason
            # only (week == 0) -- a real contract decision, not a weekly one.
            if week == 0 and coach.contract_years <= 0:
                coach_contracts.renew_contract(coach.coach_id, season.season_number)
                log.append(f"{team_abbr}:{role.value}:contract_renewed")
            continue

        fired_id = coach.coach_id
        coach_replacement.execute_fire(fired_id)
        reassigned.add(fired_id)
        in_season = week > 0
        decision = coach_replacement.decide_replacement(team_abbr, role, fired_id, season.season_number, in_season)
        if decision.coach_id is None:
            _unfilled_firings[(team_abbr, role)] = fired_id
            log.append(f"{team_abbr}:{role.value}:fired_no_replacement_found")
            continue

        coach_replacement.execute_hire(
            team_abbr, role, decision.coach_id, season.season_number, decision.appointment_type, season.league_seed)
        reassigned.add(decision.coach_id)
        log.append(f"{team_abbr}:{role.value}:fired_and_replaced({decision.source})")

        if role is CoachRole.HC:
            purged = coach_replacement.apply_new_hc_effect(
                team_abbr, decision.coach_id, season.season_number, season.league_seed)
            for purged_role, purged_fired_id, purged_new_id in purged:
                reassigned.add(purged_fired_id)
                if purged_new_id is not None:
                    reassigned.add(purged_new_id)
                log.append(f"{team_abbr}:{purged_role}:new_hc_purge")


def run_offseason_autonomy(season, exclude_team_abbr: str | None) -> list[str]:
    """Sec 10's flow, called from season_state.apply_coach_offseason()
    AFTER coach progression/retirement (so ranks/ratings are this
    season's real, final numbers) and AFTER team_expectations' snapshot
    for the season just finished still resolves (this reads the OLD
    season's expectation, not next season's -- next season's snapshot
    isn't computed until AFTER this function returns and the new Season
    object exists, see season_state.py).

    Order: (1) resolve any interim appointments from the season just
    finished, (2) evaluate every remaining coach for firing using the
    CURRENT (pre-adjustment) OwnerWinPressure -- how patient ownership
    already was ENTERING this evaluation, (3) only after every firing/
    hiring decision is made, roll each team's OwnerWinPressure forward
    for next season via its own real season outcome (Sec 3.2)."""
    from app.services import coach_records, team_expectations

    _unfilled_firings.clear()
    log: list[str] = list(coach_replacement.resolve_interim_appointments(season))

    ranks = coach_progression.compute_team_ranks(season)
    for team in TEAMS:
        if team.abbr == exclude_team_abbr:
            continue
        if season.records.get(team.abbr) is None or season.records[team.abbr].games_played == 0:
            continue
        _evaluate_team(season, team.abbr, ranks.get(team.abbr), week=0, log=log)

    log.extend(backfill_assistants(season, exclude_team_abbr))

    for team in TEAMS:
        if team.abbr == exclude_team_abbr:
            continue
        record = season.records.get(team.abbr)
        if record is None or record.games_played == 0:
            continue
        expectation = team_expectations.for_team(season.season_number, team.abbr)
        expected_win_pct = expectation.expected_win_pct if expectation is not None else record.win_pct
        outcome_bucket = coach_hiring.classify_season_outcome(record.win_pct, expected_win_pct)
        playoff_outcome = coach_records._playoff_outcome_for(season, team.abbr)
        achievement = coach_hiring.best_achievement(playoff_outcome, _is_division_champion(season, team.abbr))
        owner_pressure_store.apply_season_end(team.abbr, outcome_bucket, achievement)

    return log


def backfill_assistants(season, exclude_team_abbr: str | None) -> list[str]:
    """Keeps every AI team at coach_contracts.MAX_ASSISTANTS (4) assistant
    coaches (Brian's 2026-09-14 fixes doc). Before this, nothing ever hired
    an assistant: every internal promotion to OC/DC/ST permanently shrank
    the AC group, so a 4-assistant cap would drain toward zero within a few
    offseasons. Offseason only; the best-rated AC free agent whose market
    salary fits the team's remaining staff-cap room fills each open seat
    (execute_hire() itself refuses a 5th). The user's own team fills its
    assistant seats manually from the Staff page instead."""
    log: list[str] = []
    for team in TEAMS:
        if team.abbr == exclude_team_abbr:
            continue
        open_seats = coach_contracts.MAX_ASSISTANTS - len(coach_store.assistants(team.abbr))
        while open_seats > 0:
            room = coach_contracts.staff_cap_room(team.abbr, season.season_number)
            affordable = [
                c for c in coach_store.free_agents()
                if CoachRole(c.role) is CoachRole.AC
                and coach_contracts.coach_market_value(c, season_number=season.season_number) <= room
            ]
            if not affordable:
                log.append(f"{team.abbr}:AC:no_affordable_assistant")
                break
            pick = max(affordable, key=lambda c: (c.overall, c.coach_id))
            hired = coach_replacement.execute_hire(
                team.abbr, CoachRole.AC, pick.coach_id, season.season_number,
                APPOINTMENT_PERMANENT, season.league_seed)
            if hired is None:
                break
            log.append(f"{team.abbr}:AC:assistant_hired")
            open_seats -= 1
    return log


# The seats a team cannot enter the next offseason stage without (Brian's
# report, 2026-09-14: his own expired Head Coach let him walk straight into
# free agency). ST/AC vacancies are survivable -- the sim falls back to a
# neutral effect -- but HC/OC/DC are the play-callers.
CORE_STAFF_ROLES: tuple[CoachRole, ...] = (CoachRole.HC, CoachRole.OC, CoachRole.DC)


def core_staff_blockers(team_abbr: str) -> list[tuple[CoachRole, str]]:
    """Every HC/OC/DC seat on `team_abbr` that is vacant or holds an
    expired contract (contract_years <= 0 -- an extension resets it above
    zero, so an extended coach is never a blocker). Returns
    (role, "vacant"|"expired") pairs, empty when the staff is complete or
    the database has no coach table at all."""
    if not coach_store.has_coaches():
        return []
    blockers: list[tuple[CoachRole, str]] = []
    for role in CORE_STAFF_ROLES:
        coach = coach_store.coach_in_role(team_abbr, role)
        if coach is None:
            blockers.append((role, "vacant"))
        elif coach.contract_years <= 0:
            blockers.append((role, "expired"))
    return blockers


def ensure_core_staff(season, exclude_team_abbr: str | None) -> list[str]:
    """Safety net run right after run_offseason_autonomy(): that pass skips
    teams with no games played, leaves a seat open when a firing finds no
    replacement, and never refills a retirement (apply_coach_offseason's
    own docstring) -- so an AI team could otherwise carry a vacant or
    expired HC/OC/DC into the next stage. Expired -> renewed at market
    value (the same call _evaluate_team makes for a survivor); vacant ->
    the same decide_replacement()/execute_hire() offseason path a firing
    uses. The user's team is excluded: the Staff-stage gate makes the user
    fix their own seats manually."""
    if not coach_store.has_coaches():
        return []
    log: list[str] = []
    for team in TEAMS:
        if team.abbr == exclude_team_abbr:
            continue
        # Re-read after every fix: an internal promotion into HC opens the
        # promoted coordinator's own seat, which must be caught this pass.
        unresolvable: set[CoachRole] = set()
        for _ in range(2 * len(CORE_STAFF_ROLES)):
            pending = [(r, p) for r, p in core_staff_blockers(team.abbr) if r not in unresolvable]
            if not pending:
                break
            role, problem = pending[0]
            if problem == "expired":
                coach = coach_store.coach_in_role(team.abbr, role)
                coach_contracts.renew_contract(coach.coach_id)
                log.append(f"{team.abbr}:{role.value}:safety_net_renewed")
            else:
                just_fired = _unfilled_firings.get((team.abbr, role), "")
                decision = coach_replacement.decide_replacement(team.abbr, role, just_fired, season.season_number, in_season=False)
                if decision.coach_id is not None and decision.coach_id == just_fired:
                    others = [c for c, _ in coach_replacement.search_external_pool(
                        role, team.abbr, season.season_number, decision.appointment_type) if c.coach_id != just_fired]
                    internal = coach_replacement.best_internal_candidate(team.abbr, role, just_fired, season.season_number)
                    fallback_id = others[0].coach_id if others else (internal[0].coach_id if internal else None)
                    decision = coach_replacement.ReplacementDecision(
                        team.abbr, role, "external" if others else "internal", fallback_id, decision.appointment_type)
                if decision.coach_id is None:
                    unresolvable.add(role)
                    log.append(f"{team.abbr}:{role.value}:safety_net_no_candidate")
                    continue
                coach_replacement.execute_hire(
                    team.abbr, role, decision.coach_id, season.season_number, decision.appointment_type, season.league_seed)
                log.append(f"{team.abbr}:{role.value}:safety_net_hired({decision.source})")
            coach_store.clear_cache()
    return log


def run_inseason_autonomy(season, week: int, exclude_team_abbr: str | None) -> list[str]:
    """Sec 10's "after each game, if JSS threshold triggers" in-season
    check -- called from season_state.simulate_current_week() once the
    just-simulated week's results are recorded. Uses the identical
    firing_probability() model as the offseason pass; Sec 3.4's very low
    in-season week modifiers (0.05 through week 3-4) are what keep this
    from over-firing early, not a separate/looser rule here."""
    log: list[str] = []
    ranks = coach_progression.compute_team_ranks(season)
    for team in TEAMS:
        if team.abbr == exclude_team_abbr:
            continue
        record = season.records.get(team.abbr)
        if record is None or record.games_played == 0:
            continue
        _evaluate_team(season, team.abbr, ranks.get(team.abbr), week, log)
    return log


# R13 Sec 7: real thresholds for the AI Focus Autonomy pass below -- this
# module's own documented choices, same category as firing_probability()'s
# own week-modifier constants (the spec names the signals, not the cutoffs).
_POINTS_FOR_BOTTOM_THIRD_RANK = 22  # rank > this (of 32) counts as a real offensive weakness


def run_focus_autonomy(season, exclude_team_abbr: str | None) -> list[str]:
    """R13 Sec 7: every offseason, each AI team's ASSISTANT coaches (only
    -- HC/OC/DC/ST stay pinned to their natural lane forever, since
    reassigning a Defensive Coordinator away from DF Gameplan makes no
    narrative sense) get re-evaluated for Development/Training/Scouting
    focus, using real signals from the season just finished:

    - Points-for rank in the real bottom third (coach_progression.compute_
      team_ranks(), the SAME ranks the firing pass already computes) biases
      toward Development.
    - This team's real injury count this season, above the league average
      (injury_store.team_season_injury_count(), R1), biases toward Training.
    - A real season outcome significantly/catastrophically below this
      team's own preseason expectation (coach_hiring.classify_season_
      outcome(), the SAME bucketing OwnerWinPressure already uses) biases
      toward Scouting -- an underperforming team leans harder on the draft.

    Deterministic weighted-random selection (stable_seed-keyed per coach),
    not a hard rule -- two teams with identical signals don't necessarily
    make identical choices, same spirit as firing_probability()'s own rolls.
    No cap on how many assistants move to the same bucket in one pass (R13
    Sec 2: over-investing costs a team real OF/DF Gameplan and Development
    influence automatically -- the same opportunity-cost guardrail applies
    to the AI's own choices).

    Called from season_state.apply_coach_offseason(), AFTER progression/
    retirement (so ranks/ratings are this season's real, final numbers) and
    AFTER run_offseason_autonomy() (so a coach hired/fired this pass is
    evaluated in their real, current role). Only ASSISTANTS ever move, so a
    coach fired-and-replaced this same offseason is simply skipped if the
    replacement isn't an AC (HC/OC/DC/ST hires are never reassigned here)."""
    from app.core.db import get_session
    from app.models.coach import Coach as CoachModel
    from app.services import injury_store, team_expectations

    log: list[str] = []
    ranks = coach_progression.compute_team_ranks(season)
    injury_counts = {team.abbr: injury_store.team_season_injury_count(season.season_number, team.abbr)
                      for team in TEAMS}
    league_avg_injuries = sum(injury_counts.values()) / len(injury_counts) if injury_counts else 0.0

    # Decide every reassignment first (pure, no DB writes), then apply them
    # all in ONE session at the end -- N individual sessions/commits for a
    # 305-assistant staff would be exactly the per-row DB round-trip
    # ROADMAP.md Sec4f's own draft-perf bug already caught once this session.
    reassignments: dict[str, str] = {}
    for team in TEAMS:
        if team.abbr == exclude_team_abbr:
            continue
        record = season.records.get(team.abbr)
        if record is None or record.games_played == 0:
            continue

        team_ranks = ranks.get(team.abbr)
        offense_needs_help = (
            team_ranks is not None and team_ranks.points_for_rank is not None
            and team_ranks.points_for_rank >= _POINTS_FOR_BOTTOM_THIRD_RANK
        )
        injury_prone = injury_counts.get(team.abbr, 0) > league_avg_injuries

        expectation = team_expectations.for_team(season.season_number, team.abbr)
        expected_win_pct = expectation.expected_win_pct if expectation is not None else record.win_pct
        outcome = coach_hiring.classify_season_outcome(record.win_pct, expected_win_pct)
        rebuilding = outcome in ("significantly_below", "catastrophic")

        # Development is always the real floor -- the AI doesn't need a
        # signal to justify NOT moving someone (R13 Sec 4's own default).
        weights: dict[str, float] = {FOCUS_DEVELOPMENT: 1.0}
        if offense_needs_help:
            weights[FOCUS_DEVELOPMENT] = weights[FOCUS_DEVELOPMENT] + 1.0
        if injury_prone:
            weights[FOCUS_TRAINING] = 1.0
        if rebuilding:
            weights[FOCUS_SCOUTING] = 1.0

        options = list(weights.keys())
        probs = list(weights.values())

        for coach in coach_store.staff_for(team.abbr):
            if CoachRole(coach.role) is not CoachRole.AC:
                continue
            rng = RNG.with_seed(stable_seed(
                "focus_ai", season.league_seed, season.season_number, team.abbr, coach.coach_id))
            new_focus = rng.weighted_choice(options, probs)
            if new_focus != coach.focus_area:
                reassignments[coach.coach_id] = new_focus
                log.append(f"{team.abbr}:{coach.coach_id}:focus_reassigned({coach.focus_area}->{new_focus})")

    if reassignments:
        with get_session() as s:
            for coach_id, new_focus in reassignments.items():
                row = s.get(CoachModel, coach_id)
                if row is not None:
                    row.focus_area = new_focus
                    s.add(row)
            s.commit()
        coach_store.clear_cache()

    return log

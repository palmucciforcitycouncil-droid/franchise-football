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
from app.engine import coach_hiring, coach_progression, coach_replacement
from app.engine.rng import RNG, stable_seed
from app.models.coach import CoachRole
from app.services import coach_store, owner_pressure_store


def _is_division_champion(season, team_abbr: str) -> bool:
    info = TEAMS_BY_ABBR[team_abbr]
    rivals = [t.abbr for t in TEAMS if t.conference == info.conference and t.division == info.division]
    records = [(abbr, season.records[abbr]) for abbr in rivals if abbr in season.records]
    if not records:
        return False
    best_abbr, _ = max(records, key=lambda ar: (ar[1].win_pct, ar[1].point_diff))
    return best_abbr == team_abbr


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
            continue

        fired_id = coach.coach_id
        coach_replacement.execute_fire(fired_id)
        reassigned.add(fired_id)
        in_season = week > 0
        decision = coach_replacement.decide_replacement(team_abbr, role, fired_id, season.season_number, in_season)
        if decision.coach_id is None:
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

    log: list[str] = list(coach_replacement.resolve_interim_appointments(season))

    ranks = coach_progression.compute_team_ranks(season)
    for team in TEAMS:
        if team.abbr == exclude_team_abbr:
            continue
        if season.records.get(team.abbr) is None or season.records[team.abbr].games_played == 0:
            continue
        _evaluate_team(season, team.abbr, ranks.get(team.abbr), week=0, log=log)

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

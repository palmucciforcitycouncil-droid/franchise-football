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
from app.models.coach import (
    CoachRole, FOCUS_DEVELOPMENT, FOCUS_TRAINING, FOCUS_SCOUTING,
    FOCUS_RUNNING_GAME, FOCUS_PASSING_GAME, FOCUS_QB, FOCUS_RECEIVERS, FOCUS_OL,
    FOCUS_RUN_DEFENSE, FOCUS_PASS_DEFENSE, FOCUS_QB_PRESSURE, FOCUS_DL, FOCUS_SECONDARY,
    default_focus_area_for, focus_options_for, _rating_for_focus,
)
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
            # Coach Contract Realism: this coach survived the roll -- if
            # their contract already expired (contract_years <= 0, real
            # after season_state.apply_coach_offseason()'s own rollover
            # decrement), the front office renews them at real market
            # value rather than leaving them a lame duck forever. Offseason
            # only (week == 0) -- a real contract decision, not a weekly one.
            if week == 0 and coach.contract_years <= 0:
                coach_contracts.renew_contract(coach.coach_id)
                log.append(f"{team_abbr}:{role.value}:contract_renewed")
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


# R16 Sec 10: real thresholds for the AI Focus Autonomy pass below --
# this module's own documented choices, same category as firing_
# probability()'s own week-modifier constants.
_POINTS_FOR_BOTTOM_THIRD_RANK = 22   # rank > this (of 32) counts as a real offensive weakness
_POINTS_AGAINST_BOTTOM_THIRD_RANK = 22  # rank > this counts as a real defensive weakness

# R16 Sec 10: offense/defense-need-driven options for OC/DC/AC, split by
# side -- reused when that side's real signal (offense_needs_help/
# defense_needs_help) fires, spreading equal weight across all of them
# rather than fabricating a false-precision "which one exactly" signal
# (no per-subcategory rank -- run vs. pass weakness -- exists cheaply).
_OFFENSE_NEED_OPTIONS = (FOCUS_RUNNING_GAME, FOCUS_PASSING_GAME, FOCUS_QB, FOCUS_RECEIVERS, FOCUS_OL)
_DEFENSE_NEED_OPTIONS = (FOCUS_RUN_DEFENSE, FOCUS_PASS_DEFENSE, FOCUS_QB_PRESSURE, FOCUS_DL, FOCUS_SECONDARY)
# How much extra weight a coach's OWN best-rated available option gets --
# "favor what they're good at" alongside team need. [tune].
OWN_RATING_WEIGHT = 1.5


def _weights_for_coach(coach, options: list[str], offense_needs_help: bool, defense_needs_help: bool,
                        injury_prone: bool, rebuilding: bool) -> dict[str, float]:
    """R16 Sec 10: this ONE coach's real weighted-choice distribution
    over THEIR OWN available menu (`options`) -- blends real team-need
    signals with the coach's own rating at each option (favor what
    they're good at, not just what the team needs), and always keeps
    their role-appropriate "home" option (Balanced/Offensive/Defensive
    Gameplan for HC/OC/DC, Development for AC) as the real floor so the
    AI doesn't need a signal to justify NOT moving someone."""
    home = default_focus_area_for(CoachRole(coach.role), coach)
    weights: dict[str, float] = {home: 1.0}

    def bump(option: str, amount: float) -> None:
        if option in options:
            weights[option] = weights.get(option, 0.0) + amount

    if offense_needs_help:
        bump(FOCUS_DEVELOPMENT, 1.0)
        for opt in _OFFENSE_NEED_OPTIONS:
            bump(opt, 1.0 / len(_OFFENSE_NEED_OPTIONS))
    if defense_needs_help:
        bump(FOCUS_DEVELOPMENT, 1.0)
        for opt in _DEFENSE_NEED_OPTIONS:
            bump(opt, 1.0 / len(_DEFENSE_NEED_OPTIONS))
    if injury_prone:
        bump(FOCUS_TRAINING, 1.0)
    if rebuilding:
        bump(FOCUS_SCOUTING, 1.0)

    # Favor whatever this coach is personally best at, among their own
    # options -- the same "default to your best rating" logic AC's
    # import-time default already uses, applied every offseason instead
    # of only once at hire time.
    best_option, best_rating = None, -1.0
    for option in options:
        rating = _rating_for_focus(coach, option)
        if rating > best_rating:
            best_option, best_rating = option, rating
    if best_option is not None and best_rating > 0:
        bump(best_option, OWN_RATING_WEIGHT)

    return weights


def run_focus_autonomy(season, exclude_team_abbr: str | None) -> list[str]:
    """R16 Sec 10: every offseason, every AI team's coach -- HC, OC, DC,
    AND AC (expanded from R13's assistants-only scope: "the AI should be
    making the best decisions they can for their team") -- gets
    re-evaluated for Focus Area, blending real team-need signals with
    each coach's own rating at their available options:

    - Points-for/points-against rank in the real bottom third
      (coach_progression.compute_team_ranks()) biases toward the
      relevant side's options (offense_needs_help/defense_needs_help).
    - This team's real injury count this season, above the league
      average (injury_store.team_season_injury_count(), R1), biases
      toward Strength & Conditioning.
    - A real season outcome significantly/catastrophically below this
      team's own preseason expectation (coach_hiring.classify_season_
      outcome()) biases toward Scouting.
    - Every coach's OWN rating at each of their menu options biases
      toward whatever they're personally best at (Sec 4's "default to
      your best rating" logic, reapplied every offseason).

    Deterministic weighted-random selection (stable_seed-keyed per
    coach), not a hard rule. No cap on how many coaches move to the same
    bucket in one pass -- over-investing costs the team real influence
    elsewhere automatically (Sec 2's opportunity-cost guardrail).

    Called from season_state.apply_coach_offseason(), AFTER progression/
    retirement AND after this pass's own Coaching Tree drift/specialty
    relabel (so ratings and specialties are this season's real, final
    values), and AFTER run_offseason_autonomy() (so a coach hired/fired
    this pass is evaluated in their real, current role)."""
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
    # 433-coach league would be exactly the per-row DB round-trip
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
        defense_needs_help = (
            team_ranks is not None and team_ranks.points_against_rank is not None
            and team_ranks.points_against_rank >= _POINTS_AGAINST_BOTTOM_THIRD_RANK
        )
        injury_prone = injury_counts.get(team.abbr, 0) > league_avg_injuries

        expectation = team_expectations.for_team(season.season_number, team.abbr)
        expected_win_pct = expectation.expected_win_pct if expectation is not None else record.win_pct
        outcome = coach_hiring.classify_season_outcome(record.win_pct, expected_win_pct)
        rebuilding = outcome in ("significantly_below", "catastrophic")

        for coach in coach_store.staff_for(team.abbr):
            options = focus_options_for(coach)
            weights = _weights_for_coach(coach, options, offense_needs_help, defense_needs_help,
                                         injury_prone, rebuilding)
            rng = RNG.with_seed(stable_seed(
                "focus_ai", season.league_seed, season.season_number, team.abbr, coach.coach_id))
            new_focus = rng.weighted_choice(list(weights.keys()), list(weights.values()))
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

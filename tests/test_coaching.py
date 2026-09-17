"""
Coaching module tests (ROADMAP.md R3; GDD Part 1 Sec 7.7.2, 7.9, 8.2).

Style follows this suite's existing convention: hand-built fixtures with
exact expected values for the pure functions (same as
tests/test_scouting.py and tests/test_progression.py), and DB-backed
assertions only where a DB is genuinely what's under test.

Every DB-touching test here copies the real database to a throwaway and
redirects `app.core.db.DB_PATH` per-test with a `finally` restore --
the exact pattern tests/test_season_rollover.py established and which
ROADMAP.md Sec 2b's M14 incident note makes mandatory. The
session-scoped fixture in conftest.py covers the season-save and
power-rank paths; it deliberately does NOT cover DB_PATH (see that
note for why a global DB redirect would be silently defeated here).
"""
from __future__ import annotations
import shutil

import pytest
from sqlmodel import select

from app.core import db as db_module
from app.engine import coaching, coach_progression
from app.engine.awards import (
    _pythagorean_expected_wins, _rank_norm, coach_of_the_year,
)
from app.models.coach import (
    Coach, CoachRole, CoachSeasonStats,
    FOCUS_OFFENSIVE_GAMEPLAN, FOCUS_DEFENSIVE_GAMEPLAN, FOCUS_BALANCED_GAMEPLAN, FOCUS_DEVELOPMENT,
    FOCUS_SPECIAL_TEAMS, FOCUS_TRAINING, FOCUS_SCOUTING, default_focus_area_for,
)
from app.services import coach_store, coach_records, season_state
from scripts.import_coaches import (
    build_coaches, coach_id_for, dedupe_entries, map_title, parse_seed,
    reputation_from_salary, SeedEntry, DEFAULT_SOURCE,
)


# --------------------------------------------------------------------
# Seed parsing + the Sec 7.7.2.1a title -> role/specialty mapping
# --------------------------------------------------------------------

SAMPLE_SEED = """# Directory

## **AFC East**

### **Buffalo Bills**

> * **Head Coach:** Sean McDermott (  Salary: $10,000,000)
> * **Offensive Coordinator:** Joe Brady (  Salary: $2,500,000)
> * **Quarterbacks Coach:** Andy Janocko (  Salary: $850,000)
> * **Linebackers Coach / Assistant Head Coach:** Al Holcomb (  Salary: $900,000)
> * **Special Teams Coordinator:** Matthew Smiley (  Salary: $1,000,000)
> * **Assistant Special Teams Coach:** Curtis Modkins (  Salary: $450,000)
"""


def test_parse_seed_reads_name_title_and_salary_for_every_line():
    entries, errors = parse_seed(SAMPLE_SEED)
    assert errors == []
    assert len(entries) == 6
    first = entries[0]
    assert (first.team_abbr, first.first_name, first.last_name, first.salary_aav) == (
        "BUF", "Sean", "McDermott", 10_000_000
    )


def test_only_the_three_coordinator_titles_map_to_their_own_role():
    """R16 removed the ST role outright -- Special Teams Coordinator now
    maps to AC + a "Special Teams" specialty, same shape as any other
    coordinator-ish AC title."""
    assert map_title("Head Coach") == (CoachRole.HC, None)
    assert map_title("Offensive Coordinator") == (CoachRole.OC, None)
    assert map_title("Defensive Coordinator") == (CoachRole.DC, None)
    assert map_title("Special Teams Coordinator") == (CoachRole.AC, "Special Teams")


def test_assistants_to_a_coordinator_stay_ac_not_promoted():
    """GDD Sec 7.7.2.1a is explicit about this: an Assistant Special
    Teams Coach stays AC rather than becoming a second ST."""
    assert map_title("Assistant Special Teams Coach") == (CoachRole.AC, "Special Teams (Assistant)")
    assert map_title("Assistant Special Teams Coordinator") == (CoachRole.AC, "Special Teams (Assistant)")
    assert map_title("Assistant Quarterbacks Coach") == (CoachRole.AC, "Quarterbacks (Assistant)")


def test_dual_title_keeps_only_the_primary_position_group():
    """Sec 7.7.2.1a's own worked example: BUF's real "Linebackers Coach /
    Assistant Head Coach" becomes AC + "Linebackers", with the
    Assistant-Head-Coach tag dropped entirely."""
    assert map_title("Linebackers Coach / Assistant Head Coach") == (CoachRole.AC, "Linebackers")


def test_one_person_listed_twice_on_a_staff_collapses_to_one_row():
    """The real seed lists 17 people twice -- a broad coordinator-ish
    title plus their actual position-group line, at one salary. They are
    one employee, not two."""
    entries = [
        SeedEntry("KC", "Offensive Coordinator", "Matt", "Nagy", 3_000_000),
        SeedEntry("KC", "Quarterbacks Coach", "Matt", "Nagy", 3_000_000),
    ]
    resolved = dedupe_entries(entries)
    assert len(resolved) == 1
    # The senior job wins, and a coordinator carries no specialty.
    assert resolved[0].role is CoachRole.OC
    assert resolved[0].specialty is None


def test_two_ac_listings_keep_the_more_specific_position_group():
    entries = [
        SeedEntry("HOU", "Passing Game Coordinator", "Jerrod", "Johnson", 1_200_000),
        SeedEntry("HOU", "Quarterbacks Coach", "Jerrod", "Johnson", 1_200_000),
    ]
    resolved = dedupe_entries(entries)
    assert len(resolved) == 1
    assert (resolved[0].role, resolved[0].specialty) == (CoachRole.AC, "Quarterbacks")


def test_coach_id_is_stable_across_runs_and_distinct_per_team():
    a = SeedEntry("KC", "Head Coach", "Andy", "Reid", 20_000_000)
    b = SeedEntry("PHI", "Head Coach", "Andy", "Reid", 20_000_000)
    assert coach_id_for(a) == coach_id_for(a)  # deterministic
    assert coach_id_for(a) != coach_id_for(b)  # same name, different staff


def test_reputation_is_a_salary_percentile_within_the_role_tier():
    tier = [500_000, 1_000_000, 2_000_000, 20_000_000]
    assert reputation_from_salary(20_000_000, tier) == 99   # top of the tier
    assert reputation_from_salary(500_000, tier) == 55      # bottom, floored well above 0
    # A tie shares its percentile rather than being ordered arbitrarily.
    assert reputation_from_salary(1_000_000, [1_000_000, 1_000_000]) == 99


def test_the_real_seed_imports_all_32_staffs_with_one_of_each_coordinator():
    entries, errors = parse_seed(DEFAULT_SOURCE.read_text(encoding="utf-8"))
    assert errors == []
    coaches = build_coaches(entries, league_seed=2025)
    assert len({c.team_abbr for c in coaches}) == 32
    for role in (CoachRole.HC, CoachRole.OC, CoachRole.DC):
        assert sum(1 for c in coaches if CoachRole(c.role) is role) == 32, role


def test_generated_profiles_are_deterministic_for_a_given_league_seed():
    """GDD Sec 1.3's Determinism & Seeding Policy: the same LEAGUE_SEED
    must always produce the same staffs, and a different one must not."""
    entries, _ = parse_seed(SAMPLE_SEED)
    a = {c.coach_id: c.blitz_rate for c in build_coaches(entries, league_seed=2025)}
    b = {c.coach_id: c.blitz_rate for c in build_coaches(entries, league_seed=2025)}
    c = {cc.coach_id: cc.blitz_rate for cc in build_coaches(entries, league_seed=99)}
    assert a == b
    assert a != c


# --------------------------------------------------------------------
# StaffEffect -- the sim-facing biases (app/engine/coaching.py)
# --------------------------------------------------------------------

def _coach(role: CoachRole, **overrides) -> Coach:
    """A neutral coach (every slider and rating at a league-average 50)
    so a test only has to state the one field it's actually exercising.

    R16: `focus_area` defaults to plain Development -- play-calling no
    longer reads it at all (Sec 8), so unlike R13 there's no "role's own
    lane" to default into here; a test that cares about focus_area passes
    it explicitly. (An AC's REAL default now requires a real Coach row
    with real ratings -- see default_focus_area_for()'s own tests --
    which this bare neutral helper can't compute for itself.)"""
    fields = dict(
        coach_id=f"test_{role.value.lower()}", first_name="Test", last_name=role.value,
        role=role, team_abbr="TST", salary_aav=1_000_000, reputation=50,
        focus_area=FOCUS_DEVELOPMENT,
    )
    fields.update(overrides)
    return Coach(**fields)


def test_an_empty_staff_produces_exactly_no_bias():
    """The whole backwards-compatibility guarantee rests on this: a
    database with no coaches must simulate precisely as it did before
    coaches existed."""
    effect = coaching.build_staff_effect("TST", [])
    assert effect.pass_bias == 0.0
    assert effect.fourth_down_bias == 0.0
    assert effect.blitz_bias == 0.0
    assert effect.penalty_rate_multiplier == 1.0
    assert effect.man_coverage_prob is None


def test_a_league_average_staff_also_produces_no_bias():
    staff = [_coach(r) for r in (CoachRole.HC, CoachRole.OC, CoachRole.DC, CoachRole.AC)]
    effect = coaching.build_staff_effect("TST", staff)
    assert effect.pass_bias == pytest.approx(0.0)
    assert effect.blitz_bias == pytest.approx(0.0)
    assert effect.penalty_rate_multiplier == pytest.approx(1.0)
    # decide_coverage()'s own default is 40% man -- an average staff must
    # land exactly there, so this system is a per-team lean rather than a
    # league-wide recalibration.
    assert effect.man_coverage_prob == pytest.approx(0.40)


def test_the_ocs_own_tendency_drives_pass_bias_not_the_head_coachs():
    """R16 Sec 8: play-calling is read by ROLE, a deliberate revert of
    R13's focus-gated blend -- the OC's own run_pass_tendency drives
    pass_bias entirely; the HC's value (even wildly different) has zero
    influence, whatever either coach's focus_area happens to be."""
    staff = [
        _coach(CoachRole.HC, run_pass_tendency=0),
        _coach(CoachRole.OC, run_pass_tendency=100),
    ]
    effect = coaching.build_staff_effect("TST", staff)
    assert effect.pass_bias == pytest.approx(coaching.PASS_MIX_SCALE)
    assert effect.pass_bias > 0


def test_a_run_heavy_coordinator_biases_the_other_way():
    staff = [_coach(CoachRole.HC, run_pass_tendency=50), _coach(CoachRole.OC, run_pass_tendency=0)]
    assert coaching.build_staff_effect("TST", staff).pass_bias < 0


def test_coverage_mix_maps_man_heavy_low_and_zone_heavy_high():
    """Sec 7.7.2.2 defines coverage_mix as 0 = man heavy, 100 = zone
    heavy -- so a LOW slider must produce MORE man coverage."""
    man_heavy = coaching.build_staff_effect("TST", [_coach(CoachRole.DC, coverage_mix=0)])
    zone_heavy = coaching.build_staff_effect("TST", [_coach(CoachRole.DC, coverage_mix=100)])
    assert man_heavy.man_coverage_prob > 0.40 > zone_heavy.man_coverage_prob


def test_head_coach_discipline_drives_the_penalty_rate_in_the_right_direction():
    """GDD Sec 7.7.4: "coach discipline modulates team-level penalty
    rates" -- a MORE disciplined staff must commit FEWER penalties."""
    sloppy = coaching.build_staff_effect("TST", [_coach(CoachRole.HC, discipline=0)])
    strict = coaching.build_staff_effect("TST", [_coach(CoachRole.HC, discipline=99)])
    assert sloppy.penalty_rate_multiplier > 1.0 > strict.penalty_rate_multiplier
    assert strict.penalty_rate_multiplier == pytest.approx(coaching.PENALTY_RATE_AT_MAX_DISCIPLINE, abs=0.02)


def test_penalty_rate_is_measured_against_the_league_not_a_hardcoded_50():
    """Regression test for a real calibration bug found during this
    system's first live verification: the generated quality ratings are
    centered on `reputation`, whose league mean is ~70 (it's a salary
    percentile mapped onto 40-99), not 50. Centering on a hardcoded 50
    gave EVERY team a ~0.8x penalty multiplier -- a league-wide shift
    tuning.py and test_stat_realism.py have calibrated, rather than the
    per-team differentiation this system is for. (Player development is
    no longer part of StaffEffect at all -- R16 moved it to a seasonal
    accumulator, app/services/coach_focus_accumulator.py.)"""
    baseline = coaching.LeagueBaseline(discipline=70.0, tendency=50.0)
    average_for_this_league = coaching.build_staff_effect(
        "TST", [_coach(CoachRole.HC, discipline=70)], baseline,
    )
    assert average_for_this_league.penalty_rate_multiplier == pytest.approx(1.0)


    # R16 retired fg_range_bonus and the flat dev_multiplier_offense/
    # defense split from StaffEffect entirely -- Special Teams and Player
    # Development are now Focus Area position-group boosts/accumulator
    # entries instead (app/services/coach_focus_accumulator.py), not
    # per-game coaching-staff biases. No direct replacement test exists
    # here yet; that module needs its own dedicated test coverage.


def test_short_yardage_run_commitment_only_applies_in_short_yardage():
    effect = coaching.build_staff_effect("TST", [_coach(CoachRole.DC, fourth_down_defense=100)])
    assert coaching.defense_run_tactic_extra_penalty(effect, down=3, distance=1) > 0
    assert coaching.defense_run_tactic_extra_penalty(effect, down=3, distance=8) == 0.0
    assert coaching.defense_run_tactic_extra_penalty(effect, down=1, distance=1) == 0.0


def test_none_effect_is_a_no_op_at_every_accessor():
    assert coaching.offense_pass_bias(None, in_red_zone=True) == 0.0
    assert coaching.offense_fourth_down_bias(None) == 0.0
    assert coaching.offense_two_point_bias(None) == 0.0
    assert coaching.defense_blitz_bias(None, in_red_zone=True) == 0.0
    assert coaching.defense_coverage_man_prob(None) is None
    assert coaching.penalty_rate_multiplier(None) == 1.0
    assert coaching.injury_risk_multiplier(None) == 1.0


# --------------------------------------------------------------------
# R16: Focus Area no longer touches play-calling at all (Sec 8) -- a
# deliberate revert of R13's focus-gated blend, replaced by the plain
# role-based read covered above. Focus Area's real effect now (a
# this-game position-group boost + seasonal development) lives in
# app/services/coach_focus_accumulator.py, which needs its own tests.
# --------------------------------------------------------------------

def test_focus_area_has_zero_influence_on_play_calling():
    """The direct regression test for R16 Sec 8's revert: an OC fully
    focused on Scouting (nothing to do with play-calling) still drives
    pass_bias exactly as strongly as one focused on Offensive Gameplan --
    focus_area is irrelevant to this system now, only role and the
    coach's own tendency rating matter."""
    on_gameplan = coaching.build_staff_effect(
        "TST", [_coach(CoachRole.OC, run_pass_tendency=100, focus_area=FOCUS_OFFENSIVE_GAMEPLAN)])
    on_scouting = coaching.build_staff_effect(
        "TST", [_coach(CoachRole.OC, run_pass_tendency=100, focus_area=FOCUS_SCOUTING)])
    assert on_gameplan.pass_bias == pytest.approx(on_scouting.pass_bias)


def test_training_focus_moves_injury_risk_in_the_right_direction():
    """R13 Sec 5.2: a MORE motivated/cohesive Training-focused staff must
    LOWER the team's injury-rate multiplier."""
    lax = coaching.build_staff_effect("TST", [_coach(CoachRole.AC, motivation_chemistry=0, focus_area=FOCUS_TRAINING)])
    sharp = coaching.build_staff_effect("TST", [_coach(CoachRole.AC, motivation_chemistry=99, focus_area=FOCUS_TRAINING)])
    assert lax.injury_risk_multiplier > 1.0 > sharp.injury_risk_multiplier
    assert sharp.injury_risk_multiplier == pytest.approx(coaching.INJURY_RISK_AT_MAX_TRAINING, abs=0.02)


def test_injury_risk_multiplier_measured_against_the_league_not_a_hardcoded_50():
    baseline = coaching.LeagueBaseline(motivation_chemistry=70.0, tendency=50.0)
    effect = coaching.build_staff_effect(
        "TST", [_coach(CoachRole.AC, motivation_chemistry=70, focus_area=FOCUS_TRAINING)], baseline)
    assert effect.injury_risk_multiplier == pytest.approx(1.0)


def test_a_coach_not_focused_on_training_does_not_affect_injury_risk():
    effect = coaching.build_staff_effect(
        "TST", [_coach(CoachRole.AC, motivation_chemistry=99, focus_area=FOCUS_SCOUTING)])
    assert effect.injury_risk_multiplier == pytest.approx(1.0)


def test_default_focus_area_for_gives_hc_oc_dc_their_fixed_role_lane():
    """docs/R16_COACH_POSITION_IMPACT_SPECIFICATION.md Sec 4: HC/OC/DC get
    a fixed role default -- their job description IS that broad lane, not
    a rating to compare against a menu. `coach` is ignored for these
    three roles entirely."""
    assert default_focus_area_for(CoachRole.OC) == FOCUS_OFFENSIVE_GAMEPLAN
    assert default_focus_area_for(CoachRole.DC) == FOCUS_DEFENSIVE_GAMEPLAN
    assert default_focus_area_for(CoachRole.HC) == FOCUS_BALANCED_GAMEPLAN


def test_default_focus_area_for_an_assistant_picks_their_own_best_rating():
    """Sec 4: an AC defaults to whichever of their OWN menu options they
    have the highest real granular rating at -- a QB-coaching standout
    lands on FOCUS_QB even though their other ratings (and Development,
    which has no rating weight at all) are all left at the neutral 50."""
    qb_specialist = _coach(CoachRole.AC, focus_area=FOCUS_DEVELOPMENT, qb_coaching=99)
    from app.models.coach import FOCUS_QB
    assert default_focus_area_for(CoachRole.AC, qb_specialist) == FOCUS_QB

    # An all-neutral coach (every granular rating at the default 50) ties
    # across every rated option -- strict `>` means the FIRST option in
    # the AC menu that beats Development's fixed 0.0 baseline wins the
    # tie (Run Defense, first in FOCUS_OPTIONS_BY_ROLE[AC]), not
    # Development itself: Development only wins if every real rating
    # were somehow at or below 0, which never happens with real data.
    generalist = _coach(CoachRole.AC, focus_area=FOCUS_DEVELOPMENT)
    from app.models.coach import FOCUS_RUN_DEFENSE
    assert default_focus_area_for(CoachRole.AC, generalist) == FOCUS_RUN_DEFENSE


# --------------------------------------------------------------------
# Coach progression / lifecycle (GDD Sec 8.2.2 / 8.2.3)
# --------------------------------------------------------------------

def test_perf_score_matches_the_gdds_own_worked_example():
    """Sec 8.2.2 states PerfScore = (16.5 - Rank) * 0.2 outright."""
    assert coach_progression.perf_score(1) == pytest.approx(3.1)
    assert coach_progression.perf_score(32) == pytest.approx(-3.1)
    assert coach_progression.perf_score(16) == pytest.approx(0.1)


def test_a_top_ranked_team_improves_its_coachs_ratings_and_a_bottom_one_regresses():
    coach = _coach(CoachRole.HC, discipline=50)
    best = coach_progression.progress_coach(
        coach, coach_progression.TeamRanks(penalty_rank=1), season_number=1, league_seed=1)
    worst = coach_progression.progress_coach(
        coach, coach_progression.TeamRanks(penalty_rank=32), season_number=1, league_seed=1)
    assert best.rating_deltas["discipline"] > 0
    assert worst.rating_deltas["discipline"] < 0


def test_a_rating_with_no_real_league_rank_is_left_alone_not_drifted():
    """Sec 8.2.2 ties progression to "the team's statistical rank in
    relevant categories" -- where no such rank exists in this engine, the
    rating must not move on an invented signal."""
    result = coach_progression.progress_coach(
        _coach(CoachRole.HC), coach_progression.TeamRanks(), season_number=1, league_seed=1)
    assert result.rating_deltas == {}


def test_a_head_coach_moves_more_than_an_assistant_on_the_same_result():
    ranks = coach_progression.TeamRanks(penalty_rank=1)
    hc = coach_progression.progress_coach(_coach(CoachRole.HC), ranks, 1, 1)
    ac = coach_progression.progress_coach(_coach(CoachRole.AC), ranks, 1, 1)
    assert hc.rating_deltas["discipline"] > ac.rating_deltas["discipline"] > 0


def test_a_young_coach_never_retires_and_apply_ages_them_by_one():
    coach = _coach(CoachRole.HC, age=45, experience_years=12)
    result = coach_progression.progress_coach(coach, coach_progression.TeamRanks(), 1, 1)
    assert result.retired is False
    coach_progression.apply_coach_progression(coach, result)
    assert coach.age == 46
    assert coach.experience_years == 13


def test_retirement_is_possible_past_65_and_vacates_the_seat():
    """Sec 8.2.3: Retirement % = (Coach Age - 64) * 3, so a very old
    coach retires at some seed. Scanning seeds rather than asserting a
    single one keeps this deterministic without hardcoding which seed
    happens to roll under the threshold."""
    retired_at_some_seed = False
    for seed in range(60):
        coach = _coach(CoachRole.HC, age=79)  # -> 80 after aging, a 48% chance
        result = coach_progression.progress_coach(coach, coach_progression.TeamRanks(), 1, seed)
        if result.retired:
            coach_progression.apply_coach_progression(coach, result)
            assert coach.retired is True
            assert coach.team_abbr is None  # the seat is genuinely vacant now
            retired_at_some_seed = True
            break
    assert retired_at_some_seed


def test_retirement_rolls_identically_for_the_same_league_seed():
    a = coach_progression.progress_coach(_coach(CoachRole.HC, age=70), coach_progression.TeamRanks(), 3, 2025)
    b = coach_progression.progress_coach(_coach(CoachRole.HC, age=70), coach_progression.TeamRanks(), 3, 2025)
    assert a.retired == b.retired


def test_rating_changes_are_capped_and_clamped_to_0_99():
    coach = _coach(CoachRole.HC, discipline=98)
    result = coach_progression.progress_coach(
        coach, coach_progression.TeamRanks(penalty_rank=1), 1, 1)
    assert abs(result.rating_deltas["discipline"]) <= coach_progression.ANNUAL_CAP
    coach_progression.apply_coach_progression(coach, result)
    assert 0 <= coach.discipline <= 99


# --------------------------------------------------------------------
# Job Security Score (GDD Sec 8.2.3)
# --------------------------------------------------------------------

def test_job_security_rewards_winning_and_punishes_losing():
    winning = coach_records.job_security_score(
        win_pct=0.882, playoff_result_score=100.0, owner_patience=50.0)
    losing = coach_records.job_security_score(
        win_pct=0.176, playoff_result_score=0.0, owner_patience=50.0)
    assert winning > losing
    assert 0.0 <= losing <= winning <= 100.0


# --------------------------------------------------------------------
# COTY (GDD Sec 7.4.6)
# --------------------------------------------------------------------

def test_pythagorean_expected_wins_is_symmetric_at_even_scoring():
    assert _pythagorean_expected_wins(400, 400, 17) == pytest.approx(8.5)
    assert _pythagorean_expected_wins(500, 300, 17) > 8.5
    assert _pythagorean_expected_wins(0, 0, 17) == 0.0


def test_rank_norm_puts_the_best_at_one_and_the_worst_at_zero():
    normed = _rank_norm({"A": 10.0, "B": 5.0, "C": 1.0})
    assert normed["A"] == pytest.approx(1.0)
    assert normed["C"] == pytest.approx(0.0)
    assert 0.0 < normed["B"] < 1.0


def test_rank_norm_gives_tied_values_the_same_score():
    normed = _rank_norm({"A": 10.0, "B": 10.0, "C": 1.0})
    assert normed["A"] == normed["B"]


# --------------------------------------------------------------------
# DB-backed: Sec 7.9 championship credit + career accounting
# --------------------------------------------------------------------

@pytest.fixture(scope="module")
def completed_season(tmp_path_factory):
    """ONE isolated, fully-simulated season (regular season + all four
    playoff rounds), shared by every DB-backed test below.

    Module-scoped on purpose: simulating a full season takes ~30s, and
    the four tests here all need the same completed season, so doing it
    once instead of four times keeps this file from adding two minutes
    to every suite run -- the same cost-vs-coverage reasoning
    ROADMAP.md Sec 5.4's test-tiering guidance asks for.

    Copies the real database to a throwaway and redirects
    `app.core.db.DB_PATH`, restoring it in a `finally` no matter what --
    the pattern tests/test_season_rollover.py established, which
    ROADMAP.md Sec 2b's M14 incident note makes mandatory for anything
    that writes to the roster/coach database. (conftest.py's
    session-scoped fixture covers the season-save and power-rank paths
    but deliberately NOT DB_PATH -- see that note for why a global
    redirect would be silently defeated here.)"""
    real_path = db_module.DB_PATH
    throwaway = tmp_path_factory.mktemp("coachdb") / "franchise.db"
    shutil.copy(real_path, throwaway)
    db_module.DB_PATH = throwaway
    db_module._engine = None
    coach_store.clear_cache()
    coaching.clear_cache()
    try:
        season_state.reset_season()
        season_state.set_user_team("KC")
        while not season_state.get_season().is_complete:
            season_state.simulate_current_week()
        regular_season_records = {
            abbr: (r.wins, r.losses) for abbr, r in season_state.get_season().records.items()
        }
        for _ in range(4):
            season_state.simulate_playoff_round()
        yield season_state.get_season(), regular_season_records
    finally:
        db_module.DB_PATH = real_path
        db_module._engine = None
        coach_store.clear_cache()
        coaching.clear_cache()


def test_championship_credit_lands_on_every_role_and_is_idempotent(completed_season):
    """GDD Sec 7.9.2: the winning staff is credited by the role each
    coach held, and re-finalizing the same game must not double-count."""
    season, _ = completed_season
    if not coach_store.has_coaches():
        pytest.skip("this database has no coaches imported")
    champion = season.playoffs.champion_abbr
    assert champion

    coach_store.clear_cache()
    staff = coach_store.staff_for(champion)
    assert staff, "the champion should have a staff"
    for coach in staff:
        assert coach.super_bowl_wins == 1, coach.full_name
        assert coach.conference_titles == 1, coach.full_name
    # Every role tier CURRENTLY STAFFED is represented (Sec 7.9.2's "for
    # each of HC, OC, DC, and all ACs" -- R16 removed ST outright) -- HC
    # is required (the game can't simulate without one), but R3d's real
    # firing/replacement market (ROADMAP.md Sec 4d) can leave a
    # coordinator seat genuinely vacant if a fired coach's replacement
    # search comes up empty, so a missing OC/DC isn't itself a bug to
    # assert against here.
    roles_present = {CoachRole(c.role) for c in staff}
    assert CoachRole.HC in roles_present
    assert roles_present <= {CoachRole.HC, CoachRole.OC, CoachRole.DC, CoachRole.AC}
    # ...and each ring is recorded against the role actually held.
    hc = coach_store.head_coach(champion)
    assert hc.hc_super_bowl_wins == 1
    assert hc.oc_super_bowl_wins == 0

    # Sec 7.9.2's Idempotency clause, asserted directly.
    assert coach_records.credit_championship_round(season, "SB") == 0
    assert coach_records.credit_championship_round(season, "CONF") == 0
    coach_store.clear_cache()
    assert coach_store.head_coach(champion).super_bowl_wins == 1


def test_super_bowl_loser_gets_a_loss_but_no_ring(completed_season):
    season, _ = completed_season
    if not coach_store.has_coaches():
        pytest.skip("this database has no coaches imported")
    sb = [m for r in season.playoffs.rounds for m in r if m.round_name == "SB"][0]
    loser = sb.home_abbr if sb.winner_abbr == sb.away_abbr else sb.away_abbr

    coach_store.clear_cache()
    loser_hc = coach_store.head_coach(loser)
    assert loser_hc.super_bowl_wins == 0
    rows = coach_records.season_history(loser_hc.coach_id)
    assert any(r.super_bowl_result == "LOSS" for r in rows)


def test_season_results_roll_into_career_totals_exactly_once(completed_season):
    season, regular_season_records = completed_season
    if not coach_store.has_coaches():
        pytest.skip("this database has no coaches imported")
    coach_records.record_season_results(season)
    coach_store.clear_cache()
    hc = coach_store.head_coach("KC")
    wins, losses = regular_season_records["KC"]
    assert (hc.career_wins, hc.career_losses) == (wins, losses)
    assert hc.seasons_coached == 1

    # A second call for the same season must not double-count.
    coach_records.record_season_results(season)
    coach_store.clear_cache()
    hc = coach_store.head_coach("KC")
    assert (hc.career_wins, hc.career_losses) == (wins, losses)
    assert hc.seasons_coached == 1


def test_coach_of_the_year_ranks_a_real_season(completed_season):
    season, _ = completed_season
    if not coach_store.has_coaches():
        pytest.skip("this database has no coaches imported")
    race = coach_of_the_year(season, top_n=5)
    assert len(race) == 5
    assert race == sorted(race, key=lambda c: (-c.score, c.name))
    # The winner should be a genuinely strong team, not an arbitrary
    # one: Wins carries the single largest weight in Sec 7.4.6.
    best_wins = max(r.wins for r in season.records.values())
    assert season.records[race[0].team_abbr].wins >= best_wins - 3
    assert all(c.stat_line for c in race)


def test_coach_of_the_year_is_empty_rather_than_fabricated_without_coaches(monkeypatch):
    monkeypatch.setattr(coach_store, "all_coaches", lambda: ())
    season = season_state.get_season()
    assert coach_of_the_year(season) == []

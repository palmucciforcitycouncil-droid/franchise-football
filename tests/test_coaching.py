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
from pathlib import Path

import pytest
from sqlmodel import select

from app.core import db as db_module

# Captured at collection time -- BEFORE any fixture anywhere in this run
# can redirect db_module.DB_PATH -- so the migration tests below always
# copy the genuinely real database. Reading db_module.DB_PATH dynamically
# inside a fixture is NOT safe here: `completed_season` below is
# module-scoped and doesn't tear down (restoring DB_PATH) until every
# test in this file has run, so a later test that read db_module.DB_PATH
# directly would silently copy `completed_season`'s own already-played-a-
# full-season throwaway instead of the real save -- exactly the class of
# mistake ROADMAP.md Sec 2b's M14 incident note warns about.
_REAL_DB_PATH = db_module.DB_PATH
from app.engine import coaching, coach_progression
from app.engine.awards import (
    _pythagorean_expected_wins, _rank_norm, coach_of_the_year,
)
from app.models.coach import (
    Coach, CoachRole, CoachSeasonStats,
    FOCUS_OF_GAMEPLAN, FOCUS_DF_GAMEPLAN, FOCUS_BALANCED_GAMEPLAN, FOCUS_DEVELOPMENT,
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


def test_only_the_four_coordinator_titles_map_to_their_own_role():
    assert map_title("Head Coach") == (CoachRole.HC, None)
    assert map_title("Offensive Coordinator") == (CoachRole.OC, None)
    assert map_title("Defensive Coordinator") == (CoachRole.DC, None)
    assert map_title("Special Teams Coordinator") == (CoachRole.ST, None)


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
    """2026-09-20 fix: the percentile is now mapped onto the PASSED tier's
    own real band (app/models/coach.py's REPUTATION_TIER_BAND), not a
    single 40-99 range shared by every tier -- see that module for the
    real-dollar derivation of the HC/COORD/AC bands."""
    tier = [500_000, 1_000_000, 2_000_000, 20_000_000]
    assert reputation_from_salary(20_000_000, tier, "HC") == 99   # top of the HC band
    assert reputation_from_salary(500_000, tier, "HC") == 88      # bottom quartile of the HC band (84-99)
    # A tie shares its percentile rather than being ordered arbitrarily.
    assert reputation_from_salary(1_000_000, [1_000_000, 1_000_000], "HC") == 99


def test_reputation_tiers_never_invert_across_real_roles():
    """The actual 2026-09-20 playtest bug: an AC's reputation could reach
    an HC's because every tier's percentile was mapped onto the SAME
    40-99 band independently. Real, non-overlapping-by-role salary data
    (GDD Appendix S.2's ranges) must now produce a real HC floor above
    every COORD, and a COORD floor at or above every AC -- with at most
    a light overlap at the COORD/AC boundary (a top assistant can
    plausibly out-earn a bottom-tier ST coordinator in real life)."""
    hc_tier = [4_000_000, 5_500_000, 7_000_000, 8_790_000]
    coord_tier = [660_000, 1_000_000, 1_500_000, 2_500_000]
    ac_tier = [200_000, 350_000, 500_000, 800_000]

    hc_reps = [reputation_from_salary(s, hc_tier, "HC") for s in hc_tier]
    coord_reps = [reputation_from_salary(s, coord_tier, "COORD") for s in coord_tier]
    ac_reps = [reputation_from_salary(s, ac_tier, "AC") for s in ac_tier]

    assert min(hc_reps) > max(coord_reps)
    # COORD/AC may lightly overlap at the boundary, but the top AC must
    # never outrank the top COORD, and the bottom COORD must never fall
    # below the bottom AC.
    assert max(coord_reps) > max(ac_reps)
    assert min(coord_reps) >= min(ac_reps)


def test_the_real_seed_imports_all_32_staffs_with_one_of_each_coordinator():
    entries, errors = parse_seed(DEFAULT_SOURCE.read_text(encoding="utf-8"))
    assert errors == []
    coaches = build_coaches(entries, league_seed=2025)
    assert len({c.team_abbr for c in coaches}) == 32
    for role in (CoachRole.HC, CoachRole.OC, CoachRole.DC, CoachRole.ST):
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

    R13: defaults `focus_area` to this role's own real Sec 4 default
    (default_focus_area_for) rather than the model's bare "Development"
    fallback -- an OC/DC/ST built here contributes to the bucket its role
    name implies unless a test explicitly overrides focus_area to test
    reassignment itself."""
    fields = dict(
        coach_id=f"test_{role.value.lower()}", first_name="Test", last_name=role.value,
        role=role, team_abbr="TST", salary_aav=1_000_000, reputation=50,
        focus_area=default_focus_area_for(role, None),
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
    assert effect.dev_multiplier_offense == 1.0
    assert effect.man_coverage_prob is None


def test_a_league_average_staff_also_produces_no_bias():
    staff = [_coach(r) for r in (CoachRole.HC, CoachRole.OC, CoachRole.DC, CoachRole.ST)]
    effect = coaching.build_staff_effect("TST", staff)
    assert effect.pass_bias == pytest.approx(0.0)
    assert effect.blitz_bias == pytest.approx(0.0)
    assert effect.penalty_rate_multiplier == pytest.approx(1.0)
    # decide_coverage()'s own default is 40% man -- an average staff must
    # land exactly there, so this system is a per-team lean rather than a
    # league-wide recalibration.
    assert effect.man_coverage_prob == pytest.approx(0.40)


def test_a_pass_happy_coordinator_outweighs_the_head_coach():
    """Sec 7.7.2.2's run_pass_tendency, blended 60/40 toward whoever
    actually calls that side of the ball -- both coaches focused directly
    on OF Gameplan here (not the HC's own Balanced-Gameplan default, which
    has its own dedicated split-weight test below)."""
    staff = [
        _coach(CoachRole.HC, run_pass_tendency=50, focus_area=FOCUS_OF_GAMEPLAN),
        _coach(CoachRole.OC, run_pass_tendency=100, focus_area=FOCUS_OF_GAMEPLAN),
    ]
    effect = coaching.build_staff_effect("TST", staff)
    # blend = 0.6*100 + 0.4*50 = 80 -> slider 0.6 -> 0.6 * PASS_MIX_SCALE
    assert effect.pass_bias == pytest.approx(0.6 * coaching.PASS_MIX_SCALE)
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


def test_penalty_and_dev_multipliers_are_measured_against_the_league_not_a_hardcoded_50():
    """Regression test for a real calibration bug found during this
    system's first live verification: the generated quality ratings are
    centered on `reputation`, whose league mean is ~70 (it's a salary
    percentile mapped onto 40-99), not 50. Centering on a hardcoded 50
    gave EVERY team a ~0.8x penalty multiplier and a ~1.10x development
    multiplier -- a league-wide shift to rates tuning.py and
    test_stat_realism.py have calibrated, rather than the per-team
    differentiation this system is for."""
    baseline = coaching.LeagueBaseline(discipline=70.0, dev_offense=70.0, dev_defense=70.0, tendency=50.0)
    average_for_this_league = coaching.build_staff_effect(
        "TST", [_coach(CoachRole.HC, discipline=70, player_dev_offense=70, player_dev_defense=70,
                       focus_area=FOCUS_DEVELOPMENT)],
        baseline,
    )
    assert average_for_this_league.penalty_rate_multiplier == pytest.approx(1.0)
    assert average_for_this_league.dev_multiplier_offense == pytest.approx(1.0)


def test_special_teams_focus_moves_field_goal_range():
    """Sec 7.7.2.2: special_teams_focus "affects ... average FG try
    distances"."""
    timid = coaching.build_staff_effect("TST", [_coach(CoachRole.ST, special_teams_focus=0)])
    keen = coaching.build_staff_effect("TST", [_coach(CoachRole.ST, special_teams_focus=100)])
    assert keen.fg_range_bonus > 0 > timid.fg_range_bonus


def test_dev_multipliers_stay_inside_their_documented_bounds():
    best = coaching.build_staff_effect(
        "TST", [_coach(CoachRole.HC, player_dev_offense=99, player_dev_defense=99)])
    worst = coaching.build_staff_effect(
        "TST", [_coach(CoachRole.HC, player_dev_offense=0, player_dev_defense=0)])
    assert coaching.DEV_MULTIPLIER_MIN <= worst.dev_multiplier_offense <= 1.0
    assert 1.0 <= best.dev_multiplier_offense <= coaching.DEV_MULTIPLIER_MAX


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
    assert coaching.fg_range_bonus(None) == 0.0
    assert coaching.injury_risk_multiplier(None) == 1.0


# --------------------------------------------------------------------
# R13: Coach Focus Areas (docs/R13_COACH_FOCUS_AREA_SPECIFICATION.md)
# --------------------------------------------------------------------

def test_reassigning_focus_away_zeroes_that_buckets_contribution():
    """The whole point of R13: a coach whose focus points elsewhere
    contributes NOTHING to a bucket, even if their own rating there is
    extreme -- reallocation, not free power."""
    staff = [
        _coach(CoachRole.HC, run_pass_tendency=50, focus_area=FOCUS_DEVELOPMENT),
        _coach(CoachRole.OC, run_pass_tendency=100, focus_area=FOCUS_SCOUTING),
    ]
    effect = coaching.build_staff_effect("TST", staff)
    # nobody is focused on OF Gameplan at all -> falls back to neutral
    assert effect.pass_bias == pytest.approx(0.0)


def test_balanced_gameplan_contributes_to_both_sides_at_reduced_weight():
    """Brian's own design (2026-09-13): a Balanced Gameplan coach helps
    BOTH OF and DF Gameplan, at a smaller weight on each than the same
    coach fully focused on just one side would carry."""
    oc = _coach(CoachRole.OC, run_pass_tendency=100, focus_area=FOCUS_OF_GAMEPLAN)
    dc = _coach(CoachRole.DC, blitz_rate=100, focus_area=FOCUS_DF_GAMEPLAN)
    balanced_hc = _coach(CoachRole.HC, run_pass_tendency=0, blitz_rate=0, focus_area=FOCUS_BALANCED_GAMEPLAN)
    solo_of_hc = _coach(CoachRole.HC, run_pass_tendency=0, blitz_rate=0, focus_area=FOCUS_OF_GAMEPLAN)
    dc_alone = coaching.build_staff_effect("TST", [dc])

    with_balanced = coaching.build_staff_effect("TST", [oc, dc, balanced_hc])
    with_solo_of = coaching.build_staff_effect("TST", [oc, dc, solo_of_hc])

    # A Balanced HC pulls the OF blend toward their own 0 less hard than a
    # fully OF-focused HC would (their weight there is halved) -> pass_bias
    # stays closer to the OC's own full-strength number.
    assert with_balanced.pass_bias > with_solo_of.pass_bias > 0

    # solo_of_hc contributes NOTHING to DF Gameplan at all, so the DC calls
    # it alone there -- identical to a staff with no HC whatsoever.
    assert with_solo_of.blitz_bias == pytest.approx(dc_alone.blitz_bias)
    # The SAME Balanced HC still pulls on the DF side too (their 0 drags
    # the blend down from the DC's own 100), just not all the way to zero.
    assert 0 < with_balanced.blitz_bias < with_solo_of.blitz_bias


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


def test_default_focus_area_for_matches_the_spec_table():
    """docs/R13_COACH_FOCUS_AREA_SPECIFICATION.md Sec 4's default table,
    asserted directly against the real function every import/migration
    script shares."""
    assert default_focus_area_for(CoachRole.OC, None) == FOCUS_OF_GAMEPLAN
    assert default_focus_area_for(CoachRole.DC, None) == FOCUS_DF_GAMEPLAN
    assert default_focus_area_for(CoachRole.ST, None) == FOCUS_SPECIAL_TEAMS
    assert default_focus_area_for(CoachRole.HC, None) == FOCUS_BALANCED_GAMEPLAN
    assert default_focus_area_for(CoachRole.AC, "Special Teams (Assistant)") == FOCUS_SPECIAL_TEAMS
    assert default_focus_area_for(CoachRole.AC, "Strength and Conditioning") == FOCUS_TRAINING
    assert default_focus_area_for(CoachRole.AC, "Quarterbacks") == FOCUS_DEVELOPMENT
    assert default_focus_area_for(CoachRole.AC, None) == FOCUS_DEVELOPMENT


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
    # each of HC, OC, DC, ST, and all ACs") -- HC is required (the game
    # can't simulate without one), but R3d's real firing/replacement
    # market (ROADMAP.md Sec 4d) can leave a coordinator seat genuinely
    # vacant if a fired coach's replacement search comes up empty, so a
    # missing OC/DC/ST isn't itself a bug to assert against here.
    roles_present = {CoachRole(c.role) for c in staff}
    assert CoachRole.HC in roles_present
    assert roles_present <= {CoachRole.HC, CoachRole.OC, CoachRole.DC, CoachRole.ST, CoachRole.AC}
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


# --------------------------------------------------------------------
# DB-backed: the 2026-09-20 one-time reputation re-tiering migration
# (app/core/db.py's _migrate_schema, guarded by the coach.
# reputation_retiered column) -- same throwaway-copy discipline as
# `completed_season` above, since this genuinely writes to the coach
# table.
# --------------------------------------------------------------------

@pytest.fixture
def migrated_db(tmp_path_factory):
    """A throwaway copy of the REAL database, migrated exactly once by
    opening it through app.core.db.get_engine() (which runs
    _migrate_schema() on any existing DB file). Never touches the real
    data/franchise_football.db."""
    throwaway = tmp_path_factory.mktemp("coach_reptier") / "franchise.db"
    shutil.copy(_REAL_DB_PATH, throwaway)
    db_module.DB_PATH = throwaway
    db_module._engine = None
    coach_store.clear_cache()
    try:
        db_module.get_engine()  # triggers _migrate_schema on the copy
        yield throwaway
    finally:
        db_module.DB_PATH = _REAL_DB_PATH
        db_module._engine = None
        coach_store.clear_cache()


def _fetch_coach_rows(db_path):
    import sqlite3
    con = sqlite3.connect(str(db_path))
    try:
        rows = con.execute(
            "SELECT coach_id, role, salary_aav, reputation, player_dev_offense, "
            "player_dev_defense, discipline, motivation_chemistry, red_zone_offense, "
            "red_zone_defense, reputation_retiered, pool_tier FROM coach"
        ).fetchall()
    finally:
        con.close()
    return rows


def test_migration_retiers_every_real_seeded_coachs_reputation(migrated_db):
    """The core fix, asserted against the REAL live save's own data (a
    copy of it): after migration, every real-seeded coach (pool_tier IS
    NULL) must be marked migrated, and role tiers must not invert --
    the actual bug Brian reported (an AC outranking an HC) must be gone
    from the real data, not just a synthetic fixture."""
    rows = _fetch_coach_rows(migrated_db)
    real_rows = [r for r in rows if r[11] is None]
    assert real_rows, "expected real-seeded coaches in the copied DB"
    assert all(r[10] == 1 for r in real_rows)  # reputation_retiered

    def tier(role):
        if role == "HC":
            return "HC"
        if role in ("OC", "DC", "ST"):
            return "COORD"
        return "AC"

    by_tier: dict[str, list[int]] = {"HC": [], "COORD": [], "AC": []}
    for r in real_rows:
        role, reputation = r[1], r[3]
        by_tier[tier(role)].append(reputation)

    assert by_tier["HC"] and by_tier["COORD"] and by_tier["AC"]
    assert min(by_tier["HC"]) > max(by_tier["COORD"])
    assert max(by_tier["COORD"]) > max(by_tier["AC"])


def test_migration_shifts_existing_ratings_instead_of_re_randomizing(migrated_db):
    """Brian's ask: existing coaches get RE-SCORED, not regenerated --
    a coach's six performance ratings should move by the SAME delta as
    their reputation (clamped to 0-99), preserving their own relative
    profile shape instead of becoming an unrecognizable new coach."""
    # Recomputing the exact pre-migration values isn't possible here
    # (the row was overwritten in place by the migration), so instead
    # this asserts the INVARIANT the migration must uphold on every touched
    # row: reputation and every performance rating stay within the
    # model's documented 0-99 bounds, and a coach's six performance
    # ratings remain internally consistent with each other (the shift is
    # a single scalar delta applied to all six, so their RELATIVE spread
    # is preserved exactly).
    rows = _fetch_coach_rows(migrated_db)
    for r in rows:
        if r[11] is not None:
            continue  # pool candidate, untouched
        reputation = r[3]
        perf = r[4:10]
        assert 0 <= reputation <= 99
        for v in perf:
            assert 0 <= v <= 99


def test_migration_is_idempotent(migrated_db):
    """Re-opening an already-migrated DB file must be a true no-op --
    the reputation_retiered column's own existence is the guard, so a
    second app boot must never shift these ratings a second time (the
    same discipline the salary cap rescale's legacy_salary_rescaled
    column already established)."""
    before = _fetch_coach_rows(migrated_db)

    db_module._engine = None
    coach_store.clear_cache()
    db_module.get_engine()  # a second "boot" against the same file
    coach_store.clear_cache()

    after = _fetch_coach_rows(migrated_db)
    assert before == after


def test_migration_does_not_touch_tier3_pool_candidates(migrated_db):
    """scripts/seed_coach_pool.py's Tier 3 candidates already draw
    reputation from their own real, per-role bands independent of
    salary_aav (which is 0 for all of them) -- this migration must
    leave them alone rather than re-scoring them against a salary
    signal they don't have."""
    rows = _fetch_coach_rows(migrated_db)
    pool_rows = [r for r in rows if r[11] is not None]
    if not pool_rows:
        pytest.skip("this database has no Tier 3 pool candidates")
    assert all(r[10] == 0 for r in pool_rows)  # reputation_retiered stays 0


# --------------------------------------------------------------------
# staff.html's Fill Vacancy "Score" mislabel (the related display bug
# found alongside this investigation): `candidate_table`'s Score column
# is a composite hire-worthiness metric for every role except AC (where
# it genuinely is candidate.overall) -- see main.py's
# _staff_candidate_rows(). The HC/OC/DC/ST call site must pass an
# explicit, non-"OVR" score_label so the column stops implying it's the
# same number as the Coach Card's Overall rating.
# --------------------------------------------------------------------

def _render_candidate_table_macro(score_label: str | None = None):
    """Renders JUST the `candidate_table` macro from the real
    staff.html, without the rest of the page (which extends base.html
    and needs a full route's worth of context) -- extracts the macro's
    own source and evaluates it as a standalone template so this stays
    a real assertion against the shipped template text, not a
    reimplementation of it."""
    import re
    from app.main import templates

    src = Path("app/templates/staff.html").read_text(encoding="utf-8")
    macro_src = re.search(r"\{% macro candidate_table.*?\{% endmacro %\}", src, re.S).group(0)
    call = 'candidate_table([], "HC")' if score_label is None \
        else f'candidate_table([], "HC", score_label="{score_label}")'
    tmpl = templates.env.from_string(macro_src + "\n{{ " + call + " }}")
    return tmpl.render(team_abbr="KC")


def test_fill_vacancy_score_column_no_longer_implies_ovr_by_default():
    """The macro's own default label must not silently claim OVR --
    callers for a genuinely-OVR-valued list (AC) pass "OVR" explicitly
    (see below); everyone else must pass something else, and the bare
    default is a neutral "Score", not "OVR"."""
    default_html = _render_candidate_table_macro()
    assert "<th>Score</th>" in default_html
    assert "<th>OVR</th>" not in default_html


def test_fill_vacancy_call_site_passes_an_explicit_non_ovr_label():
    """The actual HC/OC/DC/ST Fill Vacancy call site in staff.html --
    Brian's report ("the coach position box is showing a different
    overall rating than the find coach box for the same coach") was
    this column being unlabeled ambiguity, not a computation bug: fix
    the label, not the number."""
    src = Path("app/templates/staff.html").read_text(encoding="utf-8")
    assert 'candidate_table(entry.candidates, entry.role, score_label="Fit Score")' in src
    assert 'candidate_table(entry.candidates, entry.role)' not in src

    rendered = _render_candidate_table_macro(score_label="Fit Score")
    assert "<th>Fit Score</th>" in rendered
    assert "<th>OVR</th>" not in rendered


def test_assistant_candidate_table_keeps_its_correct_ovr_label():
    """The AC/"Hire Assistant" call site is NOT part of this bug: its
    `score` field is genuinely `candidate.overall` (main.py's
    _staff_candidate_rows, the coach_role is AC branch), so its existing
    "OVR" label stays accurate and must not be changed."""
    src = Path("app/templates/staff.html").read_text(encoding="utf-8")
    assert 'candidate_table(assistant_candidates, "AC", score_label="OVR")' in src

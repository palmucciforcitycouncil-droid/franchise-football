"""
Contracts / Salary Cap / Negotiation tests (ROADMAP.md R4a; GDD Part 1
Sec 8.3). Style follows this suite's existing convention: hand-built
Player fixtures, exact/directional expected values for the pure
functions -- see app/engine/contracts.py's own module docstring for the
real, disclosed scope cuts from the GDD's fuller design.
"""
from __future__ import annotations

import pytest

from app.engine import contracts
from app.models.player import Player, Position


def _player(position: Position, overall: int, player_id: str, age: int = 26,
            years_pro: int = 4, salary: int = 5_000_000, team_abbr: str = "ZZ") -> Player:
    return Player(
        player_id=player_id, first_name="Test", last_name=player_id, position=position,
        team_abbr=team_abbr, age=age, overall_rating=overall, potential=overall, morale=70,
        years_pro=years_pro, salary=salary,
        speed=70, acceleration=70, strength=70, agility=70, jumping=70, stamina=70,
        toughness=70, durability=70, throw_power=70, throw_accuracy_short=70,
        throw_accuracy_mid=70, throw_accuracy_deep=70, play_action=70, throw_on_the_run=70,
        throw_under_pressure=70, break_sack=70, catching=70, spectacular_catch=70,
        catch_in_traffic=70, short_route_running=70, medium_route_running=70,
        deep_route_running=70, release=70, carrying=70, trucking=70, change_of_direction=70,
        ball_carrier_vision=70, stiff_arm=70, spin_move=70, juke_move=70, break_tackle=70,
        run_block=70, pass_block=70, run_block_power=70, run_block_finesse=70,
        pass_block_power=70, pass_block_finesse=70, lead_block=70, impact_blocking=70,
        tackle=70, hit_power=70, block_shedding=70, pursuit=70, play_recognition=70,
        man_coverage=70, zone_coverage=70, press=70, power_moves=70, finesse_moves=70,
        kick_power=70, kick_accuracy=70, kick_return=70, awareness=70,
    )


def test_salary_cap_grows_75_percent_per_season():
    # Updated 2026-09-12: the real-world growth rate was corrected from
    # 11.2% (2025's stale figure) to 7.5% (real 2026 rate) -- see
    # contracts.py's own SALARY_CAP_GROWTH comment.
    cap0 = contracts.salary_cap_for_season(24)  # 2026 -- pre-2026 seasons are clamped to the anchor
    cap1 = contracts.salary_cap_for_season(25)
    assert cap1 == pytest.approx(cap0 * 1.075)


def test_veteran_minimum_rises_with_years_of_service():
    rookie_min = contracts.veteran_minimum(years_pro=0, season_number=0)
    vet_min = contracts.veteran_minimum(years_pro=8, season_number=0)
    assert vet_min > rookie_min


def test_team_cap_space_is_cap_minus_committed_salaries():
    roster = [
        _player(Position.QB, 90, "qb1", salary=30_000_000),
        _player(Position.WR, 80, "wr1", salary=15_000_000),
    ]
    space = contracts.team_cap_space(roster, season_number=0)
    expected = contracts.salary_cap_for_season(0) - 45_000_000
    assert space == expected


def test_a_higher_overall_qb_has_a_higher_expected_value_than_a_lower_overall_one():
    star = _player(Position.QB, 95, "star_qb")
    backup = _player(Position.QB, 65, "backup_qb")
    assert contracts.expected_market_value(star, 0) > contracts.expected_market_value(backup, 0)


def test_qb_is_worth_more_than_a_kicker_at_the_same_overall_and_age():
    """Directly exercises the A1/A3 synergy: expected_market_value scales
    by roster_strength.POSITION_WEIGHTS, so a QB and a K at identical OVR
    should NOT be paid the same -- the entire point of reusing that
    already-tuned number instead of a second, disconnected one."""
    qb = _player(Position.QB, 80, "qb1")
    k = _player(Position.K, 80, "k1")
    assert contracts.expected_market_value(qb, 0) > contracts.expected_market_value(k, 0)


def test_expected_value_never_drops_below_the_veteran_minimum():
    scrub = _player(Position.P, 40, "scrub", age=38, years_pro=1)
    value = contracts.expected_market_value(scrub, 0)
    assert value >= contracts.veteran_minimum(scrub.years_pro, 0)


def test_a_generous_offer_is_accepted():
    player = _player(Position.WR, 80, "wr1")
    expected = contracts.expected_market_value(player, 0)
    result = contracts.evaluate_offer(player, offered_aav=expected * 1.2, offered_years=5,
                                       season_number=0, team_rating=90.0)
    assert result.verdict == contracts.OfferVerdict.ACCEPT


def test_a_lowball_offer_is_rejected_or_countered_never_accepted():
    player = _player(Position.WR, 80, "wr1")
    expected = contracts.expected_market_value(player, 0)
    result = contracts.evaluate_offer(player, offered_aav=expected * 0.3, offered_years=1,
                                       season_number=0, team_rating=50.0)
    assert result.verdict != contracts.OfferVerdict.ACCEPT


def test_a_counter_offer_names_terms_that_would_actually_clear_acceptance():
    player = _player(Position.WR, 80, "wr1")
    expected = contracts.expected_market_value(player, 0)
    result = contracts.evaluate_offer(player, offered_aav=expected * 0.85, offered_years=3,
                                       season_number=0, team_rating=70.0)
    assert result.verdict == contracts.OfferVerdict.COUNTER
    assert result.counter_aav is not None
    # The countered terms, resubmitted, should now clear ACCEPT.
    re_result = contracts.evaluate_offer(player, offered_aav=result.counter_aav, offered_years=result.counter_years,
                                          season_number=0, team_rating=70.0)
    assert re_result.verdict == contracts.OfferVerdict.ACCEPT


def test_a_better_team_rating_makes_the_same_offer_more_likely_to_clear():
    player = _player(Position.WR, 80, "wr1")
    expected = contracts.expected_market_value(player, 0)
    weak_team = contracts.evaluate_offer(player, expected * 0.9, 3, 0, team_rating=50.0)
    strong_team = contracts.evaluate_offer(player, expected * 0.9, 3, 0, team_rating=95.0)
    assert strong_team.offer_score > weak_team.offer_score


# --- guaranteed money's real effect on acceptance (Brian's ask, 2026-09-13) -------------

def test_an_unguaranteed_offer_scores_identically_to_before_the_bonus_existed():
    """The whole point of making the bonus additive rather than a 4th
    weight: offered_guaranteed=0 (the default) must not silently make
    every existing offer harder to clear than it used to be."""
    player = _player(Position.WR, 80, "wr1")
    expected = contracts.expected_market_value(player, 0)
    explicit_zero = contracts.evaluate_offer(player, expected * 0.85, 3, 0, team_rating=70.0, offered_guaranteed=0.0)
    default_omitted = contracts.evaluate_offer(player, expected * 0.85, 3, 0, team_rating=70.0)
    assert explicit_zero.offer_score == default_omitted.offer_score


def test_more_guaranteed_money_raises_the_offer_score():
    player = _player(Position.WR, 80, "wr1")
    expected = contracts.expected_market_value(player, 0)
    aav, years = expected * 0.85, 3
    unguaranteed = contracts.evaluate_offer(player, aav, years, 0, team_rating=70.0, offered_guaranteed=0.0)
    fully_guaranteed = contracts.evaluate_offer(player, aav, years, 0, team_rating=70.0, offered_guaranteed=aav * years)
    assert fully_guaranteed.offer_score > unguaranteed.offer_score


def test_enough_guaranteed_money_can_turn_a_counter_into_an_accept():
    """A borderline offer just short of ACCEPT_THRESHOLD on AAV/years/
    team-quality alone -- real guaranteed money on top should be able to
    close that real, if small, gap."""
    player = _player(Position.WR, 80, "wr1")
    expected = contracts.expected_market_value(player, 0)
    aav, years = expected * 0.93, 4
    baseline = contracts.evaluate_offer(player, aav, years, 0, team_rating=90.0)
    assert baseline.verdict == contracts.OfferVerdict.COUNTER

    guaranteed_result = contracts.evaluate_offer(player, aav, years, 0, team_rating=90.0, offered_guaranteed=aav * years)
    assert guaranteed_result.verdict == contracts.OfferVerdict.ACCEPT

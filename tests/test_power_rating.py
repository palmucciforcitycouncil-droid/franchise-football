"""
Tests for app.engine.power_rating -- the Elo-based Team Power Rating
system (GDD Part 1 Sec 7.2) feeding the Score Fidelity System's pre-game
win probability and parity/upset model.
"""
from app.engine import power_rating as pr


def test_higher_rating_and_home_field_both_increase_win_probability():
    even = pr.home_win_probability(1500, 5, 10, 1500, 5, 10, current_week=5)
    assert even > 0.5  # home field advantage alone tilts an even matchup

    favored_home = pr.home_win_probability(1650, 5, 10, 1500, 5, 10, current_week=5)
    assert favored_home > even


def test_parity_adjustment_only_applies_after_week_10_to_extreme_records():
    # Before week 10: no adjustment even for a perfect or winless record.
    assert pr.parity_adjusted_rating(1600, wins=9, games_played=9, current_week=9) == 1600
    assert pr.parity_adjusted_rating(1400, wins=0, games_played=9, current_week=9) == 1400

    # After week 10: perfect record gets penalized, winless gets boosted.
    assert pr.parity_adjusted_rating(1600, wins=10, games_played=10, current_week=11) == 1600 - pr.PARITY_ADJUSTMENT
    assert pr.parity_adjusted_rating(1400, wins=0, games_played=10, current_week=11) == 1400 + pr.PARITY_ADJUSTMENT

    # After week 10 but not an extreme record: still no adjustment.
    assert pr.parity_adjusted_rating(1550, wins=6, games_played=10, current_week=11) == 1550


def test_update_ratings_is_zero_sum_and_rewards_the_winner():
    home_new, away_new = pr.update_ratings(1500, 1500, home_score=27, away_score=10)
    assert home_new > 1500
    assert away_new < 1500
    assert round(home_new + away_new, 6) == 3000  # zero-sum: what one gains, the other loses


def test_update_ratings_dampens_a_blowout_by_a_big_favorite():
    """A big favorite (1700) blowing out a big underdog (1300) should move
    ratings less than the same margin between evenly-matched teams -- the
    result was already expected, so it's less informative."""
    home_new_even, away_new_even = pr.update_ratings(1500, 1500, home_score=35, away_score=7)
    home_new_favorite, _ = pr.update_ratings(1700, 1300, home_score=35, away_score=7)

    even_delta = home_new_even - 1500
    favorite_delta = home_new_favorite - 1700
    assert 0 < favorite_delta < even_delta


def test_update_ratings_ties_produce_no_change():
    home_new, away_new = pr.update_ratings(1500, 1500, home_score=20, away_score=20)
    assert home_new == 1500
    assert away_new == 1500


def test_regress_to_mean_pulls_toward_baseline():
    assert pr.regress_to_mean(1700) == 0.67 * 1700 + 0.33 * pr.INITIAL_RATING
    assert pr.regress_to_mean(pr.INITIAL_RATING) == pr.INITIAL_RATING


# --- Power RANKING order: rating + record anchor (2026-09-14) -------------

def test_record_anchor_is_zero_before_any_games_and_symmetric_around_500():
    assert pr.record_anchor_bonus(0, 0) == 0.0
    assert pr.record_anchor_bonus(8, 8) == 0.0
    assert pr.record_anchor_bonus(12, 4) == -pr.record_anchor_bonus(4, 12)


def test_record_anchor_grows_with_games_played():
    early = pr.record_anchor_bonus(1, 0)
    late = pr.record_anchor_bonus(15, 0)
    assert 0 < early < late


def test_late_season_11_4_outranks_8_7_despite_a_moderate_rating_edge():
    # Brian's screenshot (~Week 16): an 8-7 team ranked above an 11-4 team.
    eight_seven = pr.power_score(1620, 8, 7)
    eleven_four = pr.power_score(1550, 11, 4)
    assert eleven_four > eight_seven


def test_extreme_strength_gap_can_still_beat_record_late():
    # Strength still matters: a far stronger 8-7 team isn't forced below.
    assert pr.power_score(1800, 8, 7) > pr.power_score(1500, 11, 4)


def test_early_season_rankings_stay_driven_by_strength():
    # Week 2: a 0-1 team with a real 60-point rating edge stays ahead of a 1-0 team.
    assert pr.power_score(1560, 0, 1) > pr.power_score(1500, 1, 0)


def test_power_score_does_not_change_the_rating_used_by_the_sim():
    # Additive display/ranking key only -- win probability still reads raw ratings.
    assert pr.home_win_probability(1500, 11, 15, 1500, 4, 15, current_week=16) == \
        pr.home_win_probability(1500, 0, 15, 1500, 15, 15, current_week=5)

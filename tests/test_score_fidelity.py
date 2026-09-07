"""
Tests for app.engine.score_fidelity -- the Score Fidelity System's
EP-anchoring multiplier and weekly feedback loop (GDD Part 1 Sec 6.2,
adapted to this engine's player-attribute-driven architecture; see that
module's docstring for the full list of scope cuts and why).
"""
from app.engine.rng import RNG
from app.engine import score_fidelity as sf


def test_ep_multiplier_favors_the_favorite_on_average():
    """A single draw is noisy (GAME_VARIANCE_SIGMA), so average many
    draws with different RNG seeds to see the real win-probability signal
    through the per-game noise."""
    favorite_avg = sum(sf.ep_multiplier(RNG.with_seed(i), 0.85, True, 1.0) for i in range(500)) / 500
    underdog_avg = sum(sf.ep_multiplier(RNG.with_seed(i), 0.85, False, 1.0) for i in range(500)) / 500
    assert favorite_avg > underdog_avg


def test_ep_multiplier_stays_within_its_clamp():
    for i in range(500):
        m = sf.ep_multiplier(RNG.with_seed(i), 0.99, True, 1.15)
        lo, hi = sf.MULTIPLIER_CLAMP
        assert lo <= m <= hi


def test_ep_multiplier_is_deterministic_given_the_same_rng_state():
    m1 = sf.ep_multiplier(RNG.with_seed(42), 0.6, True, 1.0)
    m2 = sf.ep_multiplier(RNG.with_seed(42), 0.6, True, 1.0)
    assert m1 == m2


def test_weekly_feedback_decreases_multiplier_when_scoring_is_above_target():
    state = sf.SFSState()
    sf.weekly_feedback_update(state, week_num=1, measured_ppg_this_week=sf.TARGET_PPG_PER_TEAM + 5)
    assert state.scoring_feedback_multiplier < 1.0


def test_weekly_feedback_increases_multiplier_when_scoring_is_below_target():
    state = sf.SFSState()
    sf.weekly_feedback_update(state, week_num=1, measured_ppg_this_week=sf.TARGET_PPG_PER_TEAM - 5)
    assert state.scoring_feedback_multiplier > 1.0


def test_weekly_feedback_records_telemetry():
    state = sf.SFSState()
    sf.weekly_feedback_update(state, week_num=3, measured_ppg_this_week=25.0)
    assert len(state.telemetry) == 1
    entry = state.telemetry[0]
    assert entry["week"] == 3
    assert entry["measured_ppg"] == 25.0
    assert entry["target_ppg"] == sf.TARGET_PPG_PER_TEAM
    assert "multiplier_before" in entry and "multiplier_after" in entry


def test_weekly_feedback_change_is_capped_and_stays_within_its_clamp():
    """Even a wildly extreme single-week measurement shouldn't move the
    multiplier further than the weekly cap allows, and repeated extreme
    weeks should never push it outside FEEDBACK_CLAMP."""
    state = sf.SFSState()
    for week in range(1, 30):
        sf.weekly_feedback_update(state, week_num=week, measured_ppg_this_week=100.0)
        lo, hi = sf.FEEDBACK_CLAMP
        assert lo <= state.scoring_feedback_multiplier <= hi

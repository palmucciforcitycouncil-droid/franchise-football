"""
Tests for Player Progression & Regression (GDD Part 1 Sec 7.6,
app/engine/progression.py). Pure-function tests against hand-built
Player objects -- no DB needed, since progress_player()/apply_progression()
never touch persistence themselves (app/services/season_state.py's
apply_progression_to_roster owns the DB session -- see
test_season_rollover.py for that, which redirects the DB to a throwaway
copy first so it never mutates the real roster).
"""
from app.models.player import Player, Position
from app.engine.rng import RNG
from app.engine import progression


def _make_player(**overrides) -> Player:
    defaults = dict(
        player_id="p1", first_name="Test", last_name="Player",
        position=Position.QB, team_abbr="KC", age=25,
        overall_rating=75, potential=80, morale=75,
        speed=75, acceleration=75, strength=75, agility=75, jumping=75,
        stamina=75, toughness=75, durability=75,
        throw_power=75, throw_accuracy_short=75, throw_accuracy_mid=75, throw_accuracy_deep=75,
        play_action=75, throw_on_the_run=75, throw_under_pressure=75, break_sack=75,
        catching=75, spectacular_catch=75, catch_in_traffic=75,
        short_route_running=75, medium_route_running=75, deep_route_running=75, release=75,
        carrying=75, trucking=75, change_of_direction=75, ball_carrier_vision=75,
        stiff_arm=75, spin_move=75, juke_move=75, break_tackle=75,
        run_block=75, pass_block=75, run_block_power=75, run_block_finesse=75,
        pass_block_power=75, pass_block_finesse=75, lead_block=75, impact_blocking=75,
        tackle=75, hit_power=75, block_shedding=75, pursuit=75, play_recognition=75,
        man_coverage=75, zone_coverage=75, press=75, power_moves=75, finesse_moves=75,
        kick_power=75, kick_accuracy=75, kick_return=75, awareness=75,
    )
    defaults.update(overrides)
    return Player(**defaults)


def test_base_delta_is_positive_before_the_peak_window():
    # QB peak is (28, 31) -- a 22-year-old is 6 years out.
    assert progression._base_delta(Position.QB, 22) > 0


def test_base_delta_is_negative_after_the_peak_window():
    assert progression._base_delta(Position.QB, 35) < 0


def test_base_delta_is_zero_inside_the_peak_window():
    for age in range(28, 32):
        assert progression._base_delta(Position.QB, age) == 0.0


def test_base_delta_decline_is_steeper_than_growth_at_equal_distance():
    """A documented design choice: DECLINE_RATE > GROWTH_RATE, so aging
    out of the league is faster than developing into it."""
    growth = progression._base_delta(Position.QB, 24)   # 4 years before peak_start=28
    decline = progression._base_delta(Position.QB, 35)  # 4 years after peak_end=31
    assert abs(decline) > abs(growth)


def test_usage_multiplier_bounds_and_neutral_default():
    assert progression.usage_multiplier(None) == 1.0       # untracked position -- neutral, not a penalty
    assert progression.usage_multiplier(0) == 0.3           # touched the ball zero times -- floor, not zero
    assert progression.usage_multiplier(300) == 1.0
    assert progression.usage_multiplier(1000) == 1.0        # capped, doesn't exceed 1.0
    assert 0.3 < progression.usage_multiplier(150) < 1.0


def test_potential_multiplier_rewards_headroom():
    high_headroom = progression.potential_multiplier(overall_rating=70, potential=95)
    low_headroom = progression.potential_multiplier(overall_rating=90, potential=92)
    no_headroom = progression.potential_multiplier(overall_rating=95, potential=90)  # already past "potential"
    assert high_headroom > low_headroom > no_headroom
    assert 0.4 <= no_headroom <= 1.6
    assert 0.4 <= high_headroom <= 1.6


def test_progress_player_does_not_mutate_the_input():
    player = _make_player(age=22)
    original_age = player.age
    original_speed = player.speed
    progression.progress_player(player, touches=None, season_number=0, rng=RNG.with_seed(1))
    assert player.age == original_age
    assert player.speed == original_speed


def test_progress_player_is_deterministic_for_a_given_rng_seed():
    player_a = _make_player(age=22)
    player_b = _make_player(age=22)
    result_a = progression.progress_player(player_a, touches=200, season_number=0, rng=RNG.with_seed(99))
    result_b = progression.progress_player(player_b, touches=200, season_number=0, rng=RNG.with_seed(99))
    assert result_a.attribute_deltas == result_b.attribute_deltas


def test_apply_progression_ages_the_player_by_one():
    player = _make_player(age=25)
    result = progression.progress_player(player, touches=200, season_number=0, rng=RNG.with_seed(1))
    progression.apply_progression(player, result)
    assert player.age == 26


def test_apply_progression_clamps_attributes_to_0_99():
    player = _make_player(age=25, speed=98)
    # Force an extreme positive delta to prove the clamp, not just that
    # normal deltas happen to stay in range.
    result = progression.ProgressionResult(
        player_id=player.player_id,
        attribute_deltas={attr: 50.0 for attr in progression.PROGRESSED_ATTRIBUTES},
        potential_delta=0.0,
    )
    progression.apply_progression(player, result)
    assert player.speed == 99
    assert player.overall_rating <= 99


def test_apply_progression_never_drops_potential_below_overall_rating():
    player = _make_player(age=35, overall_rating=60, potential=62)  # aging veteran, little headroom
    result = progression.ProgressionResult(
        player_id=player.player_id,
        attribute_deltas={"overall_rating": -5.0},
        potential_delta=-10.0,  # a big potential drop
    )
    progression.apply_progression(player, result)
    assert player.potential >= player.overall_rating


def test_young_developing_player_trends_upward_on_average():
    """Statistical, not exact-value, test: a 22-year-old QB with real
    headroom and heavy usage should gain more than it loses across most
    attributes, averaged over many seeds (the per-attribute noise means
    any single attribute could go either way)."""
    gains = 0
    losses = 0
    for seed in range(30):
        player = _make_player(age=22, overall_rating=70, potential=90)
        result = progression.progress_player(player, touches=300, season_number=0, rng=RNG.with_seed(seed))
        avg_delta = sum(result.attribute_deltas.values()) / len(result.attribute_deltas)
        if avg_delta > 0:
            gains += 1
        else:
            losses += 1
    assert gains > losses


def test_aging_veteran_trends_downward_on_average():
    gains = 0
    losses = 0
    for seed in range(30):
        player = _make_player(age=37, position=Position.QB, overall_rating=80, potential=82)
        result = progression.progress_player(player, touches=300, season_number=0, rng=RNG.with_seed(seed))
        avg_delta = sum(result.attribute_deltas.values()) / len(result.attribute_deltas)
        if avg_delta < 0:
            losses += 1
        else:
            gains += 1
    assert losses > gains

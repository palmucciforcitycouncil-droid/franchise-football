"""
Tests for the Weekly Gameplan system (GDD Part 1 Sec 10.4.1):
app/engine/gameplan.py's pure bias functions and
app/services/gameplan_store.py's persistence.
"""
from app.engine.gameplan import (
    Gameplan,
    offense_pass_bias, offense_fourth_down_bias,
    defense_blitz_bias, defense_coverage_man_prob, defense_run_tactic_extra_penalty,
)
from app.services import gameplan_store


def test_none_gameplan_is_a_complete_no_op():
    """Every AI team passes gameplan=None through the whole chain -- each
    function must return exactly the "no override" value for None, not
    just something close to it, or AI-vs-AI games would silently change
    behavior."""
    assert offense_pass_bias(None, in_red_zone=False) == 0.0
    assert offense_pass_bias(None, in_red_zone=True) == 0.0
    assert offense_fourth_down_bias(None) == 0.0
    assert defense_blitz_bias(None, in_red_zone=False) == 0.0
    assert defense_blitz_bias(None, in_red_zone=True) == 0.0
    assert defense_coverage_man_prob(None) is None
    assert defense_run_tactic_extra_penalty(None, in_red_zone=True) == 0.0


def test_default_gameplan_values_also_produce_zero_bias():
    """A freshly-created Gameplan() (all fields 'Balanced'/'Hybrid'/
    'Standard') should bias nothing -- only a real, non-default choice
    should move any dial. The Coverage Scheme is the one exception:
    'Hybrid' has its own defined-but-still-40% man probability, not a
    None sentinel, since a real gameplan is in effect even at defaults."""
    gp = Gameplan()
    assert offense_pass_bias(gp, in_red_zone=False) == 0.0
    assert offense_fourth_down_bias(gp) == 0.0
    assert defense_blitz_bias(gp, in_red_zone=False) == 0.0
    assert defense_run_tactic_extra_penalty(gp, in_red_zone=True) == 0.0


def test_offensive_aggressiveness_shifts_pass_bias_in_the_right_direction():
    conservative = Gameplan(offensive_aggressiveness="Very Conservative")
    aggressive = Gameplan(offensive_aggressiveness="Very Aggressive")
    assert offense_pass_bias(conservative, in_red_zone=False) < 0
    assert offense_pass_bias(aggressive, in_red_zone=False) > 0
    assert offense_pass_bias(aggressive, in_red_zone=False) > offense_pass_bias(conservative, in_red_zone=False)


def test_offensive_aggressiveness_boosts_fourth_down_go_chance():
    assert offense_fourth_down_bias(Gameplan(offensive_aggressiveness="Very Aggressive")) > 0
    assert offense_fourth_down_bias(Gameplan(offensive_aggressiveness="Very Conservative")) < 0


def test_red_zone_offense_style_only_applies_inside_the_twenty():
    power_run = Gameplan(rz_offense="Power Run")
    spread = Gameplan(rz_offense="Spread/Shot")
    # Outside the red zone, rz_offense shouldn't matter at all (both Balanced aggressiveness).
    assert offense_pass_bias(power_run, in_red_zone=False) == offense_pass_bias(spread, in_red_zone=False) == 0.0
    # Inside it, Power Run should pull toward run (negative) and Spread toward pass (positive).
    assert offense_pass_bias(power_run, in_red_zone=True) < 0
    assert offense_pass_bias(spread, in_red_zone=True) > 0


def test_defensive_aggressiveness_and_blitz_strategy_both_raise_blitz_chance():
    passive = Gameplan(defensive_aggressiveness="Very Conservative", blitz="Selective")
    aggressive = Gameplan(defensive_aggressiveness="Very Aggressive", blitz="Blitz Heavy")
    assert defense_blitz_bias(passive, in_red_zone=False) < 0
    assert defense_blitz_bias(aggressive, in_red_zone=False) > 0
    assert defense_blitz_bias(aggressive, in_red_zone=False) > defense_blitz_bias(passive, in_red_zone=False)


def test_pressure_qb_red_zone_defense_adds_extra_blitz_bias_only_in_red_zone():
    gp = Gameplan(rz_defense="Pressure QB")
    outside = defense_blitz_bias(gp, in_red_zone=False)
    inside = defense_blitz_bias(gp, in_red_zone=True)
    assert inside > outside


def test_coverage_scheme_man_probability_ordering():
    man_heavy = defense_coverage_man_prob(Gameplan(coverage="Man-Heavy"))
    hybrid = defense_coverage_man_prob(Gameplan(coverage="Hybrid"))
    zone_heavy = defense_coverage_man_prob(Gameplan(coverage="Zone-Heavy"))
    assert man_heavy > hybrid > zone_heavy


def test_run_sellout_red_zone_defense_only_penalizes_inside_the_twenty():
    gp = Gameplan(rz_defense="Run-Sellout")
    assert defense_run_tactic_extra_penalty(gp, in_red_zone=False) == 0.0
    assert defense_run_tactic_extra_penalty(gp, in_red_zone=True) > 0.0
    # Every other Red Zone Defense style adds nothing extra.
    assert defense_run_tactic_extra_penalty(Gameplan(rz_defense="Pressure QB"), in_red_zone=True) == 0.0


# --- gameplan_store persistence -------------------------------------------

def test_get_gameplan_defaults_when_nothing_saved(tmp_path):
    path = tmp_path / "gameplans.json"
    gp = gameplan_store.get_gameplan("KC", path=path)
    assert gp == Gameplan()


def test_set_and_get_gameplan_round_trips(tmp_path):
    path = tmp_path / "gameplans.json"
    saved = Gameplan(
        offensive_aggressiveness="Very Aggressive",
        defensive_aggressiveness="Conservative",
        coverage="Zone-Heavy",
        blitz="Blitz Heavy",
        rz_offense="Spread/Shot",
        rz_defense="Pressure QB",
    )
    gameplan_store.set_gameplan("KC", saved, path=path)
    assert gameplan_store.get_gameplan("KC", path=path) == saved


def test_gameplan_is_per_team(tmp_path):
    path = tmp_path / "gameplans.json"
    gameplan_store.set_gameplan("KC", Gameplan(blitz="Blitz Heavy"), path=path)
    assert gameplan_store.get_gameplan("BUF", path=path) == Gameplan()
    assert gameplan_store.get_gameplan("KC", path=path).blitz == "Blitz Heavy"


def test_get_gameplan_ignores_unknown_saved_fields(tmp_path):
    """A save file from a future revision with an extra field shouldn't
    crash an older build -- unknown keys are just ignored."""
    import json
    path = tmp_path / "gameplans.json"
    path.write_text(json.dumps({"KC": {"blitz": "Blitz Heavy", "some_future_field": "xyz"}}))
    gp = gameplan_store.get_gameplan("KC", path=path)
    assert gp.blitz == "Blitz Heavy"

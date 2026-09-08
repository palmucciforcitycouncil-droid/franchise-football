"""
Weekly Gameplan (GDD Part 1 Sec 10.4.1): six opponent-strategy dropdowns
the user's Head Coach sets each week, read by the play-calling AI
(Sec 6.6/6.6.3) for the user's team only -- AI teams keep their existing
default behavior unchanged. Every function here takes `gameplan:
Gameplan | None` and returns a zero/no-op bias when it's None, which is
what lets drive_sim.py/defensive_ai.py thread an optional gameplan
through without touching AI-vs-AI games at all.

Deliberate scope cut: the GDD says settings "save per opponent" (i.e.
re-settable each week); app/services/gameplan_store.py stores one
current gameplan per team, overwritten on each save, not a full
per-opponent history -- a real, documented simplification, not an
oversight. The bias values below are a real, bounded mechanical
translation of each option's GDD tooltip text, not GDD-literal formulas
(none exist for this system) -- calibrated to be noticeable without
overwhelming the existing player-attribute-driven engine.
"""
from __future__ import annotations
from dataclasses import dataclass

OFFENSIVE_AGGRESSIVENESS = ["Very Conservative", "Conservative", "Balanced", "Aggressive", "Very Aggressive"]
DEFENSIVE_AGGRESSIVENESS = OFFENSIVE_AGGRESSIVENESS
COVERAGE_SCHEMES = ["Man-Heavy", "Hybrid", "Zone-Heavy"]
BLITZ_STRATEGIES = ["Selective", "Standard", "Blitz Heavy"]
RZ_OFFENSE_STYLES = ["Power Run", "Balanced", "Play-Action Heavy", "Spread/Shot"]
RZ_DEFENSE_STYLES = ["Bend-Don't-Break", "Balanced", "Run-Sellout", "Pressure QB"]


@dataclass(frozen=True)
class Gameplan:
    offensive_aggressiveness: str = "Balanced"
    defensive_aggressiveness: str = "Balanced"
    coverage: str = "Hybrid"
    blitz: str = "Standard"
    rz_offense: str = "Balanced"
    rz_defense: str = "Balanced"


_AGG_BIAS = {
    "Very Conservative": -0.15, "Conservative": -0.075, "Balanced": 0.0,
    "Aggressive": 0.075, "Very Aggressive": 0.15,
}
_BLITZ_BIAS = {"Selective": -0.08, "Standard": 0.0, "Blitz Heavy": 0.12}
_COVERAGE_MAN_PROB = {"Man-Heavy": 0.8, "Hybrid": 0.4, "Zone-Heavy": 0.15}
_RZ_OFFENSE_PASS_BIAS = {"Power Run": -0.15, "Balanced": 0.0, "Play-Action Heavy": 0.05, "Spread/Shot": 0.15}
_RZ_DEFENSE_BLITZ_BIAS = {"Bend-Don't-Break": -0.10, "Balanced": 0.0, "Run-Sellout": 0.0, "Pressure QB": 0.15}
_RZ_DEFENSE_RUN_TACTIC_BONUS = {"Bend-Don't-Break": 0.0, "Balanced": 0.0, "Run-Sellout": 4.0, "Pressure QB": 0.0}


def offense_pass_bias(gameplan: Gameplan | None, in_red_zone: bool) -> float:
    """Off. Aggressiveness: 'more early-down passes, deeper routes' ->
    shifts the base pass/run mix. Red Zone Offense adds its own bias
    once inside the 20 (Power Run pulls toward run, Spread/Shot toward
    pass), on top of (not instead of) the season-long aggressiveness."""
    if gameplan is None:
        return 0.0
    bias = _AGG_BIAS[gameplan.offensive_aggressiveness]
    if in_red_zone:
        bias += _RZ_OFFENSE_PASS_BIAS[gameplan.rz_offense]
    return bias


def offense_fourth_down_bias(gameplan: Gameplan | None) -> float:
    """Off. Aggressiveness: 'more 4th-down/2-pt attempts.'"""
    if gameplan is None:
        return 0.0
    return _AGG_BIAS[gameplan.offensive_aggressiveness]


def defense_blitz_bias(gameplan: Gameplan | None, in_red_zone: bool) -> float:
    """Def. Aggressiveness ('tighter coverage and more pressure') and
    Blitz Strategy both push the same blitz-chance dial; Red Zone
    Defense's Pressure QB style adds a further inside-the-20 bump."""
    if gameplan is None:
        return 0.0
    bias = _AGG_BIAS[gameplan.defensive_aggressiveness] + _BLITZ_BIAS[gameplan.blitz]
    if in_red_zone:
        bias += _RZ_DEFENSE_BLITZ_BIAS[gameplan.rz_defense]
    return bias


def defense_coverage_man_prob(gameplan: Gameplan | None) -> float | None:
    """Coverage Scheme overrides decide_coverage's default 40% man / 60%
    zone split in situations the GDD's table doesn't already force
    (3rd & 8+ always zone, goal line and a called blitz always man).
    Returns None when there's no gameplan -- callers should fall back to
    the existing default probability, not treat None as 0%."""
    if gameplan is None:
        return None
    return _COVERAGE_MAN_PROB[gameplan.coverage]


def defense_run_tactic_extra_penalty(gameplan: Gameplan | None, in_red_zone: bool) -> float:
    """Red Zone Defense's Run-Sellout style commits harder to the
    predicted run point-of-attack once inside the 20, on top of the
    normal Plug Gaps/Contain Edge penalty apply_run_tactic already
    applies."""
    if gameplan is None or not in_red_zone:
        return 0.0
    return _RZ_DEFENSE_RUN_TACTIC_BONUS.get(gameplan.rz_defense, 0.0)

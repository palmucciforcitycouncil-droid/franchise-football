"""
Player Progression & Regression (GDD Part 1 Sec 7.6): an end-of-season
system that deterministically ages and develops every player's
attributes. Applied by app/services/season_rollover.py's
start_new_season() when moving from one season to the next.

GDD Sec 7.6 gives the shape of the formula --
    Delta_attr = (Delta_base * F_pot * F_use) + epsilon_attr
-- but not concrete numbers for any of its pieces (peak-window ages
beyond two worked examples, growth/decline rates, F_pot/F_use
formulas, or annual/lifetime caps). Every constant and sub-formula
below is this module's own documented choice, not a GDD-literal value.

Deliberate, disclosed scope decisions:
- One age-curve Delta_base is computed per player and applied
  UNIFORMLY across every one of Player's ~50 skill attributes (plus
  overall_rating) -- a real, single-signal simplification, since the
  GDD doesn't specify per-attribute growth curves either.
- F_use (the "on-field performance" input) can only be computed where
  this engine actually tracks individual stats: QB attempts, RB
  carries, WR/TE targets, and DL/LB/DB defensive activity -- solo
  tackles + interceptions + forced fumbles + passes defended (both via
  app/engine/season_stats.py, the defensive side now real for every
  defender via app/engine/defensive_box_score.py, not interception-only
  as it used to be). OL/K/P still get a neutral 1.0 usage multiplier --
  no real per-play usage stat exists for them in this engine -- disclosed,
  not silently assumed to be "average." See app/services/season_state.py's
  apply_progression_to_roster() for exactly how touches is computed and
  handed to progress_player() below.
- No lifetime cap is tracked (would need per-player cumulative-change
  history this project doesn't retain) -- the natural 0-99 attribute
  bounds are the practical ceiling/floor. An annual per-attribute cap
  IS enforced (ANNUAL_CAP below).
- Dynamic Potential (Sec 7.6) is a smaller-magnitude nudge in the same
  direction as the performance signal: a young, over-performing player
  (F_use high, still pre-peak) sees potential creep up; an older,
  underperforming player sees it drift down toward their current
  overall_rating. Potential never drops below overall_rating.
"""
from __future__ import annotations
from dataclasses import dataclass

from app.engine.rng import stable_seed, RNG
from app.models.player import Player, Position

# (peak_start, peak_end), inclusive. QB and RB are the GDD's own two
# worked examples (Sec 7.6); every other position is this module's own
# reasonable extrapolation, documented rather than silently invented.
PEAK_WINDOWS: dict[Position, tuple[int, int]] = {
    Position.QB: (28, 31),
    Position.HB: (24, 26),
    Position.FB: (25, 28),
    Position.WR: (26, 29),
    Position.TE: (26, 29),
    Position.LT: (27, 30), Position.LG: (27, 30), Position.C: (27, 30),
    Position.RG: (27, 30), Position.RT: (27, 30),
    Position.LE: (26, 29), Position.RE: (26, 29), Position.DT: (26, 29),
    Position.LOLB: (25, 28), Position.MLB: (25, 28), Position.ROLB: (25, 28),
    Position.CB: (25, 28), Position.FS: (25, 28), Position.SS: (25, 28),
    Position.K: (28, 32), Position.P: (28, 32),
}

GROWTH_RATE = 1.1    # per year of distance below the peak window's start
DECLINE_RATE = 1.6   # per year of distance past the peak window's end (decline is steeper than growth)
ANNUAL_CAP = 6.0      # max |Delta_attr| enforced per attribute per rollover
NOISE_STDDEV = 0.8

# Attributes this system actually progresses -- every numeric skill
# rating on Player, deliberately excluding identity/meta/contract
# fields (age is handled separately; morale/salary/etc. aren't skill
# attributes an age curve should touch).
PROGRESSED_ATTRIBUTES = [
    "overall_rating",
    "speed", "acceleration", "strength", "agility", "jumping", "stamina", "toughness", "durability",
    "throw_power", "throw_accuracy_short", "throw_accuracy_mid", "throw_accuracy_deep",
    "play_action", "throw_on_the_run", "throw_under_pressure", "break_sack",
    "catching", "spectacular_catch", "catch_in_traffic",
    "short_route_running", "medium_route_running", "deep_route_running", "release",
    "carrying", "trucking", "change_of_direction", "ball_carrier_vision",
    "stiff_arm", "spin_move", "juke_move", "break_tackle",
    "run_block", "pass_block", "run_block_power", "run_block_finesse",
    "pass_block_power", "pass_block_finesse", "lead_block", "impact_blocking",
    "tackle", "hit_power", "block_shedding", "pursuit", "play_recognition",
    "man_coverage", "zone_coverage", "press", "power_moves", "finesse_moves",
    "kick_power", "kick_accuracy", "kick_return",
    "awareness",
]


def _base_delta(position: Position, age: int) -> float:
    """GDD Sec 7.6: gain before the peak window (g_pre), decline after
    it (g_post), stable within it."""
    start, end = PEAK_WINDOWS[position]
    if age < start:
        return GROWTH_RATE * (start - age)
    if age > end:
        return -DECLINE_RATE * (age - end)
    return 0.0


def usage_multiplier(touches: int | None) -> float:
    """F_use: normalized touches this season, capped at 1.0 (a 300+
    touch workhorse season gets the full multiplier); untracked
    positions (touches is None) get a neutral 1.0 rather than a
    penalty -- see this module's docstring."""
    if touches is None:
        return 1.0
    return max(0.3, min(1.0, touches / 300.0))


def potential_multiplier(overall_rating: int, potential: int) -> float:
    """F_pot: more headroom between current rating and potential means
    a bigger share of Delta_base actually lands (a player still well
    below their ceiling develops faster); a player already at/above
    their listed potential dampens further growth and doesn't resist
    decline at all."""
    headroom = potential - overall_rating
    return max(0.4, min(1.6, 1.0 + headroom / 40.0))


@dataclass
class ProgressionResult:
    player_id: str
    age_delta: int = 1
    attribute_deltas: dict[str, float] | None = None
    potential_delta: float = 0.0


def progress_player(player: Player, touches: int | None, season_number: int, rng: RNG) -> ProgressionResult:
    """Pure computation of one player's deltas -- does not mutate
    `player`. Callers (season_rollover.py) apply the result and persist
    it; keeping this pure makes it directly testable without a DB."""
    base = _base_delta(player.position, player.age)
    f_pot = potential_multiplier(player.overall_rating, player.potential)
    f_use = usage_multiplier(touches)

    deltas: dict[str, float] = {}
    for attr in PROGRESSED_ATTRIBUTES:
        noise = rng.gauss(0.0, NOISE_STDDEV)
        delta = base * f_pot * f_use + noise
        deltas[attr] = max(-ANNUAL_CAP, min(ANNUAL_CAP, delta))

    # Dynamic Potential: a smaller nudge in the same direction as the
    # performance signal, biased by whether the player is still pre-peak.
    still_developing = player.age <= PEAK_WINDOWS[player.position][1]
    performance_signal = (f_use - 0.65) * 2  # centered so average usage (~195 touches) is neutral
    potential_delta = (2.0 if still_developing else -1.0) * max(0.0, performance_signal)
    if not still_developing:
        potential_delta += -0.5  # potential quietly converges toward reality once a player's past their prime

    return ProgressionResult(
        player_id=player.player_id,
        attribute_deltas=deltas,
        potential_delta=potential_delta,
    )


def apply_progression(player: Player, result: ProgressionResult) -> None:
    """Mutates `player` in place with a computed ProgressionResult --
    the actual DB write/commit is the caller's responsibility
    (season_rollover.py, which owns the DB session)."""
    player.age += result.age_delta
    for attr, delta in result.attribute_deltas.items():
        current = getattr(player, attr)
        new_value = int(round(current + delta))
        setattr(player, attr, max(0, min(99, new_value)))
    new_potential = int(round(player.potential + result.potential_delta))
    player.potential = max(player.overall_rating, min(99, new_potential))

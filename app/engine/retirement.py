"""
Player retirement (GDD Sec 7.x offseason list: "Players and coaches may
choose to retire from the league"; Brian's ask, 2026-09-14: the season
summary should list retired players).

Coaches already retire (app/engine/coach_progression.py, GDD Sec 8.2.3's
age formula). Players never did -- nothing ever left the league except
an unsigned undrafted rookie aging out of undrafted_pool.py. The GDD
gives no player retirement formula, so every number below is this
module's own disclosed choice:

- No chance before a position's "retirement floor" age (30 for most
  positions, 32 for QB, 34 for K/P -- the positions whose real careers
  run longest).
- From the floor: 8% base, +10 percentage points per year past it.
- Stars hang on longer: OVR >= 85 halves the chance, OVR >= 78 cuts it
  by a quarter; a fading player (OVR < 70) gets +10 points.
- A free agent who went a whole season unsigned is much likelier to walk
  away (+25 points), and one 27+ always carries at least a 10% chance --
  nobody's calling. Not a player released THIS offseason (he hasn't
  even hit the market yet), and not a real starter-level talent
  (OVR >= 75) -- somebody will call.
- Capped at 95%, never a certainty: a real 45-year-old QB can still
  come back for one more year.

Deterministic per (league_seed, season_number, player_id), GDD Sec 1.3.
"""
from __future__ import annotations

from app.engine.rng import RNG, stable_seed
from app.models.player import Position

RETIREMENT_FLOOR_AGE: dict[Position, int] = {Position.QB: 32, Position.K: 34, Position.P: 34}
DEFAULT_RETIREMENT_FLOOR_AGE = 30
BASE_CHANCE = 0.08
PER_YEAR_CHANCE = 0.10
FREE_AGENT_BONUS = 0.25
FREE_AGENT_MIN_AGE = 27
FREE_AGENT_MIN_CHANCE = 0.10
FREE_AGENT_MAX_OVR = 74
MAX_CHANCE = 0.95


def retirement_probability(position: Position, age: int, overall_rating: int, is_free_agent: bool) -> float:
    """`is_free_agent` means a long-term unsigned player (see module
    docstring), not merely team_abbr is None."""
    floor = RETIREMENT_FLOOR_AGE.get(position, DEFAULT_RETIREMENT_FLOOR_AGE)
    chance = 0.0
    if age >= floor:
        chance = BASE_CHANCE + PER_YEAR_CHANCE * (age - floor)
        if overall_rating >= 85:
            chance *= 0.5
        elif overall_rating >= 78:
            chance *= 0.75
        elif overall_rating < 70:
            chance += 0.10
    if is_free_agent and age >= FREE_AGENT_MIN_AGE and overall_rating <= FREE_AGENT_MAX_OVR:
        chance = max(chance, FREE_AGENT_MIN_CHANCE) + FREE_AGENT_BONUS
    return max(0.0, min(MAX_CHANCE, chance))


def rolls_retirement(player, league_seed: int, season_number: int, long_term_free_agent: bool) -> bool:
    p = retirement_probability(player.position, player.age, player.overall_rating, long_term_free_agent)
    if p <= 0:
        return False
    rng = RNG.with_seed(stable_seed(league_seed, season_number, player.player_id, "retirement"))
    return rng.prob(p)

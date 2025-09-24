# app/engine/ratings.py
"""
Ratings Engine (pure functions).

- Progression (weekly or seasonal): younger players drift slightly toward potential.
- Position-based aging decline:
    RB: decline begins at age 29
    QB: decline begins at age 34
    Others: decline begins at age 30
  Decline ramps up gradually as age increases past the threshold.
- Offseason regression: small speed/stamina decline by age band; small awareness gain.
- Deterministic RNG: seedable; same inputs -> same outputs.
- Injury return penalty: temporary -5 on key ratings, then weekly recovery.
- All values clamped to 0..100.

This module is PURE: no DB or I/O side effects.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple
import random

# Attributes included in MVP scope
ATTRS = [
    "speed",
    "strength",
    "agility",
    "throw_power",
    "throw_accuracy",
    "catching",
    "tackling",
    "awareness",
    "stamina",
    "injury_proneness",  # informational; not trained
    "morale",            # used as a modifier
    "potential",         # target for young progression
]

# Trainable attributes (we will adjust these)
TRAINABLE = [
    "speed",
    "strength",
    "agility",
    "throw_power",
    "throw_accuracy",
    "catching",
    "tackling",
    "awareness",
    "stamina",
]

@dataclass(frozen=True)
class PlayerSnapshot:
    player_id: int
    position: str              # "QB", "RB", "WR", "TE", "OL", "DL", "LB", "CB", "S", "K", "P", etc.
    age: int
    season: int
    week: int
    attrs: Dict[str, float]
    games_played: int = 0
    snaps_played: int = 0
    morale: float = 50.0
    last_injury_week: int | None = None
    injury_penalty_weeks_remaining: int = 0


# ---------- helpers ----------

def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _rng_for(seed_base: int, season: int, week: int, player_id: int) -> random.Random:
    """
    Deterministic RNG derived from (seed_base, season, week, player_id).
    """
    val = (seed_base * 1_000_003) ^ (season * 10_000_019) ^ (week * 1009) ^ (player_id * 7919)
    return random.Random(val)


def _morale_scalar(morale: float) -> float:
    """
    Morale reduces gains if very low (<40), slightly boosts if very high (>80).
    Applies to deltas only.
    """
    if morale < 40:
        return 0.9
    if morale > 80:
        return 1.05
    return 1.0


def _injury_return_penalty(current: Dict[str, float], penalty_weeks: int) -> Dict[str, float]:
    """
    Apply a temporary injury penalty to prime ratings (speed, agility, stamina, awareness).
    Only applies if penalty_weeks > 0. (Caller handles the weekly recovery countdown.)
    """
    if penalty_weeks <= 0:
        return current
    penalized = current.copy()
    for k in ("speed", "agility", "stamina", "awareness"):
        penalized[k] = clamp(penalized[k] - 5.0)
    return penalized


def _usage_modifiers(games_played: int, snaps: int) -> Tuple[float, float]:
    """
    Returns (awareness_bonus, stamina_penalty) as tiny deltas.
    MVP rules:
      - >12 games: awareness +0.5 (experience)
      - >600 snaps: stamina -0.5 (fatigue)
    """
    awareness_bonus = 0.0
    stamina_penalty = 0.0
    if games_played > 12:
        awareness_bonus += 0.5
    if snaps > 600:
        stamina_penalty -= 0.5
    return (awareness_bonus, stamina_penalty)


# ---------- age/position curves ----------

def _decline_threshold_by_position(position: str) -> int:
    p = position.upper()
    if p == "RB":
        return 29
    if p == "QB":
        return 34
    # all others
    return 30


def _age_progression_factor(age: int) -> float:
    """
    Base progression strength toward potential (for younger players).
    18–24: fast (1.0)
    25–28: medium (0.6)
    29–31: small (0.3)
    32+:   minimal (0.15)
    """
    if age <= 24:
        return 1.0
    if age <= 28:
        return 0.6
    if age <= 31:
        return 0.3
    return 0.15


def _age_decline_scale(age: int, position: str) -> float:
    """
    Returns a 0..1 scale of decline based on how far past the threshold the player is.
    Ramps up linearly across ~6 years, capped at 1.0.
    """
    threshold = _decline_threshold_by_position(position)
    over = max(0, age - threshold)
    return min(1.0, over / 6.0)  # 0 at threshold, 1.0 by ~threshold+6


def _decline_weights(position: str) -> Dict[str, float]:
    """
    Attribute-specific sensitivity to aging decline (awareness excluded).
    Heavier for speed/stamina; tuned by position.

    Assumption (MVP-safe):
      - RB: Speed-1.0, Agility-0.7, Stamina-0.7, others-0.3
      - QB: Speed-0.5, Stamina-0.4, Throw Power-0.4, Throw Accuracy-0.3, others-0.2
      - Other positions: Speed-0.8, Agility-0.5, Stamina-0.6, others-0.2
    """
    p = position.upper()
    base = {k: 0.2 for k in TRAINABLE}  # gentle default
    base["awareness"] = 0.0  # awareness not penalized here

    if p == "RB":
        base.update({"speed": 1.0, "agility": 0.7, "stamina": 0.7})
        for k in ("throw_power", "throw_accuracy"):
            base[k] = 0.1
        return base

    if p == "QB":
        base.update({"speed": 0.5, "stamina": 0.4, "throw_power": 0.4, "throw_accuracy": 0.3})
        return base

    # Others (WR/TE/OL/DL/LB/CB/S/K/P...)
    base.update({"speed": 0.8, "agility": 0.5, "stamina": 0.6})
    return base


# ---------- core public API ----------

def progression_tick(
    player: PlayerSnapshot,
    seed_base: int = 2025,
    scope: str = "week",  # "week" or "season"
) -> Dict[str, float]:
    """
    Progression with position-based aging decline.
      - Younger: drift trainables slightly toward potential.
      - Older (past position threshold): apply decline that ramps up with age distance.
      - Tiny deterministic noise.
      - Usage & morale affect only the *delta* (not the base).
      - Awareness is not penalized by aging decline; it can still inch up.

    Returns a new attribute dict (non-trainables passed through).
    """
    rng = _rng_for(seed_base, player.season, player.week, player.player_id)
    current = player.attrs.copy()
    potential = clamp(current.get("potential", 50.0))
    morale = current.get("morale", player.morale)

    # Injury penalty first
    current = _injury_return_penalty(current, player.injury_penalty_weeks_remaining)

    # Scope scalar (season tick is a bigger step than week)
    scope_scalar = 1.0 if scope == "week" else 4.0

    # Younger progression strength (used when under threshold)
    prog_base = _age_progression_factor(player.age) * scope_scalar

    # Aging decline scaling (0..1), ramps up as age goes past threshold
    decline_scale = _age_decline_scale(player.age, player.position) * scope_scalar
    decline_w = _decline_weights(player.position)

    # Usage micro-effects
    awareness_bonus, stamina_penalty = _usage_modifiers(player.games_played, player.snaps_played)

    updated: Dict[str, float] = current.copy()

    for k in TRAINABLE:
        curr = current[k]

        # Awareness can naturally creep upward a bit across career
        # (treat its "target" a bit higher than current so it can drift up)
        if k == "awareness":
            target = clamp(curr + 20.0, 0.0, 100.0)
        else:
            target = potential

        # --- younger progression (toward potential) ---
        # Move a small % of the gap toward the target
        drift_toward = (target - curr) * (0.01 * prog_base)

        # Apply tiny deterministic noise ±0.2
        noise = rng.uniform(-2.0, 2.0) * 0.1

        # Usage tweaks
        if k == "awareness":
            drift_toward += awareness_bonus * 0.1
        if k == "stamina":
            drift_toward += stamina_penalty * 0.1

        # --- older decline (away from current; emphasize by weights) ---
        # If decline_scale > 0, apply a small negative drift on sensitive attributes.
        drift_away = 0.0
        if decline_scale > 0.0:
            # Heavier hit for more sensitive attributes; scaled by how far past threshold.
            # 0.05 is a gentle base so weekly moves are subtle; season scope multiplies via scope_scalar.
            drift_away = -0.05 * decline_w.get(k, 0.2) * decline_scale

        # Combine, then apply morale
        delta = (drift_toward + drift_away + noise) * _morale_scalar(morale)
        updated[k] = clamp(curr + delta)

    # Pass-through non-trainables
    updated["morale"] = clamp(current.get("morale", morale))
    updated["potential"] = clamp(current.get("potential", potential))
    updated["injury_proneness"] = clamp(current.get("injury_proneness", 50.0))
    return updated


def regression_offseason(player: PlayerSnapshot, seed_base: int = 2025) -> Dict[str, float]:
    """
    Offseason regression after age increments.
    - speed/stamina decline by age band
    - awareness may increase slightly with experience
    """
    rng = _rng_for(seed_base, player.season, 0, player.player_id)
    current = player.attrs.copy()
    age = player.age

    # Band declines for speed/stamina
    def band_decline(a: int) -> float:
        if a >= 35:
            return rng.uniform(1.5, 3.0)
        if a >= 32:
            return rng.uniform(1.0, 2.0)
        if a >= 29:
            return rng.uniform(0.5, 1.5)
        return 0.0

    decline = band_decline(age)

    updated = current.copy()
    for k in ("speed", "stamina"):
        updated[k] = clamp(updated[k] - decline)

    # Awareness creeps up a touch with age/experience
    if age <= 34:
        aware_boost = 0.0
    elif age <= 36:
        aware_boost = rng.uniform(0.3, 0.8)
    else:
        aware_boost = rng.uniform(0.1, 0.5)

    updated["awareness"] = clamp(updated["awareness"] + aware_boost)
    return updated


def recover_injury_penalty(weeks_remaining: int) -> int:
    """Reduce penalty weeks by 1 per tick until 0."""
    return max(0, weeks_remaining - 1)

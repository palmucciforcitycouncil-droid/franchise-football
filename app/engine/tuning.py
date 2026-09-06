"""
Minimal tuning parameters for the drive/ game simulation (MVP).
These are safe baseline values used by app.engine.drive_sim via:
    from .tuning import PARAMS as P
"""

from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, Any

# Global baseline knobs. Keep these conservative so Score Fidelity stays near target.
PARAMS: Dict[str, Any] = {
    # High-level sim control
    "pace": {  # approximate drives per team per game target + tempo factors
        "target_drives_per_team": 11.5,   # ~23 total drives per game
        "hurry_up_multiplier": 1.10,
        "bleed_multiplier": 0.92,
    },

    # Play mix and aggression
    "mix": {
        "run": 0.44,
        "pass": 0.56,
    },
    "aggression": {
        "base": 0.50,     # 0..1, larger = more 4th-down tries / deeper shots
        "fourth_down": 0.15,
        "two_point_try": 0.04,
    },

    # Per-play turnover baseline rates (rough league-ish priors)
    "turnover": {
        "fumble_per_rush": 0.0085,
        "fumble_per_recv": 0.0060,
        "int_per_pass_att": 0.028,
        "strip_sack_bonus": 0.0015,
    },

    # Field goal & special teams — coarse buckets are fine for MVP
    "special": {
        "fg_make_prob": {
            "<30": 0.98,
            "30-39": 0.94,
            "40-49": 0.85,
            "50+": 0.67,
        },
        "punt_touchback": 0.07,
        "punt_block": 0.002,
        "fg_block": 0.003,
    },

    # Drive outcome priors used by simple drive simulators as a starting point
    # (Your engine may update these dynamically by down/distance/field pos.)
    "drive_outcome": {
        "td_prob": 0.24,
        "fg_prob": 0.18,
        "zero_prob": 0.58,   # punt/turnover on downs/turnover before scoring
    },

    # Clock model (seconds per play under different tempos)
    "clock": {
        "base_secs_per_play": 27.0,
        "no_huddle_secs_per_play": 20.0,
        "bleed_secs_per_play": 32.0,
        "incomplete_pass_stop": True,
        "first_down_move_chains": True,
    },
}


def get_params() -> Dict[str, Any]:
    """Return a deep copy so callers can tweak without mutating the singleton."""
    return deepcopy(PARAMS)


@dataclass(frozen=True)
class DriveSimParams:
    """
    Flat, attribute-accessible parameters for the single-Gaussian-per-drive
    model in drive_sim.py. This is a different (simpler) model than the
    per-play PARAMS dict above, so it needs its own knobs rather than
    reusing that dict's keys directly.

    Threshold values below are calibrated so that, for an average matchup
    (offense rating == defense rating, field_pos == 65), the outcome mix
    roughly matches PARAMS["drive_outcome"] (td 24% / fg 18% / nothing 58%)
    under sample = Normal(ep, base_variance). This is a first-pass
    calibration, not a final one -- the Score Fidelity System (GDD Part 1
    Sec 6.2) auto-tunes exactly these kinds of knobs against real scoring
    data once it exists. Treat these as reasonable starting points, not
    settled game balance.
    """
    ep_pos_scale: float = 0.08          # field position -> EP baseline
    ep_rating_scale: float = 0.03       # offense/defense rating diff -> EP
    base_variance: float = 1.8          # stddev of the per-drive outcome sample
    aggro_variance_scale: float = 0.4   # aggression (0..1) widens variance
    two_min_pass_bias: float = 0.15     # two-minute drill: shift toward passing
    two_min_aggression: float = 0.3     # two-minute drill: EP nudge upward
    td_threshold: float = 0.9           # sample >= this -> touchdown
    fg_threshold: float = 0.0           # sample >= this (and < td) -> field goal
    fourth_down_boost: float = 0.35     # base chance to convert/extend on 4th
    punt_net_mu: float = 38.0           # average net punt yards
    punt_net_sigma: float = 8.0
    pat_make: float = 0.94              # extra-point make probability


DRIVE_SIM_PARAMS = DriveSimParams()

from typing import Tuple, Optional
from .rng import RNG
from .rating import TeamRatings
from .tuning import DRIVE_SIM_PARAMS as P

def simulate_drive(
    rng: RNG,
    offense: TeamRatings,
    defense: TeamRatings,
    field_pos: int,
    *,
    is_two_minute: bool = False,
    trailing: bool = False,
    fourth_down_ok: bool = False
) -> Tuple[int, str, int, int, int, int]:
    """
    Returns: points, summary, next_field_pos, plays, yards, turnovers
    """
    # Expected points based on field position & rating diff
    baseline = max(-2.8, min(4.8, (field_pos - 65) * P.ep_pos_scale))
    diff = (offense.offense - defense.defense) * P.ep_rating_scale
    ep = baseline + diff

    # Situational modifiers
    run_share = max(0.2, min(0.8, offense.run_bias * 0.6 + 0.2))
    variance = P.base_variance + offense.aggression * P.aggro_variance_scale
    if is_two_minute or trailing:
        variance *= 0.95
        run_share = max(0.2, run_share - P.two_min_pass_bias)
        ep += P.two_min_aggression

    sample = rng.gauss(ep, variance)

    plays = max(5, min(14, int(abs(rng.gauss(7.0, 2.2)))))
    yard_mu = 27 + (offense.offense - defense.defense) * 0.35
    if is_two_minute:
        yard_mu += 3
    yards = int(max(-10, min(95, rng.gauss(yard_mu, 16))))
    turnovers = 0

    outcome = "Punt"
    pts = 0
    if sample >= P.td_threshold:
        pts = 7 if rng.prob(P.pat_make) else 6
        outcome = "TD"
        yards = max(yards, 40)
    elif sample >= P.fg_threshold:
        pts = 3
        outcome = "FG"
        yards = max(yards, 25)
    elif sample < -1.6:
        outcome = "Turnover"
        turnovers = 1
        yards = min(yards, max(0, yards - 12))
    else:
        # Stall - small chance to extend on 4th based on aggression flag
        if fourth_down_ok and rng.prob(P.fourth_down_boost + 0.05*(offense.aggression-0.5)):
            # "extend" the drive: add some yards and maybe flip FG
            extra = int(max(0, rng.gauss(12, 8)))
            yards += extra
            if yards > 30 and rng.prob(0.6):
                pts = 3
                outcome = "FG"

    # Next field position
    if outcome == "TD":
        next_pos = 25
    elif outcome == "FG":
        next_pos = 25 if rng.prob(0.7) else 35
    elif outcome == "Punt":
        shift = P.punt_net_mu + int(rng.gauss(0, P.punt_net_sigma))
        next_pos = max(15, min(35, 100 - max(5, field_pos + shift - 100)))
    else:
        next_pos = 50 + int(abs(rng.gauss(0, 10)))

    return pts, outcome, next_pos, plays, yards, turnovers

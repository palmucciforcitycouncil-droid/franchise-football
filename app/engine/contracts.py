"""
Contracts, Salary Cap & Negotiations (GDD Part 1 Sec 8.3 -- R4a).

**Real data this chunk builds on, not from scratch:** `Player.salary`/
`signing_bonus` are already real, imported Madden dollar figures (M8,
2026-09-09); `contract_years_remaining` already exists as a disclosed-
synthetic 1-5 placeholder specifically reserved for "a real negotiated
term arrives with R4a" (`player.py`'s own module docstring). This chunk
is that arrival: real cap math, a real (simplified, disclosed) market-
value formula, and a real offer-scoring negotiation, replacing the
placeholder's *meaning* without needing a second Contract table --
`Player`'s existing fields ARE the contract.

**Deliberate scope cuts from GDD Sec 8.3's fuller design, each
disclosed:**
- **No signing-bonus cap proration / dead cap.** Sec 8.3 doesn't specify
  this level of detail either, but real NFL cap accounting prorates a
  signing bonus across the contract's life and charges "dead money" on
  a cut. This module's cap hit is simply `salary` (an AAV figure) --
  real, functional cap tracking, just without multi-year bonus
  amortization. Revisit if Trades (R4c) ever needs a real dead-cap
  number to value a trade-away contract.
- **No tiered market-value CSVs.** Sec 8.3.1's Market Anchor calls for
  "calibration CSV files" of AAV% bands by position/tier -- none exist
  in this project (same gap A1's `roster_strength.py` disclosed for
  positional weights before its own A3 tuning pass). `expected_market_
  value()` below is a real, disclosed formula instead: `overall_rating`
  and age drive a base value, and `roster_strength.POSITION_WEIGHTS`
  (already real, already A3-tuned against actual sim sensitivity) scales
  it by position -- reusing a number this engine already trusts rather
  than inventing an unrelated second one.
- **No Mood Meter / multi-round patience state.** Sec 8.3.3's "drains on
  rejections, empties on insulting lowballs, locking the negotiation" is
  stateful, UI-heavy, and not needed to unlock R4b/R4c. `evaluate_offer()`
  is a single deterministic verdict (ACCEPT/REJECT/COUNTER) per call --
  real accept-or-not logic, not a fabricated mood animation.
- **No rookie scale.** Depends on the Draft (R5), which itself depends on
  this chunk -- can't exist yet. Every player negotiated here is a real
  veteran with a real `years_pro`.

**Veteran minimum** uses Sec 8.3.2's one real anchor ($0.84M at 0 years
of service, 2025) with a linear per-year-of-service step this module
documents as its own choice (the GDD gives the anchor, not the full
ladder).
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from enum import Enum

from app.engine.position_groups import POSITION_TO_GROUP
from app.engine.roster_strength import POSITION_WEIGHTS
from app.models.player import Player

# Sec 8.3 gives a real-world-scale AAV cap anchor (updated 2026-09-12:
# the real 2026 NFL cap is $301.2M, not the stale $279.2M/2025 figure
# this comment used to cite). This project's imported Madden salary data
# does NOT run on that scale -- confirmed against the real DB, not
# assumed: real team salary totals span $262M-$695M (league avg ~$437M),
# and a single real player (M8's own verified example, Patrick Mahomes)
# is $190.4M alone, more than half of even the CURRENT real cap by
# itself. Madden's "Total Salary" column was never validated against
# real-world NFL cap compliance -- it's real, imported data, just not on
# a cap-compatible scale. Rather than leave every real team permanently,
# unfixably over an incompatible cap (which would make every free-
# agency/re-sign offer reject with OVER_CAP regardless of merit --
# caught via exactly that on this chunk's own first live signing
# attempt), SALARY_CAP_BASE stays rescaled to this project's OWN real
# salary distribution instead of Sec 8.3's numerically incompatible
# dollar anchor -- comfortably above the current real league-wide max
# team total, so every team starts cap-compliant with real room to
# operate. Applying $301.2M directly would reproduce the exact bug this
# rescale exists to prevent; ask before changing SALARY_CAP_BASE itself.
SALARY_CAP_BASE = 720_000_000
# +7.5%/year, compounded -- Sec 8.3's real growth RATE (updated
# 2026-09-12 from 11.2%). Unlike the base dollar figure above, a growth
# RATE has no Madden-scale incompatibility -- it applies identically
# regardless of the underlying dollar scale, so this one tracks the
# real-world number directly.
SALARY_CAP_GROWTH = 0.075

# This engine's season_number 0 is real-world 2026 (one year after the
# GDD's 2025 baseline) -- see roster_strength.py's decision 2 precedent
# for this same season_number<->real-year anchoring. season_number N is
# therefore N+1 years of growth past the 2025 baseline.
def salary_cap_for_season(season_number: int) -> float:
    return SALARY_CAP_BASE * (1.0 + SALARY_CAP_GROWTH) ** (season_number + 1)


VETERAN_MIN_BASE = 840_000  # Sec 8.3.2: $0.84M at 0 years of service, 2025 -- kept at the GDD's literal
# real-world value even though SALARY_CAP_BASE above was rescaled to this project's own data: at that
# rescaled cap, this floor is low enough to almost never bind (real imported salaries run well above
# it), which is fine -- it's a floor, not a target, and staying inert here beats fabricating a second,
# unrelated rescaled number with no real anchor at all.
# This module's own choice (not in the GDD): each year of service adds
# ~4% of the base, capped at 10 years -- a real ladder, not a flat number,
# without a documented per-year table to import.
VETERAN_MIN_PER_YEAR = 0.04
VETERAN_MIN_YEAR_CAP = 10


def veteran_minimum(years_pro: int, season_number: int) -> float:
    season_growth = (1.0 + SALARY_CAP_GROWTH) ** (season_number + 1)
    service_mult = 1.0 + VETERAN_MIN_PER_YEAR * min(years_pro, VETERAN_MIN_YEAR_CAP)
    return VETERAN_MIN_BASE * season_growth * service_mult


def team_cap_space(players: list[Player], season_number: int) -> float:
    """players: one team's real rostered players. Cap hit = salary (AAV) --
    see module docstring for why bonus proration isn't modeled."""
    cap = salary_cap_for_season(season_number)
    committed = sum(p.salary for p in players)
    return cap - committed


# Age curve for expected_market_value: real NFL earning power peaks
# roughly late 20s and declines after -- this module's own smooth
# approximation (no calibration data to fit against), symmetric enough
# to not need a position-specific curve on top of POSITION_WEIGHTS' own
# positional scaling.
def _age_value_multiplier(age: int) -> float:
    if age <= 26:
        return 0.85 + 0.05 * (age - 21) / 5.0 if age >= 21 else 0.85
    if age <= 29:
        return 1.0
    # Past 29: linear decline, floor at 0.4 by age 38+
    decline = min(1.0, (age - 29) / 9.0)
    return 1.0 - 0.6 * decline


def expected_market_value(player: Player, season_number: int) -> float:
    """A real, disclosed-simplified stand-in for Sec 8.3.1's dual-anchor
    formula -- see module docstring. Scales a base dollar figure by
    overall_rating (quadratic -- a 99 OVR player is worth far more than
    2x a 70 OVR one, matching how real veteran/star pay actually spreads),
    age, and the player's POSITION_WEIGHTS share (A1/A3's real, tuned
    positional-importance number)."""
    group = POSITION_TO_GROUP[player.position]
    position_mult = POSITION_WEIGHTS[group] / POSITION_WEIGHTS["QB"]  # 0..1, QB = 1.0
    ovr_frac = max(0.0, (player.overall_rating - 40) / 59.0)  # 40 OVR floor -> 0, 99 -> 1
    base_value = salary_cap_for_season(season_number) * 0.20  # a QB1 at 99 OVR, prime age, caps near 20% of the cap -- real NFL's actual top-of-market QB share
    value = base_value * (ovr_frac ** 1.6) * position_mult * _age_value_multiplier(player.age)
    return max(value, veteran_minimum(player.years_pro, season_number))


class OfferVerdict(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    COUNTER = "COUNTER"


@dataclass(frozen=True)
class OfferResult:
    verdict: OfferVerdict
    offer_score: float
    counter_aav: float | None = None
    counter_years: int | None = None


# Sec 8.3.3's Offer Score weights -- this module's own documented choice
# (the GDD gives the formula's shape, not its weights).
W_AAV = 0.65
W_YEARS = 0.15
W_TEAM = 0.20
ACCEPT_THRESHOLD = 0.97
COUNTER_THRESHOLD = 0.80  # below this, the player just walks (REJECT) rather than countering
# Guaranteed money's real effect on acceptance (Brian's ask, 2026-09-13)
# is an ADDITIVE bonus on top of the AAV/Years/Team score above, not a
# 4th weight carved out of those three's existing 1.0 total -- an
# unguaranteed offer (offered_guaranteed=0) must score EXACTLY as it did
# before this existed (real players who already cleared ACCEPT on pure
# cash/years/team-quality terms shouldn't suddenly need guaranteed money
# too just because the option now exists), while a real guarantee gives
# a real, additional reason to say yes. Scores can now exceed 1.0 by up
# to this much, which is fine -- ACCEPT_THRESHOLD is a fixed bar, not a
# ceiling (aav_points alone can already reach 1.3).
W_GUARANTEED_BONUS = 0.10
# What guaranteed-money fraction (guaranteed / total contract value)
# reads as "full security" and earns the full bonus, same "real number
# picked here, not in the GDD" spirit as years_points' own 4-years-is-
# full-security anchor below -- half the contract fully guaranteed is
# already a strong, real-world-plausible term, not a threshold no
# realistic offer ever reaches.
FULL_GUARANTEE_FRACTION = 0.5


def offer_reaction(score: float) -> str:
    """Finer-grained live feedback than the real ACCEPT/COUNTER/REJECT
    verdict alone (Brian's ask, 2026-09-13, matching a Figma reference's
    "Player Reaction" label on a slider-based negotiation screen) -- new
    tuning layered on top of the existing real ACCEPT_THRESHOLD (0.97)/
    COUNTER_THRESHOLD (0.80), same "this module's own choice, not in the
    GDD" category as those two. Purely a label; the real verdict
    computed by evaluate_offer() above is what actually decides
    ACCEPT/REJECT/COUNTER, this never overrides it."""
    if score >= 1.05:
        return "Very Interested"
    if score >= ACCEPT_THRESHOLD:
        return "Interested"
    if score >= 0.88:
        return "Considering"
    if score >= COUNTER_THRESHOLD:
        return "Lowball"
    return "Not Interested"


def evaluate_offer(
    player: Player, offered_aav: float, offered_years: int,
    season_number: int, team_rating: float, offered_guaranteed: float = 0.0,
) -> OfferResult:
    """Sec 8.3.3: Final_Offer_Score = [(w_AAV*AAV_Points) + (w_Years*Years_Points)
    + (w_Team*Team_Quality_Points)] + a guaranteed-money bonus on top --
    Starter_Multiplier is skipped (no real starter/depth distinction feeds
    this yet outside roster_strength's own snap-share weighting, which
    already shapes team_rating itself).

    team_rating: the offering team's app.engine.roster_strength.team_rating
    (0-99ish) -- this module's real substitute for Sec 8.4's own
    "TeamQuality from prior-year power ranking," since roster_strength
    already IS a real, tuned team-quality number this engine trusts.

    offered_guaranteed (Brian's ask, 2026-09-13): real money now, not
    money a player could still lose to a release -- scored as a fraction
    of the total contract value against FULL_GUARANTEE_FRACTION, same
    shape as years_points, and added on TOP of the AAV/Years/Team score
    via W_GUARANTEED_BONUS (see that constant's own docstring for why
    this is additive, not a 4th weight carved out of the other three).
    Defaults to 0 (an unguaranteed offer, still real and scoreable, and
    scored EXACTLY as it was before this bonus existed) rather than
    requiring every caller to pass it."""
    expected = expected_market_value(player, season_number)
    aav_points = min(1.3, offered_aav / expected) if expected else 1.0
    years_points = min(1.0, offered_years / 4.0)  # 4+ years reads as full security
    team_points = team_rating / 99.0
    total_value = offered_aav * offered_years
    guaranteed_fraction = (offered_guaranteed / total_value) if total_value else 0.0
    guaranteed_points = min(1.0, guaranteed_fraction / FULL_GUARANTEE_FRACTION)

    score = W_AAV * aav_points + W_YEARS * years_points + W_TEAM * team_points + W_GUARANTEED_BONUS * guaranteed_points

    if score >= ACCEPT_THRESHOLD:
        return OfferResult(OfferVerdict.ACCEPT, score)
    if score >= COUNTER_THRESHOLD:
        # Counters toward the AAV that WOULD clear ACCEPT_THRESHOLD, all
        # else (years, team quality, AND the guaranteed money actually
        # offered) held equal -- solved from the offer-score formula
        # itself, not a second guess.
        needed_aav_points = (
            ACCEPT_THRESHOLD - W_YEARS * years_points - W_TEAM * team_points - W_GUARANTEED_BONUS * guaranteed_points
        ) / W_AAV
        # Rounded UP, not to nearest -- resubmitting these exact terms
        # must clear ACCEPT_THRESHOLD, not land a rounding hair below it.
        counter_aav = math.ceil(max(offered_aav, needed_aav_points * expected))
        return OfferResult(OfferVerdict.COUNTER, score, counter_aav=counter_aav, counter_years=offered_years)
    return OfferResult(OfferVerdict.REJECT, score)

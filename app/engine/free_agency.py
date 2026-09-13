"""
Free Agency (GDD Part 1 Sec 8.4 -- R4b).

Builds directly on R4a's `app/engine/contracts.py`: `AAV_anchor` is
`contracts.expected_market_value()` (itself real, disclosed-simplified,
reusing `roster_strength.POSITION_WEIGHTS`), `TeamQuality` is
`roster_strength.team_rating` (see contracts.py's own docstring for why
that's the real substitute for "prior-year power ranking" here), and
`CoachDev` is `app.engine.coaching.staff_effect_for()`'s real
`dev_multiplier_offense`/`dev_multiplier_defense` -- three already-real,
already-tuned numbers, not new ones invented for this formula alone.

**Deliberate scope cut from Sec 8.4's fuller design, disclosed:** no
multi-team AI bidding war. Sec 8.4's "Tick Logic" (a player reviews
their top 3 offers each tick across a simulated free-agency period,
threshold decaying 1.00 -> 0.85 over time) models OTHER teams
competing for the same player. Simulating 31 AI teams' own competing
offers is a substantial system on its own (roster needs per AI team,
their own cap space, their own willingness to bid) and isn't needed to
give the user a real, functioning "sign a free agent" action. This
module instead gives a single deterministic verdict per user-submitted
offer against a FIXED threshold (no decay) -- same shape as R4a's
`contracts.evaluate_offer()`, and the real cap guardrail (Sec 8.4's own
"reject any offer that would put the team over the cap") is still
enforced for real. Revisit if/when other teams' free-agent behavior
needs to be simulated (e.g. for a real trade/FA-driven league that
isn't just the user's own moves).

**Auto-release on contract expiry** (the other half of what R4a's own
docstring flagged as "R4b's job, not R4a's"): a player whose
`contract_years_remaining` hits 0 at season rollover becomes a real
free agent (`team_abbr = None`), wired into
`season_state.apply_progression_to_roster()`.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from enum import Enum

from app.engine import coaching, contracts
from app.engine.position_groups import POSITION_TO_GROUP
from app.models.player import Player, Position


class RoleFit(float, Enum):
    """Sec 8.4's own three values."""
    STARTER = 1.0
    ROTATIONAL = 0.8
    DEPTH = 0.6


def role_fit_for(player: Player, current_group_rating: float | None) -> RoleFit:
    """Sec 8.4 doesn't define how RoleFit is actually computed -- this
    module's own real, disclosed rule: compare the free agent's
    overall_rating against the signing team's CURRENT group rating at
    that position (app.engine.roster_strength.compute_group_ratings()'s
    output, passed in by the caller since it already has the roster
    loaded). None (no players at all currently in that group) reads as
    an open Starter need."""
    if current_group_rating is None:
        return RoleFit.STARTER
    gap = player.overall_rating - current_group_rating
    if gap >= 5:
        return RoleFit.STARTER
    if gap >= -10:
        return RoleFit.ROTATIONAL
    return RoleFit.DEPTH


class FAOfferVerdict(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    OVER_CAP = "OVER_CAP"  # Sec 8.4's own real guardrail


@dataclass(frozen=True)
class FAOfferResult:
    verdict: FAOfferVerdict
    score: float


# Sec 8.4's own formula shape; weights are this module's documented
# choice (the GDD gives the shape, not the numbers, same as Sec 8.3.3).
W_AAV = 0.45
W_ROLE = 0.25
W_TEAM = 0.15
W_COACH = 0.15
ACCEPT_THRESHOLD = 1.00  # Sec 8.4's own real starting threshold, held fixed (no tick-decay -- see module docstring)


def fa_offer_reaction(score: float) -> str:
    """Same purpose as contracts.offer_reaction() (live negotiation-UI
    feedback, Brian's ask 2026-09-13) but scaled around THIS module's own
    real ACCEPT_THRESHOLD (1.00, not contracts.py's 0.97) -- reusing
    contracts.py's band offsets against a different threshold would
    silently mislabel scores near the boundary (e.g. a 0.98 here is a
    real REJECT, not "Interested"). No COUNTER concept exists in this
    module (see module docstring), so these bands are purely descriptive
    feedback -- ACCEPT/REJECT/OVER_CAP is still the only real verdict."""
    if score >= 1.10:
        return "Very Interested"
    if score >= ACCEPT_THRESHOLD:
        return "Interested"
    if score >= 0.90:
        return "Considering"
    if score >= 0.80:
        return "Lowball"
    return "Not Interested"


def evaluate_fa_offer(
    player: Player, team_abbr: str, offered_aav: float, offered_years: int,
    season_number: int, team_rating: float, current_group_rating: float | None,
    team_players_for_cap: list[Player],
) -> FAOfferResult:
    cap_space_before = contracts.team_cap_space(team_players_for_cap, season_number)
    if offered_aav > cap_space_before:
        return FAOfferResult(FAOfferVerdict.OVER_CAP, 0.0)

    aav_anchor = contracts.expected_market_value(player, season_number)
    aav_score = min(1.3, offered_aav / aav_anchor) if aav_anchor else 1.0
    role_fit = role_fit_for(player, current_group_rating)
    team_quality = min(1.1, max(0.6, team_rating / 90.0))  # Sec 8.4: "0.6-1.1"

    effect = coaching.staff_effect_for(team_abbr)
    from app.services.season_state import DEFENSIVE_POSITIONS
    coach_dev = effect.dev_multiplier_defense if player.position in DEFENSIVE_POSITIONS else effect.dev_multiplier_offense

    score = W_AAV * aav_score + W_ROLE * role_fit.value + W_TEAM * team_quality + W_COACH * coach_dev
    verdict = FAOfferVerdict.ACCEPT if score >= ACCEPT_THRESHOLD else FAOfferVerdict.REJECT
    return FAOfferResult(verdict, score)


def release_expired_contracts(players: list[Player]) -> int:
    """Sec 8.4's real trigger point: contract_years_remaining hit 0 at
    the season rollover that just decremented it. Mutates in place
    (team_abbr = None); the caller commits. Returns the count released."""
    released = 0
    for p in players:
        if p.contract_years_remaining <= 0 and p.team_abbr is not None:
            p.team_abbr = None
            released += 1
    return released


# Every position depth_chart.py's get_offensive_starters/
# get_defensive_starters unconditionally index (starters[0]/[1] with no
# None-safe fallback, unlike WR3/backups) -- a real, disclosed
# requirement this module enforces so the sim never runs a team with
# zero players at one of these, not a GDD-specified roster-minimum rule.
MIN_ROSTER_COUNTS: dict[Position, int] = {
    Position.QB: 1, Position.HB: 1, Position.WR: 2, Position.TE: 1,
    Position.LT: 1, Position.LG: 1, Position.C: 1, Position.RG: 1, Position.RT: 1,
    Position.K: 1, Position.P: 1,
    Position.DT: 2, Position.LE: 1, Position.RE: 1,
    Position.LOLB: 1, Position.MLB: 1, Position.ROLB: 1,
    Position.CB: 2, Position.FS: 1, Position.SS: 1,
}


def fill_roster_gaps(team_abbr: str, roster: list[Player], free_agent_pool: list[Player],
                      season_number: int) -> list[Player]:
    """Emergency AI signings, run for every team right after
    release_expired_contracts() each offseason (never for the user's own
    team via a user action -- this is the automated "the league doesn't
    let a roster spot sit truly empty" backstop, the real-world
    equivalent of a practice-squad call-up or a street free agent
    signing that this engine doesn't model in that level of detail).
    Signs the single best-rated available free agent at each position
    where `roster` is short of MIN_ROSTER_COUNTS, removing each signee
    from `free_agent_pool` in place so a caller processing multiple
    teams against the SAME shared pool never double-signs one player.
    Real, deterministic pay (expected_market_value), a real 2-year
    term. Returns the list of newly-signed players (mutated in place;
    the caller commits). A position with truly nobody left in the whole
    league's free-agent pool stays unfilled -- a real, disclosed edge
    case (this function can't conjure a player that doesn't exist), not
    silently hidden."""
    signed: list[Player] = []
    counts = Counter(p.position for p in roster)
    for position, minimum in MIN_ROSTER_COUNTS.items():
        deficit = minimum - counts.get(position, 0)
        for _ in range(max(0, deficit)):
            candidates = [fa for fa in free_agent_pool if fa.position == position]
            if not candidates:
                break
            best = max(candidates, key=lambda p: p.overall_rating)
            best.team_abbr = team_abbr
            best.salary = round(contracts.expected_market_value(best, season_number))
            best.contract_years_remaining = 2
            free_agent_pool.remove(best)
            signed.append(best)
    return signed

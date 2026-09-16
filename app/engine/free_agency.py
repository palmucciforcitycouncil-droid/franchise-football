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
from app.engine.rng import RNG, stable_seed
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
# Guaranteed money's real effect on acceptance (Brian's ask, 2026-09-13)
# is an ADDITIVE bonus on top of the four weights above, not a 5th
# weight carved out of their existing 1.0 total -- same reasoning as
# contracts.py's own W_GUARANTEED_BONUS (see that constant's docstring):
# an unguaranteed offer (offered_guaranteed=0) must score EXACTLY as it
# did before this existed.
W_GUARANTEED_BONUS = 0.10
# Same real, documented anchor as contracts.py's own FULL_GUARANTEE_FRACTION.
FULL_GUARANTEE_FRACTION = 0.5
# Negotiation layer bands (app/engine/negotiation.py, 2026-09-14): a
# "Considering" offer gets a seeded chance to sign; anything from the
# Lowball band up draws a counter-offer instead of a flat rejection.
CONSIDERING_FLOOR = 0.90
COUNTER_THRESHOLD = 0.80


def negotiation_model(player: Player, season_number: int):
    """This module's thresholds/AAV weight for the mood layer, which runs
    on top of evaluate_fa_offer()'s unchanged raw score (OVER_CAP is still
    decided before any of it)."""
    from app.engine.negotiation import ScoreModel
    return ScoreModel(
        accept_threshold=ACCEPT_THRESHOLD, counter_threshold=COUNTER_THRESHOLD,
        considering_floor=CONSIDERING_FLOOR, w_aav=W_AAV,
        expected_aav=contracts.expected_market_value(player, season_number), reaction=fa_offer_reaction,
    )


def fa_offer_reaction(score: float) -> str:
    """Same purpose as contracts.offer_reaction() (live negotiation-UI
    feedback, Brian's ask 2026-09-13) but scaled around THIS module's own
    real ACCEPT_THRESHOLD (1.00, not contracts.py's 0.97) -- reusing
    contracts.py's band offsets against a different threshold would
    silently mislabel scores near the boundary (e.g. a 0.98 here is a
    real REJECT, not "Interested"). evaluate_fa_offer() itself still only
    says ACCEPT/REJECT/OVER_CAP; the counter-offer and the Considering
    band's chance to sign come from app/engine/negotiation.py on top."""
    if score >= 1.10:
        return "Very Interested"
    if score >= ACCEPT_THRESHOLD:
        return "Interested"
    if score >= CONSIDERING_FLOOR:
        return "Considering"
    if score >= COUNTER_THRESHOLD:
        return "Lowball"
    return "Not Interested"


def evaluate_fa_offer(
    player: Player, team_abbr: str, offered_aav: float, offered_years: int,
    season_number: int, team_rating: float, current_group_rating: float | None,
    team_players_for_cap: list[Player], offered_guaranteed: float = 0.0,
) -> FAOfferResult:
    """offered_guaranteed (Brian's ask, 2026-09-13): scored as a fraction
    of the total contract value against FULL_GUARANTEE_FRACTION, same
    shape/anchor as contracts.evaluate_offer()'s own guaranteed term.
    Defaults to 0 (an unguaranteed offer, still real and scoreable)."""
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

    total_value = offered_aav * offered_years
    guaranteed_fraction = (offered_guaranteed / total_value) if total_value else 0.0
    guaranteed_points = min(1.0, guaranteed_fraction / FULL_GUARANTEE_FRACTION)

    score = (
        W_AAV * aav_score + W_ROLE * role_fit.value + W_TEAM * team_quality + W_COACH * coach_dev
        + W_GUARANTEED_BONUS * guaranteed_points
    )
    verdict = FAOfferVerdict.ACCEPT if score >= ACCEPT_THRESHOLD else FAOfferVerdict.REJECT
    return FAOfferResult(verdict, score)


# Sec 8.4's own real 0.6-1.1 band, reused here as the resign roll's real
# floor/ceiling -- the same "team quality" bounds evaluate_fa_offer()
# scores an OUTSIDE offer against also bound how eager a team is to keep
# its OWN player.
RESIGN_CHANCE_FLOOR = 0.15
RESIGN_CHANCE_CEILING = 0.95


def run_ai_resign_decisions(players: list[Player], season_number: int, exclude_team_abbr: str | None = None) -> int:
    """The offseason's contract-resigning window (Brian's ask,
    2026-09-13): every AI team (all but `exclude_team_abbr`, the user's
    own -- they get the real interactive GM Desk Negotiation flow
    instead, gated by season_state's "resign" offseason_stage) makes its own
    resign-or-release call for each of its players whose
    contract_years_remaining just hit 0 (season_state.
    apply_progression_to_roster's decrement, run BEFORE this -- see that
    function's own docstring for why it no longer auto-releases).

    A deterministic seeded roll per player (stable_seed/RNG, same
    convention as the rest of the engine), not a coin flip: a team only
    considers a re-sign it can actually afford (offered_aav <= its real
    cap space, contracts.team_cap_space -- re-checked fresh before each
    player since an earlier re-sign in the same team spends real cap for
    the next one), and the chance itself scales with the player's real
    overall_rating -- a clear starter is kept far more often than a
    replacement-level rookie-deal afterthought. Declining simply leaves
    the player at 0 years for release_expired_contracts() (the caller's
    next step) to pick up -- this function never sets team_abbr = None
    itself, and never touches the excluded team's players at all.

    Returns the number of players actually re-signed."""
    by_team: dict[str, list[Player]] = {}
    for p in players:
        if p.team_abbr and p.team_abbr != exclude_team_abbr and p.contract_years_remaining <= 0:
            by_team.setdefault(p.team_abbr, []).append(p)

    resigned = 0
    for team_abbr, expiring in by_team.items():
        team_roster = [p for p in players if p.team_abbr == team_abbr]
        # Best players first: a cap-strapped team that can't keep
        # everyone should spend its remaining room on its best expiring
        # player, not whichever happens to be evaluated first.
        for player in sorted(expiring, key=lambda p: -p.overall_rating):
            aav = contracts.expected_market_value(player, season_number)
            cap_space = contracts.team_cap_space(team_roster, season_number)
            if aav <= 0 or aav > cap_space:
                continue
            rng = RNG.with_seed(stable_seed(season_number, team_abbr, player.player_id, "ai_resign"))
            resign_chance = min(
                RESIGN_CHANCE_CEILING,
                max(RESIGN_CHANCE_FLOOR, (player.overall_rating - 55) / 60),
            )
            if rng.prob(resign_chance):
                player.salary = round(aav)
                player.contract_years_remaining = 3 if player.overall_rating >= 85 else 2
                resigned += 1
    return resigned


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
    Position.T: 2, Position.G: 2, Position.C: 1,
    Position.K: 1, Position.P: 1,
    Position.DT: 2, Position.EDGE: 2,
    Position.LB: 3,
    Position.CB: 2, Position.S: 2,
}


# The league-wide ROSTER REQUIREMENT (Brian's ask, 2026-09-14): what every
# team must carry before its first preseason game -- the preseason roster
# gate (app/services/roster_prep.py), the Roster page's Team Quota pills,
# and the post-draft free-agent pool guarantee all read this one table.
# A realistic 38-man core (a real 53-man roster carries more, but these are
# the counts a team genuinely can't take the field without), every entry
# >= MIN_ROSTER_COUNTS above so meeting it always satisfies the sim too.
ROSTER_REQUIREMENTS: dict[Position, int] = {
    Position.QB: 2, Position.HB: 2, Position.WR: 5, Position.TE: 2,
    Position.T: 3, Position.G: 3, Position.C: 2,
    Position.EDGE: 3, Position.DT: 3, Position.LB: 4,
    Position.CB: 4, Position.S: 3,
    Position.K: 1, Position.P: 1,
}

ACQ_FREE_AGENT = "Free Agent"
ACQ_UNDRAFTED_FA = "Undrafted FA"

# R16 (docs/R16_PRACTICE_SQUAD_ROSTER_IR_SPECIFICATION.md Sec 2, decisions
# #1/#2): the real 53-man active-roster cap (moved here from app/main.py,
# where it lived as an unenforced display-only constant -- ENFORCED for
# the first time by this feature) and the 16-slot practice squad.
MAX_ROSTER_SIZE = 53
PRACTICE_SQUAD_SIZE = 16


def roster_shortfall(roster: list[Player], requirements: dict[Position, int] | None = None) -> dict[Position, int]:
    """{position: how many more players `roster` needs}, only positions
    actually short, in the requirement table's own order. R16: callers
    building `roster` must already filter to roster_status == ACTIVE --
    this function itself stays a pure count over whatever list it's
    given, same as before (see this module's own R16 call sites, and
    app/services/roster_prep.py's, for the real filtering)."""
    requirements = ROSTER_REQUIREMENTS if requirements is None else requirements
    counts = Counter(p.position for p in roster)
    return {pos: need - counts.get(pos, 0) for pos, need in requirements.items() if counts.get(pos, 0) < need}


def mark_free_agent_acquisition(player: Player, season_year: int, was_undrafted: bool) -> None:
    """Acquisition tracking for any free-agent signing (user offer or AI
    hole fill). A re-sign of a team's own player never calls this -- the
    original draft/trade/FA acquisition stays the player's real origin."""
    player.acquisition_type = ACQ_UNDRAFTED_FA if was_undrafted else ACQ_FREE_AGENT
    player.acquisition_season = season_year
    player.acquisition_round = None
    player.acquisition_pick = None
    player.acquisition_team = None


def fill_roster_gaps(team_abbr: str, roster: list[Player], free_agent_pool: list[Player],
                      season_number: int, requirements: dict[Position, int] | None = None,
                      undrafted_ids: set[str] | None = None) -> list[Player]:
    """AI hole-filling signings -- the same logic for every AI team AND
    for the user's own team when they press Auto-Fill Roster on the
    preseason roster gate (Brian's ask, 2026-09-14: "the user team hole
    filling can follow the same logic as the AI"). Run right after
    release_expired_contracts() each offseason against MIN_ROSTER_COUNTS
    (the sim's hard floor, the default), and again before preseason
    against ROSTER_REQUIREMENTS.

    Cap-aware: for each missing slot, signs the best-rated free agent at
    that position whose market value (expected_market_value) fits the
    team's real cap space after reserving a veteran minimum for every
    other slot still to fill. If nobody fits, the hole is still filled --
    by the cheapest available player, at no more than what's left (never
    below the veteran minimum) -- because a team that can't field a
    position is a worse outcome than a team a sliver over the cap; this
    is the real-world "street free agent at the minimum" signing. Terms:
    2 years for a 65+ OVR player, 1 otherwise.

    Removes each signee from `free_agent_pool` in place so teams sharing
    one pool never double-sign. Stamps acquisition fields (Undrafted FA
    when the player's id is in `undrafted_ids`). Returns the newly-signed
    players (mutated in place; the caller commits). A position with truly
    nobody left in the pool stays unfilled -- disclosed, not hidden (the
    post-draft pool guarantee in roster_prep.py is what keeps that from
    happening in practice)."""
    from app.config import season_year
    from app.models.player import RosterStatus

    requirements = MIN_ROSTER_COUNTS if requirements is None else requirements
    undrafted_ids = undrafted_ids or set()
    # R16 Sec 9: shortfall counts ACTIVE bodies only (a full practice
    # squad must never silently satisfy a position minimum) -- but
    # `roster` itself stays the FULL roster (ACTIVE + PS + IR) for cap
    # math right below, since PS/IR salaries count against the cap too
    # (decision #3/#12). Filtering `roster` itself for this whole
    # function would be the exact wrong-direction mistake the spec
    # warns about.
    active_roster = [p for p in roster if p.roster_status == RosterStatus.ACTIVE]
    shortfall = roster_shortfall(active_roster, requirements)
    slots_left = sum(shortfall.values())
    cap_space = contracts.team_cap_space(roster, season_number)
    signed: list[Player] = []
    for position, deficit in shortfall.items():
        for _ in range(deficit):
            slots_left -= 1
            candidates = [fa for fa in free_agent_pool if fa.position == position]
            if not candidates:
                break
            budget = cap_space - slots_left * contracts.veteran_minimum(0, season_number)
            market = {c.player_id: contracts.expected_market_value(c, season_number) for c in candidates}
            affordable = [c for c in candidates if market[c.player_id] <= budget]
            if affordable:
                choice = max(affordable, key=lambda p: (p.overall_rating, p.player_id))
                salary = market[choice.player_id]
            else:
                choice = min(candidates, key=lambda p: (market[p.player_id], -p.overall_rating, p.player_id))
                salary = max(contracts.veteran_minimum(choice.years_pro, season_number), min(market[choice.player_id], budget))
            choice.team_abbr = team_abbr
            choice.roster_status = RosterStatus.ACTIVE  # R16: this fills an ACTIVE-roster hole, never PS/IR
            choice.salary = round(salary)
            choice.contract_years_remaining = 2 if choice.overall_rating >= 65 else 1
            mark_free_agent_acquisition(choice, season_year(season_number), choice.player_id in undrafted_ids)
            cap_space -= choice.salary
            free_agent_pool.remove(choice)
            signed.append(choice)
    return signed


def fill_practice_squad_gaps(team_abbr: str, roster: list[Player], free_agent_pool: list[Player],
                              season_number: int) -> list[Player]:
    """R16 Sec 4.3: the practice-squad sibling to fill_roster_gaps() --
    same "best-rated fit from the shared pool" selection, but targets
    open PS slots (up to PRACTICE_SQUAD_SIZE) rather than a position
    shortfall, and signs at the flat league minimum (decision #10:
    veteran_minimum(0, ...) -- the SAME real minimum-salary floor
    fill_roster_gaps() already anchors to, at 0 years of service so
    it's flat regardless of the signee's real experience) instead of
    market value. No cap-juggling needed in practice (PS minimums are
    small relative to the cap), but still deducted from cap room per
    decision #3/#12 -- a team already tight on cap space can still run
    out of room for practice-squad bodies, same as any other signing.

    Removes each signee from `free_agent_pool` in place, same contract
    as fill_roster_gaps(). Best-rated-first across ALL open positions
    (not position-need-aware like the active-roster fill -- a practice
    squad's whole point is organizational depth, not filling a specific
    need)."""
    from app.config import season_year
    from app.models.player import RosterStatus

    open_slots = PRACTICE_SQUAD_SIZE - sum(1 for p in roster if p.roster_status == RosterStatus.PRACTICE_SQUAD)
    if open_slots <= 0:
        return []
    cap_space = contracts.team_cap_space(roster, season_number)
    flat_salary = round(contracts.veteran_minimum(0, season_number))
    pool = sorted(free_agent_pool, key=lambda p: (-p.overall_rating, p.player_id))
    signed: list[Player] = []
    for choice in pool:
        if len(signed) >= open_slots:
            break
        if flat_salary > cap_space:
            break
        choice.team_abbr = team_abbr
        choice.roster_status = RosterStatus.PRACTICE_SQUAD
        choice.salary = flat_salary
        choice.contract_years_remaining = 1
        mark_free_agent_acquisition(choice, season_year(season_number), was_undrafted=False)
        cap_space -= flat_salary
        free_agent_pool.remove(choice)
        signed.append(choice)
    return signed

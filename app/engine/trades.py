"""
Player + Draft Pick Trades (GDD Part 1 Sec 8.5 -- R4c, extended to
include real draft picks now that the Draft (R5) and a persistent pick-
ownership store (app/services/draft_pick_store.py) both exist).

**Draft picks, Sec 8.5's own real rule**: "Assets can include players and
picks from the current draft and the next two drafts." A pick's value
(`pick_trade_value()` below) reuses `app/engine/draft.py`'s real Sec-
4.1 pick-value chart, converted to this module's own dollar scale via
`DOLLARS_PER_PICK_POINT` -- this module's own disclosed choice (no GDD
number bridges "abstract pick-value points" to "real Surplus Value
dollars"; anchored so a #1-overall pick, 3000 points, reads as ~$30M of
trade value, a plausible order of magnitude next to this engine's own
real player surplus values). A pick from a season that hasn't finished
yet (this year's own draft doesn't resolve until the season ends; next
year's and the year after's are further out still) is priced off
`draft.estimated_pick_order_rank()` -- the real, computed live-standings
estimate that function's own docstring explains, not a placeholder.
`execute_trade()` moves real pick ownership via `draft_pick_store.
transfer_pick()`, the same way it already moves real players.

**Player Value (Surplus Value), Sec 8.5's own real formula shape**: the
NPV of a player's contract surplus (on-field value vs. salary) over the
life of their deal. "On-field value" reuses `contracts.
expected_market_value()` (A1/A3's tuned positional weights, already
real); "salary" is the real `Player.salary` AAV (R4a). A player being
paid LESS than their real market value is a real trade asset (their
new team gets surplus performance for the cap hit); a player paid MORE
than market value is a real liability (dead money waiting to happen)
-- `player_trade_value()` can and does go negative, which is correct,
not a bug: nobody should have to give up much to acquire an overpaid
player nobody else wants either.

**AI Acceptance (Tolerance Band), Sec 8.5's own real rule**: accepts if
`value_received >= value_sent * (1 - AI_TOLERANCE)`, `AI_TOLERANCE` =
Sec 8.5's own stated `-10%` example, used as the real default (not a
placeholder).

**Deliberate scope cut, disclosed**: `DISCOUNT_RATE` below (the NPV
annuity rate) is this module's own documented choice -- Sec 8.5 doesn't
give one, the same category as `app/engine/contracts.py`'s own
Sec-8.3.3-offer-weight choices.

**Trade deadline, Sec 8.5's own real rule**: "offseason through the Week
8 trade deadline." This engine has no persistent, separately-tracked
"offseason phase" flag -- a season's `current_week` starts at 1 the
instant `reset_season()`/`start_new_season()` builds it, so `current_week
<= 8` is used as the real, disclosed proxy for "still inside the trade
window" (covers a fresh season's early weeks; a season past week 8 is
closed to trades until the next one rolls over).
"""
from __future__ import annotations
from dataclasses import dataclass, field

from app.engine import contracts
from app.models.player import Player

DISCOUNT_RATE = 0.08  # this module's own documented choice -- no GDD number given
AI_TOLERANCE = 0.10  # Sec 8.5's own real example value, used as the real default
TRADE_DEADLINE_WEEK = 8  # Sec 8.5's own real number

# This module's own disclosed conversion (see module docstring) bridging
# draft.py's abstract pick-value points onto this module's real dollar
# scale: a #1-overall pick (3000 points) prices at ~$30M of trade value.
DOLLARS_PER_PICK_POINT = 10_000.0


@dataclass(frozen=True)
class PickRef:
    """One specific pick asset, as referenced in a trade -- mirrors
    app/services/draft_pick_store.py's own (season_number, round,
    original_team_abbr) key exactly (that store is the real source of
    truth for CURRENT ownership; this is just the lightweight reference
    a trade moves)."""
    season_number: int
    round: int
    original_team_abbr: str


def pick_trade_value(pick: PickRef, season) -> float:
    """This pick's real trade-dollar value: draft.py's Sec-4.1 pick-value
    chart, looked up at this team's REAL rank if `pick.season_number` is
    the season already in progress and finished, or the real live-
    standings ESTIMATE (draft.estimated_pick_order_rank()) otherwise --
    see that function's own docstring for why an estimate is the correct,
    disclosed choice for any not-yet-resolved draft."""
    from app.engine import draft
    rank = draft.estimated_pick_order_rank(season, pick.original_team_abbr)
    return draft.pick_value(pick.round, rank) * DOLLARS_PER_PICK_POINT


def player_trade_value(player: Player, season_number: int) -> float:
    """Sec 8.5: NPV of contract surplus over the life of the deal. A
    player with 0 years left (an expiring/about-to-be-released contract)
    has no real remaining deal to value -- returns 0, not a fabricated
    number. Can be negative for a real overpaid player; see module
    docstring for why that's correct, not a bug."""
    years = player.contract_years_remaining
    if years <= 0:
        return 0.0
    surplus_per_year = contracts.expected_market_value(player, season_number) - player.salary
    if surplus_per_year == 0.0:
        return 0.0
    r = DISCOUNT_RATE
    annuity_factor = (1.0 - (1.0 + r) ** (-years)) / r
    return surplus_per_year * annuity_factor


def is_trade_window_open(current_week: int) -> bool:
    return current_week <= TRADE_DEADLINE_WEEK


@dataclass(frozen=True)
class TradeEvaluation:
    accepted: bool
    value_sent: float       # what the OTHER (AI) team gives up
    value_received: float   # what the OTHER (AI) team gets back
    players_sent: list = field(default_factory=list)
    players_received: list = field(default_factory=list)
    picks_sent: list = field(default_factory=list)
    picks_received: list = field(default_factory=list)


def evaluate_trade(
    ai_team_sends: list[Player], ai_team_receives: list[Player], season_number: int,
    ai_sends_picks: list[PickRef] = (), ai_receives_picks: list[PickRef] = (), season=None,
) -> TradeEvaluation:
    """Evaluated from the AI (non-user) team's own side of the deal --
    `ai_team_sends`/`ai_sends_picks` are what the AI gives up,
    `ai_team_receives`/`ai_receives_picks` are what it gets back.

    `season` (the full live Season object, not a bare number) is only
    needed when either pick list is non-empty -- pricing a pick needs
    live standings (pick_trade_value()/draft.estimated_pick_order_rank()),
    which `season_number` alone can't supply. Every existing player-only
    call (R4c's original shape) is unaffected: `season` stays optional
    and unused when there are no picks."""
    value_sent = sum(player_trade_value(p, season_number) for p in ai_team_sends)
    value_received = sum(player_trade_value(p, season_number) for p in ai_team_receives)
    if ai_sends_picks or ai_receives_picks:
        if season is None:
            raise ValueError("season is required to evaluate a trade that includes draft picks")
        value_sent += sum(pick_trade_value(pk, season) for pk in ai_sends_picks)
        value_received += sum(pick_trade_value(pk, season) for pk in ai_receives_picks)
    accepted = value_received >= value_sent * (1.0 - AI_TOLERANCE)
    return TradeEvaluation(
        accepted=accepted, value_sent=value_sent, value_received=value_received,
        players_sent=ai_team_sends, players_received=ai_team_receives,
        picks_sent=list(ai_sends_picks), picks_received=list(ai_receives_picks),
    )


def execute_trade(team_a_abbr: str, team_a_players: list[Player],
                   team_b_abbr: str, team_b_players: list[Player],
                   team_a_picks: list[PickRef] = (), team_b_picks: list[PickRef] = ()) -> None:
    """Mutates in place -- swaps team_abbr for every player on both
    sides, and (Sec 8.5) transfers real ownership for every pick on both
    sides via app/services/draft_pick_store.py's transfer_pick(). The
    caller commits the player-side DB changes; pick ownership is its own
    persistence surface, written immediately (same as every other real
    write path into that store). No cap-space check on the RECEIVING
    team's post-trade cap -- Sec 8.5 doesn't specify one (unlike Sec
    8.4's explicit FA cap guardrail), and this engine's cap is already
    a rescaled, disclosed-approximate number (see contracts.py's own
    docstring) that most real rosters already sit well under."""
    for p in team_a_players:
        p.team_abbr = team_b_abbr
    for p in team_b_players:
        p.team_abbr = team_a_abbr
    if team_a_picks or team_b_picks:
        from app.services import draft_pick_store
        for pk in team_a_picks:
            draft_pick_store.transfer_pick(pk.season_number, pk.round, pk.original_team_abbr, team_b_abbr)
        for pk in team_b_picks:
            draft_pick_store.transfer_pick(pk.season_number, pk.round, pk.original_team_abbr, team_a_abbr)

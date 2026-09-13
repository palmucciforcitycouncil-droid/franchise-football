"""
Player Trades (GDD Part 1 Sec 8.5 -- R4c).

**No draft picks.** Sec 8.5's fuller design lets a trade include picks
from "the current draft and the next two drafts." R5 (the Draft) exists
now, but it runs fully automatically each offseason from that season's
own standings (app/engine/draft.py's `generate_draft_class()`/
`simulate_draft()`) -- there's no persistent "Team X owns the 2027 1st
overall" record anywhere to trade, since pick ownership was never
modeled as a standing, transferable asset. Every trade here is still
player(s)-for-player(s) only; the reason has shifted from "no Draft
exists" to "the Draft doesn't track pick ownership as tradeable
inventory."

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


def trade_block_interest(value: float, season_number: int) -> str:
    """"High"/"medium" label for the GM Desk Trade Block panel (Brian's
    ask, 2026-09-13). A real, disclosed simplification: this engine has
    no "a team explicitly made this player available" concept anywhere,
    so the Trade Block surfaces real rostered players around the league
    with the best real Surplus Value (player_trade_value()) -- genuinely
    good bargains worth inquiring about, not a fabricated "on the block"
    flag. The threshold is a FRACTION of that season's real salary cap
    (not a fixed dollar figure) so it stays meaningful as the cap
    compounds every season (contracts.py's own SALARY_CAP_GROWTH) rather
    than becoming trivially true (or never true) 20 seasons in."""
    cap = contracts.salary_cap_for_season(season_number)
    return "high" if value >= cap * 0.01 else "medium"


@dataclass(frozen=True)
class TradeEvaluation:
    accepted: bool
    value_sent: float       # what the OTHER (AI) team gives up
    value_received: float   # what the OTHER (AI) team gets back
    players_sent: list = field(default_factory=list)
    players_received: list = field(default_factory=list)


def evaluate_trade(
    ai_team_sends: list[Player], ai_team_receives: list[Player], season_number: int,
) -> TradeEvaluation:
    """Evaluated from the AI (non-user) team's own side of the deal --
    `ai_team_sends` are the players the AI gives up, `ai_team_receives`
    are the players the AI gets in return."""
    value_sent = sum(player_trade_value(p, season_number) for p in ai_team_sends)
    value_received = sum(player_trade_value(p, season_number) for p in ai_team_receives)
    accepted = value_received >= value_sent * (1.0 - AI_TOLERANCE)
    return TradeEvaluation(
        accepted=accepted, value_sent=value_sent, value_received=value_received,
        players_sent=ai_team_sends, players_received=ai_team_receives,
    )


def execute_trade(team_a_abbr: str, team_a_players: list[Player],
                   team_b_abbr: str, team_b_players: list[Player]) -> None:
    """Mutates in place -- swaps team_abbr for every player on both
    sides. The caller commits. No cap-space check on the RECEIVING
    team's post-trade cap -- Sec 8.5 doesn't specify one (unlike Sec
    8.4's explicit FA cap guardrail), and this engine's cap is already
    a rescaled, disclosed-approximate number (see contracts.py's own
    docstring) that most real rosters already sit well under."""
    for p in team_a_players:
        p.team_abbr = team_b_abbr
    for p in team_b_players:
        p.team_abbr = team_a_abbr

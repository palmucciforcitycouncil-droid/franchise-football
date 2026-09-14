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

**Positional need (Brian's ask, 2026-09-13), a real, disclosed addition
with no direct GDD Sec 8.5 formula** -- that section prices a trade by
Surplus Value alone, with no notion of "does this team actually need
this position." Without it, the original Trade Block leaderboard (and
evaluate_trade()'s pure dollar comparison) put literal untouchable stars
up for grabs the instant their real surplus value was high -- a
thriving team's own franchise QB, paid at or below true market value, is
exactly the kind of player real Surplus Value ranks #1, but no real
front office would ever consider moving him. See `_best_other_ovr_at_
position()`/`giving_up_need_multiplier()`/`receiving_need_multiplier()`
below for the real mechanism -- both directions share one primitive,
"how good is this team's OWN best answer at this exact position, apart
from one specific player," so a team can genuinely give up a well-
regarded player at a position where it has a ready replacement in order
to fill a real hole somewhere else, the same way a real front office
does.

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

from sqlmodel import select

from app.core.db import get_session
from app.engine import contracts
from app.models.player import Player, Position

DISCOUNT_RATE = 0.08  # this module's own documented choice -- no GDD number given
AI_TOLERANCE = 0.10  # Sec 8.5's own real example value, used as the real default
TRADE_DEADLINE_WEEK = 8  # Sec 8.5's own real number

# This module's own disclosed conversion (see module docstring) bridging
# draft.py's abstract pick-value points onto this module's real dollar
# scale: a #1-overall pick (3000 points) prices at ~$30M of trade value.
DOLLARS_PER_PICK_POINT = 10_000.0

# Positional need (see module docstring) -- shared tuning for both the
# Trade Block's "is this player replaceable" gate and evaluate_trade()'s
# own need-weighted ACCEPT/REJECT math.
NEED_SENSITIVITY = 0.03  # this module's own tuned constant: a 20-point real OVR gap swings the multiplier the full +/-60%
NEED_MULTIPLIER_MIN = 0.4
NEED_MULTIPLIER_MAX = 1.6
UNLIKELY_RESIGN_THRESHOLD = 0.35  # below-even-odds real resign chance (free_agency.py's own RESIGN_CHANCE formula) -- "this team probably lets him walk"


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


def _best_other_ovr_at_position(team_abbr: str, position: Position, exclude_player_id: str | None) -> float:
    """This team's own best real overall_rating at `position`, ignoring
    one specific player if given. 0.0 if nobody else is rostered there
    (a real, disclosed floor -- an empty depth chart is a real, total
    need, not an edge case to special-case away)."""
    with get_session() as s:
        roster = list(s.exec(select(Player).where(Player.team_abbr == team_abbr, Player.position == position)))
    ratings = [p.overall_rating for p in roster if p.player_id != exclude_player_id]
    return float(max(ratings)) if ratings else 0.0


def _is_depth_chart_starter(player: Player) -> bool:
    """Whether `player` is the REAL starter at his own exact position
    slot -- the same resolved order (real user overrides included)
    roster_strength.py's own snap-share rating already reads, so "who's
    the starter" here always agrees with the Roster/Depth Chart pages.
    A team's OWN best player at a position is not automatically the
    starter if the user has overridden the order -- this asks the real
    resolved chart, not just "who has the highest OVR here."""
    from app.services import depth_chart_overrides

    with get_session() as s:
        teammates = list(s.exec(select(Player).where(
            Player.team_abbr == player.team_abbr, Player.position == player.position,
        )))
    ordered = depth_chart_overrides.resolve_order(player.team_abbr, player.position.value, teammates)
    return bool(ordered) and ordered[0].player_id == player.player_id


def _need_multiplier(gap: float) -> float:
    """A positive gap (losing this player leaves a real hole behind, or
    gaining them is a real upgrade over what's already on hand) raises
    perceived value up to NEED_MULTIPLIER_MAX; a negative gap (a ready
    replacement is already on the roster, or the addition is redundant)
    lowers it down to NEED_MULTIPLIER_MIN."""
    return max(NEED_MULTIPLIER_MIN, min(NEED_MULTIPLIER_MAX, 1.0 + gap * NEED_SENSITIVITY))


def giving_up_need_multiplier(player: Player) -> float:
    """How much it hurts `player.team_abbr` to give up `player`, beyond
    his raw Surplus Value. A player who ISN'T his own team's real
    depth-chart starter leaves no hole at all if traded away -- he's
    real backup depth, the cheapest possible player to part with,
    regardless of how close his own rating happens to sit to the
    starter's (a comparison that would otherwise wrongly flag the
    STARTER too whenever the backup is nearly as good). Only the actual
    starter's own multiplier scales with how big a real gap he'd leave
    behind (`_best_other_ovr_at_position()` against his own backup)."""
    if player.team_abbr is None:
        return 1.0
    if not _is_depth_chart_starter(player):
        return NEED_MULTIPLIER_MIN
    best_left_behind = _best_other_ovr_at_position(player.team_abbr, player.position, player.player_id)
    gap = player.overall_rating - best_left_behind
    return _need_multiplier(gap)


def receiving_need_multiplier(player: Player, receiving_team_abbr: str) -> float:
    """How much `receiving_team_abbr` values ACQUIRING `player`, beyond
    his raw Surplus Value -- high if he clearly beats their current best
    at his exact position (a real need), low if they already have
    someone as good or better there (a redundant addition). This side
    stays a plain OVR comparison (no starter/backup asymmetry needed):
    an incoming player is either an upgrade over what's already there
    or he isn't, independent of anyone's CURRENT depth-chart slot."""
    current_best = _best_other_ovr_at_position(receiving_team_abbr, player.position, None)
    gap = player.overall_rating - current_best
    return _need_multiplier(gap)


def trade_block_availability(player: Player, season_number: int) -> str | None:
    """Real, disclosed reason `player`'s own team would plausibly listen
    on offers (Brian's ask, 2026-09-13, replacing the original all-
    comers Surplus-Value leaderboard): either real positional surplus
    (he isn't his own team's real depth-chart starter at his position --
    the same signal `giving_up_need_multiplier()` uses for a live
    trade's own ACCEPT/REJECT math, so the Trade Block and the AI's real
    evaluation never disagree about who's actually replaceable), or a
    real expiring contract this team is unlikely to renew (free_agency.
    py's own resign-chance formula, read-only -- never mutates
    anything). Returns None, on purpose, for most players: not every
    team has to have a real reason to listen, and this engine has no
    "explicitly on the block" flag to fall back on for the rest. A
    team's actual starter (Josh Allen at BUF, say) is never flagged by
    the surplus reason alone, no matter how good his own backup is --
    only an expiring, unlikely-to-be-renewed deal can put a real starter
    here, matching how real front offices actually operate."""
    from app.engine import free_agency

    if player.team_abbr is not None and not _is_depth_chart_starter(player):
        return "Positional surplus"

    if player.contract_years_remaining <= 1:
        resign_chance = min(
            free_agency.RESIGN_CHANCE_CEILING,
            max(free_agency.RESIGN_CHANCE_FLOOR, (player.overall_rating - 55) / 60),
        )
        if resign_chance <= UNLIKELY_RESIGN_THRESHOLD:
            return "Expiring, unlikely to be re-signed"

    return None


def trade_reaction(score: float) -> str:
    """Live Propose Trade panel feedback (Brian's ask, 2026-09-13) --
    same purpose/shape as free_agency.fa_offer_reaction() but scaled
    around THIS module's own real accept threshold, `1.0 - AI_TOLERANCE`
    (0.90), not fa_offer's 1.00 -- a 0.92 score here is a real ACCEPT,
    not merely "Considering"."""
    if score >= 1.20:
        return "Very Interested"
    if score >= (1.0 - AI_TOLERANCE):
        return "Interested"
    if score >= 0.75:
        return "Considering"
    if score >= 0.55:
        return "Lowball"
    return "Not Interested"


@dataclass(frozen=True)
class TradeEvaluation:
    accepted: bool
    value_sent: float       # what the OTHER (AI) team gives up, need-weighted
    value_received: float   # what the OTHER (AI) team gets back, need-weighted
    players_sent: list = field(default_factory=list)
    players_received: list = field(default_factory=list)
    picks_sent: list = field(default_factory=list)
    picks_received: list = field(default_factory=list)


def evaluate_trade(
    ai_team_sends: list[Player], ai_team_receives: list[Player], season_number: int,
    ai_sends_picks: list[PickRef] = (), ai_receives_picks: list[PickRef] = (), season=None,
    ai_team_abbr: str | None = None,
) -> TradeEvaluation:
    """Evaluated from the AI (non-user) team's own side of the deal --
    `ai_team_sends`/`ai_sends_picks` are what the AI gives up,
    `ai_team_receives`/`ai_receives_picks` are what it gets back.

    `season` (the full live Season object, not a bare number) is only
    needed when either pick list is non-empty -- pricing a pick needs
    live standings (pick_trade_value()/draft.estimated_pick_order_rank()),
    which `season_number` alone can't supply. Every existing player-only
    call (R4c's original shape) is unaffected: `season` stays optional
    and unused when there are no picks.

    `ai_team_abbr` (Brian's ask, 2026-09-13) turns on real positional-
    need weighting (see module docstring) -- omitted, every player still
    prices at plain Surplus Value, the original R4c behavior (picks
    never carry a need multiplier; Sec 8.5 gives no positional concept
    for an abstract draft slot to be "needed" at)."""
    def _sent_value(p: Player) -> float:
        base = player_trade_value(p, season_number)
        if ai_team_abbr is None:
            return base
        return base * giving_up_need_multiplier(p)

    def _received_value(p: Player) -> float:
        base = player_trade_value(p, season_number)
        if ai_team_abbr is None:
            return base
        return base * receiving_need_multiplier(p, ai_team_abbr)

    value_sent = sum(_sent_value(p) for p in ai_team_sends)
    value_received = sum(_received_value(p) for p in ai_team_receives)
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

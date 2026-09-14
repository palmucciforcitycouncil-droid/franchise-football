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
placeholder). Implemented as a margin against |value_sent| since
2026-09-14 (see ai_accepts()) -- same line for any positive value_sent.

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


# Picks this many draft-years (or more) past the current season carry no
# real standings signal -- see pick_trade_value().
FAR_FUTURE_PICK_OFFSET = 3
LEAGUE_AVERAGE_PICK_RANK = 16


def pick_trade_value(pick: PickRef, season) -> float:
    """This pick's real trade-dollar value: draft.py's Sec-4.1 pick-value
    chart, looked up at this team's REAL rank if `pick.season_number` is
    the season already in progress and finished, or the real live-
    standings ESTIMATE (draft.estimated_pick_order_rank()) otherwise --
    see that function's own docstring for why an estimate is the correct,
    disclosed choice for any not-yet-resolved draft.

    2026-09-14 (5-year pick window): a pick 3+ drafts out, or any pick
    before the original team has played a single game, is priced at the
    league-average slot (rank 16) instead. Live standings say nothing
    about a draft four years away, and with every record at 0-0 the
    "estimate" is just dictionary order -- it would price one arbitrary
    team's picks as the #1 overall. The original 3-draft window with real
    games played is unchanged."""
    from app.engine import draft
    record = season.records.get(pick.original_team_abbr) if getattr(season, "records", None) else None
    games_played = (record.wins + record.losses) if record is not None else 0
    offset = pick.season_number - getattr(season, "season_number", pick.season_number)
    if offset >= FAR_FUTURE_PICK_OFFSET or (record is not None and games_played == 0):
        rank = LEAGUE_AVERAGE_PICK_RANK
    else:
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
    assets: list = field(default_factory=list)  # AssetValue breakdown (reason text, counter offers)


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
    for an abstract draft slot to be "needed" at).

    With BOTH `ai_team_abbr` and `season` given, the AI team's real
    trade profile (team_trade_profile(): rebuilding/contending + its
    starter/backup holes) adds its own bonus on top -- see
    asset_values()."""
    assets = asset_values(ai_team_sends, ai_team_receives, season_number,
                          ai_sends_picks, ai_receives_picks, season, ai_team_abbr)
    value_sent = sum(a.value for a in assets if a.side == "sent")
    value_received = sum(a.value for a in assets if a.side == "received")
    return TradeEvaluation(
        accepted=ai_accepts(value_sent, value_received), value_sent=value_sent, value_received=value_received,
        players_sent=ai_team_sends, players_received=ai_team_receives,
        picks_sent=list(ai_sends_picks), picks_received=list(ai_receives_picks),
        assets=assets,
    )


# --------------------------------------------------------------------
# Propose Trade box rebuild (Brian's ask, 2026-09-14): acceptance
# likelihood, "what they're looking for", verdict reasons, counter offers.
# --------------------------------------------------------------------

# Below this many dollars of real value on the AI's side, the -10%
# tolerance band is measured against this floor instead -- otherwise a
# pick-for-pick swap where both sides price near $0 flips on a few dollars.
MIN_VALUE_SCALE = 500_000.0

# Team-mode bonuses (additive, on top of Surplus Value x need multiplier --
# never a reweighting of either): a rebuilding team really does pay extra
# for draft capital and young players, a contender for proven starters.
REBUILD_PICK_BONUS = 0.20
REBUILD_YOUTH_BONUS = 0.10
REBUILD_YOUTH_MAX_AGE = 25
CONTEND_STARTER_BONUS = 0.10
CONTEND_STARTER_MIN_OVR = 75
# Filling a listed need (team_trade_profile().needs) -- the need multiplier
# only compares to the team's single BEST player at a position, so a CB who
# beats their weak CB2 (a real hole) would otherwise read as "redundant."
STARTER_NEED_BONUS = 0.35
BACKUP_NEED_BONUS = 0.20
# Starter retention floor (AI SENDING side only): an AI team never prices
# giving up one of its own real depth-chart starters below one season of
# his on-field market value (x the same need multiplier). Pure Surplus
# Value reads most highly paid starters as negative-value contracts --
# measured on the 2026 data, 62 of 90 players rated 90+ -- which had the
# AI handing an 86-OVR WR1 over for nothing. A floor, so any starter
# already valued above it (a real bargain) is unchanged; backups keep
# plain Surplus Value, so real salary dumps still work.
STARTER_RETENTION_SEASONS = 1.0

# team_trade_profile() tuning -- this module's own disclosed choices.
STARTER_NEED_GAP = 4.0   # team's weakest starter this many OVR below the league-average weakest starter
BACKUP_NEED_GAP = 8.0    # team's first backup this many OVR below the league-average first backup
MODE_MIN_GAMES = 4
REBUILD_WIN_PCT = 0.35
CONTEND_WIN_PCT = 0.65
MODE_RANK_BAND = 8       # bottom/top 8 by starter strength when the record doesn't say yet

# Mirrors app/main.py's STARTER_COUNTS (can't import main from the engine
# layer); every other position starts one.
_STARTERS_AT: dict[Position, int] = {
    Position.WR: 3, Position.DT: 2, Position.CB: 2,
    Position.T: 2, Position.G: 2, Position.EDGE: 2, Position.LB: 3, Position.S: 2,
}
# FB/K/P aren't listed as trade "needs" -- plenty of real teams carry no FB
# and nobody trades for a backup kicker; they're still valued normally.
_NEED_EXCLUDED = {Position.FB, Position.K, Position.P}

REJECTION_PHRASES = ("Rejected", "No way", "Not happening", "No thank you", "Pass", "Not interested")
ACCEPT_LIKELY = 70     # likelihood >= this is an ACCEPT (green)
ACCEPT_POSSIBLE = 40   # 40-69 is "maybe" (yellow)
COUNTER_MAX_ADDITIONS = 4


@dataclass(frozen=True)
class AssetValue:
    """One asset's real value to the AI team, broken out so the UI can say
    WHY (reason text) and the counter-offer search can price additions
    without re-running the whole evaluation per candidate."""
    side: str            # "sent" (AI gives up) / "received" (AI gets)
    kind: str            # "player" / "pick"
    asset_id: str        # player_id or PickAsset.pick_id
    label: str
    position: str | None
    base: float          # plain Surplus Value / pick value
    multiplier: float    # positional-need multiplier (1.0 for picks / no ai_team_abbr)
    bonus: float         # additive profile bonus, dollars
    value: float         # base * multiplier + bonus


@dataclass(frozen=True)
class TeamTradeProfile:
    team_abbr: str
    mode: str                    # "rebuilding" / "contending" / "balanced"
    mode_line: str
    needs: list = field(default_factory=list)          # human lines, most urgent first
    starter_needs: set = field(default_factory=set)    # Position values
    backup_needs: set = field(default_factory=set)
    weakest_starter_ovr: dict = field(default_factory=dict)  # Position value -> OVR (0 if missing)
    first_backup_ovr: dict = field(default_factory=dict)
    best_ovr: dict = field(default_factory=dict)


def ai_accepts(value_sent: float, value_received: float) -> bool:
    """Sec 8.5's tolerance band: accept if what the AI gets is within 10% of
    what it gives up. Measured as a margin against |value_sent| (floored at
    MIN_VALUE_SCALE) rather than `received >= sent * 0.9` -- identical for
    any real positive value_sent, but the old form rejected an exactly even
    swap of two overpaid (negative-value) players, since -X >= -0.9X is
    false."""
    scale = max(abs(value_sent), MIN_VALUE_SCALE)
    return value_received - value_sent >= -AI_TOLERANCE * scale


def acceptance_likelihood(value_sent: float, value_received: float) -> int:
    """0-100 read of how close a proposal is to the AI's real accept line,
    for the interest meter. Piecewise-linear in the same margin
    ai_accepts() uses, anchored so the accept line lands exactly on
    ACCEPT_LIKELY (70): every real ACCEPT reads >= 70 (green), every real
    REJECT < 70 -- the meter can never promise a deal the submit refuses."""
    scale = max(abs(value_sent), MIN_VALUE_SCALE)
    margin = (value_received - value_sent) / scale
    line = -AI_TOLERANCE
    if margin >= line:
        return int(min(100, ACCEPT_LIKELY + (100 - ACCEPT_LIKELY) * (margin - line) / 0.4))
    floor = line - 0.5  # half the AI's side short reads as 0%
    # Truncated, but capped at 69 so a hair-short proposal never reads green.
    return int(max(0, min(ACCEPT_LIKELY - 1, ACCEPT_LIKELY * (margin - floor) / (line - floor))))


def _league_depth() -> dict[str, dict[Position, list[int]]]:
    """team -> position -> OVRs best-first, for every rostered player in
    ONE lightweight column query (no full Player hydration)."""
    with get_session() as s:
        rows = s.exec(select(Player.team_abbr, Player.position, Player.overall_rating)
                      .where(Player.team_abbr != None)).all()  # noqa: E711
    depth: dict[str, dict[Position, list[int]]] = {}
    for abbr, pos, ovr in rows:
        depth.setdefault(abbr, {}).setdefault(Position(pos) if not isinstance(pos, Position) else pos, []).append(ovr)
    for by_pos in depth.values():
        for ovrs in by_pos.values():
            ovrs.sort(reverse=True)
    return depth


def team_trade_profile(team_abbr: str, season=None, depth: dict | None = None) -> TeamTradeProfile:
    """What an AI team is realistically shopping for, from real data only:

    * Mode -- the real record once MODE_MIN_GAMES are played (<= .350
      rebuilding, >= .650 contending); before that, the team's rank by
      average starter OVR league-wide (bottom/top 8).
    * Starter need -- its weakest starter at a position (e.g. EDGE2) sits
      STARTER_NEED_GAP+ OVR below the league-average weakest starter there.
    * Backup need -- its first backup sits BACKUP_NEED_GAP+ below the
      league-average first backup (or it has none at all).
    """
    depth = depth if depth is not None else _league_depth()
    positions = list(Position)

    def nth(ovrs: list[int], n: int) -> int:
        return ovrs[n - 1] if len(ovrs) >= n else 0

    league_starter: dict[Position, float] = {}
    league_backup: dict[Position, float] = {}
    strength: dict[str, float] = {}
    for pos in positions:
        n = _STARTERS_AT.get(pos, 1)
        league_starter[pos] = sum(nth(t.get(pos, []), n) for t in depth.values()) / max(1, len(depth))
        league_backup[pos] = sum(nth(t.get(pos, []), n + 1) for t in depth.values()) / max(1, len(depth))
    for abbr, by_pos in depth.items():
        starter_ovrs = [o for pos in positions if pos not in _NEED_EXCLUDED
                        for o in by_pos.get(pos, [])[:_STARTERS_AT.get(pos, 1)]]
        strength[abbr] = sum(starter_ovrs) / len(starter_ovrs) if starter_ovrs else 0.0

    mine = depth.get(team_abbr, {})
    weakest, backup, best = {}, {}, {}
    starter_gaps, backup_gaps = [], []
    for pos in positions:
        n = _STARTERS_AT.get(pos, 1)
        ovrs = mine.get(pos, [])
        weakest[pos.value] = nth(ovrs, n)
        backup[pos.value] = nth(ovrs, n + 1)
        best[pos.value] = ovrs[0] if ovrs else 0
        if pos in _NEED_EXCLUDED:
            continue
        s_gap = league_starter[pos] - weakest[pos.value]
        b_gap = league_backup[pos] - backup[pos.value]
        if s_gap >= STARTER_NEED_GAP:
            starter_gaps.append((s_gap, pos))
        elif b_gap >= BACKUP_NEED_GAP:
            backup_gaps.append((b_gap, pos))
    starter_gaps.sort(key=lambda g: -g[0])
    backup_gaps.sort(key=lambda g: -g[0])

    from app.engine.position_groups import POSITION_TO_GROUP
    needs = [f"Needs a starting {POSITION_TO_GROUP[p]}" for _, p in starter_gaps[:2]]
    needs += [f"Needs a backup {POSITION_TO_GROUP[p]}" for _, p in backup_gaps[:max(1, 3 - len(needs))]]

    mode = "balanced"
    record = season.records.get(team_abbr) if season is not None and getattr(season, "records", None) else None
    if record is not None and record.wins + record.losses >= MODE_MIN_GAMES:
        if record.win_pct <= REBUILD_WIN_PCT:
            mode = "rebuilding"
        elif record.win_pct >= CONTEND_WIN_PCT:
            mode = "contending"
    elif strength:
        ranked = sorted(strength, key=lambda a: strength[a])
        if team_abbr in ranked:
            idx = ranked.index(team_abbr)
            if idx < MODE_RANK_BAND:
                mode = "rebuilding"
            elif idx >= len(ranked) - MODE_RANK_BAND:
                mode = "contending"
    mode_line = {
        "rebuilding": "Rebuilding -- values high draft picks and young players",
        "contending": "Contending -- wants proven starters who help now",
        "balanced": "Middle of the pack -- open to fair value either way",
    }[mode]

    return TeamTradeProfile(
        team_abbr=team_abbr, mode=mode, mode_line=mode_line, needs=needs,
        starter_needs={p.value for _, p in starter_gaps[:2]},
        backup_needs={p.value for _, p in backup_gaps[:max(1, 3 - len(starter_gaps[:2]))]},
        weakest_starter_ovr=weakest, first_backup_ovr=backup, best_ovr=best,
    )


def _profile_bonus_fraction(player: Player | None, profile: TeamTradeProfile | None) -> float:
    """Additive bonus (fraction of base value) the RECEIVING AI team puts on
    one incoming asset (player=None means a pick)."""
    if profile is None:
        return 0.0
    if player is None:
        return REBUILD_PICK_BONUS if profile.mode == "rebuilding" else 0.0
    bonus = 0.0
    pos = player.position.value
    if pos in profile.starter_needs and player.overall_rating > profile.weakest_starter_ovr.get(pos, 0):
        bonus += STARTER_NEED_BONUS
    elif pos in profile.backup_needs and player.overall_rating > profile.first_backup_ovr.get(pos, 0):
        bonus += BACKUP_NEED_BONUS
    if profile.mode == "rebuilding" and player.age <= REBUILD_YOUTH_MAX_AGE:
        bonus += REBUILD_YOUTH_BONUS
    if profile.mode == "contending" and player.overall_rating >= CONTEND_STARTER_MIN_OVR:
        bonus += CONTEND_STARTER_BONUS
    return bonus


def _pick_label(pick: PickRef, owner_abbr: str | None = None) -> str:
    from app.config import season_year
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(pick.round, "th")
    via = f" (via {pick.original_team_abbr})" if owner_abbr and pick.original_team_abbr != owner_abbr else ""
    return f"{season_year(pick.season_number)} {pick.round}{suffix} Round Pick{via}"


def _pick_id(pick: PickRef) -> str:
    return f"{pick.season_number}_{pick.round}_{pick.original_team_abbr}"


def asset_values(
    ai_team_sends: list[Player], ai_team_receives: list[Player], season_number: int,
    ai_sends_picks=(), ai_receives_picks=(), season=None, ai_team_abbr: str | None = None,
    profile: TeamTradeProfile | None = None,
) -> list[AssetValue]:
    """Per-asset real value to the AI team -- the one pricing path both
    evaluate_trade() and the counter-offer search share. Each asset is
    priced independently of the others (the need multiplier compares to
    the AI's CURRENT roster, not to the rest of the package), which is what
    lets build_counter_offer() price a candidate addition by itself."""
    if (ai_sends_picks or ai_receives_picks) and season is None:
        raise ValueError("season is required to evaluate a trade that includes draft picks")
    if profile is None and ai_team_abbr is not None and season is not None:
        profile = team_trade_profile(ai_team_abbr, season)

    out: list[AssetValue] = []
    for p in ai_team_sends:
        base = player_trade_value(p, season_number)
        mult = giving_up_need_multiplier(p) if ai_team_abbr is not None else 1.0
        value = base * mult
        floor_bonus = 0.0
        if ai_team_abbr is not None and p.team_abbr is not None and _is_depth_chart_starter(p):
            floor = STARTER_RETENTION_SEASONS * contracts.expected_market_value(p, season_number) * mult
            floor_bonus = max(0.0, floor - value)
        out.append(AssetValue("sent", "player", p.player_id, p.full_name, p.position.value, base, mult,
                              floor_bonus, value + floor_bonus))
    for p in ai_team_receives:
        base = player_trade_value(p, season_number)
        mult = receiving_need_multiplier(p, ai_team_abbr) if ai_team_abbr is not None else 1.0
        bonus = max(0.0, base) * _profile_bonus_fraction(p, profile)
        out.append(AssetValue("received", "player", p.player_id, p.full_name, p.position.value, base, mult, bonus,
                              base * mult + bonus))
    for pk in ai_sends_picks:
        base = pick_trade_value(pk, season)
        out.append(AssetValue("sent", "pick", _pick_id(pk), _pick_label(pk), None, base, 1.0, 0.0, base))
    for pk in ai_receives_picks:
        base = pick_trade_value(pk, season)
        bonus = base * _profile_bonus_fraction(None, profile)
        out.append(AssetValue("received", "pick", _pick_id(pk), _pick_label(pk), None, base, 1.0, bonus, base + bonus))
    return out


def verdict_reason(evaluation: TradeEvaluation, profile: TeamTradeProfile | None = None) -> str:
    """Short, real reason text for the verdict -- read off the same per-
    asset breakdown the verdict itself was computed from."""
    assets = evaluation.assets
    received = [a for a in assets if a.side == "received"]
    sent = [a for a in assets if a.side == "sent"]
    from app.engine.position_groups import POSITION_TO_GROUP

    def group(pos: str) -> str:
        return POSITION_TO_GROUP[Position(pos)]

    if evaluation.accepted:
        need_fill = [a for a in received if a.kind == "player" and a.bonus > 0 and profile is not None
                     and a.position in (profile.starter_needs | profile.backup_needs)]
        if need_fill:
            a = max(need_fill, key=lambda x: x.value)
            return f"{a.label} fills a need at {group(a.position)}"
        if profile is not None and profile.mode == "rebuilding" and any(a.kind == "pick" for a in received):
            return "They're rebuilding and like the draft capital"
        if any(a.kind == "player" and a.multiplier >= 1.25 for a in received):
            a = max((x for x in received if x.kind == "player" and x.multiplier >= 1.25), key=lambda x: x.value)
            return f"{a.label} is an upgrade at {group(a.position)}"
        return "The value works for them"

    if not received:
        return "You have to send something back"
    # A key starter being asked for is the headline reason whenever one is
    # in the deal -- "they don't need your backup QB" is true but beside
    # the point when the ask is their franchise QB.
    key_starters = [a for a in sent if a.kind == "player" and (a.multiplier >= 1.25 or a.bonus > 0)]
    if key_starters:
        a = max(key_starters, key=lambda x: x.value)
        return f"{a.label} is too important to them"
    unwanted = [a for a in received if a.kind == "player" and a.base > 0 and a.multiplier <= 0.7 and a.bonus == 0]
    if unwanted and sum(a.base - a.value for a in unwanted) > 0.25 * max(abs(evaluation.value_sent), MIN_VALUE_SCALE):
        a = max(unwanted, key=lambda x: x.base - x.value)
        return f"They don't need a {group(a.position)}"
    bad_contracts = [a for a in received if a.kind == "player" and a.value < 0]
    if bad_contracts:
        a = min(bad_contracts, key=lambda x: x.value)
        return f"They don't want {a.label}'s contract"
    return "Asking price too high"


@dataclass(frozen=True)
class CounterOffer:
    possible: bool
    already_acceptable: bool
    add_players: list = field(default_factory=list)   # Player rows from the user's side
    add_picks: list = field(default_factory=list)     # PickRef from the user's side
    message: str = ""


def build_counter_offer(
    ai_team_abbr: str, ai_team_sends: list[Player], ai_team_receives: list[Player],
    ai_sends_picks: list[PickRef], ai_receives_picks: list[PickRef], season,
    candidate_players: list[Player], candidate_picks: list[PickRef],
    max_additions: int = COUNTER_MAX_ADDITIONS,
) -> CounterOffer:
    """The AI's "Get Counter Offer": what's the SMALLEST addition from the
    user's side (players and/or picks not already in the deal) that pushes
    this exact proposal over the real accept line? Prefers one asset that
    covers the whole shortfall with the least overpay; otherwise the
    fewest high-value assets (up to max_additions), with the last slot
    swapped for the cheapest asset that still closes the gap. Re-verified
    through evaluate_trade() before it's returned, so a counter the AI
    proposes is always one it would actually accept."""
    season_number = season.season_number
    profile = team_trade_profile(ai_team_abbr, season)
    if not (ai_team_sends or ai_sends_picks):
        return CounterOffer(False, False, message="Pick something you want from them first.")

    current = evaluate_trade(ai_team_sends, ai_team_receives, season_number, ai_sends_picks, ai_receives_picks,
                             season=season, ai_team_abbr=ai_team_abbr)
    if current.accepted:
        return CounterOffer(True, True, message="They'd already accept this deal as-is.")

    scale = max(abs(current.value_sent), MIN_VALUE_SCALE)
    deficit = current.value_sent - AI_TOLERANCE * scale - current.value_received

    in_deal_players = {p.player_id for p in ai_team_receives}
    in_deal_picks = set(ai_receives_picks)
    player_pool = [p for p in candidate_players if p.player_id not in in_deal_players]
    pick_pool = [pk for pk in candidate_picks if pk not in in_deal_picks]
    priced = asset_values([], player_pool, season_number, (), pick_pool, season, ai_team_abbr, profile=profile)
    by_id = {p.player_id: p for p in player_pool}
    by_id.update({_pick_id(pk): pk for pk in pick_pool})
    options = sorted((a for a in priced if a.value > 0), key=lambda a: a.value)

    chosen: list[AssetValue] | None = None
    single = next((a for a in options if a.value >= deficit), None)
    if single is not None:
        chosen = [single]
    else:
        greedy: list[AssetValue] = []
        total = 0.0
        for a in reversed(options):
            if len(greedy) >= max_additions:
                break
            greedy.append(a)
            total += a.value
            if total >= deficit:
                break
        if total >= deficit:
            before_last = total - greedy[-1].value
            used = {a.asset_id for a in greedy[:-1]}
            cheapest_last = next((a for a in options if a.asset_id not in used and before_last + a.value >= deficit), greedy[-1])
            chosen = greedy[:-1] + [cheapest_last]

    not_possible = CounterOffer(False, False, message="A deal is not possible with those terms.")
    if chosen is None:
        return not_possible
    add_players = [by_id[a.asset_id] for a in chosen if a.kind == "player"]
    add_picks = [by_id[a.asset_id] for a in chosen if a.kind == "pick"]
    check = evaluate_trade(ai_team_sends, list(ai_team_receives) + add_players, season_number,
                           ai_sends_picks, list(ai_receives_picks) + add_picks, season=season, ai_team_abbr=ai_team_abbr)
    if not check.accepted:
        return not_possible
    names = ", ".join(a.label for a in chosen)
    return CounterOffer(True, False, add_players, add_picks, message=f"They'd do it if you add: {names}")


def execute_trade(team_a_abbr: str, team_a_players: list[Player],
                   team_b_abbr: str, team_b_players: list[Player],
                   team_a_picks: list[PickRef] = (), team_b_picks: list[PickRef] = (),
                   acquisition_year: int | None = None) -> None:
    """Mutates in place -- swaps team_abbr for every player on both
    sides, and (Sec 8.5) transfers real ownership for every pick on both
    sides via app/services/draft_pick_store.py's transfer_pick(). The
    caller commits the player-side DB changes; pick ownership is its own
    persistence surface, written immediately (same as every other real
    write path into that store). No cap-space check on the RECEIVING
    team's post-trade cap -- Sec 8.5 doesn't specify one (unlike Sec
    8.4's explicit FA cap guardrail), and this engine's cap is already
    a rescaled, disclosed-approximate number (see contracts.py's own
    docstring) that most real rosters already sit well under.

    Every moved player's acquisition record is rewritten to this trade
    (type "Trade", the team he came from, and `acquisition_year` -- the
    calendar year -- when the caller supplies it); draft round/pick are
    cleared since they described how he joined his PREVIOUS team."""
    def _moved(p: Player, from_abbr: str, to_abbr: str) -> None:
        p.team_abbr = to_abbr
        p.acquisition_type = "Trade"
        p.acquisition_team = from_abbr
        p.acquisition_season = acquisition_year
        p.acquisition_round = None
        p.acquisition_pick = None

    for p in team_a_players:
        _moved(p, team_a_abbr, team_b_abbr)
    for p in team_b_players:
        _moved(p, team_b_abbr, team_a_abbr)
    if team_a_picks or team_b_picks:
        from app.services import draft_pick_store
        for pk in team_a_picks:
            draft_pick_store.transfer_pick(pk.season_number, pk.round, pk.original_team_abbr, team_b_abbr)
        for pk in team_b_picks:
            draft_pick_store.transfer_pick(pk.season_number, pk.round, pk.original_team_abbr, team_a_abbr)

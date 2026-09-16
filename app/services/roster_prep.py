"""
Preseason roster readiness (Brian's ask, 2026-09-14).

Three jobs, all against free_agency.ROSTER_REQUIREMENTS (the one league-
wide requirement table):

1. **The user's gate** -- `team_holes()` / `holes_summary()`: before the
   first preseason game, app/main.py sends a user whose roster is short to
   /roster with a "Roster Holes" banner and an Auto-Fill Roster button.
2. **Auto-fill** -- `auto_fill_user_roster()` signs free agents into the
   user's holes with the exact AI logic (free_agency.fill_roster_gaps),
   THEN runs `prepare_ai_rosters()`: every AI team fills its own holes and
   gets a fresh depth chart. User first, league second -- Brian's order.
   `prepare_ai_rosters()` also runs unconditionally from season_state as
   the first game of a season is simulated, so AI teams are always fixed
   before preseason whether or not the user ever saw the gate.
3. **Pool guarantee** -- `ensure_free_agent_pool_depth()`: after the draft
   (and defensively before any hole fill) the free-agent pool is topped up
   per position to cover the whole league's shortfall plus a 20% buffer,
   with generated undrafted rookies (draft.supplemental_udfa_player), so
   "there's nobody left to sign" never happens.
"""
from __future__ import annotations

import math
from collections import defaultdict

from sqlmodel import select

from app.core.db import get_session
from app.data.teams import TEAMS
from app.engine import draft, free_agency
from app.models.player import Player, Position, RosterStatus

POOL_BUFFER_FRACTION = 0.20
# A position the league is NOT short at still keeps a couple of bodies
# available, so a mid-preseason release/injury or a manual user search
# never meets an empty list.
POOL_FLOOR = 2


def active_roster_count(team_abbr: str) -> int:
    """R16 Sec 4.1/10: the real enforcement number the over-53 gate
    checks -- how many of this team's players are actually on the
    ACTIVE 53, not the team's total body count (PS/IR included)."""
    with get_session() as s:
        return len(s.exec(select(Player).where(
            Player.team_abbr == team_abbr, Player.roster_status == RosterStatus.ACTIVE)).all())


def team_holes(team_abbr: str) -> dict[Position, int]:
    # R16 Sec 9: a position minimum is measured against the ACTIVE
    # roster only -- a full practice squad at a position must not
    # silently satisfy this gate.
    with get_session() as s:
        roster = list(s.exec(select(Player).where(
            Player.team_abbr == team_abbr, Player.roster_status == RosterStatus.ACTIVE)))
    return free_agency.roster_shortfall(roster)


def holes_summary(holes: dict[Position, int]) -> str:
    """"2 EDGE, 1 CB, 1 TE" -- the gate banner's own wording."""
    return ", ".join(f"{n} {pos.value}" for pos, n in holes.items())


def _rosters_and_pool(s) -> tuple[dict[str, list[Player]], list[Player]]:
    rosters: dict[str, list[Player]] = defaultdict(list)
    pool: list[Player] = []
    for p in s.exec(select(Player)).all():
        if p.team_abbr is None:
            pool.append(p)
        else:
            rosters[p.team_abbr].append(p)
    return rosters, pool


def ensure_free_agent_pool_depth(league_seed: int, season_number: int) -> dict[Position, int]:
    """Tops the free-agent pool up to ceil(league shortfall x 1.2) (never
    below POOL_FLOOR) at every required position. Deterministic: new
    players' ids/ratings come from (league_seed, season_number, position,
    ordinal), with the ordinal continuing past whatever this season
    already generated, so a repeat call with nothing short is a no-op and
    a replay produces identical players. New players join the undrafted
    pool (3-year expiry) so they don't pile up across seasons. Returns
    {position: players generated}."""
    from app.services import undrafted_pool

    generated: dict[Position, int] = {}
    new_ids: list[str] = []
    with get_session() as s:
        rosters, pool = _rosters_and_pool(s)
        pool_counts = defaultdict(int)
        for p in pool:
            pool_counts[p.position] += 1
        shortfall = defaultdict(int)
        for team in TEAMS:
            # R16 Sec 9: same ACTIVE-only measurement as team_holes() --
            # `rosters` here is the FULL roster (fill_roster_gaps() below
            # needs that for cap math), so filter just for this count.
            team_active = [p for p in rosters.get(team.abbr, []) if p.roster_status == RosterStatus.ACTIVE]
            for pos, need in free_agency.roster_shortfall(team_active).items():
                shortfall[pos] += need
        existing_ids = {p.player_id for p in pool} | {p.player_id for r in rosters.values() for p in r}
        for pos in free_agency.ROSTER_REQUIREMENTS:
            target = max(math.ceil(shortfall[pos] * (1 + POOL_BUFFER_FRACTION)), POOL_FLOOR)
            missing = target - pool_counts[pos]
            if missing <= 0:
                continue
            prefix = f"udfa_{season_number}_{pos.value}_"
            ordinal = sum(1 for pid in existing_ids if pid.startswith(prefix))
            for _ in range(missing):
                player = draft.supplemental_udfa_player(pos, ordinal, league_seed, season_number)
                ordinal += 1
                s.add(player)
                new_ids.append(player.player_id)
            generated[pos] = missing
        s.commit()
    if new_ids:
        undrafted_pool.add_undrafted(new_ids)
    return generated


def _fill_teams(team_abbrs: list[str], season_number: int) -> dict[str, list[str]]:
    """fill_roster_gaps() for each team in order against ONE shared pool,
    one session, one commit. Returns {team_abbr: [signed player names]}."""
    from app.services import undrafted_pool

    undrafted_ids = undrafted_pool.tracked_ids()
    signed_by_team: dict[str, list[str]] = {}
    signed_ids: list[str] = []
    with get_session() as s:
        rosters, pool = _rosters_and_pool(s)
        # Deterministic pool order (fill_roster_gaps breaks ties by id too).
        pool.sort(key=lambda p: p.player_id)
        for abbr in team_abbrs:
            signed = free_agency.fill_roster_gaps(
                abbr, rosters.get(abbr, []), pool, season_number,
                requirements=free_agency.ROSTER_REQUIREMENTS, undrafted_ids=undrafted_ids,
            )
            if signed:
                signed_by_team[abbr] = [p.full_name for p in signed]
                signed_ids.extend(p.player_id for p in signed)
                for p in signed:
                    s.add(p)
        s.commit()
    undrafted_pool.remove_many(signed_ids)
    return signed_by_team


def _fill_practice_squads(team_abbrs: list[str], season_number: int) -> dict[str, list[str]]:
    """R16 Sec 4.3/Sec 8's own "run right after the existing active-
    roster fill" order -- the practice-squad sibling to _fill_teams(),
    same one-shared-pool/one-session/one-commit shape."""
    signed_by_team: dict[str, list[str]] = {}
    with get_session() as s:
        rosters, pool = _rosters_and_pool(s)
        pool.sort(key=lambda p: p.player_id)
        for abbr in team_abbrs:
            signed = free_agency.fill_practice_squad_gaps(abbr, rosters.get(abbr, []), pool, season_number)
            if signed:
                signed_by_team[abbr] = [p.full_name for p in signed]
                for p in signed:
                    s.add(p)
        s.commit()
    return signed_by_team


def auto_cut_team_to_limits(team_abbr: str) -> dict[str, int]:
    """R16 Sec 8's first bullet: an AI team's simple-heuristic initial
    cut to 53 -- the real, one-time (per team) migration moment every
    currently-oversized roster (54-72 real imported players, nothing
    ever enforced the cap before this feature) needs on first load.

    Position-need-aware, per the spec's own §8 wording ("keep the 53 best-
    rated players BY POSITION NEED, per ROSTER_REQUIREMENTS") -- NOT a
    blunt rating-only cut. Each position's ROSTER_REQUIREMENTS minimum is
    guaranteed from that position's own best-rated players first; the
    remaining slots (53 minus every guaranteed slot -- the requirement
    table sums to 38, so there's always room) go to the next-best players
    overall, any position. A blunt cut can accidentally zero out a thin
    position (real bug caught 2026-09-15: LV came up short a Center,
    cascading into fill_practice_squad_gaps() finding no Center anywhere
    to sign), which this guarantee step exists specifically to prevent.

    Overflow beyond 53 (guaranteed + best-of-the-rest) goes to the
    practice squad, best-rated first, up to PRACTICE_SQUAD_SIZE; anyone
    still left over (a team like ARI, 72 total) is released outright to
    the free-agent pool (decision #14), worst-rated first. A no-op for a
    team already at or under 53 active (idempotent -- safe to call every
    offseason, not just once). Returns {"active": n, "practice_squad": n,
    "released": n}."""
    with get_session() as s:
        roster = list(s.exec(select(Player).where(Player.team_abbr == team_abbr)))
        active = [p for p in roster if p.roster_status == RosterStatus.ACTIVE]
        if len(active) <= free_agency.MAX_ROSTER_SIZE:
            return {"active": len(active), "practice_squad": 0, "released": 0}
        # Non-active players (already PS/IR) are untouched by this pass --
        # only the ACTIVE pool is what needs trimming.
        active.sort(key=lambda p: (-p.overall_rating, p.player_id))
        by_position: dict[Position, list[Player]] = defaultdict(list)
        for p in active:
            by_position[p.position].append(p)
        guaranteed_ids: set[str] = set()
        for pos, need in free_agency.ROSTER_REQUIREMENTS.items():
            for p in by_position.get(pos, [])[:need]:
                guaranteed_ids.add(p.player_id)
        rest = [p for p in active if p.player_id not in guaranteed_ids]
        extra_slots = max(0, free_agency.MAX_ROSTER_SIZE - len(guaranteed_ids))
        keep_ids = guaranteed_ids | {p.player_id for p in rest[:extra_slots]}
        keep = [p for p in active if p.player_id in keep_ids]
        overflow = [p for p in active if p.player_id not in keep_ids]
        to_ps = overflow[:free_agency.PRACTICE_SQUAD_SIZE]
        to_release = overflow[free_agency.PRACTICE_SQUAD_SIZE:]
        for p in to_ps:
            p.roster_status = RosterStatus.PRACTICE_SQUAD
            s.add(p)
        for p in to_release:
            p.team_abbr = None
            p.roster_status = RosterStatus.ACTIVE
            s.add(p)
        s.commit()
        return {"active": len(keep), "practice_squad": len(to_ps), "released": len(to_release)}


def prepare_ai_rosters(league_seed: int, season_number: int, user_team_abbr: str | None) -> dict[str, list[str]]:
    """Every AI team fills its holes, then every AI depth chart is re-sorted
    (auto-fill) so new signings -- and any roster churn since the last
    sort -- land in the right slots, then starter caches are cleared.
    Idempotent: with no holes it signs nobody; the depth re-sort is a pure
    function of the roster.

    R16 Sec 8: runs each AI team's initial cut-to-53 (a real no-op once a
    team's already at or under the limit) BEFORE filling holes -- a team
    over the cap needs cutting, not more signings; a genuine position
    hole can still exist afterward for a team whose excess bodies were
    concentrated elsewhere, which the normal fill-gaps pass below still
    catches. The pool depth-guarantee runs AFTER the cuts, not before --
    a blunt rating-only cut can create a brand-new shortfall at a thin
    position (e.g. a team's only real Center loses out on rating and
    drops to the practice squad) that didn't exist when every team still
    carried its real 54-72-man import; topping the pool up against the
    PRE-cut shortfall (still zero everywhere, real rosters run deep)
    would leave that new hole with nothing to sign (caught via a real
    test failure, 2026-09-15: LV came up short a Center). The PS-specific
    auto-fill runs last (Sec 8's own order: "right after the existing
    active-roster fill")."""
    from app.services import depth_chart, depth_chart_overrides

    ai_teams = [t.abbr for t in TEAMS if t.abbr != user_team_abbr]
    for abbr in ai_teams:
        auto_cut_team_to_limits(abbr)
    ensure_free_agent_pool_depth(league_seed, season_number)
    signed = _fill_teams(ai_teams, season_number)
    _fill_practice_squads(ai_teams, season_number)

    with get_session() as s:
        rosters: dict[str, dict[Position, list[Player]]] = {abbr: defaultdict(list) for abbr in ai_teams}
        for p in s.exec(select(Player).where(Player.team_abbr != None)).all():  # noqa: E711
            if p.team_abbr in rosters:
                rosters[p.team_abbr][p.position].append(p)
    depth_chart_overrides.auto_fill_teams(rosters)
    depth_chart.clear_starters_cache()
    return signed


def auto_fill_user_roster(league_seed: int, season_number: int, user_team_abbr: str) -> list[str]:
    """The gate's AUTO-FILL ROSTER button: the user's team signs first,
    then the rest of the league makes its moves. Returns the user's own
    signees' names (for the confirmation banner)."""
    from app.services import depth_chart

    ensure_free_agent_pool_depth(league_seed, season_number)
    user_signed = _fill_teams([user_team_abbr], season_number).get(user_team_abbr, [])
    depth_chart.clear_starters_cache()
    prepare_ai_rosters(league_seed, season_number, user_team_abbr)
    return user_signed

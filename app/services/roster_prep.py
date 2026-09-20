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
from app.models.player import Player, Position

POOL_BUFFER_FRACTION = 0.20
# A position the league is NOT short at still keeps a real, browsable
# handful of bodies available, so a mid-preseason release/injury or a
# manual user search never meets an empty list. Raised from 2 to 6
# (2026-09-20, Brian's playtest report: "0 free agents" in a season-2
# preseason) -- 2 wasn't a real floor in practice anyway, see
# prepare_ai_rosters()'s own comment on why the guarantee needs to be
# re-checked AFTER AI teams consume from the same top-up pass.
POOL_FLOOR = 6


def team_holes(team_abbr: str) -> dict[Position, int]:
    with get_session() as s:
        roster = list(s.exec(select(Player).where(Player.team_abbr == team_abbr)))
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
            for pos, need in free_agency.roster_shortfall(rosters.get(team.abbr, [])).items():
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


def prepare_ai_rosters(league_seed: int, season_number: int, user_team_abbr: str | None) -> dict[str, list[str]]:
    """Every AI team fills its holes, then every AI depth chart is re-sorted
    (auto-fill) so new signings -- and any roster churn since the last
    sort -- land in the right slots, then starter caches are cleared.
    Idempotent: with no holes it signs nobody; the depth re-sort is a pure
    function of the roster."""
    from app.services import depth_chart, depth_chart_overrides

    ensure_free_agent_pool_depth(league_seed, season_number)
    ai_teams = [t.abbr for t in TEAMS if t.abbr != user_team_abbr]
    signed = _fill_teams(ai_teams, season_number)
    # 2026-09-20 fix (Brian's playtest report: free agent pool showed
    # ZERO players at every position in a season-2 preseason). The FIRST
    # ensure_free_agent_pool_depth() call above only guarantees POOL_FLOOR
    # exists the MOMENT it's generated -- the very next line then lets all
    # 31 AI teams draw from that same pool in one pass, which can (and,
    # by season 2, reliably did) consume it right back down to empty.
    # Re-checking the guarantee AFTER AI consumption is what actually
    # keeps something real behind for the user to browse.
    ensure_free_agent_pool_depth(league_seed, season_number)

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

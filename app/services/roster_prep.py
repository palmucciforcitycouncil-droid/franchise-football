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
# A position the league is NOT short at still keeps a real, browsable
# handful of bodies available, so a mid-preseason release/injury or a
# manual user search never meets an empty list. Raised from 2 to 6
# (2026-09-20, Brian's playtest report: "0 free agents" in a season-2
# preseason) -- 2 wasn't a real floor in practice anyway, see
# prepare_ai_rosters()'s own comment on why the guarantee needs to be
# re-checked AFTER AI teams consume from the same top-up pass.
POOL_FLOOR = 6


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
    # 2026-09-20 fix (Brian's playtest report: free agent pool showed
    # ZERO players at every position in a season-2 preseason). The FIRST
    # ensure_free_agent_pool_depth() call above only guarantees POOL_FLOOR
    # exists the MOMENT it's generated -- every line since then (active-
    # roster AI fills, then PS fills) lets teams draw from that same
    # pool, which can (and, by season 2, reliably did) consume it right
    # back down to empty. Re-checking the guarantee AFTER every real
    # consumer has had its turn is what actually keeps something real
    # behind for the user to browse.
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


def auto_place_ai_players_on_ir(new_injuries: list, user_team_abbr: str | None, week_num: int) -> list[str]:
    """R16 Sec 7/Sec 8: "auto-place at the weeks_out >= 4 threshold, no
    user-style manual judgment call" -- every AI team's own equivalent of
    the user's manual Place on IR button. `injury.placed_on_ir` is
    already computed at injury-generation time (injuries.py), so this is
    pure wiring: any brand-new injury this week that qualifies, on a
    player who isn't the user's own (the user's Roster/Player Card gets
    the manual control instead, Sec 11's usual "manual for the user,
    autonomous for AI" split), moves that player off the active 53 --
    freeing his slot exactly the way a real team activates a replacement
    -- without signing anyone new: this feature's AI never re-fills a
    hole mid-season (prepare_ai_rosters() only ever runs once, before the
    season's first game, same as every other roster gap already left
    unaddressed mid-season pre-R16). Returns the names moved, for
    an optional headline hook.

    Only ACTIVE/PRACTICE_SQUAD players move -- a fresh injury can't hit
    someone already on IR (one active injury per player, injuries.py's
    own roll_injuries_for_week() docstring)."""
    moved: list[str] = []
    with get_session() as s:
        for injury in new_injuries:
            if not injury.placed_on_ir:
                continue
            player = s.get(Player, injury.player_id)
            if player is None or player.team_abbr is None or player.team_abbr == user_team_abbr:
                continue
            if player.roster_status not in (RosterStatus.ACTIVE, RosterStatus.PRACTICE_SQUAD):
                continue
            player.roster_status = RosterStatus.IR
            player.ir_placed_week = week_num
            s.add(player)
            moved.append(player.full_name)
        s.commit()
    return moved


# --- R16 Sec 5: Poaching -----------------------------------------------

POACH_LOCK_WEEKS = 3
# A poach candidate must clear the poacher's own weakest ACTIVE group
# rating by this many points to count as a "clear upgrade" (Sec 8) --
# disclosed tuning knob, not a spec-locked number (the spec names the
# RULE, not a magnitude -- Brian's own playtesting note elsewhere in
# this project applies here too).
POACH_UPGRADE_MARGIN = 8.0


def _team_players(s, team_abbr: str) -> list[Player]:
    return list(s.exec(select(Player).where(Player.team_abbr == team_abbr)))


def weakest_active_need(team_abbr: str) -> tuple[str, float] | None:
    """R16 Sec 8: the AI poacher's own target -- the lowest-rated
    QUOTA_GROUPS group among this team's ACTIVE roster only (a deep
    practice squad at a position doesn't mean the team isn't starting a
    real stopgap there right now, and PS/IR players don't play).
    roster_strength.compute_group_ratings() already does the real
    snap-share-weighted math; this just calls it with an ACTIVE-only
    roster instead of that function's own (deliberately broader, used
    elsewhere for prestige/trade-value purposes) full-roster default."""
    from app.engine import roster_strength

    with get_session() as s:
        active = [p for p in _team_players(s, team_abbr) if p.roster_status == RosterStatus.ACTIVE]
    ratings = roster_strength.compute_group_ratings(team_abbr, active)
    if not ratings:
        return None
    return min(ratings.items(), key=lambda kv: kv[1])


def _unprotected_ps_by_team() -> dict[str, list[Player]]:
    with get_session() as s:
        players = list(s.exec(select(Player).where(Player.roster_status == RosterStatus.PRACTICE_SQUAD)))
    by_team: dict[str, list[Player]] = defaultdict(list)
    for p in players:
        if not p.ps_protected:
            by_team[p.team_abbr].append(p)
    return by_team


def find_poach_candidate(poacher_abbr: str, unprotected_by_team: dict[str, list[Player]]) -> Player | None:
    """The single best available upgrade for `poacher_abbr` at their own
    weakest ACTIVE group, across every OTHER team's unprotected PS --
    None if nobody clears POACH_UPGRADE_MARGIN. Best-rated pick within
    the qualifying group, ties broken by id for determinism."""
    from app.engine.position_groups import POSITION_TO_GROUP

    need = weakest_active_need(poacher_abbr)
    if need is None:
        return None
    group, need_rating = need
    candidates = [
        p for team_abbr, players in unprotected_by_team.items() if team_abbr != poacher_abbr
        for p in players if POSITION_TO_GROUP.get(p.position) == group
    ]
    if not candidates:
        return None
    best = max(candidates, key=lambda p: (p.overall_rating, p.player_id))
    if best.overall_rating - need_rating >= POACH_UPGRADE_MARGIN:
        return best
    return None


def execute_poach(player_id: str, poacher_abbr: str, week_num: int) -> None:
    """R16 Sec 5.1: signs an unprotected PS player STRAIGHT to the
    poaching team's own 53 (never their PS, decision #6) -- caller's job
    to have already confirmed an open slot and that the player is a
    real, still-unprotected target (both AI and user poaching routes
    check this themselves, right before calling, so the check lives
    there rather than silently no-op'ing here on a stale target).
    3-simulated-week lock either direction (decision #17) via the same
    `roster_lock_until_week` field a defensive block-promotion also
    sets. Salary/contract are left exactly as they were on the PS (the
    flat league minimum, decision #10) -- "guaranteed 3 weeks of salary"
    (Sec 5.1.4) is about that deal surviving the move, not a raise."""
    with get_session() as s:
        player = s.get(Player, player_id)
        player.poached_from_team_abbr = player.team_abbr
        player.team_abbr = poacher_abbr
        player.roster_status = RosterStatus.ACTIVE
        player.ps_protected = False
        player.roster_lock_until_week = week_num + POACH_LOCK_WEEKS
        s.add(player)
        s.commit()


def block_poach(player_id: str, week_num: int) -> None:
    """R16 Sec 5.1.7: the original team pre-empts a poach by promoting
    the targeted player to their OWN 53 first -- same 3-game lock as an
    actual poach (decision #17, closing the "promote for a week,
    restash" loophole), but no poached_from_team_abbr (he never left his
    own team)."""
    with get_session() as s:
        player = s.get(Player, player_id)
        player.roster_status = RosterStatus.ACTIVE
        player.ps_protected = False
        player.roster_lock_until_week = week_num + POACH_LOCK_WEEKS
        s.add(player)
        s.commit()


def clear_expired_poach_locks(week_num: int) -> None:
    """R16 Sec 3: "poached_from_team_abbr... cleared once his lock
    expires" -- run weekly so a player's post-lock state (both fields
    clear) is real and current, not just implied by comparing two
    fields everywhere they're read."""
    with get_session() as s:
        expired = list(s.exec(select(Player).where(
            Player.roster_lock_until_week != None, Player.roster_lock_until_week < week_num)))  # noqa: E711
        for p in expired:
            p.roster_lock_until_week = None
            p.poached_from_team_abbr = None
            s.add(p)
        s.commit()


def auto_protect_ai_ps(team_abbrs: list[str]) -> None:
    """R16 Sec 8: "auto-protect the 4 highest-rated unprotected PS
    players" -- recomputed fresh each week (cheap, and correctly reacts
    to PS composition changes from a poach/promotion/release since the
    last pass) rather than a one-time pick with manual upkeep, since an
    AI team has no equivalent of the user's own "carries over until
    changed" convenience (decision #16 is explicitly about not
    forcing the USER to re-pick every week -- the AI has no such
    friction to spare it from)."""
    with get_session() as s:
        for team_abbr in team_abbrs:
            ps = [p for p in _team_players(s, team_abbr) if p.roster_status == RosterStatus.PRACTICE_SQUAD]
            ps.sort(key=lambda p: (-p.overall_rating, p.player_id))
            for i, p in enumerate(ps):
                want_protected = i < 4
                if p.ps_protected != want_protected:
                    p.ps_protected = want_protected
                    s.add(p)
        s.commit()


def run_weekly_poaching(season) -> dict | None:
    """R16 Sec 5.2: the weekly AI poaching pass -- runs once per week
    (guarded by `season.poaching_evaluated_through_week`, so re-hitting
    /season/simulate-week after resolving a pending decision, or just a
    stray double-click, never re-rolls the same week's AI decisions).
    AI-vs-AI poaches resolve immediately; the first AI decision to
    target the USER's own PS becomes `season.pending_poach` and gates
    the rest of Sim Week (app/main.py's own route checks this return
    value) -- deliberately capped at one pending user-facing poach per
    week, same "simple heuristic, not exhaustive" spirit as the rest of
    this feature's AI tier. Returns the pending decision, or None."""
    week_num = season.current_week
    if season.poaching_evaluated_through_week >= week_num:
        return season.pending_poach
    clear_expired_poach_locks(week_num)
    ai_teams = [t.abbr for t in TEAMS if t.abbr != season.user_team_abbr]
    auto_protect_ai_ps(ai_teams)
    unprotected_by_team = _unprotected_ps_by_team()
    pending: dict | None = None
    for poacher_abbr in ai_teams:
        if active_roster_count(poacher_abbr) >= free_agency.MAX_ROSTER_SIZE:
            continue
        target = find_poach_candidate(poacher_abbr, unprotected_by_team)
        if target is None:
            continue
        # One attempt per player per week regardless of outcome -- keeps
        # a second poacher from also going after the same just-targeted
        # player in this same pass.
        unprotected_by_team[target.team_abbr] = [
            p for p in unprotected_by_team[target.team_abbr] if p.player_id != target.player_id
        ]
        if target.team_abbr == season.user_team_abbr:
            if pending is None:
                pending = {
                    "player_id": target.player_id, "player_name": target.full_name,
                    "position": target.position.value, "from_team": target.team_abbr,
                    "to_team": poacher_abbr, "week": week_num,
                }
            continue  # awaits the user's own allow/block decision
        execute_poach(target.player_id, poacher_abbr, week_num)
    season.pending_poach = pending
    season.poaching_evaluated_through_week = week_num
    return pending


# --- R16 Sec 6: Game-Day Elevation --------------------------------------

def revert_elevated_players() -> None:
    """R16 Sec 6: "auto-reverts to PRACTICE_SQUAD immediately after that
    week's game(s) simulate" -- unlimited manual uses (decision #9) only
    stays a real weekly choice if elevation doesn't quietly become a
    permanent promotion. User's team only in practice (no AI equivalent,
    Sec 6's own last bullet -- nothing ever sets ELEVATED for an AI
    team), but this scans every team's roster rather than assuming
    that, so it stays correct even if that ever changes."""
    with get_session() as s:
        elevated = list(s.exec(select(Player).where(Player.roster_status == RosterStatus.ELEVATED)))
        for p in elevated:
            p.roster_status = RosterStatus.PRACTICE_SQUAD
            s.add(p)
        s.commit()

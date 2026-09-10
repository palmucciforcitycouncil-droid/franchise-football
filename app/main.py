from __future__ import annotations

import json
import tempfile
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlencode

from dotenv import load_dotenv
load_dotenv()

from markupsafe import Markup, escape
from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_league_seed
from app.data.teams import TEAMS, TEAMS_BY_ABBR, TeamInfo
from app.engine.placeholder_ratings import ratings_for
from app.engine.rng import RNG, stable_seed
from app.engine.game_sim import simulate_game, TeamSim
from app.engine.box_score import build_box_score
from app.engine.defensive_box_score import build_defensive_box_score
from app.engine.season_stats import aggregate_season_stats, aggregate_season_defensive_stats
from app.engine import score_fidelity, awards
from app.engine.playoffs import bubble_teams, final_division_standings
from app.engine.scouting import find_next_opponent, build_scouting_report
from app.engine.gameplan import (
    Gameplan, OFFENSIVE_AGGRESSIVENESS, DEFENSIVE_AGGRESSIVENESS,
    COVERAGE_SCHEMES, BLITZ_STRATEGIES, RZ_OFFENSE_STYLES, RZ_DEFENSE_STYLES,
)
from app.engine.progression import PROGRESSED_ATTRIBUTES
from app.services import season_state, depth_chart_overrides, gameplan_store, history_store
from app.services.depth_chart import clear_starters_cache
from app.core.db import get_session
from app.models.player import Player, Position
from sqlmodel import select

app = FastAPI(title="Franchise Football")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"teams": TEAMS})


FREE_AGENTS_TEAM = TeamInfo(abbr="FA", location="Free Agents", conference="", division="")

# How many players at each position actually start, per depth_chart.py's
# OffensiveStarters/DefensiveStarters (wr1/wr2/wr3, dt1/dt2, cb1/cb2) --
# every other position starts exactly one. Used to highlight the right
# NUMBER of starters on /roster and /depth-chart, not just the top player
# at every position regardless of how many the engine actually plays.
STARTER_COUNTS: dict[Position, int] = {Position.WR: 3, Position.DT: 2, Position.CB: 2}

# Position roster minimums for Team Quota badges (M4: Figma RosterPage.tsx)
_ROSTER_POSITION_MINIMUMS: dict[str, int] = {
    "QB": 2, "RB": 3, "WR": 5, "TE": 2, "C": 1, "G": 2, "T": 2,
    "DE": 2, "DT": 1, "LB": 6, "CB": 4, "S": 4, "K": 1, "P": 1,
}

# M11 correction: Team Quota pills need a GENERIC group per player --
# `_ROSTER_POSITION_MINIMUMS` above was always keyed by these generic
# labels, but the original M4 build counted players by their RAW
# Position enum value (QB/HB/FB/WR/TE/LT/LG/C/RG/RT/LE/RE/DT/LOLB/MLB/
# ROLB/CB/FS/SS/K/P -- Madden's granular scheme, see player.py's own
# docstring for why it's kept that granular). Since the minimums dict
# has no "HB"/"LT"/"LOLB"/etc keys, 6 of 14 pills (RB/G/T/DE/LB/S) never
# matched anything and silently never rendered -- a real, previously-
# unnoticed bug, not a stale-doc issue like M9's. This mapping is what
# was actually missing.
_QUOTA_GROUP_FOR_POSITION: dict[Position, str] = {
    Position.QB: "QB", Position.HB: "RB", Position.FB: "RB",
    Position.WR: "WR", Position.TE: "TE",
    Position.LT: "T", Position.RT: "T", Position.LG: "G", Position.RG: "G", Position.C: "C",
    Position.LE: "DE", Position.RE: "DE", Position.DT: "DT",
    Position.LOLB: "LB", Position.MLB: "LB", Position.ROLB: "LB",
    Position.CB: "CB", Position.FS: "S", Position.SS: "S",
    Position.K: "K", Position.P: "P",
}
QUOTA_GROUPS = ["QB", "RB", "WR", "TE", "C", "G", "T", "DE", "DT", "LB", "CB", "S", "K", "P"]

# The real Figma source uses a SECOND, coarser 10-group breakdown for the
# Filter panel's position checkboxes and the Top Free Agents pager
# (FilterPanel.tsx's own `positions` list collapses OL/DL/ST further than
# the Team Quota pills' 14-group split does). Deliberately NOT reproduced
# as a second grouping here: a quota pill and a filter checkbox sharing
# one `position` query param but two different label spaces (e.g. a "G"
# pill setting `position=G`, which the 10-group filter would never match)
# is a real bug, not a faithfulness nice-to-have -- so both widgets share
# QUOTA_GROUPS/_QUOTA_GROUP_FOR_POSITION instead. Finer-grained than
# Figma's filter panel, not a regression.

MAX_ROSTER_SIZE = 53  # the real NFL active-roster limit (RosterTable.tsx's
                       # own hardcoded constant) -- not fabricated per-team
                       # data, just an unenforced real-world number this
                       # engine doesn't cap rosters against yet.

# Column ids sortable via the Roster table's header links (RosterTable.tsx's
# own `handleSort` keys), GET-param + full-page-reload like Stats' M3
# precedent -- not client JS state.
ROSTER_SORT_KEYS = (
    "num", "name", "pos", "age", "ovr", "pot", "spd", "str", "agi",
    "tpw", "tac", "cth", "tck", "awr", "sta", "inj", "mor", "ctr", "yrs", "dep",
)


def _roster_avg_throw_accuracy(p: Player) -> int:
    """RosterTable.tsx's TAC column -- not a single modeled attribute on
    Player, but a real, disclosed average of the three throw-accuracy
    splits the model already has (short/mid/deep), not a fabricated one."""
    return round((p.throw_accuracy_short + p.throw_accuracy_mid + p.throw_accuracy_deep) / 3)


def _roster_injury_risk(p: Player) -> int:
    """RosterTable.tsx's INJ column, read the opposite direction from our
    real `durability` field per Player's own module docstring formula
    (`proneness = 99 - durability`) -- the same real data, not a second
    modeled attribute."""
    return 99 - p.durability


def _roster_sort_value(p: Player, key: str, depth_slot: dict[str, str]):
    return {
        "num": p.jersey_number, "name": p.full_name.lower(), "pos": p.position.value,
        "age": p.age, "ovr": p.overall_rating, "pot": p.potential, "spd": p.speed,
        "str": p.strength, "agi": p.agility, "tpw": p.throw_power,
        "tac": _roster_avg_throw_accuracy(p), "cth": p.catching, "tck": p.tackle,
        "awr": p.awareness, "sta": p.stamina, "inj": _roster_injury_risk(p),
        "mor": p.morale, "ctr": p.salary, "yrs": p.years_pro,
        "dep": depth_slot.get(p.player_id, ""),
    }.get(key, p.overall_rating)


@app.get("/roster", response_class=HTMLResponse)
def roster_view(
    request: Request,
    team_abbr: str | None = None,
    view: str = "attributes",
    position: list[str] = Query(default=[]),
    min_ovr: int | None = None, max_ovr: int | None = None,
    min_spd: int | None = None, max_spd: int | None = None,
    min_cth: int | None = None, max_cth: int | None = None,
    min_tck: int | None = None, max_tck: int | None = None,
    rookie: bool = False,
    sort: str | None = None, dir: str = "asc",
    fa_pos: str = "All",
    find_q: str = "", find_pos: str = "all", find_team: str = "all",
):
    """Real player data (2,365 players across 32 teams, plus 71 free
    agents) has existed since the roster import but was only ever
    consumed internally by the engine -- this is the first page that
    actually shows it. No team selected yet -> just the picker.
    `team_abbr=FA` is a pseudo-team (Player.team_abbr is None for a free
    agent) rather than a real TEAMS entry -- FREE_AGENTS_TEAM stands in
    so the template's `team.location`/`team.abbr` access works the same
    way for both. `starters` marks the top N highest-overall_rating
    players at each position (STARTER_COUNTS -- 3 for WR, 2 for DT/CB,
    1 otherwise, matching how many depth_chart.py's OffensiveStarters/
    DefensiveStarters actually start at each position) -- always empty
    for free agents, since "starter" isn't a meaningful concept for
    players with no team.

    M11 correction (real source: RosterPage.tsx/RosterTable.tsx/
    FilterPanel.tsx, not M4's simplified build): real Filter panel
    (position groups, OVR/SPD/CTH/TCK ranges, Rookie toggle -- Injured/
    Trade-block toggles stayed omitted, no in-season health or trade
    system exists), clickable Team Quota pills (+ a real ALL/53 pill,
    fixing the quota-count bug described above `_QUOTA_GROUP_FOR_POSITION`),
    sortable/sticky-column table with the 8 real attribute columns M4
    never added (TPW/TAC/CTH/TCK/INJ/MOR/Contract/Depth -- Health/Trade
    columns stay omitted, same disclosed no-real-data reasoning), a
    whole-row click to open the Player Card, and the two of Figma's three
    quick-access boxes with real underlying data (Top Free Agents, Find
    Player -- Trade Block is skipped, no trade system exists, see the
    GM Desk audit note in ROADMAP.md §2b)."""
    if view not in ("attributes", "stats"):
        view = "attributes"
    if team_abbr is None:
        # GDD Sec 10.1: default screen state resolves to the user's team
        # without a picker interaction, once one has been chosen.
        team_abbr = season_state.get_season().user_team_abbr
    if team_abbr is None:
        return templates.TemplateResponse(request, "roster.html", {"teams": TEAMS, "team": None, "players": None, "view": view})
    if team_abbr != "FA" and team_abbr not in TEAMS_BY_ABBR:
        raise HTTPException(404, "No such team")

    with get_session() as s:
        if team_abbr == "FA":
            players = list(s.exec(select(Player).where(Player.team_abbr == None)))  # noqa: E711 (SQLAlchemy needs `== None`, not `is None`)
        else:
            players = list(s.exec(select(Player).where(Player.team_abbr == team_abbr)))

    position_rank = {pos: i for i, pos in enumerate(Position)}
    players.sort(key=lambda p: (position_rank[p.position], -p.overall_rating))

    starters: set[str] = set()
    if team_abbr != "FA":
        seen_counts: dict[Position, int] = {}
        for p in players:
            count_so_far = seen_counts.get(p.position, 0)
            if count_so_far < STARTER_COUNTS.get(p.position, 1):
                starters.add(p.player_id)
            seen_counts[p.position] = count_so_far + 1

    # Team Quota badges: counted by the fixed generic grouping (see
    # _QUOTA_GROUP_FOR_POSITION's docstring for the bug this replaces).
    total_roster_count = len(players)
    position_quotas = {
        grp: {"current": sum(1 for p in players if _QUOTA_GROUP_FOR_POSITION[p.position] == grp),
              "min": _ROSTER_POSITION_MINIMUMS.get(grp, 1)}
        for grp in QUOTA_GROUPS
    }

    # Depth chart groups (reusing depth_chart_view's logic)
    by_position = defaultdict(list)
    for p in players:
        by_position[p.position].append(p)
    depth_chart_groups = [
        {
            "position": pos.value,
            "players": depth_chart_overrides.resolve_order(team_abbr, pos.value, players_at_pos),
            "starter_count": STARTER_COUNTS.get(pos, 1),
        }
        for pos, players_at_pos in sorted(by_position.items(), key=lambda kv: list(Position).index(kv[0]))
    ] if team_abbr != "FA" else []

    # Depth slot label per player ("QB1", "QB2", ...) -- RosterTable.tsx's
    # DEP column, real (each group's already-resolved starter order),
    # not fabricated. Empty for free agents (no depth chart concept).
    depth_slot: dict[str, str] = {}
    for group in depth_chart_groups:
        for i, p in enumerate(group["players"], start=1):
            depth_slot[p.player_id] = f"{group['position']}{i}"

    # Real Filter panel (FilterPanel.tsx): position groups (QUOTA_GROUPS --
    # see that constant's own comment for why this reuses the quota
    # grouping instead of Figma's separate 10-group filter list), attribute
    # ranges, Rookie (age <= 23, Figma's own definition). Applied to the
    # TABLE ROWS only -- position_quotas/total_roster_count above stay
    # computed off the full roster, same as RosterTable.tsx's own
    # `totalRosterCount = players.length` (the unfiltered prop), not the
    # filtered `sortedPlayers`.
    filtered_players = players
    if position:
        wanted = set(position)
        filtered_players = [p for p in filtered_players if _QUOTA_GROUP_FOR_POSITION[p.position] in wanted]
    if min_ovr is not None:
        filtered_players = [p for p in filtered_players if p.overall_rating >= min_ovr]
    if max_ovr is not None:
        filtered_players = [p for p in filtered_players if p.overall_rating <= max_ovr]
    if min_spd is not None:
        filtered_players = [p for p in filtered_players if p.speed >= min_spd]
    if max_spd is not None:
        filtered_players = [p for p in filtered_players if p.speed <= max_spd]
    if min_cth is not None:
        filtered_players = [p for p in filtered_players if p.catching >= min_cth]
    if max_cth is not None:
        filtered_players = [p for p in filtered_players if p.catching <= max_cth]
    if min_tck is not None:
        filtered_players = [p for p in filtered_players if p.tackle >= min_tck]
    if max_tck is not None:
        filtered_players = [p for p in filtered_players if p.tackle <= max_tck]
    if rookie:
        filtered_players = [p for p in filtered_players if p.age <= 23]

    active_filters = []
    if position:
        active_filters.append("Position: " + ", ".join(position))
    if min_ovr is not None or max_ovr is not None:
        active_filters.append(f"OVR {min_ovr if min_ovr is not None else 0}-{max_ovr if max_ovr is not None else 99}")
    if min_spd is not None or max_spd is not None:
        active_filters.append(f"SPD {min_spd if min_spd is not None else 0}-{max_spd if max_spd is not None else 99}")
    if min_cth is not None or max_cth is not None:
        active_filters.append(f"CTH {min_cth if min_cth is not None else 0}-{max_cth if max_cth is not None else 99}")
    if min_tck is not None or max_tck is not None:
        active_filters.append(f"TCK {min_tck if min_tck is not None else 0}-{max_tck if max_tck is not None else 99}")
    if rookie:
        active_filters.append("Rookie (age <= 23)")
    generated_query = " AND ".join(active_filters) if active_filters else None

    # Sortable columns (GET-param + full-page-reload, Stats' M3 precedent).
    effective_sort = sort if sort in ROSTER_SORT_KEYS else None
    direction = dir if dir in ("asc", "desc") else "asc"
    if effective_sort:
        rows = sorted(filtered_players, key=lambda p: _roster_sort_value(p, effective_sort, depth_slot), reverse=(direction == "desc"))
    else:
        rows = filtered_players

    def roster_query(overrides: dict) -> str:
        base: dict = {
            "team_abbr": team_abbr, "view": view, "position": position,
            "min_ovr": min_ovr, "max_ovr": max_ovr, "min_spd": min_spd, "max_spd": max_spd,
            "min_cth": min_cth, "max_cth": max_cth, "min_tck": min_tck, "max_tck": max_tck,
            "rookie": "1" if rookie else None,
        }
        base.update(overrides)
        params = []
        for key, val in base.items():
            if key == "position":
                params.extend(("position", v) for v in val)
            elif val not in (None, "", False):
                params.append((key, val))
        return "/roster?" + urlencode(params)

    sort_links = {}
    for cid in ROSTER_SORT_KEYS:
        next_dir = "desc" if (effective_sort == cid and direction == "asc") else "asc"
        sort_links[cid] = roster_query({"sort": cid, "dir": next_dir})

    quota_pill_links = {}
    for grp in QUOTA_GROUPS:
        new_position = [] if position == [grp] else [grp]
        quota_pill_links[grp] = roster_query({"position": new_position})
    all_pill_link = roster_query({"position": []})
    clear_filters_link = roster_query({
        "position": [], "min_ovr": None, "max_ovr": None, "min_spd": None, "max_spd": None,
        "min_cth": None, "max_cth": None, "min_tck": None, "max_tck": None, "rookie": None,
    })

    # Compute stats data if needed
    stats_data = None
    if view == "stats":
        season = season_state.get_season()
        player_rows, _ = _stats_page_aggregates(season)
        # Filter to this team only
        stats_data = {(r["player_name"], r["player_pos"]): r for r in player_rows if r["player_team"] == team_abbr}

    # Top Free Agents (TopFreeAgentsBox.tsx): real free agents, OVR >= 75,
    # top 5 for the currently-paged position group. Position-paged via a
    # GET param (fa_pos) rather than JS prev/next state, same pattern as
    # everything else on this page.
    if fa_pos not in QUOTA_GROUPS and fa_pos != "All":
        fa_pos = "All"
    with get_session() as s:
        all_free_agents = list(s.exec(select(Player).where(Player.team_abbr == None)))  # noqa: E711
    if fa_pos != "All":
        all_free_agents = [p for p in all_free_agents if _QUOTA_GROUP_FOR_POSITION[p.position] == fa_pos]
    top_free_agents = sorted((p for p in all_free_agents if p.overall_rating >= 75), key=lambda p: -p.overall_rating)[:5]
    fa_pos_options = ["All"] + QUOTA_GROUPS
    fa_prev_pos = fa_pos_options[fa_pos_options.index(fa_pos) - 1]
    fa_next_pos = fa_pos_options[(fa_pos_options.index(fa_pos) + 1) % len(fa_pos_options)]

    # Find Player (FindPlayerBox.tsx): real league-wide name/position/team
    # search -- unlike Figma's own mock version, results reuse this
    # project's existing Player Card modal (player_link()) instead of a
    # second, separate detail dialog.
    find_results = []
    if find_q or find_pos != "all" or find_team != "all":
        with get_session() as s:
            find_results = list(s.exec(select(Player)))
        if find_q:
            ql = find_q.lower()
            find_results = [p for p in find_results if ql in p.full_name.lower()]
        if find_pos != "all":
            find_results = [p for p in find_results if p.position.value == find_pos]
        if find_team != "all":
            find_results = [p for p in find_results if p.team_abbr == find_team]
        find_results.sort(key=lambda p: -p.overall_rating)
        find_results = find_results[:25]

    team = FREE_AGENTS_TEAM if team_abbr == "FA" else TEAMS_BY_ABBR[team_abbr]
    return templates.TemplateResponse(
        request,
        "roster.html",
        {
            "teams": TEAMS, "team": team, "players": rows, "starters": starters,
            "view": view, "position_quotas": position_quotas, "depth_chart_groups": depth_chart_groups,
            "stats_data": stats_data, "depth_slot": depth_slot,
            "total_roster_count": total_roster_count, "max_roster_size": MAX_ROSTER_SIZE,
            "quota_pill_links": quota_pill_links, "all_pill_link": all_pill_link,
            "position_filter": position, "sort_links": sort_links, "sort": effective_sort, "dir": direction,
            "filter_groups": QUOTA_GROUPS,
            "min_ovr": min_ovr, "max_ovr": max_ovr, "min_spd": min_spd, "max_spd": max_spd,
            "min_cth": min_cth, "max_cth": max_cth, "min_tck": min_tck, "max_tck": max_tck,
            "rookie": rookie, "generated_query": generated_query, "clear_filters_link": clear_filters_link,
            "avg_throw_accuracy": _roster_avg_throw_accuracy, "injury_risk": _roster_injury_risk,
            "top_free_agents": top_free_agents, "fa_pos": fa_pos, "fa_prev_pos": fa_prev_pos, "fa_next_pos": fa_next_pos,
            "find_q": find_q, "find_pos": find_pos, "find_team": find_team, "find_results": find_results,
            "all_positions": list(Position),
        },
    )


def _roster_by_position(team_abbr: str) -> dict[Position, list[Player]]:
    with get_session() as s:
        players = list(s.exec(select(Player).where(Player.team_abbr == team_abbr)))
    by_position: dict[Position, list[Player]] = {}
    for p in players:
        by_position.setdefault(p.position, []).append(p)
    return by_position


@app.get("/depth-chart", response_class=HTMLResponse)
def depth_chart_view(request: Request, team_abbr: str | None = None):
    """The real depth chart (app/services/depth_chart_overrides.py) --
    lets the user actually set who starts at each position, replacing
    the highest-overall_rating stand-in depth_chart.py used alone. Each
    position group is ordered via resolve_order (override, falling back
    to rating) so this page shows exactly what the engine will use."""
    if team_abbr is None:
        # GDD Sec 10.1: default screen state resolves to the user's team
        # without a picker interaction, once one has been chosen.
        team_abbr = season_state.get_season().user_team_abbr
    if team_abbr is None:
        return templates.TemplateResponse(request, "depth_chart.html", {"teams": TEAMS, "team": None, "groups": None})
    if team_abbr not in TEAMS_BY_ABBR:
        raise HTTPException(404, "No such team")

    by_position = _roster_by_position(team_abbr)
    groups = [
        {
            "position": pos.value,
            "players": depth_chart_overrides.resolve_order(team_abbr, pos.value, players),
            "starter_count": STARTER_COUNTS.get(pos, 1),
        }
        for pos, players in sorted(by_position.items(), key=lambda kv: list(Position).index(kv[0]))
    ]

    return templates.TemplateResponse(
        request,
        "depth_chart.html",
        {"teams": TEAMS, "team": TEAMS_BY_ABBR[team_abbr], "groups": groups},
    )


@app.post("/depth-chart/{team_abbr}/{position_value}/move")
def depth_chart_move(team_abbr: str, position_value: str, player_id: str = Form(...), direction: str = Form(...)):
    if team_abbr not in TEAMS_BY_ABBR:
        raise HTTPException(404, "No such team")
    try:
        position = Position(position_value)
    except ValueError:
        raise HTTPException(404, "No such position")

    players = _roster_by_position(team_abbr).get(position, [])
    current_order = [p.player_id for p in depth_chart_overrides.resolve_order(team_abbr, position_value, players)]
    depth_chart_overrides.move_player(team_abbr, position_value, current_order, player_id, direction)
    clear_starters_cache()  # the override just changed -- don't serve a stale cached starter

    return RedirectResponse(url=f"/depth-chart?team_abbr={team_abbr}", status_code=303)


@app.post("/depth-chart/{team_abbr}/auto-fill")
def depth_chart_auto_fill(team_abbr: str, respect_fatigue: bool = Form(False), lock_starters: bool = Form(False)):
    """M15 correction (real source: AutoFillModal.tsx) -- see
    depth_chart_overrides.auto_fill()'s own docstring for exactly which
    2 of the source's 4 toggles are offered and why the other 2 aren't
    (both need data this engine's Player model doesn't have)."""
    if team_abbr not in TEAMS_BY_ABBR:
        raise HTTPException(404, "No such team")

    by_position = _roster_by_position(team_abbr)
    depth_chart_overrides.auto_fill(team_abbr, by_position, STARTER_COUNTS, respect_fatigue=respect_fatigue, lock_starters=lock_starters)
    clear_starters_cache()

    return RedirectResponse(url=f"/depth-chart?team_abbr={team_abbr}", status_code=303)


def _season_stat_leaders(season, top_n: int = 15):
    """Thin wrapper: aggregate_season_stats does the real work (shared
    with app/engine/awards.py, which needs the full untruncated
    aggregation); this just sorts by yards and slices to top_n for
    Dashboard/Stats display."""
    passing, rushing, receiving = aggregate_season_stats(season)
    return (
        sorted(passing.values(), key=lambda l: -l.yards)[:top_n],
        sorted(rushing.values(), key=lambda l: -l.yards)[:top_n],
        sorted(receiving.values(), key=lambda l: -l.yards)[:top_n],
    )


def _defensive_stat_leaders(season, top_n: int = 15):
    """Same pattern as _season_stat_leaders, sorted by solo tackles
    (the closest single-number analog to "yards" for a defensive
    leaderboard) -- see app/engine/defensive_box_score.py for what's
    real here, including Defensive TD (GDD Sec 6.7.2, ROADMAP.md M1)."""
    defense = aggregate_season_defensive_stats(season)
    return sorted(defense.values(), key=lambda l: -l.solo_tackles)[:top_n]


def _team_schedule_for(season, team_abbr: str) -> list[dict]:
    """One row per week this team plays (byes just don't appear), each
    with the opponent and W/L/score once that week's game has been
    simulated -- the real per-team view the Figma source's TeamSchedule
    component shows, as opposed to the league-wide "latest results"
    the pre-M9 dashboard had. Built from season.schedule, the same data
    every other schedule view (e.g. /season) already reads."""
    rows = []
    for week_num, week in enumerate(season.schedule, start=1):
        game = next((g for g in week if team_abbr in (g.home_abbr, g.away_abbr)), None)
        if game is None:
            continue
        is_home = game.home_abbr == team_abbr
        opponent_abbr = game.away_abbr if is_home else game.home_abbr
        result = None
        if game.result is not None:
            user_score = game.result.home_score if is_home else game.result.away_score
            opp_score = game.result.away_score if is_home else game.result.home_score
            won = (game.result.winner == "home") == is_home
            result = {"won": won, "user_score": user_score, "opp_score": opp_score}
        rows.append({"week": week_num, "opponent_abbr": opponent_abbr, "is_home": is_home, "result": result})
    return rows


def _last_played_game_for(season, team_abbr: str) -> dict | None:
    """The most recently completed game involving this team specifically
    (not just the most recent league-wide week, which may have been a
    bye for this team) -- feeds the Dashboard's Box Score/Play-by-Play
    widgets (ROADMAP.md M9), reusing the exact same build_box_score/
    build_defensive_box_score calls result.html already makes for any
    other game."""
    for week_num in range(season.current_week - 1, 0, -1):
        game = next(
            (g for g in season.schedule[week_num - 1]
             if team_abbr in (g.home_abbr, g.away_abbr) and g.result is not None),
            None,
        )
        if game is None:
            continue
        is_home = game.home_abbr == team_abbr
        opponent_abbr = game.away_abbr if is_home else game.home_abbr
        return {
            "week": week_num,
            "opponent_abbr": opponent_abbr,
            "is_home": is_home,
            "home_abbr": game.home_abbr,
            "away_abbr": game.away_abbr,
            "won": (game.result.winner == "home") == is_home,
            "user_score": game.result.home_score if is_home else game.result.away_score,
            "opp_score": game.result.away_score if is_home else game.result.home_score,
            "box": build_box_score(game.result.plays, team_abbr),
            "defense": build_defensive_box_score(game.result.plays, team_abbr),
            "plays": game.result.plays,
        }
    return None


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_view(request: Request):
    """League-at-a-glance landing page, pulling from pieces that already
    exist rather than introducing new state. Doesn't replace `/`, which
    stays the single-game simulator -- the GDD lists Dashboard and
    "Simulate a Game" as distinct screens.

    GDD Sec 10.1: Dashboard is the default landing page and always
    resolves to the user's team -- if no team has been chosen yet for
    this franchise, redirect to the one-time team-selection screen
    rather than rendering a teamless dashboard.

    ROADMAP.md M9: the real Figma layout (docs/figma-export/src/app/
    DASHBOARD_DOCUMENTATION.md) is a 3-column grid of 8 widgets --
    Division Standings, Team Schedule, Scouting Panel, League Power
    Rankings, League Top Performers, Box Score, Team Top Performers,
    Play-by-Play. All 8 are real data already produced elsewhere in
    the engine (standings/schedule/scouting/box-score machinery); this
    route just queries/filters it per-widget instead of the single
    league-wide top-10 + latest-week-results shape the pre-M9 version
    used, and dashboard.html arranges the result into that grid."""
    season = season_state.get_season()
    if season.user_team_abbr is None:
        return RedirectResponse(url="/team-select", status_code=303)

    user_abbr = season.user_team_abbr
    user_info = TEAMS_BY_ABBR[user_abbr]
    gameplan = gameplan_store.get_gameplan(user_abbr)

    next_opponent = find_next_opponent(season, user_abbr)
    scouting = None
    if next_opponent is not None:
        opponent_abbr, team_is_home = next_opponent
        scouting = build_scouting_report(season, opponent_abbr)
        scouting["opponent_team"] = TEAMS_BY_ABBR[opponent_abbr]
        scouting["is_home_game"] = team_is_home

    division_standings = sorted(
        (r for r in season.records.values()
         if TEAMS_BY_ABBR[r.abbr].conference == user_info.conference
         and TEAMS_BY_ABBR[r.abbr].division == user_info.division),
        key=lambda r: (-r.win_pct, -r.point_diff, r.location),
    )
    power_rankings = sorted(season.records.values(), key=lambda r: -r.power_rating)[:10]
    team_schedule = _team_schedule_for(season, user_abbr)
    last_game = _last_played_game_for(season, user_abbr)

    passing_leaders, rushing_leaders, receiving_leaders = _season_stat_leaders(season, top_n=5)

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "season": season,
            "gameplan": gameplan,
            "scouting": scouting,
            "offensive_aggressiveness_options": OFFENSIVE_AGGRESSIVENESS,
            "defensive_aggressiveness_options": DEFENSIVE_AGGRESSIVENESS,
            "coverage_options": COVERAGE_SCHEMES,
            "blitz_options": BLITZ_STRATEGIES,
            "rz_offense_options": RZ_OFFENSE_STYLES,
            "rz_defense_options": RZ_DEFENSE_STYLES,
            "division_standings": division_standings,
            "power_rankings": power_rankings,
            "team_schedule": team_schedule,
            "last_game": last_game,
            "passing_leaders": passing_leaders,
            "rushing_leaders": rushing_leaders,
            "receiving_leaders": receiving_leaders,
        },
    )


@app.post("/gameplan")
def gameplan_submit(
    offensive_aggressiveness: str = Form(...),
    defensive_aggressiveness: str = Form(...),
    coverage: str = Form(...),
    blitz: str = Form(...),
    rz_offense: str = Form(...),
    rz_defense: str = Form(...),
):
    """GDD Sec 10.4.1's Weekly Gameplan: always sets the CURRENT user's
    team (there's no team_abbr in the form -- the panel only ever
    appears on the user's own Dashboard/Staff screens, matching Sec
    10.1's "gameplan settings" being exclusive to the user's team).
    404s if no team has been chosen yet rather than silently no-op'ing."""
    season = season_state.get_season()
    if season.user_team_abbr is None:
        raise HTTPException(404, "No team chosen yet")

    for value, options, field in [
        (offensive_aggressiveness, OFFENSIVE_AGGRESSIVENESS, "offensive_aggressiveness"),
        (defensive_aggressiveness, DEFENSIVE_AGGRESSIVENESS, "defensive_aggressiveness"),
        (coverage, COVERAGE_SCHEMES, "coverage"),
        (blitz, BLITZ_STRATEGIES, "blitz"),
        (rz_offense, RZ_OFFENSE_STYLES, "rz_offense"),
        (rz_defense, RZ_DEFENSE_STYLES, "rz_defense"),
    ]:
        if value not in options:
            raise HTTPException(422, f"Invalid {field}: {value!r}")

    gameplan_store.set_gameplan(season.user_team_abbr, Gameplan(
        offensive_aggressiveness=offensive_aggressiveness,
        defensive_aggressiveness=defensive_aggressiveness,
        coverage=coverage,
        blitz=blitz,
        rz_offense=rz_offense,
        rz_defense=rz_defense,
    ))
    return RedirectResponse(url="/dashboard", status_code=303)


# Stats page redesign (GDD Sec 10.4, ROADMAP.md M3). Real source:
# docs/figma-export/src/app/components/StatsPage.tsx +
# stats/StatColumnChooser.tsx -- Team/Player/Coach tabs, sortable
# columns, a customizable-column chooser. Translated from the Figma
# source's React client-state implementation into this project's
# existing GET-query-param + full-page-reload pattern (see /playoffs's
# ?view=, and the "no htmx/framework" architecture note in HANDOFF.md)
# rather than introducing a new client-side JS subsystem. The catalog
# below is a deliberately TRIMMED version of the Figma source's ~150-stat
# hierarchy (docs/figma-export/src/app/lib/statHierarchy.ts) -- only
# stats this engine actually attributes to a real player/team
# (season_stats.py, defensive_box_score.py, TeamRecord) are offered;
# advanced metrics with no real underlying data here (air yards,
# pressures, contested catches, snap counts, coach records, ...) are
# omitted rather than fabricated, same discipline as the Player Card's
# Stats tab (and its Contract tab, M8 -- real salary/signing bonus, no
# fabricated cap/years-remaining data).
PLAYER_STAT_CATEGORIES: list[dict] = [
    {"label": "Identity & Participation", "stats": [
        {"id": "player_name", "label": "Player Name"},
        {"id": "player_pos", "label": "Position"},
        {"id": "player_team", "label": "Team"},
        {"id": "player_num", "label": "Jersey #"},
        {"id": "player_age", "label": "Age"},
        {"id": "player_exp", "label": "Years Pro"},
        {"id": "games_played", "label": "Games Played"},
    ]},
    {"label": "Passing", "stats": [
        {"id": "pass_att", "label": "Pass Attempts"},
        {"id": "pass_cmp", "label": "Completions"},
        {"id": "pass_cmp_pct", "label": "Completion %"},
        {"id": "pass_yds", "label": "Passing Yards"},
        {"id": "pass_yds_per_att", "label": "Yards per Attempt"},
        {"id": "pass_td", "label": "Passing TDs"},
        {"id": "pass_int", "label": "Interceptions Thrown"},
        {"id": "sacks_taken", "label": "Sacks Taken"},
        {"id": "qb_rating", "label": "Passer Rating"},
    ]},
    {"label": "Rushing", "stats": [
        {"id": "rush_att", "label": "Rush Attempts"},
        {"id": "rush_yds", "label": "Rushing Yards"},
        {"id": "yds_per_rush", "label": "Yards per Rush"},
        {"id": "rush_td", "label": "Rushing TDs"},
        {"id": "fumbles_lost", "label": "Fumbles Lost"},
    ]},
    {"label": "Receiving", "stats": [
        {"id": "targets", "label": "Targets"},
        {"id": "receptions", "label": "Receptions"},
        {"id": "catch_pct", "label": "Catch %"},
        {"id": "rec_yds", "label": "Receiving Yards"},
        {"id": "rec_td", "label": "Receiving TDs"},
    ]},
    {"label": "Defense", "stats": [
        {"id": "solo_tackles", "label": "Solo Tackles"},
        {"id": "tackles_for_loss", "label": "Tackles for Loss"},
        {"id": "sacks", "label": "Sacks"},
        {"id": "def_int", "label": "Interceptions"},
        {"id": "passes_defended", "label": "Passes Defended"},
        {"id": "forced_fumbles", "label": "Forced Fumbles"},
        {"id": "fumble_recoveries", "label": "Fumble Recoveries"},
        {"id": "defensive_tds", "label": "Defensive TDs"},
    ]},
    {"label": "Kicking", "stats": [
        {"id": "fg_att", "label": "FG Attempts"},
        {"id": "fg_made", "label": "FG Made"},
        {"id": "fg_pct", "label": "FG %"},
        {"id": "fg_lt30", "label": "FG <30 yds"},
        {"id": "fg_30_39", "label": "FG 30-39 yds"},
        {"id": "fg_40_49", "label": "FG 40-49 yds"},
        {"id": "fg_50_plus", "label": "FG 50+ yds"},
        {"id": "xp_att", "label": "XP Attempts"},
        {"id": "xp_made", "label": "XP Made"},
        {"id": "xp_pct", "label": "XP %"},
    ]},
    {"label": "Punting", "stats": [
        {"id": "punts", "label": "Punts"},
        {"id": "punt_net_yds", "label": "Punt Yards (Net)"},
        {"id": "punt_net_avg", "label": "Net Punt Average"},
        {"id": "punts_inside_20", "label": "Punts Inside 20"},
    ]},
]
PLAYER_DEFAULT_COLUMNS = ["player_name", "player_pos", "player_team", "player_age", "games_played"]
PLAYER_STAT_LABELS = {s["id"]: s["label"] for cat in PLAYER_STAT_CATEGORIES for s in cat["stats"]}
PLAYER_PRESETS: dict[str, list[str]] = {
    "default": PLAYER_DEFAULT_COLUMNS,
    "qb": ["player_name", "player_pos", "player_team", "games_played", "pass_att", "pass_cmp", "pass_cmp_pct", "pass_yds", "pass_yds_per_att", "pass_td", "pass_int", "qb_rating"],
    "rushing": ["player_name", "player_pos", "player_team", "games_played", "rush_att", "rush_yds", "yds_per_rush", "rush_td", "fumbles_lost"],
    "receiving": ["player_name", "player_pos", "player_team", "games_played", "targets", "receptions", "catch_pct", "rec_yds", "rec_td"],
    "defense": ["player_name", "player_pos", "player_team", "games_played", "solo_tackles", "tackles_for_loss", "sacks", "def_int", "passes_defended", "forced_fumbles", "fumble_recoveries", "defensive_tds"],
    "kicking": ["player_name", "player_team", "games_played", "fg_made", "fg_att", "fg_pct", "xp_made", "xp_att", "xp_pct"],
    "punting": ["player_name", "player_team", "games_played", "punts", "punt_net_yds", "punt_net_avg", "punts_inside_20"],
    "all": list(PLAYER_STAT_LABELS),
}

TEAM_STAT_CATEGORIES: list[dict] = [
    {"label": "Identity & Record", "stats": [
        {"id": "team_name", "label": "Team Name"},
        {"id": "conference", "label": "Conference"},
        {"id": "division", "label": "Division"},
        {"id": "wins", "label": "Wins"},
        {"id": "losses", "label": "Losses"},
        {"id": "win_pct", "label": "Win %"},
        {"id": "points_for", "label": "Points For"},
        {"id": "points_against", "label": "Points Against"},
        {"id": "point_diff", "label": "Point Differential"},
        {"id": "power_rating", "label": "Power Rating"},
    ]},
    {"label": "Offense", "stats": [
        {"id": "off_plays", "label": "Offensive Plays"},
        {"id": "off_yds", "label": "Total Yards"},
        {"id": "team_pass_att", "label": "Pass Attempts"},
        {"id": "team_pass_cmp", "label": "Completions"},
        {"id": "team_pass_yds", "label": "Passing Yards"},
        {"id": "team_pass_td", "label": "Passing TDs"},
        {"id": "team_pass_int", "label": "Interceptions Thrown"},
        {"id": "team_rush_att", "label": "Rush Attempts"},
        {"id": "team_rush_yds", "label": "Rushing Yards"},
        {"id": "team_rush_td", "label": "Rushing TDs"},
    ]},
    {"label": "Defense", "stats": [
        {"id": "def_yds_allowed", "label": "Total Yards Allowed"},
        {"id": "team_pass_yds_allowed", "label": "Passing Yards Allowed"},
        {"id": "team_rush_yds_allowed", "label": "Rushing Yards Allowed"},
        {"id": "team_sacks", "label": "Sacks"},
        {"id": "team_int_def", "label": "Interceptions"},
        {"id": "team_fumble_recoveries", "label": "Fumble Recoveries"},
        {"id": "def_turnovers_forced", "label": "Turnovers Forced"},
    ]},
    {"label": "Special Teams", "stats": [
        {"id": "team_fg_pct", "label": "FG %"},
        {"id": "team_punt_net_avg", "label": "Net Punt Average"},
    ]},
]
TEAM_DEFAULT_COLUMNS = ["team_name", "conference", "division", "wins", "losses", "win_pct"]
TEAM_STAT_LABELS = {s["id"]: s["label"] for cat in TEAM_STAT_CATEGORIES for s in cat["stats"]}
TEAM_PRESETS: dict[str, list[str]] = {
    "default": TEAM_DEFAULT_COLUMNS,
    "record": ["team_name", "wins", "losses", "win_pct", "points_for", "points_against", "point_diff", "power_rating"],
    "offense": ["team_name", "wins", "losses", "points_for", "off_yds", "team_pass_yds", "team_rush_yds"],
    "defense": ["team_name", "wins", "losses", "points_against", "def_yds_allowed", "team_sacks", "def_turnovers_forced"],
    "special-teams": ["team_name", "team_fg_pct", "team_punt_net_avg"],
    "all": list(TEAM_STAT_LABELS),
}

STATS_PERCENT_COLUMNS = {"pass_cmp_pct", "catch_pct", "win_pct", "fg_pct", "xp_pct", "team_fg_pct"}
CONFERENCES = ["AFC", "NFC"]
DIVISIONS = ["East", "North", "South", "West"]


def _stats_page_aggregates(season) -> tuple[list[dict], list[dict]]:
    """Builds the real per-player and per-team rows the Stats page's
    Player/Team tabs display. Reuses the same aggregate_season_stats /
    aggregate_season_defensive_stats helpers the old fixed leaderboards
    and awards.py already share (no reimplemented stat math), plus one
    extra pass over the season's played games for two things those
    helpers don't track: per-player games-played (a player counts as
    having played a game if they were credited with any offensive or
    defensive stat in it) and per-team offense/defense totals (summed
    from the same box_score.py/defensive_box_score.py lines, with
    "yards allowed" read off the OPPONENT's offensive box for that
    game). Identity fields (position/jersey/age/years pro) are joined
    in from the live Player rows by (team_abbr, full_name) -- the same
    lookup key app.main._player_link_or_name already uses -- and left
    as "-"/None if no live match exists (shouldn't happen for a
    currently-simulated season, but a real name/team mismatch should
    show as unknown, not fabricate a player)."""
    passing, rushing, receiving = aggregate_season_stats(season)
    defense = aggregate_season_defensive_stats(season)

    games_played: dict[tuple[str, str], int] = defaultdict(int)
    team_off: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    team_def: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    # M13: Kicking/Punting season totals -- box_score.py's KickingLine/
    # PuntingLine (real, per-game, built by M2) were never rolled up into
    # a season aggregate anywhere before this. Kept local to this
    # function (not a new season_stats.py aggregator) since nothing else
    # -- awards.py included -- needs a Kicking/Punting season view yet.
    kicking: dict[tuple[str, str], dict] = {}
    punting: dict[tuple[str, str], dict] = {}
    team_st: dict[str, dict] = defaultdict(lambda: {"fg_made": 0, "fg_att": 0, "punts": 0, "punt_net_yds": 0})

    for week in season.schedule:
        for g in week:
            if g.result is None:
                continue
            boxes = {abbr: build_box_score(g.result.plays, abbr) for abbr in (g.home_abbr, g.away_abbr)}
            def_boxes = {abbr: build_defensive_box_score(g.result.plays, abbr) for abbr in (g.home_abbr, g.away_abbr)}

            for abbr in (g.home_abbr, g.away_abbr):
                for k in boxes[abbr].kicking:
                    row = kicking.setdefault((abbr, k.name), {
                        "fg_made": 0, "fg_att": 0, "xp_made": 0, "xp_att": 0,
                        "fg_lt30": [0, 0], "fg_30_39": [0, 0], "fg_40_49": [0, 0], "fg_50_plus": [0, 0],
                    })
                    row["fg_made"] += k.fg_made
                    row["fg_att"] += k.fg_attempted
                    row["xp_made"] += k.xp_made
                    row["xp_att"] += k.xp_attempted
                    for bucket, bucket_key in (("<30", "fg_lt30"), ("30-39", "fg_30_39"), ("40-49", "fg_40_49"), ("50+", "fg_50_plus")):
                        made, att = k.fg_by_bucket[bucket]
                        row[bucket_key][0] += made
                        row[bucket_key][1] += att
                    team_st[abbr]["fg_made"] += k.fg_made
                    team_st[abbr]["fg_att"] += k.fg_attempted
                for pu in boxes[abbr].punting:
                    row = punting.setdefault((abbr, pu.name), {"punts": 0, "net_yards": 0, "inside_20": 0})
                    row["punts"] += pu.punts
                    row["net_yards"] += pu.net_yards
                    row["inside_20"] += pu.inside_20
                    team_st[abbr]["punts"] += pu.punts
                    team_st[abbr]["punt_net_yds"] += pu.net_yards
                box = boxes[abbr]
                participants = {p.name for p in box.passing} | {r.name for r in box.rushing} | {rc.name for rc in box.receiving} | {d.name for d in def_boxes[abbr]}
                for name in participants:
                    games_played[(abbr, name)] += 1

                off = team_off[abbr]
                for p in box.passing:
                    off["pass_att"] += p.attempts
                    off["pass_cmp"] += p.completions
                    off["pass_yds"] += p.yards
                    off["pass_td"] += p.touchdowns
                    off["pass_int"] += p.interceptions
                for r in box.rushing:
                    off["rush_att"] += r.carries
                    off["rush_yds"] += r.yards
                    off["rush_td"] += r.touchdowns

                d = team_def[abbr]
                for dl in def_boxes[abbr]:
                    d["sacks"] += dl.sacks
                    d["int"] += dl.interceptions
                    d["fumble_rec"] += dl.fumble_recoveries

            home_pass_yds = sum(p.yards for p in boxes[g.home_abbr].passing)
            home_rush_yds = sum(r.yards for r in boxes[g.home_abbr].rushing)
            away_pass_yds = sum(p.yards for p in boxes[g.away_abbr].passing)
            away_rush_yds = sum(r.yards for r in boxes[g.away_abbr].rushing)
            team_def[g.home_abbr]["pass_yds_allowed"] += away_pass_yds
            team_def[g.home_abbr]["rush_yds_allowed"] += away_rush_yds
            team_def[g.away_abbr]["pass_yds_allowed"] += home_pass_yds
            team_def[g.away_abbr]["rush_yds_allowed"] += home_rush_yds

    with get_session() as s:
        live_players = list(s.exec(select(Player)))
    player_by_key = {(p.team_abbr, p.full_name): p for p in live_players if p.team_abbr}

    all_keys = set(passing) | set(rushing) | set(receiving) | set(defense) | set(kicking) | set(punting)
    player_rows = []
    for abbr, name in all_keys:
        p = player_by_key.get((abbr, name))
        pas = passing.get((abbr, name))
        rus = rushing.get((abbr, name))
        rec = receiving.get((abbr, name))
        dfn = defense.get((abbr, name))
        kck = kicking.get((abbr, name))
        pnt = punting.get((abbr, name))
        player_rows.append({
            "player_name": name,
            "player_pos": p.position.value if p else "-",
            "player_team": abbr,
            "player_num": p.jersey_number if p else None,
            "player_age": p.age if p else None,
            "player_exp": p.years_pro if p else None,
            "games_played": games_played.get((abbr, name), 0),
            "pass_att": pas.attempts if pas else 0,
            "pass_cmp": pas.completions if pas else 0,
            "pass_yds": pas.yards if pas else 0,
            "pass_td": pas.touchdowns if pas else 0,
            "pass_int": pas.interceptions if pas else 0,
            "pass_cmp_pct": round(pas.completions / pas.attempts * 100, 1) if pas and pas.attempts else None,
            "pass_yds_per_att": round(pas.yards / pas.attempts, 1) if pas and pas.attempts else None,
            "sacks_taken": pas.sacks_taken if pas else 0,
            "qb_rating": _passer_rating(pas.attempts, pas.completions, pas.yards, pas.touchdowns, pas.interceptions) if pas else None,
            "rush_att": rus.carries if rus else 0,
            "rush_yds": rus.yards if rus else 0,
            "rush_td": rus.touchdowns if rus else 0,
            "yds_per_rush": round(rus.yards / rus.carries, 1) if rus and rus.carries else None,
            "fumbles_lost": rus.fumbles_lost if rus else 0,
            "targets": rec.targets if rec else 0,
            "receptions": rec.receptions if rec else 0,
            "rec_yds": rec.yards if rec else 0,
            "rec_td": rec.touchdowns if rec else 0,
            "catch_pct": round(rec.receptions / rec.targets * 100, 1) if rec and rec.targets else None,
            "solo_tackles": dfn.solo_tackles if dfn else 0,
            "tackles_for_loss": dfn.tackles_for_loss if dfn else 0,
            "sacks": dfn.sacks if dfn else 0,
            "def_int": dfn.interceptions if dfn else 0,
            "passes_defended": dfn.passes_defended if dfn else 0,
            "forced_fumbles": dfn.forced_fumbles if dfn else 0,
            "fumble_recoveries": dfn.fumble_recoveries if dfn else 0,
            "defensive_tds": dfn.defensive_touchdowns if dfn else 0,
            "fg_att": kck["fg_att"] if kck else 0,
            "fg_made": kck["fg_made"] if kck else 0,
            "fg_pct": round(kck["fg_made"] / kck["fg_att"] * 100, 1) if kck and kck["fg_att"] else None,
            "fg_lt30": f"{kck['fg_lt30'][0]}/{kck['fg_lt30'][1]}" if kck else "-",
            "fg_30_39": f"{kck['fg_30_39'][0]}/{kck['fg_30_39'][1]}" if kck else "-",
            "fg_40_49": f"{kck['fg_40_49'][0]}/{kck['fg_40_49'][1]}" if kck else "-",
            "fg_50_plus": f"{kck['fg_50_plus'][0]}/{kck['fg_50_plus'][1]}" if kck else "-",
            "xp_att": kck["xp_att"] if kck else 0,
            "xp_made": kck["xp_made"] if kck else 0,
            "xp_pct": round(kck["xp_made"] / kck["xp_att"] * 100, 1) if kck and kck["xp_att"] else None,
            "punts": pnt["punts"] if pnt else 0,
            "punt_net_yds": pnt["net_yards"] if pnt else 0,
            "punt_net_avg": round(pnt["net_yards"] / pnt["punts"], 1) if pnt and pnt["punts"] else None,
            "punts_inside_20": pnt["inside_20"] if pnt else 0,
        })

    team_rows = []
    for t in TEAMS:
        rec = season.records[t.abbr]
        off = team_off.get(t.abbr, {})
        d = team_def.get(t.abbr, {})
        team_rows.append({
            "team_name": t.location,
            "team_abbr": t.abbr,
            "conference": t.conference,
            "division": t.division,
            "wins": rec.wins,
            "losses": rec.losses,
            "win_pct": round(rec.win_pct * 100, 1),
            "points_for": rec.points_for,
            "points_against": rec.points_against,
            "point_diff": rec.point_diff,
            "power_rating": round(rec.power_rating, 1),
            "off_plays": off.get("pass_att", 0) + off.get("rush_att", 0),
            "off_yds": off.get("pass_yds", 0) + off.get("rush_yds", 0),
            "team_pass_att": off.get("pass_att", 0),
            "team_pass_cmp": off.get("pass_cmp", 0),
            "team_pass_yds": off.get("pass_yds", 0),
            "team_pass_td": off.get("pass_td", 0),
            "team_pass_int": off.get("pass_int", 0),
            "team_rush_att": off.get("rush_att", 0),
            "team_rush_yds": off.get("rush_yds", 0),
            "team_rush_td": off.get("rush_td", 0),
            "def_yds_allowed": d.get("pass_yds_allowed", 0) + d.get("rush_yds_allowed", 0),
            "team_pass_yds_allowed": d.get("pass_yds_allowed", 0),
            "team_rush_yds_allowed": d.get("rush_yds_allowed", 0),
            "team_sacks": d.get("sacks", 0),
            "team_int_def": d.get("int", 0),
            "team_fumble_recoveries": d.get("fumble_rec", 0),
            "def_turnovers_forced": d.get("int", 0) + d.get("fumble_rec", 0),
            "team_fg_pct": round(team_st[t.abbr]["fg_made"] / team_st[t.abbr]["fg_att"] * 100, 1) if team_st[t.abbr]["fg_att"] else None,
            "team_punt_net_avg": round(team_st[t.abbr]["punt_net_yds"] / team_st[t.abbr]["punts"], 1) if team_st[t.abbr]["punts"] else None,
        })

    return player_rows, team_rows


def _passer_rating(att: int, cmp: int, yds: int, td: int, ints: int) -> float | None:
    """The real, standard NFL passer rating formula (not a fabricated or
    simplified stand-in) -- computed from stats this engine already
    tracks in full (att/cmp/yds/td/int), same as StatColumnChooser.tsx's
    `qb_rating` column."""
    if not att:
        return None
    a = max(0.0, min(2.375, ((cmp / att) - 0.3) * 5))
    b = max(0.0, min(2.375, ((yds / att) - 3) * 0.25))
    c = max(0.0, min(2.375, (td / att) * 20))
    d = max(0.0, min(2.375, 2.375 - (ints / att) * 25))
    return round((a + b + c + d) / 6 * 100, 1)


def _sort_stat_rows(rows: list[dict], key: str, direction: str) -> list[dict]:
    """Nulls always sort last, independent of direction -- matches the
    Figma source's own sort comparator (StatsPage.tsx's handleSort)."""
    have = [r for r in rows if r.get(key) is not None]
    missing = [r for r in rows if r.get(key) is None]
    have.sort(key=lambda r: r[key], reverse=(direction == "desc"))
    return have + missing


@app.get("/stats", response_class=HTMLResponse)
def stats_view(
    request: Request,
    tab: str = "player",
    sort: str | None = None,
    dir: str = "desc",
    team: str = "all",
    pos: str = "all",
    conference: str = "all",
    division: str = "all",
    q: str = "",
    cols: list[str] = Query(default=[]),
    preset: str | None = None,
):
    if tab not in ("player", "team", "coach"):
        tab = "player"

    season = season_state.get_season()
    games_played = sum(1 for week in season.schedule for g in week if g.result is not None)
    awards_race = awards.season_awards(season) if games_played else None

    ctx = {
        "season": season, "games_played": games_played, "awards_race": awards_race, "tab": tab,
        "teams": TEAMS, "positions": list(Position), "conferences": CONFERENCES, "divisions": DIVISIONS,
        "team_filter": team, "pos_filter": pos, "conference_filter": conference, "division_filter": division,
        "q": q, "sort": sort,
    }

    if games_played == 0 or tab == "coach":
        ctx["dir"] = dir if dir in ("asc", "desc") else "desc"
        return templates.TemplateResponse(request, "stats.html", ctx)

    player_rows, team_rows = _stats_page_aggregates(season)

    if tab == "player":
        categories, presets, default_cols, labels = PLAYER_STAT_CATEGORIES, PLAYER_PRESETS, PLAYER_DEFAULT_COLUMNS, PLAYER_STAT_LABELS
        rows = player_rows
        if team != "all":
            rows = [r for r in rows if r["player_team"] == team]
        if pos != "all":
            rows = [r for r in rows if r["player_pos"] == pos]
        if q:
            ql = q.lower()
            rows = [r for r in rows if ql in r["player_name"].lower() or ql in r["player_team"].lower()]
        default_sort, default_dir = "player_name", "asc"
    else:
        categories, presets, default_cols, labels = TEAM_STAT_CATEGORIES, TEAM_PRESETS, TEAM_DEFAULT_COLUMNS, TEAM_STAT_LABELS
        rows = team_rows
        if conference != "all":
            rows = [r for r in rows if r["conference"] == conference]
        if division != "all":
            rows = [r for r in rows if r["division"] == division]
        if q:
            ql = q.lower()
            rows = [r for r in rows if ql in r["team_name"].lower() or ql in r["team_abbr"].lower()]
        default_sort, default_dir = "wins", "desc"

    valid_ids = set(labels)
    if preset and preset in presets:
        columns = presets[preset]
    else:
        submitted = [c for c in cols if c in valid_ids]
        columns = submitted if submitted else default_cols

    # A raw `sort` param only ever arrives from a header-sort link, which
    # always sends `dir` alongside it -- so an explicit sort honors the
    # requested direction, while the very first (no `sort` yet) load uses
    # a sensible per-tab default (alphabetical for names, best-record-
    # first for team standings) rather than always defaulting to "desc",
    # which read as Z-to-A on an untouched Player tab.
    if sort in valid_ids:
        effective_sort = sort
        direction = dir if dir in ("asc", "desc") else "desc"
    else:
        effective_sort = default_sort
        direction = default_dir
    ctx["dir"] = direction
    rows = _sort_stat_rows(rows, effective_sort, direction)
    display_rows = []
    for r in rows:
        dr = dict(r)
        for pct_col in STATS_PERCENT_COLUMNS:
            if pct_col in dr and dr[pct_col] is not None:
                dr[pct_col] = f"{dr[pct_col]}%"
        display_rows.append(dr)

    def stats_query(overrides: dict) -> str:
        base: dict = {"tab": tab, "cols": columns}
        if tab == "player":
            base["team"], base["pos"] = team, pos
        else:
            base["conference"], base["division"] = conference, division
        if q:
            base["q"] = q
        base.update(overrides)
        params = []
        for key, val in base.items():
            if key == "cols":
                params.extend(("cols", c) for c in val)
            elif val not in (None, ""):
                params.append((key, val))
        return "/stats?" + urlencode(params)

    sort_links = {}
    for cid in columns:
        next_dir = "asc" if (sort == cid and direction == "desc") else "desc"
        sort_links[cid] = stats_query({"sort": cid, "dir": next_dir})

    preset_links = {pid: stats_query({"cols": plist, "sort": None, "dir": None}) for pid, plist in presets.items()}
    reset_link = stats_query({"cols": default_cols, "sort": None, "dir": None})

    ctx.update({
        "categories": categories,
        "labels": labels,
        "column_ids": columns,
        "columns": [{"id": cid, "label": labels[cid]} for cid in columns],
        "rows": display_rows,
        "sort_links": sort_links,
        "preset_links": preset_links,
        "reset_link": reset_link,
        "row_count": len(rows),
    })
    return templates.TemplateResponse(request, "stats.html", ctx)


@app.get("/season", response_class=HTMLResponse)
def season_view(request: Request):
    season = season_state.get_season()
    return templates.TemplateResponse(
        request,
        "season.html",
        {
            "season": season,
            "standings": season.standings(),
            "n_weeks": season_state.N_WEEKS,
            "target_ppg": score_fidelity.TARGET_PPG_PER_TEAM,
        },
    )


@app.get("/season/week/{week_num}/game/{home_abbr}/{away_abbr}", response_class=HTMLResponse)
def season_game_view(request: Request, week_num: int, home_abbr: str, away_abbr: str):
    """Reuses result.html (the single-game simulator's play-by-play +
    box score view) for an already-simulated season game -- season_state
    already retains each game's full GameResult (plays, per-team totals,
    see save_service.py's round-trip), it just had no route/link to view
    one. 404s on an unplayed or nonexistent week/matchup rather than
    rendering an empty page, since there's nothing to show yet."""
    season = season_state.get_season()
    if not (1 <= week_num <= season_state.N_WEEKS):
        raise HTTPException(404, "No such week")

    game = next(
        (g for g in season.schedule[week_num - 1] if g.home_abbr == home_abbr and g.away_abbr == away_abbr),
        None,
    )
    if game is None or game.result is None:
        raise HTTPException(404, "That game hasn't been played yet")

    home_info = TEAMS_BY_ABBR[home_abbr]
    away_info = TEAMS_BY_ABBR[away_abbr]
    home = TeamSim(name=home_info.location, abbr=home_info.abbr, ratings=None)
    away = TeamSim(name=away_info.location, abbr=away_info.abbr, ratings=None)

    result = game.result
    home_box = build_box_score(result.plays, home_info.abbr)
    away_box = build_box_score(result.plays, away_info.abbr)
    home_defense = build_defensive_box_score(result.plays, home_info.abbr)
    away_defense = build_defensive_box_score(result.plays, away_info.abbr)
    game_seed = stable_seed(season.league_seed, week_num, home_abbr, away_abbr)

    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "home": home,
            "away": away,
            "result": result,
            "league_seed": season.league_seed,
            "game_seed": game_seed,
            "home_box": home_box,
            "away_box": away_box,
            "home_defense": home_defense,
            "away_defense": away_defense,
            "back_url": "/season",
            "back_label": "Back to season",
        },
    )


def _ordinal(n: int) -> str:
    """1 -> '1st', 2 -> '2nd', 11 -> '11th', 22 -> '22nd', etc. -- the
    11-13 exception is why this can't be a simple `n % 10` lookup."""
    if 11 <= n % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _header_context() -> dict:
    """GDD Sec 10.3: a persistent header (team badge, name, record/
    division/power-rank, a Sim Week control) visible on EVERY screen,
    not just Dashboard -- registered as a Jinja2 global (see
    `templates.env.globals` below) and called directly from
    base.html, rather than threading the same few values through every
    single route's own context dict for data that's always the same
    shape. Returns user_team=None before a team's been chosen (team-
    select, or a route hit before any franchise setup) -- base.html
    falls back to the plain title in that case."""
    season = season_state.get_season()
    if season.user_team_abbr is None:
        return {"user_team": None}
    team = TEAMS_BY_ABBR[season.user_team_abbr]
    record = season.records[season.user_team_abbr]
    rank = next((i for i, r in enumerate(season.standings(), start=1) if r.abbr == team.abbr), None)
    return {
        "user_team": team,
        "user_record": record,
        "user_rank_ordinal": _ordinal(rank) if rank is not None else None,
    }


templates.env.globals["header_context"] = _header_context


# GDD Sec 10.3 / Sec 7.5: player names open a Player Card Modal, everywhere
# a player name appears (Roster, Dashboard leaders, Scouting, box scores,
# Playoffs, Stats leaderboards, ...). Confirmed against the real Figma
# component (PlayerDrawer.tsx) -- same dark-panel/gold-OVR-badge layout,
# same Overview/Ratings/Stats/Contract tab set. Implemented WITHOUT a
# server round-trip per click: the trigger element (see the player_link
# Jinja macro, app/templates/macros.html) carries this player's full data
# as one JSON blob in a data-card attribute, and a single shared <dialog>
# + a small vanilla-JS click handler in base.html reads it and renders
# the card client-side -- consistent with "no per-player pre-rendering,
# no framework, no extra network request" (base.html's own <dialog> is
# the ONE thing on the page, not one hidden card per player).
ATTRIBUTE_LABELS: dict[str, str] = {
    "speed": "Speed", "acceleration": "Acceleration", "strength": "Strength", "agility": "Agility",
    "jumping": "Jumping", "stamina": "Stamina", "toughness": "Toughness", "durability": "Durability (Injury)",
    "throw_power": "Throw Power", "throw_accuracy_short": "Throw Accuracy (Short)",
    "throw_accuracy_mid": "Throw Accuracy (Mid)", "throw_accuracy_deep": "Throw Accuracy (Deep)",
    "play_action": "Play Action", "throw_on_the_run": "Throw on the Run",
    "throw_under_pressure": "Throw Under Pressure", "break_sack": "Break Sack",
    "catching": "Catching", "spectacular_catch": "Spectacular Catch", "catch_in_traffic": "Catch in Traffic",
    "short_route_running": "Short Routes", "medium_route_running": "Medium Routes",
    "deep_route_running": "Deep Routes", "release": "Release",
    "carrying": "Ball Carrying", "trucking": "Trucking", "change_of_direction": "Change of Direction",
    "ball_carrier_vision": "Vision", "stiff_arm": "Stiff Arm", "spin_move": "Spin Move",
    "juke_move": "Juke Move", "break_tackle": "Break Tackle",
    "run_block": "Run Block", "pass_block": "Pass Block", "run_block_power": "Run Block Power",
    "run_block_finesse": "Run Block Finesse", "pass_block_power": "Pass Block Power",
    "pass_block_finesse": "Pass Block Finesse", "lead_block": "Lead Block", "impact_blocking": "Impact Blocking",
    "tackle": "Tackle", "hit_power": "Hit Power", "block_shedding": "Block Shedding",
    "pursuit": "Pursuit", "play_recognition": "Play Recognition", "man_coverage": "Man Coverage",
    "zone_coverage": "Zone Coverage", "press": "Press", "power_moves": "Power Moves", "finesse_moves": "Finesse Moves",
    "kick_power": "Kick Power", "kick_accuracy": "Kick Accuracy", "kick_return": "Kick Return",
    "awareness": "Awareness",
}


def _passing_row(label: str, completions: int, attempts: int, yards: int, touchdowns: int, interceptions: int, sacks_taken: int) -> dict:
    return {
        "season_label": label, "completions": completions, "attempts": attempts,
        "pct": round(completions / attempts * 100, 1) if attempts else None,
        "yards": yards, "ypa": round(yards / attempts, 1) if attempts else None,
        "touchdowns": touchdowns, "interceptions": interceptions, "sacks_taken": sacks_taken,
        "rating": _passer_rating(attempts, completions, yards, touchdowns, interceptions),
    }


def _rushing_row(label: str, carries: int, yards: int, touchdowns: int, fumbles_lost: int) -> dict:
    return {
        "season_label": label, "carries": carries, "yards": yards,
        "avg": round(yards / carries, 1) if carries else None,
        "touchdowns": touchdowns, "fumbles_lost": fumbles_lost,
    }


def _receiving_row(label: str, receptions: int, targets: int, yards: int, touchdowns: int) -> dict:
    return {
        "season_label": label, "receptions": receptions, "targets": targets, "yards": yards,
        "avg": round(yards / receptions, 1) if receptions else None, "touchdowns": touchdowns,
    }


def _defense_row(label: str, solo_tackles: int, tackles_for_loss: int, sacks: int, interceptions: int,
                  passes_defended: int, forced_fumbles: int, fumble_recoveries: int, defensive_touchdowns: int) -> dict:
    return {
        "season_label": label, "solo_tackles": solo_tackles, "tackles_for_loss": tackles_for_loss,
        "sacks": sacks, "interceptions": interceptions, "passes_defended": passes_defended,
        "forced_fumbles": forced_fumbles, "fumble_recoveries": fumble_recoveries,
        "defensive_touchdowns": defensive_touchdowns,
    }


def _season_by_season_stats_for(p: Player) -> dict | None:
    """Player Card Stats tab, redesigned per Brian's own request into a
    real Madden-style year-by-year table instead of one combined career
    total: one row per season (current in-progress season first, then
    every archived season most-recent-first, via
    history_store.season_by_season_stats()), with a Career summary row
    (history_store.career_stats(), unchanged, still real/cumulative)
    appended last. No Team column -- every row would show the same
    abbr today anyway, since no trade system exists yet (Player.team_abbr
    is stable for a player's whole tenure); add one if/when R4c (Trades)
    ever makes it a real per-season fact instead of a constant.
    Games Played/Started aren't included either -- SeasonRecord's
    archived leader lines don't carry that, only the CURRENT season's
    live aggregation does (see _stats_page_aggregates's own games_played
    dict), so it isn't available for past seasons without a real
    archival-schema change this chunk didn't scope."""
    if not p.team_abbr:
        return None

    season = season_state.get_season()
    cur_passing, cur_rushing, cur_receiving = aggregate_season_stats(season)
    cur_defense = aggregate_season_defensive_stats(season)
    key = (p.team_abbr, p.full_name)
    cur_label = f"Season {season.season_number + 1} (in progress)"

    archived = history_store.season_by_season_stats(p.team_abbr, p.full_name)
    passing_rows = [_passing_row(f"Season {r['season_number'] + 1}", r["completions"], r["attempts"], r["yards"], r["touchdowns"], r["interceptions"], r.get("sacks_taken", 0)) for r in archived["passing"]]
    rushing_rows = [_rushing_row(f"Season {r['season_number'] + 1}", r["carries"], r["yards"], r["touchdowns"], r.get("fumbles_lost", 0)) for r in archived["rushing"]]
    receiving_rows = [_receiving_row(f"Season {r['season_number'] + 1}", r["receptions"], r["targets"], r["yards"], r["touchdowns"]) for r in archived["receiving"]]
    defense_rows = [_defense_row(f"Season {r['season_number'] + 1}", r["solo_tackles"], r["tackles_for_loss"], r["sacks"], r["interceptions"], r["passes_defended"], r["forced_fumbles"], r["fumble_recoveries"], r["defensive_touchdowns"]) for r in archived["defense"]]

    if key in cur_passing:
        l = cur_passing[key]
        passing_rows.insert(0, _passing_row(cur_label, l.completions, l.attempts, l.yards, l.touchdowns, l.interceptions, l.sacks_taken))
    if key in cur_rushing:
        l = cur_rushing[key]
        rushing_rows.insert(0, _rushing_row(cur_label, l.carries, l.yards, l.touchdowns, l.fumbles_lost))
    if key in cur_receiving:
        l = cur_receiving[key]
        receiving_rows.insert(0, _receiving_row(cur_label, l.receptions, l.targets, l.yards, l.touchdowns))
    if key in cur_defense:
        l = cur_defense[key]
        defense_rows.insert(0, _defense_row(cur_label, l.solo_tackles, l.tackles_for_loss, l.sacks, l.interceptions, l.passes_defended, l.forced_fumbles, l.fumble_recoveries, l.defensive_touchdowns))

    career_passing, career_rushing, career_receiving, career_defense = history_store.career_stats()
    if key in career_passing:
        l = career_passing[key]
        passing_rows.append(_passing_row(f"Career ({l.seasons} seasons)", l.completions, l.attempts, l.yards, l.touchdowns, l.interceptions, l.sacks_taken))
    if key in career_rushing:
        l = career_rushing[key]
        rushing_rows.append(_rushing_row(f"Career ({l.seasons} seasons)", l.carries, l.yards, l.touchdowns, l.fumbles_lost))
    if key in career_receiving:
        l = career_receiving[key]
        receiving_rows.append(_receiving_row(f"Career ({l.seasons} seasons)", l.receptions, l.targets, l.yards, l.touchdowns))
    if key in career_defense:
        l = career_defense[key]
        defense_rows.append(_defense_row(f"Career ({l.seasons} seasons)", l.solo_tackles, l.tackles_for_loss, l.sacks, l.interceptions, l.passes_defended, l.forced_fumbles, l.fumble_recoveries, l.defensive_touchdowns))

    lines = {}
    if passing_rows:
        lines["passing"] = passing_rows
    if rushing_rows:
        lines["rushing"] = rushing_rows
    if receiving_rows:
        lines["receiving"] = receiving_rows
    if defense_rows:
        lines["defense"] = defense_rows
    return lines or None


def _player_card_json(p: Player) -> str:
    attrs = {ATTRIBUTE_LABELS.get(a, a): getattr(p, a) for a in PROGRESSED_ATTRIBUTES if a != "overall_rating"}
    return json.dumps({
        "name": p.full_name, "num": p.jersey_number, "pos": p.position.value,
        "age": p.age, "ovr": p.overall_rating, "pot": p.potential,
        "team": p.team_abbr or "FA", "morale": p.morale, "stamina": p.stamina,
        "attrs": attrs, "career": _season_by_season_stats_for(p),
        "salary": p.salary, "signing_bonus": p.signing_bonus,
    })


templates.env.filters["player_card_json"] = _player_card_json


# Stat-line dataclasses (PassingLine, SeasonDefensiveLine, HOFCandidate, ...)
# only ever carry a plain `name` string, not a real Player row -- some of
# them (real-NFL-seeded history, retired players) have NO live Player row
# to find at all. This looks one up by (name, team_abbr) and falls back to
# plain escaped text when there's no live match, rather than fabricating a
# card. Brian's own instruction was "every player name... (except maybe
# HOF)" -- HOF is skipped entirely (see hof.html) since its whole point is
# retired/historical players, most with no live row; this handles the
# other pages (dashboard/stats/history leaders, box scores) where the
# named player is usually still on a live roster but isn't guaranteed to be.
def _player_link_or_name(name: str, team_abbr: str | None) -> Markup:
    if team_abbr:
        with get_session() as s:
            candidates = list(s.exec(select(Player).where(Player.team_abbr == team_abbr)))
        for p in candidates:
            if p.full_name == name:
                card_json = escape(_player_card_json(p))
                return Markup(f"<button type=\"button\" class=\"player-link\" data-card='{card_json}'>{escape(name)}</button>")
    return escape(name)


templates.env.globals["player_link_or_name"] = _player_link_or_name


def _grouped_teams() -> dict[str, dict[str, list[TeamInfo]]]:
    grouped: dict[str, dict[str, list[TeamInfo]]] = {}
    for t in TEAMS:
        grouped.setdefault(t.conference, {}).setdefault(t.division, []).append(t)
    return grouped


ROUND_LABELS = {"WC": "Wild Card", "DIV": "Divisional", "CONF": "Conference Championship", "SB": "Super Bowl"}


@app.get("/history", response_class=HTMLResponse)
def history_view(request: Request):
    """League History: every season archived by season_state.start_new_season()
    right before it's replaced -- final standings/champion/awards/stat
    leaders, permanently. Most recent season first. Career-cumulative
    totals and Hall of Fame induction are built from this same archive
    -- see /hof and history_store.py's own docstring."""
    records = list(reversed(history_store.get_history()))
    return templates.TemplateResponse(request, "history.html", {"records": records})


def _hof_new_inductee_keys(full_history: list, full_inductee_keys: set[tuple[str, str]]) -> set[tuple[str, str]]:
    """Which of `full_inductee_keys` (the CURRENT Hall of Fame class,
    already computed by the caller) weren't there as of the PREVIOUS
    archived season -- i.e. genuinely inducted this cycle, matching GDD
    Sec 10.4.8's "Class of [current year] Inductees" highlight section.
    history_store.hall_of_fame() only ever answers "who qualifies right
    now" (it recomputes from career_stats() fresh every call, no stored
    induction-year field) -- so this re-runs it against history with
    the most recent season dropped, via a throwaway temp file (the only
    way to feed it a truncated history without changing its path-only
    signature, which a concurrent M6 session was actively editing for
    its own real reasons -- lru_cache-ing career_stats() -- while this
    chunk was built), and diffs the two candidate sets."""
    if len(full_history) < 2:
        return set()
    prior_dicts = [history_store._record_to_dict(r) for r in full_history[:-1]]
    with tempfile.TemporaryDirectory() as d:
        temp_path = Path(d) / "prior_history.json"
        history_store._save(prior_dicts, temp_path)
        prior_inductees = history_store.hall_of_fame(path=temp_path)
    prior_keys = {(c.team_abbr, c.name) for c in prior_inductees}
    return full_inductee_keys - prior_keys


def _hof_all_years_active(full_history: list) -> dict[str, str]:
    """(team_abbr|name) -> a human-facing "Season X" or "Season X-Y"
    span, derived from real per-season leader presence across the
    archive (passing/rushing/receiving/defensive_leaders already carry
    every credited player, not just top-N, since the top-15 cap was
    removed for career_stats()'s sake -- see history_store.py's own
    docstring). +1 everywhere to match history.html's own season-number-
    is-zero-indexed convention."""
    spans: dict[str, list[int]] = {}
    for rec in full_history:
        for pool in (rec.passing_leaders, rec.rushing_leaders, rec.receiving_leaders, rec.defensive_leaders):
            for l in pool:
                spans.setdefault(f"{l.team_abbr}|{l.name}", []).append(rec.season_number)
    return {
        k: (f"Season {min(v) + 1}" if min(v) == max(v) else f"Season {min(v) + 1}–{max(v) + 1}")
        for k, v in spans.items()
    }


def _hof_eligible_candidates(inductee_keys: set[tuple[str, str]], limit: int = 10, path: Path | None = None) -> list[dict]:
    """Real, not-yet-inducted players who've cleared history_store's own
    MIN_HOF_SEASONS bar -- GDD Sec 10.4.8's "Eligible Candidates" list
    (this engine has no voting system, so `progress_pct` stands in for
    the Figma source's voting percentage: each category's own primary
    counting stat as a percentage of that category's current pool
    leader -- a real, if simplified, "how close" proxy, not the exact
    private HOF composite score formula that lives inside
    history_store.hall_of_fame() -- disclosed in the template rather
    than duplicating that formula here). `path` mirrors career_stats()'s
    own optional-path signature (None = the real live history file) --
    lets tests pass a temp path directly instead of monkeypatching
    history_store.DEFAULT_PATH, which would collide with career_stats()'s
    own lru_cache (keyed on the path ARGUMENT, not on DEFAULT_PATH)."""
    passing, rushing, receiving, defense = history_store.career_stats(path)

    def _pool(pool: dict, position: str, stat_fmt, primary):
        eligible = [
            l for l in pool.values()
            if l.seasons >= history_store.MIN_HOF_SEASONS and (l.team_abbr, l.name) not in inductee_keys
        ]
        if not eligible:
            return []
        peak = max(primary(l) for l in eligible) or 1
        return [
            {
                "name": l.name, "team_abbr": l.team_abbr, "position": position, "seasons": l.seasons,
                "stat_line": stat_fmt(l), "progress_pct": round(100 * primary(l) / peak),
            }
            for l in eligible
        ]

    candidates = (
        _pool(passing, "QB", lambda l: f"{l.yards:,} career pass yds, {l.touchdowns} TD", lambda l: l.yards)
        + _pool(rushing, "RB", lambda l: f"{l.yards:,} career rush yds, {l.touchdowns} TD", lambda l: l.yards)
        + _pool(receiving, "WR/TE", lambda l: f"{l.yards:,} career rec yds, {l.touchdowns} TD", lambda l: l.yards)
        + _pool(defense, "DEF", lambda l: f"{l.solo_tackles} career tkl, {l.sacks} sacks, {l.interceptions} INT", lambda l: l.solo_tackles)
    )
    return sorted(candidates, key=lambda c: -c["progress_pct"])[:limit]


def _hof_record_book(path: Path | None = None) -> list[dict]:
    """GDD Sec 10.4.8's League Record Book: top-10 all-time leaders per
    major real category, from the same real career_stats() archive the
    Hall of Fame itself is built on -- one card per category, most-
    productive-first. Field goals are deliberately omitted: M2 built a
    real per-game Kicking box-score line, but nothing rolls it into a
    season or career total anywhere yet, so a Kicking category here
    would have to be fabricated rather than real -- disclosed in the
    template instead of guessed at. `path` mirrors career_stats()'s own
    optional-path signature -- see _hof_eligible_candidates()'s
    docstring for why (lets tests bypass career_stats()'s lru_cache)."""
    passing, rushing, receiving, defense = history_store.career_stats(path)

    def _top(pool: dict, key, limit=10):
        ranked = sorted((l for l in pool.values() if key(l) > 0), key=lambda l: -key(l))
        return [(l.name, l.team_abbr, key(l)) for l in ranked[:limit]]

    return [
        {"label": "Passing Yards", "leaders": _top(passing, lambda l: l.yards)},
        {"label": "Passing TDs", "leaders": _top(passing, lambda l: l.touchdowns)},
        {"label": "Rushing Yards", "leaders": _top(rushing, lambda l: l.yards)},
        {"label": "Rushing TDs", "leaders": _top(rushing, lambda l: l.touchdowns)},
        {"label": "Receiving Yards", "leaders": _top(receiving, lambda l: l.yards)},
        {"label": "Receiving TDs", "leaders": _top(receiving, lambda l: l.touchdowns)},
        {"label": "Sacks", "leaders": _top(defense, lambda l: l.sacks)},
        {"label": "Interceptions", "leaders": _top(defense, lambda l: l.interceptions)},
    ]


@app.get("/hof", response_class=HTMLResponse)
def hof_view(request: Request, pos: str = "all", q: str = ""):
    """Hall of Fame: real induction over the real career-cumulative
    archive (history_store.career_stats()/hall_of_fame()) -- see that
    module's docstring for the disclosed, GDD-underspecified induction
    formula. GDD Sec 10.4.8 redesign (ROADMAP.md M5): adds a real
    "Class of [Season N] Inductees" highlight, a real "Eligible
    Candidates" list, filterable/searchable Hall of Fame Members (GET-
    query-param + full-page-reload, same pattern /stats's M3 already
    established -- no htmx/framework here), a real League Record Book,
    and a real Super Bowl History table -- see each helper above for
    its own disclosed scope. Empty/near-empty until a league has played
    enough seasons for any career to clear the bar."""
    full_history = history_store.get_history()
    inductees = history_store.hall_of_fame()
    inductee_keys = {(c.team_abbr, c.name) for c in inductees}
    new_keys = _hof_new_inductee_keys(full_history, inductee_keys)
    new_inductees = [c for c in inductees if (c.team_abbr, c.name) in new_keys]

    positions = sorted({c.position for c in inductees})
    members = inductees
    if pos != "all":
        members = [c for c in members if c.position == pos]
    if q:
        ql = q.lower()
        members = [c for c in members if ql in c.name.lower() or ql in c.team_abbr.lower()]

    years_active = _hof_all_years_active(full_history)
    eligible = _hof_eligible_candidates(inductee_keys)
    record_book = _hof_record_book() if full_history else []
    sb_history = [rec for rec in reversed(full_history) if rec.champion_abbr]
    current_season_label = (full_history[-1].season_number + 1) if full_history else None

    return templates.TemplateResponse(request, "hof.html", {
        "new_inductees": new_inductees,
        "members": members,
        "total_members": len(inductees),
        "eligible": eligible,
        "record_book": record_book,
        "sb_history": sb_history,
        "years_active": years_active,
        "positions": positions,
        "pos_filter": pos,
        "q": q,
        "current_season_label": current_season_label,
    })


@app.get("/staff", response_class=HTMLResponse)
def staff_view(request: Request):
    """GDD Sec 10.4.3: Post-MVP. Nav item exists per Sec 10.3's stated
    MVP navigation behavior ("Staff, GM Desk, and Draft remain in the
    navigation bar but render a 'Coming Soon' message until Part 2
    ships") -- this route/page didn't exist at all before now."""
    return templates.TemplateResponse(request, "coming_soon.html", {
        "title": "Staff",
        "gdd_section": "GDD §10.4.3",
        "summary": "Your coaching staff (Head Coach, Offensive/Defensive Coordinators, Assistant Coaches) with "
                    "ratings, focus areas, and hire/fire/re-sign contract flows, plus a searchable Find Coaches "
                    "list of free agents and coaches on other teams. Needs the Coaching Staff system (Part 2) first.",
    })


@app.get("/gm-desk", response_class=HTMLResponse)
def gm_desk_view(request: Request):
    """GDD Sec 10.4.4: Post-MVP. Consolidates the old Free Agents and
    Trading Block screens into one hub."""
    return templates.TemplateResponse(request, "coming_soon.html", {
        "title": "GM Desk",
        "gdd_section": "GDD §10.4.4",
        "summary": "Salary cap summary, trade-block browsing and offers, your own expiring contracts, top "
                    "draft-eligible prospects, and league-wide player search. Needs Contracts/Cap and Trades "
                    "(both Part 2) first.",
    })


@app.get("/draft", response_class=HTMLResponse)
def draft_view(request: Request):
    """GDD Sec 10.4.5: Post-MVP."""
    return templates.TemplateResponse(request, "coming_soon.html", {
        "title": "Draft",
        "gdd_section": "GDD §10.4.5",
        "summary": "A draft-class scouting board (reusing the Roster table interface, with multi-select "
                    "prospect comparison), your draft picks by round, and position-quota filtering. Needs the "
                    "Draft system (Part 2) first.",
    })


PLAYOFF_VIEWS = ("full", "afc", "nfc", "superbowl")


def _rounds_by_conference(bracket, conference: str | None) -> dict[str, list]:
    """Bracket rounds filtered to one conference (WC/DIV/CONF matchups
    for "AFC"/"NFC", or the single Super Bowl matchup for `None`) --
    each round in `bracket.rounds` mixes both conferences' games
    together (and the WC/DIV/CONF rounds happen in the same round-list
    entry for whichever games are ready), so the Full/AFC/NFC/Super Bowl
    tab views (GDD Sec 10.4.6) all read from this rather than each
    re-filtering `bracket.rounds` in the template."""
    result: dict[str, list] = {}
    for round_ in bracket.rounds:
        name = round_[0].round_name
        result[name] = [m for m in round_ if m.conference == conference]
    return result


def _conference_hunt_and_standings(season, bracket) -> tuple[dict, dict]:
    """Real "In The Hunt" bubble teams and real division standings for
    the AFC/NFC Playoffs views (GDD Sec 10.4.6) -- both built from the
    same real tiebreak-chain functions the bracket seeding itself uses
    (`bubble_teams`/`final_division_standings` in playoffs.py), not a
    separate approximate ranking.

    M12 correction adds two real per-team fields HuntCard.tsx specifies
    (`seed_if_made`/`gb`), computed rather than fabricated:
    - `seed_if_made`: `8 + index` in `bubble_teams`' own real wildcard-
      tiebreak-chain order (the exact order between bubble teams is
      exact, from the real chain -- the "8" starting point is a stated,
      disclosed simplifying convention assuming all 7 real seeds already
      outrank every bubble team in that same chain, true for the
      overwhelming majority of real standings; not re-deriving a second,
      separate absolute-rank computation across all 16 conference teams
      just to cover the rare case a weak division winner doesn't).
    - `gb` ("games back"): the standard sports games-behind formula
      against the conference's actual 7-seed (the real cutoff line),
      using each team's real win/loss record -- not a modeled stat, just
      arithmetic on data already in `season.records`.
    """
    div_standings_raw = final_division_standings(season)
    hunt: dict[str, list[dict]] = {}
    standings: dict[str, dict[str, list[dict]]] = {}
    for conf, seeds in (("AFC", bracket.afc_seeds), ("NFC", bracket.nfc_seeds)):
        cutoff = season.records[seeds[6]]  # the real 7-seed -- the actual bubble line
        bubble = bubble_teams(season, conf, seeds)
        hunt[conf] = [
            {
                "abbr": abbr, "location": TEAMS_BY_ABBR[abbr].location, "record": season.records[abbr],
                "seed_if_made": 8 + i,
                "gb": round(((cutoff.wins - season.records[abbr].wins) + (season.records[abbr].losses - cutoff.losses)) / 2, 1),
            }
            for i, abbr in enumerate(bubble)
        ]
        standings[conf] = {
            div: [
                {"abbr": abbr, "location": TEAMS_BY_ABBR[abbr].location, "record": season.records[abbr]}
                for abbr in abbrs
            ]
            for (c, div), abbrs in div_standings_raw.items() if c == conf
        }
    return hunt, standings


def _conference_champion(bracket, conference: str) -> dict | None:
    """The real conference champion once that conference's CONF round is
    complete, for the Full Bracket/Conference Bracket Champion columns
    (FullPlayoffTree.tsx/ConferenceBracket.tsx) -- None (renders as TBD)
    until then."""
    conf_matchup = next((m for round_ in bracket.rounds for m in round_ if m.conference == conference and m.round_name == "CONF"), None)
    if conf_matchup is None or not conf_matchup.is_complete:
        return None
    return {"abbr": conf_matchup.winner_abbr, "seed": conf_matchup.winner_seed, "location": TEAMS_BY_ABBR[conf_matchup.winner_abbr].location}


@app.get("/playoffs", response_class=HTMLResponse)
def playoffs_view(request: Request, view: str = "full"):
    """GDD Sec 10.4.6: Full Bracket / AFC / NFC / Super Bowl tab views,
    matching the Figma-derived layout -- AFC/NFC views also show real
    "In The Hunt" bubble teams and real division standings."""
    if view not in PLAYOFF_VIEWS:
        view = "full"
    season = season_state.get_season()
    if not season.is_complete:
        return templates.TemplateResponse(request, "playoffs.html", {
            "season": season, "bracket": None, "round_labels": ROUND_LABELS, "view": view,
        })
    if season.playoffs is None:
        season_state.simulate_playoff_round()  # builds the Wild Card round on first visit
        season = season_state.get_season()
    bracket = season.playoffs
    in_the_hunt, division_standings = _conference_hunt_and_standings(season, bracket)
    afc_rounds = _rounds_by_conference(bracket, "AFC")
    nfc_rounds = _rounds_by_conference(bracket, "NFC")
    sb_matchups = _rounds_by_conference(bracket, None).get("SB", [])
    sb_matchup = sb_matchups[0] if sb_matchups else None

    ctx = {
        "season": season, "bracket": bracket, "round_labels": ROUND_LABELS,
        "view": view, "in_the_hunt": in_the_hunt, "division_standings": division_standings,
        "afc_rounds": afc_rounds, "nfc_rounds": nfc_rounds, "sb_matchup": sb_matchup,
        "teams_by_abbr": TEAMS_BY_ABBR,
    }

    if view == "full":
        # M12 correction (real source: FullPlayoffTree.tsx): the Champion
        # columns flanking the Super Bowl card.
        ctx["afc_champion"] = _conference_champion(bracket, "AFC")
        ctx["nfc_champion"] = _conference_champion(bracket, "NFC")

    if view in ("afc", "nfc"):
        # M12 correction (real source: ConferenceBracket.tsx): the 4th
        # "Champion" column this view never had.
        ctx["conf_champion"] = _conference_champion(bracket, "AFC" if view == "afc" else "NFC")

    if view == "superbowl":
        # M12 correction (real source: SuperBowlView.tsx): compact side
        # Wild Card previews (real, just the first 2 of each conference's
        # 3 WC games), a real Scouting Panel per SB team (reusing
        # build_scouting_report() and the Dashboard's own .dash-tab
        # widget, not a second implementation), and -- once the game is
        # actually simulated -- a real final-score summary linking to the
        # full box score/play-by-play (playoffs_game_view below) rather
        # than a second, duplicate inline copy of that same page. MVP is
        # deliberately NOT included: no per-game "player of the game"
        # stat exists anywhere in this engine (awards.py's MVP is a real,
        # but SEASON-long, computation), and Figma's own MVP block is
        # itself hardcoded demo data ("Tom Brady... Kansas City Chiefs"),
        # not something a real API would ever return either -- faking a
        # number here would be strictly worse than the source.
        ctx["afc_wc_preview"] = afc_rounds.get("WC", [])[:2]
        ctx["nfc_wc_preview"] = nfc_rounds.get("WC", [])[:2]
        if sb_matchup is not None:
            ctx["sb_scouting"] = {
                sb_matchup.home_abbr: build_scouting_report(season, sb_matchup.home_abbr),
                sb_matchup.away_abbr: build_scouting_report(season, sb_matchup.away_abbr),
            }

    return templates.TemplateResponse(request, "playoffs.html", ctx)


@app.get("/playoffs/game/{round_name}/{home_abbr}/{away_abbr}", response_class=HTMLResponse)
def playoffs_game_view(request: Request, round_name: str, home_abbr: str, away_abbr: str):
    """Same result.html play-by-play + box score view as a regular-season
    game (app/main.py's season_game_view) -- playoff games are simulated
    with the same engine and retain the same full GameResult."""
    season = season_state.get_season()
    if season.playoffs is None:
        raise HTTPException(404, "No playoff bracket yet")

    matchup = next(
        (m for round_ in season.playoffs.rounds for m in round_
         if m.round_name == round_name and m.home_abbr == home_abbr and m.away_abbr == away_abbr),
        None,
    )
    if matchup is None or matchup.result is None:
        raise HTTPException(404, "That playoff game hasn't been played yet")

    home_info = TEAMS_BY_ABBR[home_abbr]
    away_info = TEAMS_BY_ABBR[away_abbr]
    home = TeamSim(name=home_info.location, abbr=home_info.abbr, ratings=None)
    away = TeamSim(name=away_info.location, abbr=away_info.abbr, ratings=None)

    result = matchup.result
    home_box = build_box_score(result.plays, home_info.abbr)
    away_box = build_box_score(result.plays, away_info.abbr)
    home_defense = build_defensive_box_score(result.plays, home_info.abbr)
    away_defense = build_defensive_box_score(result.plays, away_info.abbr)
    game_seed = stable_seed(season.league_seed, "playoffs", round_name, home_abbr, away_abbr)

    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "home": home,
            "away": away,
            "result": result,
            "league_seed": season.league_seed,
            "game_seed": game_seed,
            "home_box": home_box,
            "away_box": away_box,
            "home_defense": home_defense,
            "away_defense": away_defense,
            "back_url": "/playoffs",
            "back_label": "Back to playoffs",
        },
    )


@app.get("/team-select", response_class=HTMLResponse)
def team_select_view(request: Request):
    """GDD Sec 10.1: the one-time, conference/division-grouped team grid
    shown at franchise creation. No records or power rankings shown --
    a brand-new league has no history yet (see Sec 10.1's note that this
    step deliberately does exactly one job)."""
    season = season_state.get_season()
    return templates.TemplateResponse(
        request,
        "team_select.html",
        {"grouped": _grouped_teams(), "current": season.user_team_abbr},
    )


@app.post("/team-select")
def team_select_submit(team_abbr: str = Form(...)):
    if team_abbr not in TEAMS_BY_ABBR:
        raise HTTPException(404, "No such team")
    season_state.set_user_team(team_abbr)
    return RedirectResponse(url="/dashboard", status_code=303)


def _safe_internal_redirect(path: str | None, default: str) -> str:
    """Only ever redirects back to a path on THIS app -- rejects
    anything that could be an open redirect (an absolute URL, or a
    protocol-relative "//host/..." path browsers still treat as
    absolute) rather than trusting the submitted value outright."""
    if not path or not path.startswith("/") or path.startswith("//"):
        return default
    return path


@app.post("/season/simulate-week")
def season_simulate_week(redirect_to: str | None = Form(None)):
    """GDD Sec 4's game loop (Regular Season -> Playoffs -> Championship)
    is one continuous cycle from the player's perspective -- a single
    "Sim Week" control, matching the Figma header's one sim button
    (Sec 10.3), now persistent across every page (base.html's header,
    via _header_context()) rather than living only on /season. Once the
    regular season is done, the same button just starts simulating
    playoff rounds instead. `redirect_to` (the page the button was
    clicked from, a hidden field in the header's own form) sends the
    player back to where they were rather than always yanking them to
    /season/-/playoffs -- the whole point of a persistent control is
    that using it doesn't lose your place."""
    season = season_state.get_season()
    if season.is_complete:
        season_state.simulate_playoff_round()
        return RedirectResponse(url=_safe_internal_redirect(redirect_to, "/playoffs"), status_code=303)
    season_state.simulate_current_week()
    return RedirectResponse(url=_safe_internal_redirect(redirect_to, "/season"), status_code=303)


@app.post("/season/reset")
def season_reset():
    season_state.reset_season()
    return RedirectResponse(url="/season", status_code=303)


@app.post("/season/new-season")
def season_new_season():
    """GDD Sec 4's Offseason step + Sec 7.6 (Player Progression &
    Regression): moves the franchise into its next season once the
    playoffs are fully decided. 404s rather than silently no-op'ing if
    called too early."""
    try:
        season_state.start_new_season()
    except ValueError as e:
        raise HTTPException(404, str(e))
    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/simulate", response_class=HTMLResponse)
def simulate(request: Request, home_abbr: str = Form(...), away_abbr: str = Form(...)):
    league_seed = get_league_seed()

    home_info = TEAMS_BY_ABBR[home_abbr]
    away_info = TEAMS_BY_ABBR[away_abbr]

    home = TeamSim(name=home_info.location, abbr=home_info.abbr, ratings=ratings_for(home_info, league_seed))
    away = TeamSim(name=away_info.location, abbr=away_info.abbr, ratings=ratings_for(away_info, league_seed))

    # Derived per-game RNG, distinct from the placeholder-rating RNG above,
    # matching the "derived, not global" spirit of GDD Part 1 Sec 1.3.
    game_seed = stable_seed(league_seed, home_abbr, away_abbr, "demo_game")
    rng = RNG.with_seed(game_seed)

    result = simulate_game(rng, home, away)
    home_box = build_box_score(result.plays, home_info.abbr)
    away_box = build_box_score(result.plays, away_info.abbr)
    home_defense = build_defensive_box_score(result.plays, home_info.abbr)
    away_defense = build_defensive_box_score(result.plays, away_info.abbr)

    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "home": home,
            "away": away,
            "result": result,
            "league_seed": league_seed,
            "game_seed": game_seed,
            "home_box": home_box,
            "away_box": away_box,
            "home_defense": home_defense,
            "away_defense": away_defense,
        },
    )

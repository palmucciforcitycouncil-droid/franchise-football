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


@app.get("/roster", response_class=HTMLResponse)
def roster_view(request: Request, team_abbr: str | None = None, view: str = "attributes"):
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
    players with no team. M4 adds: Attributes/Stats view toggle,
    Team Quota badges (position buttons), Filter/Export controls (stubs),
    and embedded depth-chart widget (below main table)."""
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

    # Position quotas for Team Quota badges (per GDD §10.4.2 Figma source)
    position_quotas = {pos.value: {"current": sum(1 for p in players if p.position == pos), "min": _ROSTER_POSITION_MINIMUMS.get(pos.value, 1)} for pos in Position}

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

    # Compute stats data if needed
    stats_data = None
    if view == "stats":
        season = season_state.get_season()
        player_rows, _ = _stats_page_aggregates(season)
        # Filter to this team only
        stats_data = {(r["player_name"], r["player_pos"]): r for r in player_rows if r["player_team"] == team_abbr}

    team = FREE_AGENTS_TEAM if team_abbr == "FA" else TEAMS_BY_ABBR[team_abbr]
    return templates.TemplateResponse(
        request,
        "roster.html",
        {
            "teams": TEAMS, "team": team, "players": players, "starters": starters,
            "view": view, "position_quotas": position_quotas, "depth_chart_groups": depth_chart_groups,
            "stats_data": stats_data,
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


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_view(request: Request):
    """League-at-a-glance landing page, pulling from pieces that already
    exist rather than introducing new state: season.standings() (top 10
    by record), the most recently completed week's scores, and the top
    5 stat leaders per category (_season_stat_leaders). Doesn't replace
    `/`, which stays the single-game simulator -- the GDD lists Dashboard
    and "Simulate a Game" as distinct screens.

    GDD Sec 10.1: Dashboard is the default landing page and always
    resolves to the user's team -- if no team has been chosen yet for
    this franchise, redirect to the one-time team-selection screen
    rather than rendering a teamless dashboard."""
    season = season_state.get_season()
    if season.user_team_abbr is None:
        return RedirectResponse(url="/team-select", status_code=303)

    gameplan = gameplan_store.get_gameplan(season.user_team_abbr)

    next_opponent = find_next_opponent(season, season.user_team_abbr)
    scouting = None
    if next_opponent is not None:
        opponent_abbr, team_is_home = next_opponent
        scouting = build_scouting_report(season, opponent_abbr)
        scouting["opponent_team"] = TEAMS_BY_ABBR[opponent_abbr]
        scouting["is_home_game"] = team_is_home

    standings = season.standings()[:10]

    last_played_week = None
    last_week_games = []
    for week_num in range(season.current_week - 1, 0, -1):
        games = [g for g in season.schedule[week_num - 1] if g.result is not None]
        if games:
            last_played_week = week_num
            last_week_games = games
            break

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
            "standings": standings,
            "last_played_week": last_played_week,
            "last_week_games": last_week_games,
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
# Stats/Contract tab stubs.
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
        {"id": "pass_td", "label": "Passing TDs"},
        {"id": "pass_int", "label": "Interceptions Thrown"},
    ]},
    {"label": "Rushing", "stats": [
        {"id": "rush_att", "label": "Rush Attempts"},
        {"id": "rush_yds", "label": "Rushing Yards"},
        {"id": "yds_per_rush", "label": "Yards per Rush"},
        {"id": "rush_td", "label": "Rushing TDs"},
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
]
PLAYER_DEFAULT_COLUMNS = ["player_name", "player_pos", "player_team", "player_age", "games_played"]
PLAYER_STAT_LABELS = {s["id"]: s["label"] for cat in PLAYER_STAT_CATEGORIES for s in cat["stats"]}
PLAYER_PRESETS: dict[str, list[str]] = {
    "default": PLAYER_DEFAULT_COLUMNS,
    "qb": ["player_name", "player_pos", "player_team", "games_played", "pass_att", "pass_cmp", "pass_cmp_pct", "pass_yds", "pass_td", "pass_int"],
    "rushing": ["player_name", "player_pos", "player_team", "games_played", "rush_att", "rush_yds", "yds_per_rush", "rush_td"],
    "receiving": ["player_name", "player_pos", "player_team", "games_played", "targets", "receptions", "catch_pct", "rec_yds", "rec_td"],
    "defense": ["player_name", "player_pos", "player_team", "games_played", "solo_tackles", "tackles_for_loss", "sacks", "def_int", "passes_defended", "forced_fumbles", "fumble_recoveries", "defensive_tds"],
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
]
TEAM_DEFAULT_COLUMNS = ["team_name", "conference", "division", "wins", "losses", "win_pct"]
TEAM_STAT_LABELS = {s["id"]: s["label"] for cat in TEAM_STAT_CATEGORIES for s in cat["stats"]}
TEAM_PRESETS: dict[str, list[str]] = {
    "default": TEAM_DEFAULT_COLUMNS,
    "record": ["team_name", "wins", "losses", "win_pct", "points_for", "points_against", "point_diff", "power_rating"],
    "offense": ["team_name", "wins", "losses", "points_for", "off_yds", "team_pass_yds", "team_rush_yds"],
    "defense": ["team_name", "wins", "losses", "points_against", "def_yds_allowed", "team_sacks", "def_turnovers_forced"],
    "all": list(TEAM_STAT_LABELS),
}

STATS_PERCENT_COLUMNS = {"pass_cmp_pct", "catch_pct", "win_pct"}
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

    for week in season.schedule:
        for g in week:
            if g.result is None:
                continue
            boxes = {abbr: build_box_score(g.result.plays, abbr) for abbr in (g.home_abbr, g.away_abbr)}
            def_boxes = {abbr: build_defensive_box_score(g.result.plays, abbr) for abbr in (g.home_abbr, g.away_abbr)}

            for abbr in (g.home_abbr, g.away_abbr):
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

    all_keys = set(passing) | set(rushing) | set(receiving) | set(defense)
    player_rows = []
    for abbr, name in all_keys:
        p = player_by_key.get((abbr, name))
        pas = passing.get((abbr, name))
        rus = rushing.get((abbr, name))
        rec = receiving.get((abbr, name))
        dfn = defense.get((abbr, name))
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
            "rush_att": rus.carries if rus else 0,
            "rush_yds": rus.yards if rus else 0,
            "rush_td": rus.touchdowns if rus else 0,
            "yds_per_rush": round(rus.yards / rus.carries, 1) if rus and rus.carries else None,
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
        })

    return player_rows, team_rows


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


def _career_stats_for(p: Player) -> dict | None:
    """M6: real archived-season totals (history_store.career_stats(),
    already real/tested, previously had no UI consumer) for the Player
    Card's Stats tab. Keyed by (team_abbr, name), the same identity
    career_stats() itself uses -- see history_store.py's docstring for
    why that's safe here (no trade system yet). A player only shows up
    here once at least one full season has been archived (start_new_season()
    has run at least once); brand-new/current-season production isn't
    included, since career_stats() only ever sums ARCHIVED seasons --
    that's genuinely a different, not-yet-final number, not this tab's job."""
    if not p.team_abbr:
        return None
    passing, rushing, receiving, defense = history_store.career_stats()
    key = (p.team_abbr, p.full_name)
    lines: dict[str, dict] = {}
    if key in passing:
        lines["passing"] = asdict(passing[key])
    if key in rushing:
        lines["rushing"] = asdict(rushing[key])
    if key in receiving:
        lines["receiving"] = asdict(receiving[key])
    if key in defense:
        lines["defense"] = asdict(defense[key])
    return lines or None


def _player_card_json(p: Player) -> str:
    attrs = {ATTRIBUTE_LABELS.get(a, a): getattr(p, a) for a in PROGRESSED_ATTRIBUTES if a != "overall_rating"}
    return json.dumps({
        "name": p.full_name, "num": p.jersey_number, "pos": p.position.value,
        "age": p.age, "ovr": p.overall_rating, "pot": p.potential,
        "team": p.team_abbr or "FA", "morale": p.morale, "stamina": p.stamina,
        "attrs": attrs, "career": _career_stats_for(p),
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


def _hof_new_inductee_keys(full_history: list) -> set[tuple[str, str]]:
    """Which (team_abbr, name) keys in the current Hall of Fame class
    weren't there as of the PREVIOUS archived season -- i.e. genuinely
    inducted this cycle, matching GDD Sec 10.4.8's "Class of [current
    year] Inductees" highlight section. history_store.hall_of_fame()
    only ever answers "who qualifies right now" (it recomputes from
    career_stats() fresh every call, no stored induction-year field) --
    so this re-runs it against history with the most recent season
    dropped, via a throwaway temp file (the only way to feed it a
    truncated history without changing its path-only signature, which
    a concurrent M6 session was actively editing for its own real
    reasons -- lru_cache-ing career_stats() -- while this chunk was
    built), and diffs the two candidate sets."""
    if len(full_history) < 2:
        return set()
    prior_dicts = [history_store._record_to_dict(r) for r in full_history[:-1]]
    with tempfile.TemporaryDirectory() as d:
        temp_path = Path(d) / "prior_history.json"
        history_store._save(prior_dicts, temp_path)
        prior_inductees = history_store.hall_of_fame(path=temp_path)
    return {(c.team_abbr, c.name) for c in prior_inductees}


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


def _hof_eligible_candidates(inductee_keys: set[tuple[str, str]], limit: int = 10) -> list[dict]:
    """Real, not-yet-inducted players who've cleared history_store's own
    MIN_HOF_SEASONS bar -- GDD Sec 10.4.8's "Eligible Candidates" list
    (this engine has no voting system, so `progress_pct` stands in for
    the Figma source's voting percentage: each category's own primary
    counting stat as a percentage of that category's current pool
    leader -- a real, if simplified, "how close" proxy, not the exact
    private HOF composite score formula that lives inside
    history_store.hall_of_fame() -- disclosed in the template rather
    than duplicating that formula here)."""
    passing, rushing, receiving, defense = history_store.career_stats()

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


def _hof_record_book() -> list[dict]:
    """GDD Sec 10.4.8's League Record Book: top-10 all-time leaders per
    major real category, from the same real career_stats() archive the
    Hall of Fame itself is built on -- one card per category, most-
    productive-first. Field goals are deliberately omitted: M2 built a
    real per-game Kicking box-score line, but nothing rolls it into a
    season or career total anywhere yet, so a Kicking category here
    would have to be fabricated rather than real -- disclosed in the
    template instead of guessed at."""
    passing, rushing, receiving, defense = history_store.career_stats()

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
    new_keys = _hof_new_inductee_keys(full_history)
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
    separate approximate ranking."""
    div_standings_raw = final_division_standings(season)
    hunt: dict[str, list[dict]] = {}
    standings: dict[str, dict[str, list[dict]]] = {}
    for conf, seeds in (("AFC", bracket.afc_seeds), ("NFC", bracket.nfc_seeds)):
        hunt[conf] = [
            {"abbr": abbr, "location": TEAMS_BY_ABBR[abbr].location, "record": season.records[abbr]}
            for abbr in bubble_teams(season, conf, seeds)
        ]
        standings[conf] = {
            div: [
                {"abbr": abbr, "location": TEAMS_BY_ABBR[abbr].location, "record": season.records[abbr]}
                for abbr in abbrs
            ]
            for (c, div), abbrs in div_standings_raw.items() if c == conf
        }
    return hunt, standings


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
    return templates.TemplateResponse(request, "playoffs.html", {
        "season": season, "bracket": bracket, "round_labels": ROUND_LABELS,
        "view": view, "in_the_hunt": in_the_hunt, "division_standings": division_standings,
        "afc_rounds": afc_rounds, "nfc_rounds": nfc_rounds,
        "sb_matchup": sb_matchups[0] if sb_matchups else None,
    })


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

from __future__ import annotations

from dataclasses import dataclass

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Form, HTTPException
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
from app.engine.scouting import find_next_opponent, build_scouting_report
from app.engine.gameplan import (
    Gameplan, OFFENSIVE_AGGRESSIVENESS, DEFENSIVE_AGGRESSIVENESS,
    COVERAGE_SCHEMES, BLITZ_STRATEGIES, RZ_OFFENSE_STYLES, RZ_DEFENSE_STYLES,
)
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


@app.get("/roster", response_class=HTMLResponse)
def roster_view(request: Request, team_abbr: str | None = None):
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
    players with no team."""
    if team_abbr is None:
        # GDD Sec 10.1: default screen state resolves to the user's team
        # without a picker interaction, once one has been chosen.
        team_abbr = season_state.get_season().user_team_abbr
    if team_abbr is None:
        return templates.TemplateResponse(request, "roster.html", {"teams": TEAMS, "team": None, "players": None})
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

    team = FREE_AGENTS_TEAM if team_abbr == "FA" else TEAMS_BY_ABBR[team_abbr]
    return templates.TemplateResponse(
        request,
        "roster.html",
        {"teams": TEAMS, "team": team, "players": players, "starters": starters},
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
    real here (Defensive TD is the one disclosed gap, not modeled)."""
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


@app.get("/stats", response_class=HTMLResponse)
def stats_view(request: Request):
    season = season_state.get_season()
    games_played = sum(1 for week in season.schedule for g in week if g.result is not None)
    passing_leaders, rushing_leaders, receiving_leaders = _season_stat_leaders(season)
    defensive_leaders = _defensive_stat_leaders(season)
    awards_race = awards.season_awards(season) if games_played else None
    return templates.TemplateResponse(
        request,
        "stats.html",
        {
            "season": season,
            "games_played": games_played,
            "passing_leaders": passing_leaders,
            "rushing_leaders": rushing_leaders,
            "receiving_leaders": receiving_leaders,
            "defensive_leaders": defensive_leaders,
            "awards_race": awards_race,
        },
    )


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


@app.get("/hof", response_class=HTMLResponse)
def hof_view(request: Request):
    """Hall of Fame: real induction over the real career-cumulative
    archive (history_store.career_stats()/hall_of_fame()) -- see that
    module's docstring for the disclosed, GDD-underspecified induction
    formula. Empty until a league has played enough seasons for any
    career to clear the bar."""
    inductees = history_store.hall_of_fame()
    return templates.TemplateResponse(request, "hof.html", {"inductees": inductees})


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


@app.get("/playoffs", response_class=HTMLResponse)
def playoffs_view(request: Request):
    """GDD Sec 10.4.6: AFC/NFC bracket view through the Super Bowl. This
    build renders every round in one page (no AFC/NFC/SB tab-switching
    JS yet -- see Sec 10.5's htmx notes for that) rather than the
    Figma-derived three-tab layout; the underlying bracket data is the
    same either way."""
    season = season_state.get_season()
    if not season.is_complete:
        return templates.TemplateResponse(request, "playoffs.html", {
            "season": season, "bracket": None, "round_labels": ROUND_LABELS,
        })
    if season.playoffs is None:
        season_state.simulate_playoff_round()  # builds the Wild Card round on first visit
        season = season_state.get_season()
    return templates.TemplateResponse(request, "playoffs.html", {
        "season": season, "bracket": season.playoffs, "round_labels": ROUND_LABELS,
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

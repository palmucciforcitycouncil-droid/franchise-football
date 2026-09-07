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
from app.engine import score_fidelity
from app.services import season_state, depth_chart_overrides
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


@app.get("/roster", response_class=HTMLResponse)
def roster_view(request: Request, team_abbr: str | None = None):
    """Real player data (2,365 players across 32 teams, plus 71 free
    agents) has existed since the roster import but was only ever
    consumed internally by the engine -- this is the first page that
    actually shows it. No team selected yet -> just the picker.
    `team_abbr=FA` is a pseudo-team (Player.team_abbr is None for a free
    agent) rather than a real TEAMS entry -- FREE_AGENTS_TEAM stands in
    so the template's `team.location`/`team.abbr` access works the same
    way for both. `starters` marks the highest-overall_rating player at
    each position actually present on the roster (independent of
    depth_chart.py's OffensiveStarters/DefensiveStarters, which model
    the fixed 11/11 personnel package the engine plays with, not a
    display concern, and would crash on positions like K/P that aren't
    part of that package) -- always empty for free agents, since
    "starter" isn't a meaningful concept for players with no team."""
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
        seen_positions = set()
        for p in players:
            if p.position not in seen_positions:
                starters.add(p.player_id)
                seen_positions.add(p.position)

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
        return templates.TemplateResponse(request, "depth_chart.html", {"teams": TEAMS, "team": None, "groups": None})
    if team_abbr not in TEAMS_BY_ABBR:
        raise HTTPException(404, "No such team")

    by_position = _roster_by_position(team_abbr)
    groups = [
        {"position": pos.value, "players": depth_chart_overrides.resolve_order(team_abbr, pos.value, players)}
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


@dataclass
class SeasonPassingLine:
    name: str
    team_abbr: str
    completions: int = 0
    attempts: int = 0
    yards: int = 0
    touchdowns: int = 0
    interceptions: int = 0


@dataclass
class SeasonRushingLine:
    name: str
    team_abbr: str
    carries: int = 0
    yards: int = 0
    touchdowns: int = 0


@dataclass
class SeasonReceivingLine:
    name: str
    team_abbr: str
    receptions: int = 0
    targets: int = 0
    yards: int = 0
    touchdowns: int = 0


def _season_stat_leaders(season, top_n: int = 15):
    """Aggregates every played game's box score (build_box_score, already
    computed per-game for result.html) into season totals, keyed by
    (team_abbr, name) so two players who happen to share a name on
    different teams don't get merged. Reuses build_box_score rather than
    re-deriving stats from raw plays -- same convention/caveat as that
    function: the passing/rushing line's name comes from the team's
    CURRENT starting QB/HB (get_offensive_starters), not necessarily who
    actually played in an older game if the depth chart has since
    changed -- a pre-existing simplification (single active passer/
    rusher per team, no in-season substitution modeled), not something
    new introduced here."""
    passing: dict[tuple[str, str], SeasonPassingLine] = {}
    rushing: dict[tuple[str, str], SeasonRushingLine] = {}
    receiving: dict[tuple[str, str], SeasonReceivingLine] = {}

    for week in season.schedule:
        for g in week:
            if g.result is None:
                continue
            for abbr in (g.home_abbr, g.away_abbr):
                box = build_box_score(g.result.plays, abbr)
                for p in box.passing:
                    line = passing.setdefault((abbr, p.name), SeasonPassingLine(name=p.name, team_abbr=abbr))
                    line.completions += p.completions
                    line.attempts += p.attempts
                    line.yards += p.yards
                    line.touchdowns += p.touchdowns
                    line.interceptions += p.interceptions
                for r in box.rushing:
                    line = rushing.setdefault((abbr, r.name), SeasonRushingLine(name=r.name, team_abbr=abbr))
                    line.carries += r.carries
                    line.yards += r.yards
                    line.touchdowns += r.touchdowns
                for rc in box.receiving:
                    line = receiving.setdefault((abbr, rc.name), SeasonReceivingLine(name=rc.name, team_abbr=abbr))
                    line.receptions += rc.receptions
                    line.targets += rc.targets
                    line.yards += rc.yards
                    line.touchdowns += rc.touchdowns

    return (
        sorted(passing.values(), key=lambda l: -l.yards)[:top_n],
        sorted(rushing.values(), key=lambda l: -l.yards)[:top_n],
        sorted(receiving.values(), key=lambda l: -l.yards)[:top_n],
    )


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_view(request: Request):
    """League-at-a-glance landing page, pulling from pieces that already
    exist rather than introducing new state: season.standings() (top 10
    by record), the most recently completed week's scores, and the top
    5 stat leaders per category (_season_stat_leaders). Doesn't replace
    `/`, which stays the single-game simulator -- the GDD lists Dashboard
    and "Simulate a Game" as distinct screens."""
    season = season_state.get_season()
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
            "standings": standings,
            "last_played_week": last_played_week,
            "last_week_games": last_week_games,
            "passing_leaders": passing_leaders,
            "rushing_leaders": rushing_leaders,
            "receiving_leaders": receiving_leaders,
        },
    )


@app.get("/stats", response_class=HTMLResponse)
def stats_view(request: Request):
    season = season_state.get_season()
    games_played = sum(1 for week in season.schedule for g in week if g.result is not None)
    passing_leaders, rushing_leaders, receiving_leaders = _season_stat_leaders(season)
    return templates.TemplateResponse(
        request,
        "stats.html",
        {
            "season": season,
            "games_played": games_played,
            "passing_leaders": passing_leaders,
            "rushing_leaders": rushing_leaders,
            "receiving_leaders": receiving_leaders,
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
            "back_url": "/season",
            "back_label": "Back to season",
        },
    )


@app.post("/season/simulate-week")
def season_simulate_week():
    season_state.simulate_current_week()
    return RedirectResponse(url="/season", status_code=303)


@app.post("/season/reset")
def season_reset():
    season_state.reset_season()
    return RedirectResponse(url="/season", status_code=303)


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
        },
    )

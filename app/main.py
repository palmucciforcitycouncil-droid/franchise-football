from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_league_seed
from app.data.teams import TEAMS, TEAMS_BY_ABBR
from app.engine.placeholder_ratings import ratings_for
from app.engine.rng import RNG
from app.engine.game_sim import simulate_game, TeamSim
from app.engine.box_score import build_box_score
from app.services import season_state
from app.core.db import get_session
from app.models.player import Player, Position
from sqlmodel import select

app = FastAPI(title="Franchise Football")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"teams": TEAMS})


@app.get("/roster", response_class=HTMLResponse)
def roster_view(request: Request, team_abbr: str | None = None):
    """Real player data (2,365 players across 32 teams) has existed since
    the roster import but was only ever consumed internally by the engine
    -- this is the first page that actually shows it. No team selected
    yet -> just the picker. `starters` marks the highest-overall_rating
    player at each position actually present on the roster (independent
    of depth_chart.py's OffensiveStarters/DefensiveStarters, which model
    the fixed 11/11 personnel package the engine plays with, not a
    display concern, and would crash on positions like K/P that aren't
    part of that package)."""
    if team_abbr is None:
        return templates.TemplateResponse(request, "roster.html", {"teams": TEAMS, "team": None, "players": None})
    if team_abbr not in TEAMS_BY_ABBR:
        raise HTTPException(404, "No such team")

    with get_session() as s:
        players = list(s.exec(select(Player).where(Player.team_abbr == team_abbr)))

    position_rank = {pos: i for i, pos in enumerate(Position)}
    players.sort(key=lambda p: (position_rank[p.position], -p.overall_rating))

    starters: set[str] = set()
    seen_positions = set()
    for p in players:
        if p.position not in seen_positions:
            starters.add(p.player_id)
            seen_positions.add(p.position)

    return templates.TemplateResponse(
        request,
        "roster.html",
        {"teams": TEAMS, "team": TEAMS_BY_ABBR[team_abbr], "players": players, "starters": starters},
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
    game_seed = hash((season.league_seed, week_num, home_abbr, away_abbr)) & 0xFFFFFFFF

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
    # matching the "derived, not global" spirit of GDD Part 1 Sec 1.3
    # (a full make_rng(season_year, week, game_id, subsystem) helper comes
    # later, once there's a real season/week/game_id to key off of).
    game_seed = hash((league_seed, home_abbr, away_abbr, "demo_game")) & 0xFFFFFFFF
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

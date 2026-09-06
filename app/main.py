from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_league_seed
from app.data.teams import TEAMS, TEAMS_BY_ABBR
from app.engine.placeholder_ratings import ratings_for
from app.engine.rng import RNG
from app.engine.game_sim import simulate_game, TeamSim
from app.services import season_state

app = FastAPI(title="Franchise Football")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"teams": TEAMS})


@app.get("/season", response_class=HTMLResponse)
def season_view(request: Request):
    season = season_state.get_season()
    this_week = None
    if not season.is_complete:
        this_week = season.schedule[season.current_week - 1]
    return templates.TemplateResponse(
        request,
        "season.html",
        {
            "season": season,
            "standings": season.standings(),
            "this_week": this_week,
            "n_weeks": season_state.N_WEEKS,
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

    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "home": home,
            "away": away,
            "result": result,
            "league_seed": league_seed,
            "game_seed": game_seed,
        },
    )

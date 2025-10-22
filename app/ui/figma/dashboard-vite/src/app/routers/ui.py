from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from app.db import get_session
from app.models.sim_models import Team, Game
from app.services.stats_service import box_score_for_game

router = APIRouter(tags=["ui"])

@router.get("/", response_class=HTMLResponse)
def dash(request: Request):
    return request.app.state.templates.TemplateResponse("dashboard.html", {"request": request, "title":"Dashboard"})

@router.get("/teams", response_class=HTMLResponse)
def teams_page(request: Request, session: Session = Depends(get_session)):
    teams = session.exec(select(Team).order_by(Team.id)).all()
    return request.app.state.templates.TemplateResponse("teams.html", {"request": request, "title":"Teams", "teams": teams})

@router.get("/games/{season}/{week}", response_class=HTMLResponse)
def games_page(season: int, week: int, request: Request, session: Session = Depends(get_session)):
    teams = {t.id:t for t in session.exec(select(Team)).all()}
    games = session.exec(select(Game).where(Game.season==season, Game.week==week).order_by(Game.id)).all()
    return request.app.state.templates.TemplateResponse("games.html", {"request": request, "title":"Games", "season":season, "week":week, "games":games, "teams":teams})

@router.get("/box/{game_id}", response_class=HTMLResponse)
def box_page(game_id: int, request: Request, session: Session = Depends(get_session)):
    teams = {t.id:t for t in session.exec(select(Team)).all()}
    data = box_score_for_game(session, game_id)
    if "error" in data:
        return HTMLResponse(f"<pre>Not found</pre>", status_code=404)
    game = session.get(Game, game_id)
    # Team stats rows from service
    stats = data.get("teams", [])
    return request.app.state.templates.TemplateResponse("box.html", {"request": request, "title":"Box", "game":game, "teams":teams, "stats":stats})

@router.get("/health-ui", response_class=HTMLResponse)
def health_ui(request: Request, session: Session = Depends(get_session)):
    from app.routers.health import health as health_api
    payload = health_api(session)  # call directly
    return request.app.state.templates.TemplateResponse("health.html", {"request": request, "title":"Health", "payload": payload})

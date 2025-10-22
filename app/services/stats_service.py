from typing import Dict, List
from sqlmodel import Session, select, func
from app.models.stats_models import TeamGameStats
from app.models.sim_models import SimGame

def record_team_game_stats(session: Session, game: SimGame, home_totals, away_totals):
    # delete existing if re-sim
    session.query(TeamGameStats).filter(TeamGameStats.game_id==game.id).delete()
    session.add(TeamGameStats(
        game_id=game.id, season=game.season, week=game.week,
        team_id=game.home_team_id, is_home=True,
        points=home_totals.points, plays=home_totals.plays, yards_total=home_totals.yards,
        pass_yards=home_totals.pass_yards, rush_yards=home_totals.rush_yards, turnovers=home_totals.turnovers
    ))
    session.add(TeamGameStats(
        game_id=game.id, season=game.season, week=game.week,
        team_id=game.away_team_id, is_home=False,
        points=away_totals.points, plays=away_totals.plays, yards_total=away_totals.yards,
        pass_yards=away_totals.pass_yards, rush_yards=away_totals.rush_yards, turnovers=away_totals.turnovers
    ))
    session.commit()

def team_season_aggregates(session: Session, season: int) -> List[dict]:
    q = session.query(
        TeamGameStats.team_id.label("team_id"),
        func.sum(TeamGameStats.points).label("points_for"),
        func.sum(TeamGameStats.yards_total).label("yards"),
        func.sum(TeamGameStats.pass_yards).label("pass_yards"),
        func.sum(TeamGameStats.rush_yards).label("rush_yards"),
        func.sum(TeamGameStats.turnovers).label("turnovers"),
        func.sum(TeamGameStats.plays).label("plays"),
        func.count(TeamGameStats.id).label("games")
    ).filter(TeamGameStats.season==season).group_by(TeamGameStats.team_id)
    rows = q.all()
    return [dict(r._mapping) for r in rows]

def box_score_for_game(session: Session, game_id: int) -> dict:
    g = session.query(SimGame).filter(SimGame.id == game_id).first()
    if not g: return {"error": "NOT_FOUND"}
    stats = session.query(TeamGameStats).filter(TeamGameStats.game_id==game_id).all()
    return {
        "game_id": game_id,
        "season": g.season,
        "week": g.week,
        "home_team_id": g.home_team_id,
        "away_team_id": g.away_team_id,
        "home_score": g.home_score, "away_score": g.away_score,
        "teams": [s.model_dump() for s in stats]
    }

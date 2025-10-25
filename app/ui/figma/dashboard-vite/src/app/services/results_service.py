from __future__ import annotations
from typing import List, Dict, Any
from sqlmodel import Session, select
from app.models.sim_models import Game
from app.models.results import TeamGameStats, PlayerBox

def record_game_result(sess: Session, season: int, week: int, game_id: int, home_score: int, away_score: int):
    """Record or update the final score for a game."""
    g = sess.get(Game, game_id)
    if not g:
        g = Game(id=game_id, season=season, week=week, home_team_id=0, away_team_id=0)  # fallback; better to ensure game exists
        sess.add(g)
        sess.commit()
        sess.refresh(g)
    
    # Update the game with the final score
    g.home_score = home_score
    g.away_score = away_score
    g.status = "final"
    sess.add(g)
    sess.commit()

def upsert_team_game(sess: Session, payload: dict):
    """
    Upsert team game stats for a specific game.
    payload keys: game_id, season, week, team_id, points, yards_offense, pass_yds, rush_yds, takeaways, giveaways, sacks,
                  third_down_pct, red_zone_td_pct, time_of_possession_sec
    """
    row = sess.exec(select(TeamGameStats).where(
        TeamGameStats.game_id==payload["game_id"], 
        TeamGameStats.team_id==payload["team_id"]
    )).first()
    
    if not row:
        row = TeamGameStats(**payload)
    else:
        for k, v in payload.items(): 
            setattr(row, k, v)
    
    sess.add(row)
    sess.commit()
    sess.refresh(row)
    return row

def bulk_upsert_player_boxes(sess: Session, boxes: List[dict]):
    """
    Bulk upsert player box scores for a game.
    boxes: list of dicts matching PlayerBox fields. Upsert by (game_id, player_id).
    """
    for b in boxes:
        row = sess.exec(select(PlayerBox).where(
            PlayerBox.game_id==b["game_id"], 
            PlayerBox.player_id==b["player_id"]
        )).first()
        
        if not row:
            row = PlayerBox(**b)
        else:
            for k, v in b.items(): 
                setattr(row, k, v)
        sess.add(row)
    sess.commit()

def week_scoreboard(sess: Session, season: int, week: int) -> List[Dict[str, Any]]:
    """Get the scoreboard for a specific week."""
    games = list(sess.exec(select(Game).where(Game.season==season, Game.week==week)))
    out = []
    for g in games:
        out.append({
            "game_id": g.id, 
            "home_team_id": g.home_team_id, 
            "away_team_id": g.away_team_id,
            "home_score": g.home_score if g.status == "final" else None, 
            "away_score": g.away_score if g.status == "final" else None
        })
    return out

def team_schedule(sess: Session, season: int, team_id: int) -> List[Dict[str, Any]]:
    """Get the full schedule for a specific team in a season."""
    gs = list(sess.exec(select(Game).where(Game.season==season)))
    out = []
    for g in gs:
        if g.home_team_id != team_id and g.away_team_id != team_id: 
            continue
        out.append({
            "game_id": g.id, 
            "week": g.week, 
            "home_team_id": g.home_team_id, 
            "away_team_id": g.away_team_id,
            "home_score": g.home_score if g.status == "final" else None, 
            "away_score": g.away_score if g.status == "final" else None
        })
    out.sort(key=lambda x: x["week"])
    return out

def game_box(sess: Session, game_id: int) -> Dict[str, Any]:
    """Get the complete box score for a specific game."""
    # Team lines
    teams = list(sess.exec(select(TeamGameStats).where(TeamGameStats.game_id==game_id)))
    # Player lines
    players = list(sess.exec(select(PlayerBox).where(PlayerBox.game_id==game_id)))
    
    return {
        "teams": [
            {k: getattr(t, k) for k in TeamGameStats.__fields__.keys() if k != "id"} 
            for t in teams
        ],
        "players": [
            {k: getattr(p, k) for k in PlayerBox.__fields__.keys() if k != "id"} 
            for p in players
        ]
    }

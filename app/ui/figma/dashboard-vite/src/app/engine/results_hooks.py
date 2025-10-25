from __future__ import annotations
from typing import List, Dict
from sqlmodel import Session
from app.services.results_service import record_game_result, upsert_team_game, bulk_upsert_player_boxes

def persist_full_game(sess: Session, *, season: int, week: int, game_id: int,
                      home_score: int, away_score: int,
                      home_team_line: Dict, away_team_line: Dict,
                      player_boxes: List[Dict]):
    """
    Call this at the end of your sim for each game.
    - team lines must include: game_id, season, week, team_id, points, yards_offense, pass_yds, rush_yds, ...
    - each player box must include: game_id, season, week, team_id, opponent_id, player_id, pos, and relevant stats.
    """
    record_game_result(sess, season, week, game_id, home_score, away_score)
    upsert_team_game(sess, {**home_team_line, "game_id": game_id, "season": season, "week": week, "points": home_score})
    upsert_team_game(sess, {**away_team_line, "game_id": game_id, "season": season, "week": week, "points": away_score})
    bulk_upsert_player_boxes(sess, player_boxes)


from __future__ import annotations
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select

def _try(path: str, name: str):
    """Defensive import helper - returns None if model doesn't exist."""
    try:
        mod = __import__(path, fromlist=[name])
        return getattr(mod, name)
    except Exception:
        return None

# Defensive imports for models that may not exist yet
Game = _try("app.models.schedule", "Game")
GameResult = _try("app.models.schedule", "GameResult")
PlayerStats = _try("app.models.stats", "PlayerStats")
CoachStats = _try("app.models.stats", "CoachStats")

def recent_player_games(sess: Session, player_id: int, season: int, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Get recent games for a player with mini-logs.
    Returns list of dicts with game info and key stats.
    """
    if not Game or not GameResult or not PlayerStats:
        return []
    
    # Get recent games for the player's team
    player = sess.exec(select(PlayerStats).where(PlayerStats.player_id == player_id)).first()
    if not player:
        return []
    
    team_id = getattr(player, 'team_id', None)
    if not team_id:
        return []
    
    # Get recent games for the team
    games = list(sess.exec(
        select(Game).where(
            Game.season == season,
            (Game.home_team_id == team_id) | (Game.away_team_id == team_id)
        ).order_by(Game.week.desc()).limit(limit)
    ))
    
    recent_games = []
    for game in games:
        # Get game result
        result = sess.exec(
            select(GameResult).where(GameResult.game_id == game.id)
        ).first()
        
        if not result:
            continue
        
        # Get player stats for this game
        player_stats = sess.exec(
            select(PlayerStats).where(
                PlayerStats.player_id == player_id,
                PlayerStats.game_id == game.id
            )
        ).first()
        
        if not player_stats:
            continue
        
        # Determine if home or away
        is_home = game.home_team_id == team_id
        opponent_team_id = game.away_team_id if is_home else game.home_team_id
        team_score = result.home_score if is_home else result.away_score
        opponent_score = result.away_score if is_home else result.home_score
        
        # Extract key stats
        key_stats = {
            "passing_yards": getattr(player_stats, 'passing_yards', 0),
            "passing_tds": getattr(player_stats, 'passing_tds', 0),
            "rushing_yards": getattr(player_stats, 'rushing_yards', 0),
            "rushing_tds": getattr(player_stats, 'rushing_tds', 0),
            "receiving_yards": getattr(player_stats, 'receiving_yards', 0),
            "receiving_tds": getattr(player_stats, 'receiving_tds', 0),
            "tackles": getattr(player_stats, 'tackles', 0),
            "sacks": getattr(player_stats, 'sacks', 0),
            "interceptions": getattr(player_stats, 'interceptions', 0),
        }
        
        recent_games.append({
            "game_id": game.id,
            "week": game.week,
            "season": game.season,
            "opponent_team_id": opponent_team_id,
            "is_home": is_home,
            "team_score": team_score,
            "opponent_score": opponent_score,
            "result": "W" if team_score > opponent_score else "L" if team_score < opponent_score else "T",
            "key_stats": key_stats
        })
    
    return recent_games

def recent_coach_games(sess: Session, coach_id: int, season: int, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Get recent games for a coach with mini-logs.
    Returns list of dicts with game info and team performance.
    """
    if not Game or not GameResult or not CoachStats:
        return []
    
    # Get coach stats to find team
    coach_stats = sess.exec(select(CoachStats).where(CoachStats.coach_id == coach_id)).first()
    if not coach_stats:
        return []
    
    team_id = getattr(coach_stats, 'team_id', None)
    if not team_id:
        return []
    
    # Get recent games for the team
    games = list(sess.exec(
        select(Game).where(
            Game.season == season,
            (Game.home_team_id == team_id) | (Game.away_team_id == team_id)
        ).order_by(Game.week.desc()).limit(limit)
    ))
    
    recent_games = []
    for game in games:
        # Get game result
        result = sess.exec(
            select(GameResult).where(GameResult.game_id == game.id)
        ).first()
        
        if not result:
            continue
        
        # Get coach stats for this game
        coach_game_stats = sess.exec(
            select(CoachStats).where(
                CoachStats.coach_id == coach_id,
                CoachStats.game_id == game.id
            )
        ).first()
        
        if not coach_game_stats:
            continue
        
        # Determine if home or away
        is_home = game.home_team_id == team_id
        opponent_team_id = game.away_team_id if is_home else game.home_team_id
        team_score = result.home_score if is_home else result.away_score
        opponent_score = result.away_score if is_home else result.home_score
        
        # Extract key coaching stats
        key_stats = {
            "offensive_yards": getattr(coach_game_stats, 'offensive_yards', 0),
            "defensive_yards_allowed": getattr(coach_game_stats, 'defensive_yards_allowed', 0),
            "turnovers_forced": getattr(coach_game_stats, 'turnovers_forced', 0),
            "turnovers_committed": getattr(coach_game_stats, 'turnovers_committed', 0),
            "penalties": getattr(coach_game_stats, 'penalties', 0),
            "penalty_yards": getattr(coach_game_stats, 'penalty_yards', 0),
        }
        
        recent_games.append({
            "game_id": game.id,
            "week": game.week,
            "season": game.season,
            "opponent_team_id": opponent_team_id,
            "is_home": is_home,
            "team_score": team_score,
            "opponent_score": opponent_score,
            "result": "W" if team_score > opponent_score else "L" if team_score < opponent_score else "T",
            "key_stats": key_stats
        })
    
    return recent_games

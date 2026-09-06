from __future__ import annotations
from typing import Tuple, Dict, Any
from sqlmodel import Session
from app.engine.gameplan_compose import compose_final_engine_config

def prepare_game_configs(sess: Session, game_id: int, season: int, week: int, home_team_id: int, away_team_id: int) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Prepares the final gameplan configurations for both teams before kickoff.
    
    Returns (home_cfg, away_cfg) dicts for the engine to consume.
    Each config contains the composed gameplan with HC influence + User selections + Coach focus.
    """
    home_cfg = compose_final_engine_config(sess, game_id, season, week, home_team_id, away_team_id).__dict__
    away_cfg = compose_final_engine_config(sess, game_id, season, week, away_team_id, home_team_id).__dict__
    return home_cfg, away_cfg

def prepare_week_game_configs(sess: Session, season: int, week: int, games: list) -> Dict[int, Tuple[Dict[str, Any], Dict[str, Any]]]:
    """
    Prepares gameplan configurations for all games in a week.
    
    Args:
        sess: Database session
        season: Current season
        week: Current week
        games: List of game objects with id, home_team_id, away_team_id
    
    Returns:
        Dict mapping game_id to (home_cfg, away_cfg) tuple
    """
    configs = {}
    for game in games:
        home_cfg, away_cfg = prepare_game_configs(
            sess, game.id, season, week, game.home_team_id, game.away_team_id
        )
        configs[game.id] = (home_cfg, away_cfg)
    return configs

# Example usage before simming the week's games:
# for game in schedule:
#     home_cfg, away_cfg = prepare_game_configs(sess, game.id, season, week, game.home_id, game.away_id)
#     engine.run_game(game, home_cfg, away_cfg)


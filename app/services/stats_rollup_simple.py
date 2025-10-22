from __future__ import annotations
from typing import Dict, List, Any, Optional
import json
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.sim_models import Game, GameEvent
from app.models.stats import PlayerGameStats, TeamGameStats
from app.models.team import Team
import logging

logger = logging.getLogger(__name__)

def rollup_game_stats_simple(s: Session, game_id: int) -> bool:
    """Simple rollup stats for a specific game from PBP data"""
    
    try:
        # Get game info
        game = s.get(Game, game_id)
        if not game:
            logger.error(f"Game {game_id} not found")
            return False
        
        # Get all events for this game
        events = s.exec(
            select(GameEvent).where(GameEvent.game_id == game_id)
        ).all()
        
        if not events:
            logger.warning(f"No events found for game {game_id}")
            return False
        
        # Initialize basic stats
        home_stats = {
            "game_id": game_id,
            "team_id": game.home_team_id,
            "gp": True,
            "snaps_offense": 0,
            "snaps_defense": 0,
            "snaps_st": 0,
            "pass_attempts": 0,
            "pass_completions": 0,
            "pass_yards": 0,
            "pass_td": 0,
            "pass_int": 0,
            "rush_attempts": 0,
            "rush_yards": 0,
            "rush_td": 0,
            "total_yards": 0,
            "total_td": 0,
            "turnovers": 0,
            "punts": 0,
            "punt_yards": 0,
            "fg_attempts": 0,
            "fg_made": 0,
            "penalties": 0,
            "penalty_yards": 0,
        }
        
        away_stats = {
            "game_id": game_id,
            "team_id": game.away_team_id,
            "gp": True,
            "snaps_offense": 0,
            "snaps_defense": 0,
            "snaps_st": 0,
            "pass_attempts": 0,
            "pass_completions": 0,
            "pass_yards": 0,
            "pass_td": 0,
            "pass_int": 0,
            "rush_attempts": 0,
            "rush_yards": 0,
            "rush_td": 0,
            "total_yards": 0,
            "total_td": 0,
            "turnovers": 0,
            "punts": 0,
            "punt_yards": 0,
            "fg_attempts": 0,
            "fg_made": 0,
            "penalties": 0,
            "penalty_yards": 0,
        }
        
        # Process events
        for event in events:
            if event.event_type not in ["play", "punt", "turnover", "td", "fg"]:
                continue
            
            try:
                payload = json.loads(event.description) if event.description else {}
            except:
                continue
            
            team = payload.get("team")
            if team not in ["home", "away"]:
                continue
            
            stats = home_stats if team == "home" else away_stats
            
            if event.event_type == "play":
                yards = payload.get("yards", 0)
                is_pass = payload.get("play") == "pass"
                is_run = payload.get("play") == "run"
                is_complete = payload.get("complete", False)
                is_td = payload.get("is_td", False)
                
                if is_pass:
                    stats["pass_attempts"] += 1
                    if is_complete:
                        stats["pass_completions"] += 1
                        stats["pass_yards"] += yards
                    if is_td:
                        stats["pass_td"] += 1
                        stats["total_td"] += 1
                elif is_run:
                    stats["rush_attempts"] += 1
                    stats["rush_yards"] += yards
                    if is_td:
                        stats["rush_td"] += 1
                        stats["total_td"] += 1
                
                stats["total_yards"] += yards
                stats["snaps_offense"] += 1
            
            elif event.event_type == "turnover":
                stats["turnovers"] += 1
            
            elif event.event_type == "punt":
                stats["punts"] += 1
                stats["punt_yards"] += payload.get("yards", 0)
                stats["snaps_st"] += 1
            
            elif event.event_type == "fg":
                stats["fg_attempts"] += 1
                if payload.get("made", False):
                    stats["fg_made"] += 1
        
        # Save team stats
        for stats in [home_stats, away_stats]:
            # Check if stats already exist
            existing = s.exec(
                select(TeamGameStats).where(
                    TeamGameStats.game_id == game_id,
                    TeamGameStats.team_id == stats["team_id"]
                )
            ).first()
            
            if existing:
                # Update existing stats
                for key, value in stats.items():
                    if key not in ["game_id", "team_id"]:
                        setattr(existing, key, value)
            else:
                # Create new stats
                team_game_stats = TeamGameStats(**stats)
                s.add(team_game_stats)
        
        # Create minimal player stats
        for stats in [home_stats, away_stats]:
            existing_player = s.exec(
                select(PlayerGameStats).where(
                    PlayerGameStats.game_id == game_id,
                    PlayerGameStats.team_id == stats["team_id"]
                )
            ).first()
            
            if not existing_player:
                player_game_stats = PlayerGameStats(
                    game_id=game_id,
                    player_id=1,  # Placeholder
                    team_id=stats["team_id"],
                    gp=True,
                    gs=True,
                    snaps_offense=stats["snaps_offense"],
                    pass_attempts=stats["pass_attempts"],
                    pass_completions=stats["pass_completions"],
                    pass_yards=stats["pass_yards"],
                    pass_td=stats["pass_td"],
                    rush_attempts=stats["rush_attempts"],
                    rush_yards=stats["rush_yards"],
                    rush_td=stats["rush_td"],
                )
                s.add(player_game_stats)
        
        s.commit()
        logger.info(f"Successfully rolled up simple stats for game {game_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error rolling up simple stats for game {game_id}: {e}")
        s.rollback()
        return False

def rollup_season_stats_simple(s: Session, season: int) -> bool:
    """Simple rollup stats for all games in a season"""
    
    try:
        # Get all games for the season
        games = s.exec(
            select(Game).where(Game.season == season)
        ).all()
        
        if not games:
            logger.warning(f"No games found for season {season}")
            return False
        
        success_count = 0
        for game_row in games:
            try:
                game = game_row[0]  # Extract Game object from Row
                if rollup_game_stats_simple(s, game.id):
                    success_count += 1
            except Exception as e:
                logger.error(f"Error rolling up simple stats for game {game_row[0].id if game_row else 'unknown'}: {e}")
                continue
        
        logger.info(f"Successfully rolled up simple stats for {success_count}/{len(games)} games in season {season}")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"Error rolling up simple stats for season {season}: {e}")
        return False

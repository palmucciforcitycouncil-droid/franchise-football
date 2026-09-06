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

def rollup_game_stats(s: Session, game_id: int) -> bool:
    """Roll up stats for a specific game from PBP data"""
    
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
        
        # Initialize stats dictionaries
        player_stats: Dict[int, Dict[str, Any]] = {}
        team_stats: Dict[int, Dict[str, Any]] = {}
        
        # Process each event
        for event in events:
            if event.event_type not in ["play", "punt", "turnover", "td", "fg", "safety"]:
                continue
            
            try:
                payload = json.loads(event.description) if event.description else {}
            except:
                continue
            
            # Determine team
            team = payload.get("team")
            if team not in ["home", "away"]:
                continue
            
            team_id = game.home_team_id if team == "home" else game.away_team_id
            other_team_id = game.away_team_id if team == "home" else game.home_team_id
            
            # Initialize team stats if needed
            if team_id not in team_stats:
                team_stats[team_id] = {
                    "game_id": game_id,
                    "team_id": team_id,
                    "gp": True,
                    "snaps_offense": 0,
                    "snaps_defense": 0,
                    "snaps_st": 0,
                    "pass_attempts": 0,
                    "pass_completions": 0,
                    "pass_yards": 0,
                    "pass_td": 0,
                    "pass_int": 0,
                    "sacks_allowed": 0.0,
                    "sack_yards_allowed": 0,
                    "qb_hits_allowed": 0,
                    "pressures_allowed": 0,
                    "rush_attempts": 0,
                    "rush_yards": 0,
                    "rush_td": 0,
                    "total_yards": 0,
                    "total_td": 0,
                    "turnovers": 0,
                    "tackles_solo": 0,
                    "tackles_assist": 0,
                    "tfl": 0,
                    "sacks": 0.0,
                    "qb_hits": 0,
                    "pressures": 0,
                    "interceptions": 0,
                    "int_yards": 0,
                    "int_td": 0,
                    "pbus": 0,
                    "forced_fumbles": 0,
                    "fumble_recoveries": 0,
                    "fr_yards": 0,
                    "fr_td": 0,
                    "kickoffs": 0,
                    "kickoff_touchbacks": 0,
                    "punts": 0,
                    "punt_yards": 0,
                    "punts_in_20": 0,
                    "punt_touchbacks": 0,
                    "punt_returns": 0,
                    "punt_return_yards": 0,
                    "punt_return_td": 0,
                    "kickoff_returns": 0,
                    "kickoff_return_yards": 0,
                    "kickoff_return_td": 0,
                    "fg_attempts": 0,
                    "fg_made": 0,
                    "fg_yards": 0,
                    "xp_attempts": 0,
                    "xp_made": 0,
                    "penalties": 0,
                    "penalty_yards": 0,
                    "epa": 0.0,
                    "success_rate": 0.0,
                    "explosives": 0,
                    "third_down_conversions": 0,
                    "third_down_attempts": 0,
                }
            
            # Process different event types
            if event.event_type == "play":
                # Basic play stats
                yards = payload.get("yards", 0)
                is_pass = payload.get("play") == "pass"
                is_run = payload.get("play") == "run"
                is_complete = payload.get("complete", False)
                is_td = payload.get("is_td", False)
                is_sack = payload.get("is_sack", False)
                
                if is_pass:
                    team_stats[team_id]["pass_attempts"] += 1
                    if is_complete:
                        team_stats[team_id]["pass_completions"] += 1
                        team_stats[team_id]["pass_yards"] += yards
                    if is_td:
                        team_stats[team_id]["pass_td"] += 1
                        team_stats[team_id]["total_td"] += 1
                    if is_sack:
                        team_stats[team_id]["sacks_allowed"] += 1.0
                        team_stats[team_id]["sack_yards_allowed"] += abs(yards)
                
                elif is_run:
                    team_stats[team_id]["rush_attempts"] += 1
                    team_stats[team_id]["rush_yards"] += yards
                    if is_td:
                        team_stats[team_id]["rush_td"] += 1
                        team_stats[team_id]["total_td"] += 1
                
                team_stats[team_id]["total_yards"] += yards
                team_stats[team_id]["snaps_offense"] += 1
            
            elif event.event_type == "turnover":
                team_stats[team_id]["turnovers"] += 1
            
            elif event.event_type == "punt":
                team_stats[team_id]["punts"] += 1
                team_stats[team_id]["punt_yards"] += payload.get("yards", 0)
                team_stats[team_id]["snaps_st"] += 1
            
            elif event.event_type == "fg":
                team_stats[team_id]["fg_attempts"] += 1
                if payload.get("made", False):
                    team_stats[team_id]["fg_made"] += 1
                team_stats[team_id]["fg_yards"] += payload.get("yards", 0)
                team_stats[team_id]["snaps_st"] += 1
            
            elif event.event_type == "td":
                team_stats[team_id]["total_td"] += 1
        
        # Save team stats
        for team_id, stats in team_stats.items():
            # Check if stats already exist
            existing = s.exec(
                select(TeamGameStats).where(
                    TeamGameStats.game_id == game_id,
                    TeamGameStats.team_id == team_id
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
        
        # For now, create minimal player stats (we'll enhance this later)
        # This is a placeholder to make the API work
        for team_id in team_stats.keys():
            # Create a placeholder player stats entry
            existing_player = s.exec(
                select(PlayerGameStats).where(
                    PlayerGameStats.game_id == game_id,
                    PlayerGameStats.team_id == team_id
                )
            ).first()
            
            if not existing_player:
                player_game_stats = PlayerGameStats(
                    game_id=game_id,
                    player_id=1,  # Placeholder player ID
                    team_id=team_id,
                    gp=True,
                    gs=True,
                    snaps_offense=team_stats[team_id]["snaps_offense"],
                    snaps_defense=team_stats[team_id]["snaps_defense"],
                    snaps_st=team_stats[team_id]["snaps_st"],
                    pass_attempts=team_stats[team_id]["pass_attempts"],
                    pass_completions=team_stats[team_id]["pass_completions"],
                    pass_yards=team_stats[team_id]["pass_yards"],
                    pass_td=team_stats[team_id]["pass_td"],
                    pass_int=team_stats[team_id]["pass_int"],
                    rush_attempts=team_stats[team_id]["rush_attempts"],
                    rush_yards=team_stats[team_id]["rush_yards"],
                    rush_td=team_stats[team_id]["rush_td"],
                    total_yards=team_stats[team_id]["total_yards"],
                    total_td=team_stats[team_id]["total_td"],
                    turnovers=team_stats[team_id]["turnovers"],
                )
                s.add(player_game_stats)
        
        s.commit()
        logger.info(f"Successfully rolled up stats for game {game_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error rolling up stats for game {game_id}: {e}")
        s.rollback()
        return False

def rollup_season_stats(s: Session, season: int) -> bool:
    """Roll up stats for all games in a season"""
    
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
                if rollup_game_stats(s, game.id):
                    success_count += 1
            except Exception as e:
                logger.error(f"Error rolling up stats for game {game_row[0].id if game_row else 'unknown'}: {e}")
                continue
        
        logger.info(f"Successfully rolled up stats for {success_count}/{len(games)} games in season {season}")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"Error rolling up stats for season {season}: {e}")
        return False

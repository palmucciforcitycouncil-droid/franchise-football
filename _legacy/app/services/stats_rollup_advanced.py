"""
Advanced Stats Rollup Service

Handles aggregation of PBP events into comprehensive game, season, and career stats
including all GDD v3.2 Stat Catalog fields.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional, Tuple
import json
import math
from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete
from app.models.sim_models import GameEvent, Game
from app.models.stats import PlayerGameStats, TeamGameStats, PlayerSeasonStats, TeamSeasonStats, PlayerCareerStats
import logging

logger = logging.getLogger(__name__)

def rollup_game_stats_advanced(s: Session, game_id: int) -> bool:
    """Advanced rollup stats for a specific game from PBP data with all GDD v3.2 fields."""
    
    try:
        # Get game info
        game = s.exec(select(Game).where(Game.id == game_id)).first()
        if not game:
            logger.warning(f"Game {game_id} not found")
            return False
        
        # Get all events for this game
        events = s.exec(
            select(GameEvent).where(GameEvent.game_id == game_id)
        ).all()
        
        if not events:
            logger.warning(f"No events found for game {game_id}")
            return False
        
        # Initialize team stats
        home_team_id = game.home_team_id
        away_team_id = game.away_team_id
        
        team_stats = {
            home_team_id: _initialize_team_stats(game_id, home_team_id),
            away_team_id: _initialize_team_stats(game_id, away_team_id)
        }
        
        # Initialize player stats (placeholder for now - would need roster data)
        player_stats = {}
        
        # Process events
        for event in events:
            _process_event_advanced(event, team_stats, player_stats, home_team_id, away_team_id)
        
        # Calculate derived metrics
        for team_id, stats in team_stats.items():
            _calculate_derived_metrics(stats)
        
        # Save team stats
        for team_id, stats in team_stats.items():
            _save_team_game_stats(s, stats)
        
        # Save player stats
        for player_id, stats in player_stats.items():
            _save_player_game_stats(s, stats)
        
        s.commit()
        logger.info(f"Successfully rolled up advanced stats for game {game_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error rolling up advanced stats for game {game_id}: {e}")
        s.rollback()
        return False

def _initialize_team_stats(game_id: int, team_id: int) -> Dict[str, Any]:
    """Initialize team stats dictionary with all GDD v3.2 fields."""
    return {
        "game_id": game_id,
        "team_id": team_id,
        "gp": True,
        
        # Snap counts
        "snaps_offense": 0,
        "snaps_defense": 0,
        "snaps_st": 0,
        
        # Offensive stats
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
        
        # Defensive stats
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
        
        # Special teams
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
        
        # Kicking
        "fg_attempts": 0,
        "fg_made": 0,
        "fg_yards": 0,
        "xp_attempts": 0,
        "xp_made": 0,
        
        # Penalties
        "penalties": 0,
        "penalty_yards": 0,
        
        # Advanced metrics
        "epa": 0.0,
        "success_rate": 0.0,
        "explosives": 0,
        "third_down_conversions": 0,
        "third_down_attempts": 0,
        
        # GDD v3.2 Stat Catalog Add-On Fields
        
        # Offensive Line fields
        "run_block_wins": 0,
        "pass_block_wins": 0,
        "penalties_ol": 0,
        
        # Enhanced Defense fields
        "targets_faced": 0,
        "completions_allowed": 0,
        "yards_allowed": 0,
        "yac_allowed": 0,
        "td_allowed": 0,
        "passer_rating_against": 0.0,
        "missed_tackles": 0,
        "run_stops": 0,
        
        # Enhanced Special Teams fields
        "punt_net_avg": 0.0,
        "hang_time_avg": 0.0,
        "kick_distance_avg": 0.0,
        "blocked_kicks": 0,
        "return_avg": 0.0,
        "return_td": 0,
        "fair_catches": 0,
        
        # Situational splits
        "fourth_down_conversions": 0,
        "fourth_down_attempts": 0,
        "red_zone_td": 0,
        "red_zone_attempts": 0,
        "goal_to_go_td": 0,
        "goal_to_go_attempts": 0,
        "two_minute_plays": 0,
        "hurry_up_plays": 0,
        "garbage_time_excluded": 0,
    }

def _process_event_advanced(event: GameEvent, team_stats: Dict[int, Dict], player_stats: Dict[int, Dict], 
                          home_team_id: int, away_team_id: int) -> None:
    """Process a single PBP event and update stats."""
    
    try:
        # Parse event data
        if event.data_json:
            payload = json.loads(event.data_json)
        elif event.description:
            payload = json.loads(event.description)
        else:
            payload = {}
        
        # Determine offense and defense teams
        offense_team_id = event.offense_team_id or home_team_id
        defense_team_id = event.defense_team_id or away_team_id
        
        if offense_team_id == home_team_id:
            defense_team_id = away_team_id
        else:
            defense_team_id = home_team_id
        
        offense_stats = team_stats[offense_team_id]
        defense_stats = team_stats[defense_team_id]
        
        # Process based on event type
        if event.event_type == "play":
            _process_play_event(event, payload, offense_stats, defense_stats)
        elif event.event_type == "punt":
            _process_punt_event(event, payload, offense_stats, defense_stats)
        elif event.event_type == "turnover":
            _process_turnover_event(event, payload, offense_stats, defense_stats)
        elif event.event_type == "td":
            _process_td_event(event, payload, offense_stats, defense_stats)
        elif event.event_type == "fg":
            _process_fg_event(event, payload, offense_stats, defense_stats)
        elif event.event_type == "xp":
            _process_xp_event(event, payload, offense_stats, defense_stats)
        elif event.event_type == "safety":
            _process_safety_event(event, payload, offense_stats, defense_stats)
        
    except Exception as e:
        logger.error(f"Error processing event {event.id}: {e}")

def _process_play_event(event: GameEvent, payload: Dict, offense_stats: Dict, defense_stats: Dict) -> None:
    """Process a play event with advanced PBP fields."""
    
    play_type = payload.get("play")
    yards = payload.get("yards", 0)
    down = payload.get("down", 1)
    to_go = payload.get("to_go", 10)
    yardline = payload.get("yardline", 50)
    quarter = event.quarter
    clock_seconds = _parse_clock_to_seconds(event.clock)
    
    # Update snap counts
    offense_stats["snaps_offense"] += 1
    defense_stats["snaps_defense"] += 1
    
    # Process situational flags
    _update_situational_flags(offense_stats, down, to_go, yardline, quarter, clock_seconds)
    
    if play_type == "pass":
        _process_pass_play(payload, offense_stats, defense_stats, yards)
    elif play_type == "run":
        _process_run_play(payload, offense_stats, defense_stats, yards)
    
    # Update total yards
    offense_stats["total_yards"] += max(0, yards)
    
    # Check for explosive plays (20+ yards)
    if abs(yards) >= 20:
        offense_stats["explosives"] += 1

def _process_pass_play(payload: Dict, offense_stats: Dict, defense_stats: Dict, yards: int) -> None:
    """Process a pass play with advanced fields."""
    
    offense_stats["pass_attempts"] += 1
    
    # Basic pass stats
    is_complete = payload.get("complete", False)
    is_sack = payload.get("is_sack", False)
    
    if is_sack:
        offense_stats["sacks_allowed"] += 1.0
        offense_stats["sack_yards_allowed"] += abs(yards)
        defense_stats["sacks"] += 1.0
    elif is_complete:
        offense_stats["pass_completions"] += 1
        offense_stats["pass_yards"] += yards
        defense_stats["completions_allowed"] += 1
        defense_stats["yards_allowed"] += yards
        
        # YAC calculation
        yac = payload.get("yac", int(yards * 0.35))
        defense_stats["yac_allowed"] += yac
    else:
        # Incomplete pass
        defense_stats["targets_faced"] += 1
        
        # Check for pass breakup
        if payload.get("is_pd", False):
            defense_stats["pbus"] += 1
    
    # Process advanced PBP fields
    _process_advanced_pass_fields(payload, offense_stats, defense_stats)

def _process_run_play(payload: Dict, offense_stats: Dict, defense_stats: Dict, yards: int) -> None:
    """Process a run play with advanced fields."""
    
    offense_stats["rush_attempts"] += 1
    offense_stats["rush_yards"] += yards
    
    # Process advanced PBP fields
    _process_advanced_run_fields(payload, offense_stats, defense_stats)

def _process_advanced_pass_fields(payload: Dict, offense_stats: Dict, defense_stats: Dict) -> None:
    """Process advanced PBP fields for pass plays."""
    
    # Offensive line responsibility
    ol_block = payload.get("ol_block", {})
    if ol_block:
        outcome = ol_block.get("outcome")
        if outcome == "win":
            offense_stats["pass_block_wins"] += 1
        elif outcome in ["pressure", "hit", "sack"]:
            offense_stats["pressures_allowed"] += 1
            if outcome == "hit":
                offense_stats["qb_hits_allowed"] += 1
    
    # Front-seven attribution
    pressures_by_ids = payload.get("pressures_by_ids", [])
    defense_stats["pressures"] += len(pressures_by_ids)
    
    hits_by_ids = payload.get("hits_by_ids", [])
    defense_stats["qb_hits"] += len(hits_by_ids)
    
    sack_split = payload.get("sack_split", [])
    for defender_id, share in sack_split:
        defense_stats["sacks"] += share
    
    # Coverage / Secondary
    coverage_result = payload.get("coverage_result")
    if coverage_result == "intercepted":
        defense_stats["interceptions"] += 1
        defense_stats["int_yards"] += payload.get("yards", 0)
    
    # Missed tackles
    missed_tackle_by_ids = payload.get("missed_tackle_by_ids", [])
    defense_stats["missed_tackles"] += len(missed_tackle_by_ids)

def _process_advanced_run_fields(payload: Dict, offense_stats: Dict, defense_stats: Dict) -> None:
    """Process advanced PBP fields for run plays."""
    
    # Offensive line responsibility
    ol_block = payload.get("ol_block", {})
    if ol_block:
        outcome = ol_block.get("outcome")
        if outcome == "win":
            offense_stats["run_block_wins"] += 1
        elif outcome == "tfl":
            offense_stats["tfl_allowed"] += 1
            defense_stats["tfl"] += 1
    
    # Tackling attribution
    tackler_id = payload.get("tackler_id")
    if tackler_id:
        defense_stats["tackles_solo"] += 1
    
    assist_tackler_id = payload.get("assist_tackler_id")
    if assist_tackler_id:
        defense_stats["tackles_assist"] += 1
    
    # Missed tackles
    missed_tackle_by_ids = payload.get("missed_tackle_by_ids", [])
    defense_stats["missed_tackles"] += len(missed_tackle_by_ids)
    
    # Broken tackles
    broken_tackle = payload.get("broken_tackle", 0)
    if broken_tackle > 0:
        offense_stats["broken_tackles"] += broken_tackle

def _process_punt_event(event: GameEvent, payload: Dict, offense_stats: Dict, defense_stats: Dict) -> None:
    """Process a punt event with special teams fields."""
    
    offense_stats["punts"] += 1
    offense_stats["snaps_st"] += 1
    defense_stats["snaps_st"] += 1
    
    punt_yards = payload.get("yards", 0)
    offense_stats["punt_yards"] += punt_yards
    
    # Special teams advanced fields
    hang_time_ms = payload.get("hang_time_ms", 0)
    if hang_time_ms > 0:
        offense_stats["hang_time_avg"] = hang_time_ms / 1000.0  # Convert to seconds
    
    net_yards = payload.get("net_yards", punt_yards)
    offense_stats["punt_net_avg"] = net_yards
    
    in_20 = payload.get("in_20", False)
    if in_20:
        offense_stats["punts_in_20"] += 1
    
    fair_catch = payload.get("fair_catch", False)
    if fair_catch:
        defense_stats["fair_catches"] += 1
    
    blocked = payload.get("blocked", False)
    if blocked:
        offense_stats["blocked_kicks"] += 1
        defense_stats["blocked_kicks"] += 1
    
    # Return yards
    return_yards = payload.get("return_yards", 0)
    if return_yards > 0:
        defense_stats["punt_returns"] += 1
        defense_stats["punt_return_yards"] += return_yards
        defense_stats["return_avg"] = defense_stats["punt_return_yards"] / defense_stats["punt_returns"]

def _process_turnover_event(event: GameEvent, payload: Dict, offense_stats: Dict, defense_stats: Dict) -> None:
    """Process a turnover event."""
    
    offense_stats["turnovers"] += 1
    
    turnover_type = payload.get("type", "fumble")
    if turnover_type == "interception":
        offense_stats["pass_int"] += 1
        defense_stats["interceptions"] += 1
        defense_stats["int_yards"] += payload.get("return_yards", 0)
    elif turnover_type == "fumble":
        offense_stats["fumbles"] += 1
        offense_stats["fumbles_lost"] += 1
        defense_stats["forced_fumbles"] += 1
        defense_stats["fumble_recoveries"] += 1

def _process_td_event(event: GameEvent, payload: Dict, offense_stats: Dict, defense_stats: Dict) -> None:
    """Process a touchdown event."""
    
    offense_stats["total_td"] += 1
    
    td_type = payload.get("type", "pass")
    if td_type == "pass":
        offense_stats["pass_td"] += 1
        defense_stats["td_allowed"] += 1
    elif td_type == "rush":
        offense_stats["rush_td"] += 1
        defense_stats["td_allowed"] += 1

def _process_fg_event(event: GameEvent, payload: Dict, offense_stats: Dict, defense_stats: Dict) -> None:
    """Process a field goal event."""
    
    offense_stats["fg_attempts"] += 1
    offense_stats["snaps_st"] += 1
    defense_stats["snaps_st"] += 1
    
    distance = payload.get("distance", 0)
    offense_stats["fg_yards"] += distance
    
    made = payload.get("good", False)
    if made:
        offense_stats["fg_made"] += 1
    
    # Special teams advanced fields
    kick_distance = payload.get("kick_distance", distance)
    offense_stats["kick_distance_avg"] = kick_distance
    
    blocked = payload.get("blocked", False)
    if blocked:
        offense_stats["blocked_kicks"] += 1
        defense_stats["blocked_kicks"] += 1

def _process_xp_event(event: GameEvent, payload: Dict, offense_stats: Dict, defense_stats: Dict) -> None:
    """Process an extra point event."""
    
    offense_stats["xp_attempts"] += 1
    offense_stats["snaps_st"] += 1
    defense_stats["snaps_st"] += 1
    
    made = payload.get("good", False)
    if made:
        offense_stats["xp_made"] += 1
    
    # Special teams advanced fields
    blocked = payload.get("blocked", False)
    if blocked:
        offense_stats["blocked_kicks"] += 1
        defense_stats["blocked_kicks"] += 1

def _process_safety_event(event: GameEvent, payload: Dict, offense_stats: Dict, defense_stats: Dict) -> None:
    """Process a safety event."""
    
    # Safety is scored by the defense
    defense_stats["total_td"] += 1  # Safety counts as defensive TD

def _update_situational_flags(stats: Dict, down: int, to_go: int, yardline: int, quarter: int, clock_seconds: int) -> None:
    """Update situational split flags."""
    
    # Down flags
    if down == 3:
        stats["third_down_attempts"] += 1
    elif down == 4:
        stats["fourth_down_attempts"] += 1
    
    # Field position flags
    if yardline <= 20:
        stats["red_zone_attempts"] += 1
    if yardline <= 10:
        stats["goal_to_go_attempts"] += 1
    
    # Time flags
    if quarter >= 4 and clock_seconds <= 120:
        stats["two_minute_plays"] += 1
    if quarter >= 4 and clock_seconds <= 60:
        stats["hurry_up_plays"] += 1

def _calculate_derived_metrics(stats: Dict) -> None:
    """Calculate derived metrics from basic stats."""
    
    # Success rate (simplified)
    total_plays = stats["pass_attempts"] + stats["rush_attempts"]
    if total_plays > 0:
        successful_plays = stats["pass_completions"] + stats["rush_attempts"]  # Simplified
        stats["success_rate"] = (successful_plays / total_plays) * 100
    
    # Passer rating against (simplified)
    if stats["targets_faced"] > 0:
        completion_pct = stats["completions_allowed"] / stats["targets_faced"]
        ypa = stats["yards_allowed"] / stats["targets_faced"]
        td_pct = stats["td_allowed"] / stats["targets_faced"]
        int_pct = stats["interceptions"] / stats["targets_faced"]
        
        # Simplified passer rating formula
        stats["passer_rating_against"] = max(0, min(158.3, 
            ((completion_pct - 0.3) * 5 + 
             (ypa - 3) * 0.25 + 
             td_pct * 20 + 
             (2.375 - int_pct * 25)) * 100 / 6))

def _save_team_game_stats(s: Session, stats: Dict) -> None:
    """Save team game stats to database."""
    
    # Check if stats already exist
    existing = s.exec(
        select(TeamGameStats).where(
            TeamGameStats.game_id == stats["game_id"],
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

def _save_player_game_stats(s: Session, stats: Dict) -> None:
    """Save player game stats to database."""
    
    # Check if stats already exist
    existing = s.exec(
        select(PlayerGameStats).where(
            PlayerGameStats.game_id == stats["game_id"],
            PlayerGameStats.player_id == stats["player_id"]
        )
    ).first()
    
    if existing:
        # Update existing stats
        for key, value in stats.items():
            if key not in ["game_id", "player_id", "team_id"]:
                setattr(existing, key, value)
    else:
        # Create new stats
        player_game_stats = PlayerGameStats(**stats)
        s.add(player_game_stats)

def _parse_clock_to_seconds(clock: str) -> int:
    """Parse MM:SS clock format to seconds."""
    try:
        parts = clock.split(":")
        minutes = int(parts[0])
        seconds = int(parts[1])
        return minutes * 60 + seconds
    except:
        return 0

def rollup_season_stats_advanced(s: Session, season: int) -> bool:
    """Advanced rollup stats for all games in a season."""
    
    try:
        # Get all games for the season
        games = s.exec(
            select(Game).where(Game.season == season)
        ).all()
        
        if not games:
            logger.warning(f"No games found for season {season}")
            return False
        
        success_count = 0
        for game in games:
            try:
                if rollup_game_stats_advanced(s, game.id):
                    success_count += 1
            except Exception as e:
                logger.error(f"Error rolling up advanced stats for game {game.id}: {e}")
                continue
        
        logger.info(f"Successfully rolled up advanced stats for {success_count}/{len(games)} games in season {season}")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"Error rolling up advanced stats for season {season}: {e}")
        return False

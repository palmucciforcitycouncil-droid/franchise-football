from __future__ import annotations
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.core.db import session_scope
from app.models.stats import PlayerGameStats, TeamGameStats
from app.models.sim_models import Game, GameEvent
import json
import logging

logger = logging.getLogger(__name__)

def validate_game_totals(game_id: int) -> List[str]:
    """
    Validate game statistics for consistency and accuracy.
    
    Args:
        game_id: The game ID to validate
        
    Returns:
        List of validation error messages. Empty list means all checks passed.
    """
    errors: List[str] = []
    
    with session_scope() as session:
        # Get game info
        game = session.get(Game, game_id)
        if not game:
            errors.append(f"Game {game_id} not found")
            return errors
        
        # Get team stats for this game
        team_stats = session.exec(
            select(TeamGameStats).where(TeamGameStats.game_id == game_id)
        ).all()
        
        if len(team_stats) != 2:
            errors.append(f"Expected 2 team stats records, found {len(team_stats)}")
            return errors
        
        home_team_stat = next((ts for ts in team_stats if ts.team_id == game.home_team_id), None)
        away_team_stat = next((ts for ts in team_stats if ts.team_id == game.away_team_id), None)
        
        if not home_team_stat or not away_team_stat:
            errors.append("Missing team stats for home or away team")
            return errors
        
        # Get player stats for this game
        player_stats = session.exec(
            select(PlayerGameStats).where(PlayerGameStats.game_id == game_id)
        ).all()
        
        # Group player stats by team
        home_player_stats = [ps for ps in player_stats if ps.team_id == game.home_team_id]
        away_player_stats = [ps for ps in player_stats if ps.team_id == game.away_team_id]
        
        # Validate team totals match sum of player totals
        errors.extend(_validate_team_player_totals(home_team_stat, home_player_stats, "Home"))
        errors.extend(_validate_team_player_totals(away_team_stat, away_player_stats, "Away"))
        
        # Validate sack yards are subtracted correctly
        errors.extend(_validate_sack_yards(home_team_stat, home_player_stats, "Home"))
        errors.extend(_validate_sack_yards(away_team_stat, away_player_stats, "Away"))
        
        # Validate half-sack consistency
        errors.extend(_validate_half_sacks(home_player_stats, "Home"))
        errors.extend(_validate_half_sacks(away_player_stats, "Away"))
        
        # Validate denominators are safe
        errors.extend(_validate_denominators(home_player_stats, "Home"))
        errors.extend(_validate_denominators(away_player_stats, "Away"))
        
        # Validate drive/quarter/final scores reconcile
        errors.extend(_validate_score_reconciliation(game, session))
        
        # Validate no negative snaps
        errors.extend(_validate_negative_snaps(home_player_stats, "Home"))
        errors.extend(_validate_negative_snaps(away_player_stats, "Away"))
    
    return errors

def _validate_team_player_totals(team_stat: TeamGameStats, player_stats: List[PlayerGameStats], 
                                 team_name: str) -> List[str]:
    """Validate that team totals equal sum of player totals."""
    errors: List[str] = []
    
    # Sum player stats
    player_totals = {
        'snaps_offense': sum(ps.snaps_offense for ps in player_stats),
        'snaps_defense': sum(ps.snaps_defense for ps in player_stats),
        'snaps_st': sum(ps.snaps_st for ps in player_stats),
        'pass_attempts': sum(ps.pass_attempts for ps in player_stats),
        'pass_completions': sum(ps.pass_completions for ps in player_stats),
        'pass_yards': sum(ps.pass_yards for ps in player_stats),
        'pass_td': sum(ps.pass_td for ps in player_stats),
        'pass_int': sum(ps.pass_int for ps in player_stats),
        'rush_attempts': sum(ps.rush_attempts for ps in player_stats),
        'rush_yards': sum(ps.rush_yards for ps in player_stats),
        'rush_td': sum(ps.rush_td for ps in player_stats),
        'total_yards': sum(ps.pass_yards + ps.rush_yards for ps in player_stats),
        'total_td': sum(ps.pass_td + ps.rush_td for ps in player_stats),
        'turnovers': sum(ps.fumbles_lost + ps.pass_int for ps in player_stats),
        'tackles_solo': sum(ps.tackles_solo for ps in player_stats),
        'tackles_assist': sum(ps.tackles_assist for ps in player_stats),
        'sacks': sum(ps.sacks_defense for ps in player_stats),
        'interceptions': sum(ps.interceptions for ps in player_stats),
        'forced_fumbles': sum(ps.forced_fumbles for ps in player_stats),
        'fumble_recoveries': sum(ps.fumble_recoveries for ps in player_stats),
        'penalties': sum(ps.penalties for ps in player_stats),
        'penalty_yards': sum(ps.penalty_yards for ps in player_stats),
    }
    
    # Compare with team stats (with tolerance for half-sacks)
    for field, player_total in player_totals.items():
        team_value = getattr(team_stat, field, 0)
        
        if field == 'sacks':
            # Allow 0.5 tolerance for half-sack rounding
            if abs(team_value - player_total) > 0.5:
                errors.append(f"{team_name} team {field}: {team_value} != player sum: {player_total}")
        else:
            if team_value != player_total:
                errors.append(f"{team_name} team {field}: {team_value} != player sum: {player_total}")
    
    return errors

def _validate_sack_yards(team_stat: TeamGameStats, player_stats: List[PlayerGameStats], 
                        team_name: str) -> List[str]:
    """Validate that sack yards are subtracted correctly from team passing yards."""
    errors: List[str] = []
    
    # Calculate total sack yards from players
    total_sack_yards = sum(abs(ps.sack_yards) for ps in player_stats if ps.sack_yards < 0)
    
    # Team sack yards allowed should match
    if team_stat.sack_yards_allowed != total_sack_yards:
        errors.append(f"{team_name} team sack_yards_allowed: {team_stat.sack_yards_allowed} != player sum: {total_sack_yards}")
    
    # Team passing yards should account for sacks
    # This is more complex as it depends on how sacks are handled in the rollup
    # For now, just check that sack yards are reasonable
    if team_stat.sack_yards_allowed > team_stat.pass_yards:
        errors.append(f"{team_name} team sack yards ({team_stat.sack_yards_allowed}) exceed pass yards ({team_stat.pass_yards})")
    
    return errors

def _validate_half_sacks(player_stats: List[PlayerGameStats], team_name: str) -> List[str]:
    """Validate half-sack consistency."""
    errors: List[str] = []
    
    # Check that half-sacks are valid (0, 0.5, 1.0, 1.5, etc.)
    for ps in player_stats:
        if ps.sacks_defense < 0:
            errors.append(f"{team_name} player {ps.player_id} has negative sacks: {ps.sacks_defense}")
        elif ps.sacks_defense != round(ps.sacks_defense * 2) / 2:
            errors.append(f"{team_name} player {ps.player_id} has invalid half-sack: {ps.sacks_defense}")
    
    return errors

def _validate_denominators(player_stats: List[PlayerGameStats], team_name: str) -> List[str]:
    """Validate that denominators are safe for rate calculations."""
    errors: List[str] = []
    
    for ps in player_stats:
        # Check completion percentage
        if ps.pass_attempts == 0 and ps.pass_completions > 0:
            errors.append(f"{team_name} player {ps.player_id} has completions but no attempts")
        
        # Check rushing stats
        if ps.rush_attempts == 0 and ps.rush_yards > 0:
            errors.append(f"{team_name} player {ps.player_id} has rush yards but no attempts")
        
        # Check receiving stats
        if ps.targets == 0 and ps.receptions > 0:
            errors.append(f"{team_name} player {ps.player_id} has receptions but no targets")
        
        # Check kicking stats
        if ps.fg_attempts == 0 and ps.fg_made > 0:
            errors.append(f"{team_name} player {ps.player_id} has FG made but no attempts")
        
        if ps.xp_attempts == 0 and ps.xp_made > 0:
            errors.append(f"{team_name} player {ps.player_id} has XP made but no attempts")
    
    return errors

def _validate_score_reconciliation(game: Game, session: Session) -> List[str]:
    """Validate that drive/quarter/final scores reconcile."""
    errors: List[str] = []
    
    # Get all scoring events from PBP
    scoring_events = session.exec(
        select(GameEvent).where(
            GameEvent.game_id == game.id,
            GameEvent.event_type.in_(["td", "fg", "safety"])
        )
    ).all()
    
    # Calculate total points from events
    home_points_from_events = 0
    away_points_from_events = 0
    
    for event in scoring_events:
        try:
            event_data = json.loads(event.description or "{}")
            team = event_data.get("team")
            
            if event.event_type == "td":
                points = 7  # TD + XP
            elif event.event_type == "fg":
                points = 3
            elif event.event_type == "safety":
                points = 2
            else:
                continue
            
            if team == "home":
                home_points_from_events += points
            elif team == "away":
                away_points_from_events += points
        
        except Exception as e:
            logger.warning(f"Error parsing scoring event {event.id}: {e}")
            continue
    
    # Compare with final score
    if home_points_from_events != game.home_score:
        errors.append(f"Home team points from events ({home_points_from_events}) != final score ({game.home_score})")
    
    if away_points_from_events != game.away_score:
        errors.append(f"Away team points from events ({away_points_from_events}) != final score ({game.away_score})")
    
    return errors

def _validate_negative_snaps(player_stats: List[PlayerGameStats], team_name: str) -> List[str]:
    """Validate that snap counts are not negative."""
    errors: List[str] = []
    
    for ps in player_stats:
        if ps.snaps_offense < 0:
            errors.append(f"{team_name} player {ps.player_id} has negative offensive snaps: {ps.snaps_offense}")
        
        if ps.snaps_defense < 0:
            errors.append(f"{team_name} player {ps.player_id} has negative defensive snaps: {ps.snaps_defense}")
        
        if ps.snaps_st < 0:
            errors.append(f"{team_name} player {ps.player_id} has negative special teams snaps: {ps.snaps_st}")
    
    return errors

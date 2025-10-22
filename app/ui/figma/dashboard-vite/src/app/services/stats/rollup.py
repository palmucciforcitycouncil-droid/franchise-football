"""
Advanced stats rollup service for processing PBP events into game stats.
Handles OL/DL attribution, coverage, ST net/in-20, situational splits.
"""

from typing import Dict, List, Optional, Tuple
from sqlmodel import Session, select
from app.models.pbp_event import PBPEvent
from app.models.stats_models import PlayerGameStats, TeamGameStats
from app.services.stats.helpers import (
    calculate_completion_percentage,
    calculate_passer_rating,
    calculate_yards_per_attempt,
    calculate_yards_per_carry,
    calculate_yards_per_reception,
    calculate_net_punt_average,
    calculate_field_goal_percentage,
    calculate_third_down_percentage,
    calculate_red_zone_percentage,
    safe_divide
)


def rollup_game_stats(game_id: int, session: Session) -> Dict[str, int]:
    """
    Roll up all PBP events for a game into player and team stats.
    Returns summary of records created/updated.
    """
    # Get all PBP events for the game
    events = session.exec(
        select(PBPEvent).where(PBPEvent.game_id == game_id)
    ).all()
    
    if not events:
        raise ValueError(f"No PBP events found for game {game_id}")
    
    # Initialize stat accumulators
    player_stats: Dict[int, PlayerGameStats] = {}
    team_stats: Dict[int, TeamGameStats] = {}
    
    # Process each event
    for event in events:
        _process_event(event, player_stats, team_stats, session)
    
    # Save all stats
    created_count = 0
    updated_count = 0
    
    for player_stat in player_stats.values():
        existing = session.exec(
            select(PlayerGameStats).where(
                PlayerGameStats.game_id == game_id,
                PlayerGameStats.player_id == player_stat.player_id
            )
        ).first()
        
        if existing:
            # Update existing
            for field in player_stat.__fields__:
                if field not in ['id', 'created_at', 'updated_at']:
                    setattr(existing, field, getattr(player_stat, field))
            updated_count += 1
        else:
            # Create new
            session.add(player_stat)
            created_count += 1
    
    for team_stat in team_stats.values():
        existing = session.exec(
            select(TeamGameStats).where(
                TeamGameStats.game_id == game_id,
                TeamGameStats.team_id == team_stat.team_id
            )
        ).first()
        
        if existing:
            # Update existing
            for field in team_stat.__fields__:
                if field not in ['id', 'created_at', 'updated_at']:
                    setattr(existing, field, getattr(team_stat, field))
            updated_count += 1
        else:
            # Create new
            session.add(team_stat)
            created_count += 1
    
    session.commit()
    
    return {
        "game_id": game_id,
        "events_processed": len(events),
        "player_stats_created": created_count,
        "player_stats_updated": updated_count,
        "team_stats_created": len([s for s in team_stats.values() if not s.id]),
        "team_stats_updated": len([s for s in team_stats.values() if s.id])
    }


def _process_event(event: PBPEvent, player_stats: Dict[int, PlayerGameStats], 
                  team_stats: Dict[int, TeamGameStats], session: Session):
    """Process a single PBP event and update stat accumulators."""
    
    # Skip garbage time plays
    if event.is_garbage_time_excluded:
        return
    
    # Get or create player stats for involved players
    involved_players = _get_involved_players(event)
    for player_id in involved_players:
        if player_id not in player_stats:
            player_stats[player_id] = _create_player_game_stats(event, player_id)
    
    # Get or create team stats
    for team_id in [event.offense_team_id, event.defense_team_id]:
        if team_id not in team_stats:
            team_stats[team_id] = _create_team_game_stats(event, team_id)
    
    # Process based on play type
    if event.play_type == "pass":
        _process_pass_play(event, player_stats, team_stats)
    elif event.play_type == "run":
        _process_run_play(event, player_stats, team_stats)
    elif event.play_type == "punt":
        _process_punt_play(event, player_stats, team_stats)
    elif event.play_type == "fg":
        _process_fg_play(event, player_stats, team_stats)
    elif event.play_type == "kickoff":
        _process_kickoff_play(event, player_stats, team_stats)
    
    # Process situational splits
    _process_situational_splits(event, player_stats, team_stats)
    
    # Process penalties
    if event.penalty:
        _process_penalty(event, player_stats, team_stats)


def _get_involved_players(event: PBPEvent) -> List[int]:
    """Get all player IDs involved in the event."""
    players = []
    
    # Core players
    if event.passer_id:
        players.append(event.passer_id)
    if event.target_id:
        players.append(event.target_id)
    if event.rusher_id:
        players.append(event.rusher_id)
    if event.receiver_id:
        players.append(event.receiver_id)
    if event.kicker_id:
        players.append(event.kicker_id)
    if event.punter_id:
        players.append(event.punter_id)
    if event.returner_id:
        players.append(event.returner_id)
    
    # Defensive players
    if event.intercepted_by_id:
        players.append(event.intercepted_by_id)
    if event.forced_by_id:
        players.append(event.forced_by_id)
    if event.recovered_by_id:
        players.append(event.recovered_by_id)
    if event.pass_breakup_by_id:
        players.append(event.pass_breakup_by_id)
    if event.targeted_db_id:
        players.append(event.targeted_db_id)
    if event.blocked_by_id:
        players.append(event.blocked_by_id)
    
    # Pressure/hit/sack attribution
    players.extend(event.pressures_by_ids)
    players.extend(event.hits_by_ids)
    players.extend([player_id for player_id, _ in event.sack_split])
    players.extend(event.tfl_by_ids)
    players.extend(event.missed_tackle_by_ids)
    
    return list(set(players))  # Remove duplicates


def _create_player_game_stats(event: PBPEvent, player_id: int) -> PlayerGameStats:
    """Create a new PlayerGameStats record."""
    return PlayerGameStats(
        game_id=event.game_id,
        player_id=player_id,
        team_id=_get_player_team_id(player_id, event),
        snaps_offense=0,
        snaps_defense=0,
        snaps_special_teams=0,
        # Initialize all stat fields to 0
        pass_attempts=0, pass_completions=0, pass_yards=0, pass_touchdowns=0,
        interceptions=0, sacks_taken=0.0, sack_yards=0, qb_hits=0, pressures_faced=0,
        rush_attempts=0, rush_yards=0, rush_touchdowns=0, fumbles=0, fumbles_lost=0,
        targets=0, receptions=0, receiving_yards=0, receiving_touchdowns=0,
        drops=0, yards_after_catch=0,
        tackles=0, tackles_for_loss=0, sacks=0.0, quarterback_hits=0, pressures=0,
        pass_deflections=0, interceptions_caught=0, forced_fumbles=0, fumble_recoveries=0,
        targets_against=0, completions_allowed=0, yards_allowed=0, touchdowns_allowed=0,
        passes_defended=0,
        field_goals_made=0, field_goals_attempted=0, extra_points_made=0, extra_points_attempted=0,
        punts=0, punt_yards=0, punt_net_yards=0, punts_in_20=0,
        kickoff_returns=0, kickoff_return_yards=0, punt_returns=0, punt_return_yards=0,
        sacks_allowed=0.0, pressures_allowed=0, qb_hits_allowed=0,
        third_down_conversions=0, third_down_attempts=0,
        fourth_down_conversions=0, fourth_down_attempts=0,
        red_zone_touchdowns=0, red_zone_attempts=0,
        goal_to_go_touchdowns=0, goal_to_go_attempts=0,
        two_minute_touchdowns=0, two_minute_attempts=0
    )


def _create_team_game_stats(event: PBPEvent, team_id: int) -> TeamGameStats:
    """Create a new TeamGameStats record."""
    return TeamGameStats(
        game_id=event.game_id,
        team_id=team_id,
        is_home_team=team_id == event.offense_team_id,  # Simplified
        points_scored=0,
        total_yards=0, passing_yards=0, rushing_yards=0,
        turnovers_committed=0, turnovers_forced=0,
        field_goals_made=0, field_goals_attempted=0,
        punts=0, punt_net_yards=0, punts_in_20=0,
        third_down_conversions=0, third_down_attempts=0,
        fourth_down_conversions=0, fourth_down_attempts=0,
        red_zone_touchdowns=0, red_zone_attempts=0
    )


def _get_player_team_id(player_id: int, event: PBPEvent) -> int:
    """Determine which team a player belongs to based on the event."""
    # This is simplified - in reality you'd query the player's team
    # For now, assume players are on offense team
    return event.offense_team_id


def _process_pass_play(event: PBPEvent, player_stats: Dict[int, PlayerGameStats], 
                      team_stats: Dict[int, TeamGameStats]):
    """Process a passing play."""
    if event.passer_id and event.passer_id in player_stats:
        ps = player_stats[event.passer_id]
        ps.pass_attempts += 1
        ps.pass_yards += event.yards_gained
        ps.sacks_taken += 1.0 if event.sack else 0.0
        ps.sack_yards += event.sack_yards if event.sack else 0
        ps.qb_hits += 1 if event.qb_hit else 0
        ps.pressures_faced += 1 if event.pressure else 0
        
        if event.completed:
            ps.pass_completions += 1
        if event.is_scoring_play and event.points_offense > 0:
            ps.pass_touchdowns += 1
        if event.interception:
            ps.interceptions += 1
    
    if event.target_id and event.target_id in player_stats:
        ps = player_stats[event.target_id]
        ps.targets += 1
        if event.completed:
            ps.receptions += 1
            ps.receiving_yards += event.yards_gained
            ps.yards_after_catch += event.yac
        if event.is_scoring_play and event.points_offense > 0:
            ps.receiving_touchdowns += 1
    
    # Process defensive stats
    if event.intercepted_by_id and event.intercepted_by_id in player_stats:
        ps = player_stats[event.intercepted_by_id]
        ps.interceptions_caught += 1
    
    if event.pass_breakup_by_id and event.pass_breakup_by_id in player_stats:
        ps = player_stats[event.pass_breakup_by_id]
        ps.pass_deflections += 1
    
    # Process pressure attribution
    for player_id in event.pressures_by_ids:
        if player_id in player_stats:
            player_stats[player_id].pressures += 1
    
    for player_id in event.hits_by_ids:
        if player_id in player_stats:
            player_stats[player_id].quarterback_hits += 1
    
    # Process sack attribution with shares
    for player_id, share in event.sack_split:
        if player_id in player_stats:
            player_stats[player_id].sacks += share


def _process_run_play(event: PBPEvent, player_stats: Dict[int, PlayerGameStats], 
                     team_stats: Dict[int, TeamGameStats]):
    """Process a running play."""
    if event.rusher_id and event.rusher_id in player_stats:
        ps = player_stats[event.rusher_id]
        ps.rush_attempts += 1
        ps.rush_yards += event.yards_gained
        if event.is_scoring_play and event.points_offense > 0:
            ps.rush_touchdowns += 1
    
    # Process TFL attribution
    for player_id in event.tfl_by_ids:
        if player_id in player_stats:
            player_stats[player_id].tackles_for_loss += 1
    
    # Process missed tackles
    for player_id in event.missed_tackle_by_ids:
        if player_id in player_stats:
            # Missed tackles could be tracked separately
            pass


def _process_punt_play(event: PBPEvent, player_stats: Dict[int, PlayerGameStats], 
                      team_stats: Dict[int, TeamGameStats]):
    """Process a punt play."""
    if event.punter_id and event.punter_id in player_stats:
        ps = player_stats[event.punter_id]
        ps.punts += 1
        ps.punt_yards += event.kick_distance or 0
        ps.punt_net_yards += event.net_yards or 0
        ps.punts_in_20 += 1 if event.in_20 else 0
    
    if event.returner_id and event.returner_id in player_stats:
        ps = player_stats[event.returner_id]
        ps.punt_returns += 1
        ps.punt_return_yards += event.yards_gained


def _process_fg_play(event: PBPEvent, player_stats: Dict[int, PlayerGameStats], 
                    team_stats: Dict[int, TeamGameStats]):
    """Process a field goal play."""
    if event.kicker_id and event.kicker_id in player_stats:
        ps = player_stats[event.kicker_id]
        ps.field_goals_attempted += 1
        if event.is_scoring_play and event.points_offense > 0:
            ps.field_goals_made += 1


def _process_kickoff_play(event: PBPEvent, player_stats: Dict[int, PlayerGameStats], 
                        team_stats: Dict[int, TeamGameStats]):
    """Process a kickoff play."""
    if event.returner_id and event.returner_id in player_stats:
        ps = player_stats[event.returner_id]
        ps.kickoff_returns += 1
        ps.kickoff_return_yards += event.yards_gained


def _process_situational_splits(event: PBPEvent, player_stats: Dict[int, PlayerGameStats], 
                               team_stats: Dict[int, TeamGameStats]):
    """Process situational split flags."""
    involved_players = _get_involved_players(event)
    
    for player_id in involved_players:
        if player_id in player_stats:
            ps = player_stats[player_id]
            
            if event.is_third_down:
                ps.third_down_attempts += 1
                if event.yards_gained >= event.distance:
                    ps.third_down_conversions += 1
            
            if event.is_fourth_down:
                ps.fourth_down_attempts += 1
                if event.yards_gained >= event.distance:
                    ps.fourth_down_conversions += 1
            
            if event.is_red_zone:
                ps.red_zone_attempts += 1
                if event.is_scoring_play and event.points_offense > 0:
                    ps.red_zone_touchdowns += 1
            
            if event.is_goal_to_go:
                ps.goal_to_go_attempts += 1
                if event.is_scoring_play and event.points_offense > 0:
                    ps.goal_to_go_touchdowns += 1
            
            if event.is_two_minute:
                ps.two_minute_attempts += 1
                if event.is_scoring_play and event.points_offense > 0:
                    ps.two_minute_touchdowns += 1


def _process_penalty(event: PBPEvent, player_stats: Dict[int, PlayerGameStats], 
                    team_stats: Dict[int, TeamGameStats]):
    """Process penalty information."""
    if event.penalty and 'player_id' in event.penalty:
        player_id = event.penalty['player_id']
        if player_id in player_stats:
            # Penalty stats could be tracked separately
            pass

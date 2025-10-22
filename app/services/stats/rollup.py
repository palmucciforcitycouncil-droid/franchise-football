from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from app.core.db import session_scope
from app.models.sim_models import GameEvent, Game
from app.models.stats import PlayerGameStats, TeamGameStats
from app.models.pbp_event import PBPEvent, PlayType, TurnoverType, KickType
import json
import logging

logger = logging.getLogger(__name__)

def rollup_game_stats(game_id: int) -> None:
    """
    Roll up player and team statistics for a single game from PBP events.
    
    Args:
        game_id: The game ID to process
        
    Raises:
        ValueError: If game not found or invalid PBP data
    """
    with session_scope() as session:
        # Get game info
        game = session.get(Game, game_id)
        if not game:
            raise ValueError(f"Game {game_id} not found")
        
        # Get all PBP events for this game, ordered by quarter and clock
        events_query = select(GameEvent).where(
            GameEvent.game_id == game_id
        ).order_by(
            GameEvent.quarter,
            GameEvent.clock
        )
        events = session.exec(events_query).all()
        
        if not events:
            raise ValueError(f"No PBP events found for game {game_id}")
        
        # Initialize player and team stat accumulators
        player_stats: Dict[int, PlayerGameStats] = {}
        team_stats: Dict[int, TeamGameStats] = {}
        
        # Initialize team stats for both teams
        home_team_id = game.home_team_id
        away_team_id = game.away_team_id
        
        team_stats[home_team_id] = TeamGameStats(
            game_id=game_id,
            team_id=home_team_id
        )
        team_stats[away_team_id] = TeamGameStats(
            game_id=game_id,
            team_id=away_team_id
        )
        
        # Process each event
        for event in events:
            try:
                # Parse event description as JSON
                event_data = json.loads(event.description or "{}")
                
                # Convert to PBPEvent for validation
                pbp_event = _convert_to_pbp_event(event, event_data)
                
                # Process the event
                _process_event(pbp_event, player_stats, team_stats, session)
                
            except Exception as e:
                logger.warning(f"Error processing event {event.id}: {e}")
                continue
        
        # Delete existing stats for this game
        session.exec(delete(PlayerGameStats).where(PlayerGameStats.game_id == game_id))
        session.exec(delete(TeamGameStats).where(TeamGameStats.game_id == game_id))
        
        # Save all stats
        for player_stat in player_stats.values():
            session.add(player_stat)
        
        for team_stat in team_stats.values():
            session.add(team_stat)
        
        session.commit()
        logger.info(f"Successfully rolled up stats for game {game_id}")

def _convert_to_pbp_event(event: GameEvent, event_data: Dict) -> PBPEvent:
    """Convert GameEvent to PBPEvent for processing"""
    
    # Map event_type to PlayType
    play_type_map = {
        "play": PlayType.PASS if event_data.get("play") == "pass" else PlayType.RUSH,
        "punt": PlayType.PUNT,
        "fg": PlayType.FIELD_GOAL,
        "td": PlayType.TOUCHDOWN,
        "turnover": PlayType.TURNOVER,
        "safety": PlayType.SAFETY,
        "final": PlayType.FINAL
    }
    
    play_type = play_type_map.get(event.event_type, PlayType.PASS)
    
    # Extract basic info
    offense_team_id = event.offense_team_id or event_data.get("team_id")
    defense_team_id = event.defense_team_id
    
    # Determine team IDs from game context
    if event_data.get("team") == "home":
        offense_team_id = event.game.home_team_id
        defense_team_id = event.game.away_team_id
    elif event_data.get("team") == "away":
        offense_team_id = event.game.away_team_id
        defense_team_id = event.game.home_team_id
    
    return PBPEvent(
        game_id=event.game_id,
        drive_id=event.drive_index,
        play_id=event.play_index,
        quarter=event.quarter,
        clock=event.clock or "00:00",
        offense_team_id=offense_team_id,
        defense_team_id=defense_team_id,
        down=event.down,
        distance=event.distance,
        yardline=event.yard_line,
        play_type=play_type,
        yards_gained=event.yards_gained or 0,
        is_scoring_play=event_data.get("is_scoring_play", False),
        points_offense=event.score_home if offense_team_id == event.game.home_team_id else event.score_away,
        points_defense=event.score_away if offense_team_id == event.game.home_team_id else event.score_home,
        
        # Passing stats
        passer_id=event_data.get("passer_id"),
        target_id=event_data.get("target_id"),
        completed=event_data.get("complete"),
        air_yards=event_data.get("air_yards"),
        yac=event_data.get("yac"),
        interception=event_data.get("interception", False),
        intercepted_by_id=event_data.get("intercepted_by"),
        sack=event_data.get("is_sack", False),
        sack_yards=event_data.get("sack_yards"),
        qb_hit=event_data.get("qb_hit", False),
        pressure=event_data.get("pressure", False),
        thrown_away=event_data.get("thrown_away", False),
        
        # Rushing stats
        rusher_id=event_data.get("rusher_id"),
        broken_tackle=event_data.get("broken_tackle", 0),
        
        # Receiving stats
        receiver_id=event_data.get("receiver_id"),
        
        # Turnover stats
        fumble=event_data.get("fumble", False),
        fumbled_by_id=event_data.get("fumbled_by"),
        forced_by_id=event_data.get("forced_by"),
        recovered_by_id=event_data.get("recovered_by"),
        turnover_type=TurnoverType(event_data.get("type")) if event_data.get("type") else None,
        
        # Special teams
        kick_type=KickType(event_data.get("kick_type")) if event_data.get("kick_type") else None,
        kicker_id=event_data.get("kicker_id"),
        punter_id=event_data.get("punter_id"),
        returner_id=event_data.get("returner_id"),
        blocked=event_data.get("blocked", False),
        touchback=event_data.get("touchback", False),
        downed=event_data.get("downed", False),
        in_20=event_data.get("in_20", False),
        
        # EPA and success
        ep_before=event_data.get("ep_before"),
        ep_after=event_data.get("ep_after"),
        success=event_data.get("success"),
        
        description=event.description
    )

def _process_event(pbp_event: PBPEvent, player_stats: Dict[int, PlayerGameStats], 
                  team_stats: Dict[int, TeamGameStats], session: Session) -> None:
    """Process a single PBP event and update stats"""
    
    offense_team_id = pbp_event.offense_team_id
    defense_team_id = pbp_event.defense_team_id
    
    # Update team stats
    _update_team_stats(pbp_event, team_stats[offense_team_id], team_stats[defense_team_id])
    
    # Update player stats
    _update_player_stats(pbp_event, player_stats, session)

def _update_team_stats(pbp_event: PBPEvent, offense_team: TeamGameStats, 
                      defense_team: TeamGameStats) -> None:
    """Update team statistics based on PBP event"""
    
    # Update snap counts
    if pbp_event.play_type in [PlayType.PASS, PlayType.RUSH]:
        offense_team.snaps_offense += 1
        defense_team.snaps_defense += 1
    elif pbp_event.play_type in [PlayType.PUNT, PlayType.FIELD_GOAL, PlayType.KICKOFF]:
        offense_team.snaps_st += 1
        defense_team.snaps_st += 1
    
    # Passing stats
    if pbp_event.play_type == PlayType.PASS:
        offense_team.pass_attempts += 1
        
        if pbp_event.completed:
            offense_team.pass_completions += 1
            offense_team.pass_yards += pbp_event.yards_gained
            if pbp_event.is_scoring_play:
                offense_team.pass_td += 1
        elif pbp_event.interception:
            offense_team.pass_int += 1
            defense_team.interceptions += 1
            if pbp_event.intercepted_by_id:
                defense_team.int_yards += pbp_event.yards_gained
        elif pbp_event.sack:
            offense_team.sacks_allowed += 1
            offense_team.sack_yards_allowed += abs(pbp_event.sack_yards or 0)
            defense_team.sacks += 1
    
    # Rushing stats
    elif pbp_event.play_type == PlayType.RUSH:
        offense_team.rush_attempts += 1
        offense_team.rush_yards += pbp_event.yards_gained
        if pbp_event.is_scoring_play:
            offense_team.rush_td += 1
    
    # Special teams
    elif pbp_event.play_type == PlayType.PUNT:
        offense_team.punts += 1
        offense_team.punt_yards += pbp_event.yards_gained
        if pbp_event.in_20:
            offense_team.punts_in_20 += 1
        if pbp_event.touchback:
            offense_team.punt_touchbacks += 1
        
        if pbp_event.returner_id:
            defense_team.punt_returns += 1
            defense_team.punt_return_yards += pbp_event.yards_gained
    
    elif pbp_event.play_type == PlayType.FIELD_GOAL:
        offense_team.fg_attempts += 1
        if pbp_event.is_scoring_play:
            offense_team.fg_made += 1
            offense_team.fg_yards += pbp_event.yards_gained
    
    # Turnovers
    if pbp_event.turnover_type:
        offense_team.turnovers += 1
        if pbp_event.turnover_type == TurnoverType.FUMBLE:
            defense_team.forced_fumbles += 1
            if pbp_event.recovered_by_id:
                defense_team.fumble_recoveries += 1
                defense_team.fr_yards += pbp_event.yards_gained
    
    # Penalties
    if pbp_event.penalty and pbp_event.penalty.flag:
        if pbp_event.penalty.team_id == offense_team.team_id:
            offense_team.penalties += 1
            offense_team.penalty_yards += pbp_event.penalty.yards
        else:
            defense_team.penalties += 1
            defense_team.penalty_yards += pbp_event.penalty.yards
    
    # Update totals
    offense_team.total_yards = offense_team.pass_yards + offense_team.rush_yards
    offense_team.total_td = offense_team.pass_td + offense_team.rush_td

def _update_player_stats(pbp_event: PBPEvent, player_stats: Dict[int, PlayerGameStats], 
                        session: Session) -> None:
    """Update player statistics based on PBP event"""
    
    def get_or_create_player_stat(player_id: int, team_id: int, game_id: int) -> PlayerGameStats:
        if player_id not in player_stats:
            player_stats[player_id] = PlayerGameStats(
                game_id=game_id,
                player_id=player_id,
                team_id=team_id
            )
        return player_stats[player_id]
    
    # Passing stats
    if pbp_event.passer_id:
        passer_stat = get_or_create_player_stat(
            pbp_event.passer_id, pbp_event.offense_team_id, pbp_event.game_id
        )
        passer_stat.snaps_offense += 1
        passer_stat.pass_attempts += 1
        
        if pbp_event.completed:
            passer_stat.pass_completions += 1
            passer_stat.pass_yards += pbp_event.yards_gained
            if pbp_event.is_scoring_play:
                passer_stat.pass_td += 1
        elif pbp_event.interception:
            passer_stat.pass_int += 1
        elif pbp_event.sack:
            passer_stat.sacks += 1
            passer_stat.sack_yards += abs(pbp_event.sack_yards or 0)
        
        if pbp_event.qb_hit:
            passer_stat.qb_hits += 1
        if pbp_event.pressure:
            passer_stat.pressures += 1
    
    # Rushing stats
    if pbp_event.rusher_id:
        rusher_stat = get_or_create_player_stat(
            pbp_event.rusher_id, pbp_event.offense_team_id, pbp_event.game_id
        )
        rusher_stat.snaps_offense += 1
        rusher_stat.rush_attempts += 1
        rusher_stat.rush_yards += pbp_event.yards_gained
        rusher_stat.broken_tackle += pbp_event.broken_tackle
        if pbp_event.is_scoring_play:
            rusher_stat.rush_td += 1
    
    # Receiving stats
    if pbp_event.receiver_id:
        receiver_stat = get_or_create_player_stat(
            pbp_event.receiver_id, pbp_event.offense_team_id, pbp_event.game_id
        )
        receiver_stat.snaps_offense += 1
        receiver_stat.targets += 1
        receiver_stat.receptions += 1
        receiver_stat.receiving_yards += pbp_event.yards_gained
        receiver_stat.yac += pbp_event.yac or 0
        if pbp_event.is_scoring_play:
            receiver_stat.receiving_td += 1
    
    # Defense stats
    if pbp_event.intercepted_by_id:
        defender_stat = get_or_create_player_stat(
            pbp_event.intercepted_by_id, pbp_event.defense_team_id, pbp_event.game_id
        )
        defender_stat.snaps_defense += 1
        defender_stat.interceptions += 1
        defender_stat.int_yards += pbp_event.yards_gained
    
    if pbp_event.forced_by_id:
        defender_stat = get_or_create_player_stat(
            pbp_event.forced_by_id, pbp_event.defense_team_id, pbp_event.game_id
        )
        defender_stat.snaps_defense += 1
        defender_stat.forced_fumbles += 1
    
    if pbp_event.recovered_by_id:
        defender_stat = get_or_create_player_stat(
            pbp_event.recovered_by_id, pbp_event.defense_team_id, pbp_event.game_id
        )
        defender_stat.snaps_defense += 1
        defender_stat.fumble_recoveries += 1
        defender_stat.fr_yards += pbp_event.yards_gained
    
    # Special teams
    if pbp_event.kicker_id:
        kicker_stat = get_or_create_player_stat(
            pbp_event.kicker_id, pbp_event.offense_team_id, pbp_event.game_id
        )
        kicker_stat.snaps_st += 1
        if pbp_event.play_type == PlayType.FIELD_GOAL:
            kicker_stat.fg_attempts += 1
            if pbp_event.is_scoring_play:
                kicker_stat.fg_made += 1
                kicker_stat.fg_yards += pbp_event.yards_gained
    
    if pbp_event.punter_id:
        punter_stat = get_or_create_player_stat(
            pbp_event.punter_id, pbp_event.offense_team_id, pbp_event.game_id
        )
        punter_stat.snaps_st += 1
        if pbp_event.play_type == PlayType.PUNT:
            punter_stat.punts += 1
            punter_stat.punt_yards += pbp_event.yards_gained
            if pbp_event.in_20:
                punter_stat.punts_in_20 += 1
            if pbp_event.touchback:
                punter_stat.punt_touchbacks += 1
    
    if pbp_event.returner_id:
        returner_stat = get_or_create_player_stat(
            pbp_event.returner_id, pbp_event.defense_team_id, pbp_event.game_id
        )
        returner_stat.snaps_st += 1
        if pbp_event.play_type == PlayType.PUNT:
            returner_stat.punt_returns += 1
            returner_stat.punt_return_yards += pbp_event.yards_gained

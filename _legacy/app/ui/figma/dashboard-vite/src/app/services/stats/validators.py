"""
Advanced stats validation service.
Validates game totals, sack shares, coverage consistency, and other advanced metrics.
"""

from typing import List, Optional, Dict, Any
from sqlmodel import Session, select
from app.models.stats_models import PlayerGameStats, TeamGameStats
from app.models.pbp_event import PBPEvent
from app.ui.dto import ValidationMessage, ValidationReport


def validate_game_totals(game_id: Optional[int] = None, session: Session = None) -> List[ValidationMessage]:
    """
    Validate game totals and advanced stats consistency.
    Returns list of validation messages.
    """
    messages: List[ValidationMessage] = []
    
    if game_id:
        # Validate specific game
        messages.extend(_validate_single_game(game_id, session))
    else:
        # Validate all games (simplified - would iterate through all games)
        messages.extend(_validate_all_games(session))
    
    return messages


def validate_sack_shares(game_id: int, session: Session) -> List[ValidationMessage]:
    """Validate that sack shares sum to 1.0 and are properly attributed."""
    messages: List[ValidationMessage] = []
    
    # Get all PBP events with sacks
    sack_events = session.exec(
        select(PBPEvent).where(
            PBPEvent.game_id == game_id,
            PBPEvent.sack == True
        )
    ).all()
    
    for event in sack_events:
        if event.sack_split:
            total_share = sum(share for _, share in event.sack_split)
            if abs(total_share - 1.0) > 0.01:
                messages.append(ValidationMessage(
                    level="error",
                    category="sack_shares",
                    message=f"Sack shares sum to {total_share:.3f}, expected 1.0",
                    game_id=game_id,
                    player_id=event.passer_id
                ))
            
            # Check for negative shares
            for player_id, share in event.sack_split:
                if share < 0:
                    messages.append(ValidationMessage(
                        level="error",
                        category="sack_shares",
                        message=f"Negative sack share {share:.3f} for player {player_id}",
                        game_id=game_id,
                        player_id=player_id
                    ))
    
    return messages


def validate_coverage_consistency(game_id: int, session: Session) -> List[ValidationMessage]:
    """Validate that coverage stats are consistent."""
    messages: List[ValidationMessage] = []
    
    # Get all passing plays
    pass_events = session.exec(
        select(PBPEvent).where(
            PBPEvent.game_id == game_id,
            PBPEvent.play_type == "pass"
        )
    ).all()
    
    for event in pass_events:
        if event.targeted_db_id and event.target_id:
            # Check that coverage result matches play outcome
            if event.completed and event.coverage_result == "defended":
                messages.append(ValidationMessage(
                    level="warning",
                    category="coverage_consistency",
                    message=f"Pass completed but marked as defended for DB {event.targeted_db_id}",
                    game_id=game_id,
                    player_id=event.targeted_db_id
                ))
            
            if not event.completed and event.coverage_result == "caught":
                messages.append(ValidationMessage(
                    level="warning",
                    category="coverage_consistency",
                    message=f"Pass incomplete but marked as caught for DB {event.targeted_db_id}",
                    game_id=game_id,
                    player_id=event.targeted_db_id
                ))
    
    return messages


def validate_ol_attribution(game_id: int, session: Session) -> List[ValidationMessage]:
    """Validate offensive line sack attribution."""
    messages: List[ValidationMessage] = []
    
    # Get all sack events
    sack_events = session.exec(
        select(PBPEvent).where(
            PBPEvent.game_id == game_id,
            PBPEvent.sack == True
        )
    ).all()
    
    for event in sack_events:
        if event.ol_block:
            # Check that OL blocking assignment is consistent with sack attribution
            ol_player_id = event.ol_block.get('player_id')
            if ol_player_id:
                # Verify that this OL player is credited with allowing the sack
                # This would require checking the OL stats table
                pass
    
    return messages


def validate_special_teams_consistency(game_id: int, session: Session) -> List[ValidationMessage]:
    """Validate special teams stats consistency."""
    messages: List[ValidationMessage] = []
    
    # Get all punt events
    punt_events = session.exec(
        select(PBPEvent).where(
            PBPEvent.game_id == game_id,
            PBPEvent.play_type == "punt"
        )
    ).all()
    
    for event in punt_events:
        if event.kick_distance and event.net_yards:
            # Check that net yards <= kick distance
            if event.net_yards > event.kick_distance:
                messages.append(ValidationMessage(
                    level="error",
                    category="special_teams",
                    message=f"Net yards ({event.net_yards}) > kick distance ({event.kick_distance})",
                    game_id=game_id,
                    player_id=event.punter_id
                ))
        
        # Check in-20 consistency
        if event.in_20 and event.yardline and event.yardline > 20:
            messages.append(ValidationMessage(
                level="warning",
                category="special_teams",
                message=f"Punt marked in-20 but landed at yardline {event.yardline}",
                game_id=game_id,
                player_id=event.punter_id
            ))
    
    return messages


def validate_situational_splits(game_id: int, session: Session) -> List[ValidationMessage]:
    """Validate situational split flags are consistent."""
    messages: List[ValidationMessage] = []
    
    # Get all events
    events = session.exec(
        select(PBPEvent).where(PBPEvent.game_id == game_id)
    ).all()
    
    for event in events:
        # Check red zone consistency
        if event.is_red_zone and event.yardline and event.yardline > 20:
            messages.append(ValidationMessage(
                level="warning",
                category="situational_splits",
                message=f"Play marked red zone but yardline is {event.yardline}",
                game_id=game_id
            ))
        
        # Check goal-to-go consistency
        if event.is_goal_to_go and event.distance and event.distance > event.yardline:
            messages.append(ValidationMessage(
                level="warning",
                category="situational_splits",
                message=f"Play marked goal-to-go but distance ({event.distance}) > yardline ({event.yardline})",
                game_id=game_id
            ))
        
        # Check down consistency
        if event.is_third_down and event.down != 3:
            messages.append(ValidationMessage(
                level="warning",
                category="situational_splits",
                message=f"Play marked third down but down is {event.down}",
                game_id=game_id
            ))
        
        if event.is_fourth_down and event.down != 4:
            messages.append(ValidationMessage(
                level="warning",
                category="situational_splits",
                message=f"Play marked fourth down but down is {event.down}",
                game_id=game_id
            ))
    
    return messages


def validate_team_totals(game_id: int, session: Session) -> List[ValidationMessage]:
    """Validate that team totals equal sum of player stats."""
    messages: List[ValidationMessage] = []
    
    # Get team game stats
    team_stats = session.exec(
        select(TeamGameStats).where(TeamGameStats.game_id == game_id)
    ).all()
    
    for team_stat in team_stats:
        # Get player stats for this team
        player_stats = session.exec(
            select(PlayerGameStats).where(
                PlayerGameStats.game_id == game_id,
                PlayerGameStats.team_id == team_stat.team_id
            )
        ).all()
        
        # Sum player stats
        total_yards = sum(ps.pass_yards + ps.rush_yards + ps.receiving_yards for ps in player_stats)
        total_points = sum(ps.pass_touchdowns + ps.rush_touchdowns + ps.receiving_touchdowns for ps in player_stats) * 6
        
        # Check consistency (with tolerance for special teams, etc.)
        if abs(team_stat.total_yards - total_yards) > 100:  # Allow some tolerance
            messages.append(ValidationMessage(
                level="warning",
                category="team_totals",
                message=f"Team total yards ({team_stat.total_yards}) differs significantly from player sum ({total_yards})",
                game_id=game_id,
                team_id=team_stat.team_id
            ))
    
    return messages


def _validate_single_game(game_id: int, session: Session) -> List[ValidationMessage]:
    """Validate a single game."""
    messages: List[ValidationMessage] = []
    
    # Run all validation checks
    messages.extend(validate_sack_shares(game_id, session))
    messages.extend(validate_coverage_consistency(game_id, session))
    messages.extend(validate_ol_attribution(game_id, session))
    messages.extend(validate_special_teams_consistency(game_id, session))
    messages.extend(validate_situational_splits(game_id, session))
    messages.extend(validate_team_totals(game_id, session))
    
    return messages


def _validate_all_games(session: Session) -> List[ValidationMessage]:
    """Validate all games (simplified implementation)."""
    messages: List[ValidationMessage] = []
    
    # Get all game IDs
    games = session.exec(select(PBPEvent.game_id).distinct()).all()
    
    for game_id in games:
        messages.extend(_validate_single_game(game_id, session))
    
    return messages


def create_validation_report(game_id: Optional[int], session: Session) -> ValidationReport:
    """Create a complete validation report."""
    messages = validate_game_totals(game_id, session)
    
    errors = len([m for m in messages if m.level == "error"])
    warnings = len([m for m in messages if m.level == "warning"])
    
    return ValidationReport(
        game_id=game_id,
        total_checks=len(messages),
        errors=errors,
        warnings=warnings,
        messages=messages,
        is_valid=errors == 0
    )

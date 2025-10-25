from __future__ import annotations
from random import Random
from sqlmodel import Session
from app.services.injury_service import (
    maybe_injure_player, 
    active_penalty_for_player, 
    is_player_active,
    get_player_injury_status,
    get_team_injuries,
    get_injury_stats
)

def check_and_apply_injury(sess: Session, rnd: Random, season: int, week: int, game_id: int, team_id: int, opponent_id: int, player_id: int, pos: str) -> bool:
    """
    Call once pregame (or per drive / per N snaps if you want more granularity).
    Returns True if player got injured this call.
    """
    inj = maybe_injure_player(sess, rnd, season, week, game_id, team_id, opponent_id, player_id, pos)
    return inj is not None

def availability(sess: Session, player_id: int) -> bool:
    """Check if a player is available to play."""
    return is_player_active(sess, player_id)

def rtp_overall_penalty(sess: Session, player_id: int) -> float:
    """Get RTP penalty for a player's overall rating."""
    return active_penalty_for_player(sess, player_id)

def rtp_positional_penalty(sess: Session, player_id: int) -> float:
    """Get RTP penalty for a player's positional rating."""
    from sqlmodel import select
    from app.models.injury import Injury, InjuryStatus
    
    # Get the worst positional penalty from recent injuries
    rows = list(sess.exec(select(Injury).where(Injury.player_id == player_id)))
    penalty = 0.0
    
    for inj in rows:
        if inj.resolved and inj.status == InjuryStatus.ACTIVE:
            penalty = max(penalty, inj.rtp_penalty_pos)
    
    return penalty

def get_player_availability_status(sess: Session, player_id: int) -> dict:
    """Get comprehensive availability status for a player."""
    from app.models.injury import InjuryStatus
    
    is_available = availability(sess, player_id)
    injury_status = get_player_injury_status(sess, player_id)
    overall_penalty = rtp_overall_penalty(sess, player_id)
    positional_penalty = rtp_positional_penalty(sess, player_id)
    
    return {
        "player_id": player_id,
        "is_available": is_available,
        "injury_status": injury_status.value if injury_status else InjuryStatus.ACTIVE.value,
        "overall_penalty": overall_penalty,
        "positional_penalty": positional_penalty,
        "total_penalty": overall_penalty + positional_penalty
    }

def get_team_availability(sess: Session, team_id: int, season: int) -> dict:
    """Get team-wide availability status."""
    injuries = get_team_injuries(sess, team_id, season)
    stats = get_injury_stats(sess, team_id, season)
    
    return {
        "team_id": team_id,
        "season": season,
        "active_injuries": len([i for i in injuries if not i.resolved]),
        "ir_players": len([i for i in injuries if i.placed_on_ir]),
        "stats": stats
    }

def apply_injury_penalties_to_rating(sess: Session, player_id: int, base_overall: int, base_positional: int) -> tuple[int, int]:
    """Apply RTP penalties to player ratings."""
    overall_penalty = rtp_overall_penalty(sess, player_id)
    positional_penalty = rtp_positional_penalty(sess, player_id)
    
    # Apply penalties as percentage reductions
    adjusted_overall = int(base_overall * (1.0 - overall_penalty))
    adjusted_positional = int(base_positional * (1.0 - positional_penalty))
    
    # Ensure minimum values
    adjusted_overall = max(1, adjusted_overall)
    adjusted_positional = max(1, adjusted_positional)
    
    return adjusted_overall, adjusted_positional

def pregame_injury_check(sess: Session, rnd: Random, season: int, week: int, game_id: int, home_team_id: int, away_team_id: int, player_roster: list[dict]) -> list[dict]:
    """
    Perform pregame injury checks for all players.
    Returns list of injury results.
    """
    injury_results = []
    
    for player in player_roster:
        player_id = player["player_id"]
        team_id = player["team_id"]
        pos = player["pos"]
        
        # Determine opponent
        opponent_id = away_team_id if team_id == home_team_id else home_team_id
        
        # Check for injury
        injured = check_and_apply_injury(sess, rnd, season, week, game_id, team_id, opponent_id, player_id, pos)
        
        injury_results.append({
            "player_id": player_id,
            "team_id": team_id,
            "injured": injured,
            "available": availability(sess, player_id) if not injured else False
        })
    
    return injury_results

def get_depth_chart_adjustments(sess: Session, team_id: int, season: int) -> dict:
    """Get depth chart adjustments based on injuries."""
    injuries = get_team_injuries(sess, team_id, season)
    
    adjustments = {
        "injured_players": [],
        "ir_players": [],
        "questionable_players": [],
        "probable_players": []
    }
    
    for injury in injuries:
        if not injury.resolved:
            if injury.placed_on_ir:
                adjustments["ir_players"].append(injury.player_id)
            elif injury.status.value == "QUESTIONABLE":
                adjustments["questionable_players"].append(injury.player_id)
            elif injury.status.value == "PROBABLE":
                adjustments["probable_players"].append(injury.player_id)
            else:
                adjustments["injured_players"].append(injury.player_id)
    
    return adjustments

def simulate_game_injuries(sess: Session, rnd: Random, season: int, week: int, game_id: int, home_team_id: int, away_team_id: int, home_roster: list[dict], away_roster: list[dict]) -> dict:
    """Simulate injuries for an entire game."""
    home_injuries = []
    away_injuries = []
    
    # Check home team players
    for player in home_roster:
        if check_and_apply_injury(sess, rnd, season, week, game_id, home_team_id, away_team_id, player["player_id"], player["pos"]):
            home_injuries.append(player["player_id"])
    
    # Check away team players
    for player in away_roster:
        if check_and_apply_injury(sess, rnd, season, week, game_id, away_team_id, home_team_id, player["player_id"], player["pos"]):
            away_injuries.append(player["player_id"])
    
    return {
        "home_injuries": home_injuries,
        "away_injuries": away_injuries,
        "total_injuries": len(home_injuries) + len(away_injuries)
    }


"""Adapters to bridge CPU Trade Evaluation with existing services."""
from __future__ import annotations
from typing import Dict, List
from sqlmodel import Session, select
from app.models.player import Player
from app.models.contract_models import PlayerContract

def get_player_basic_info(sess: Session, player_id: int) -> Dict:
    """Get basic player info for trade evaluation."""
    p = sess.get(Player, player_id)
    if not p:
        return {}
    
    # Calculate overall from individual ratings
    overall = (
        p.speed + p.strength + p.agility + p.awareness + 
        p.potential + getattr(p, 'throw_accuracy', p.awareness) if p.position == 'QB' else p.catching
    ) // 5
    
    # Get contract info
    con = sess.exec(
        select(PlayerContract).where(
            PlayerContract.player_id == player_id,
            PlayerContract.is_active == True
        )
    ).first()
    
    contract_years = getattr(con, 'contract_years', 2) if con else 2
    aav = getattr(con, 'aav', 0) if con else 0
    
    return {
        'position': p.position,
        'age': p.age,
        'ovr': min(99, max(0, overall)),
        'potential': p.potential,
        'contract_years': contract_years,
        'contract_salary_aav': aav
    }

def get_team_needs_simple(sess: Session, team_id: int, season: int) -> Dict[str, float]:
    """Get normalized team needs (0-1 scale) per position."""
    from app.services.team_needs_service import team_needs
    try:
        needs = team_needs(sess, season, team_id)
        # Return dict mapping position to need value (0-1)
        return {k: (1.0 if v.get('need', False) else 0.0) for k, v in needs.items()}
    except Exception:
        # Fallback: return neutral needs
        return {pos: 0.5 for pos in ["QB","RB","WR","TE","LT","LG","C","RG","RT","EDGE","IDL","LB","CB","S"]}

def get_team_counts_after_simple(sess: Session, team_id: int, outgoing: List[int], incoming: List[int]) -> Dict[str, int]:
    """Calculate position counts after trade."""
    # Get current roster
    current = list(sess.exec(
        select(Player).where(Player.team_id == team_id)
    ))
    
    # Count by position
    counts = {}
    for p in current:
        pos = p.position
        counts[pos] = counts.get(pos, 0) + 1
    
    # Remove outgoing
    for pid in outgoing:
        p = sess.get(Player, pid)
        if p and p.position in counts:
            counts[p.position] = max(0, counts[p.position] - 1)
    
    # Add incoming
    for pid in incoming:
        p = sess.get(Player, pid)
        if p:
            pos = p.position
            counts[pos] = counts.get(pos, 0) + 1
    
    return counts

def get_cap_after_simple(sess: Session, team_id: int, outgoing: List[int], incoming: List[int], season: int) -> int:
    """Calculate cap space after trade (simplified)."""
    # TODO: Get actual team cap space
    current_cap = 100_000_000  # placeholder
    
    # Sum outgoing AAV
    outgoing_aaav = 0
    for pid in outgoing:
        con = sess.exec(
            select(PlayerContract).where(
                PlayerContract.player_id == pid,
                PlayerContract.is_active == True
            )
        ).first()
        if con:
            outgoing_aaav += getattr(con, 'aav', 0)
    
    # Sum incoming AAV
    incoming_aaav = 0
    for pid in incoming:
        con = sess.exec(
            select(PlayerContract).where(
                PlayerContract.player_id == pid,
                PlayerContract.is_active == True
            )
        ).first()
        if con:
            incoming_aaav += getattr(con, 'aav', 0)
    
    # Simple cap check
    return current_cap + outgoing_aaav - incoming_aaav

def compute_need_gain_simple(sess: Session, team_id: int, offer, season: int) -> Dict[str, float]:
    """Calculate need improvement (simplified)."""
    # For MVP: return placeholder improvement
    return {
        'WR': 8.0,
        'CB': 6.0
    }

def propose_counter_simple(cpu_id: int, offer, target: float, max_steps: int) -> Dict[str, List[int]]:
    """Generate counter offer suggestion (simplified)."""
    return {
        'add_players': [],
        'remove_players': []
    }

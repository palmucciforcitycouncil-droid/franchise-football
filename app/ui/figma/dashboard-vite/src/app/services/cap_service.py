from __future__ import annotations
from typing import Optional, Dict, Any
from sqlmodel import Session, select

def _try(path: str, name: str):
    """Defensive import helper - returns None if model doesn't exist."""
    try:
        mod = __import__(path, fromlist=[name])
        return getattr(mod, name)
    except Exception:
        return None

# Defensive imports for models that may not exist yet
PlayerContract = _try("app.models.contracts", "PlayerContract")
Player = _try("app.models.player", "Player")

def active_contract(sess: Session, player_id: int) -> Optional[Any]:
    """
    Get the active contract for a player.
    Returns None if no active contract found.
    """
    if not PlayerContract:
        return None
    
    return sess.exec(
        select(PlayerContract).where(
            PlayerContract.player_id == player_id,
            PlayerContract.is_active == True
        )
    ).first()

def cap_snapshot_for_release(sess: Session, player_id: int, season: int) -> Dict[str, Any]:
    """
    Calculate cap impact of releasing a player.
    Returns dict with current_cap_hit, dead_cap_now, savings_now, years_remaining.
    """
    contract = active_contract(sess, player_id)
    
    if not contract:
        return {
            "current_cap_hit": 0,
            "dead_cap_now": 0,
            "savings_now": 0,
            "years_remaining": 0
        }
    
    # Calculate years remaining
    years_remaining = max(0, contract.end_season - season + 1)
    
    # Current cap hit (simplified - just AAV for MVP)
    current_cap_hit = contract.aav
    
    # Dead cap calculation (simplified MVP: 50% of remaining AAV)
    dead_cap_now = int(contract.aav * years_remaining * 0.5)
    
    # Savings = current hit - dead cap
    savings_now = current_cap_hit - dead_cap_now
    
    return {
        "current_cap_hit": current_cap_hit,
        "dead_cap_now": dead_cap_now,
        "savings_now": savings_now,
        "years_remaining": years_remaining
    }

def cap_snapshot_for_resign(sess: Session, player_id: int, new_aav: int, season: int) -> Dict[str, Any]:
    """
    Calculate cap impact of re-signing a player.
    Returns dict with current_cap_hit, projected_cap_hit, delta.
    """
    contract = active_contract(sess, player_id)
    
    if not contract:
        return {
            "current_cap_hit": 0,
            "projected_cap_hit": new_aav,
            "delta": new_aav
        }
    
    # Current cap hit
    current_cap_hit = contract.aav
    
    # Projected cap hit (new AAV)
    projected_cap_hit = new_aav
    
    # Delta (change in cap hit)
    delta = projected_cap_hit - current_cap_hit
    
    return {
        "current_cap_hit": current_cap_hit,
        "projected_cap_hit": projected_cap_hit,
        "delta": delta
    }
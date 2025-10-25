from __future__ import annotations
from typing import List
from sqlmodel import Session
from app.models.trade import DraftPick

# Pick value curve (Jimmy Johnson-ish but flattened). Units match player value scale (~100k base).
PICK_VALUE_BY_ROUND = {
    1: 5_000_000,
    2: 2_500_000,
    3: 1_200_000,
    4: 700_000,
    5: 400_000,
    6: 250_000,
    7: 150_000,
}

def pick_value(sess: Session, pick_id: int) -> int:
    """Calculate the trade value of a draft pick."""
    p = sess.get(DraftPick, pick_id)
    if not p: 
        return 0
    
    base = PICK_VALUE_BY_ROUND.get(p.round, 100_000)
    # You can nudge by expected slot later; MVP returns base.
    return base

def players_value(sess: Session, player_ids: List[int], season: int) -> int:
    """Calculate the total trade value of a list of players."""
    total_value = 0
    for pid in player_ids:
        try:
            # Try to use existing player_trade_value function
            from app.services.trade_valuation import player_trade_value
            value = player_trade_value(sess, pid, season)
        except ImportError:
            # Fallback: simple value based on overall rating
            try:
                from app.models.player import Player
                player = sess.get(Player, pid)
                if player:
                    # Simple fallback: overall * 100k
                    value = max(100_000, player.overall * 100_000)
                else:
                    value = 100_000
            except ImportError:
                value = 100_000
        
        total_value += max(100_000, value)  # Minimum value of 100k
    
    return total_value

def picks_value(sess: Session, pick_ids: List[int]) -> int:
    """Calculate the total trade value of a list of draft picks."""
    return sum(pick_value(sess, pk) for pk in pick_ids)

def bundle_value(sess: Session, season: int, players: List[int], picks: List[int]) -> int:
    """Calculate the total trade value of a bundle of players and picks."""
    return players_value(sess, players, season) + picks_value(sess, picks)

def get_pick_value_by_round(round_num: int) -> int:
    """Get the base value for a draft pick by round number."""
    return PICK_VALUE_BY_ROUND.get(round_num, 100_000)

def calculate_trade_balance(from_value: int, to_value: int) -> dict:
    """Calculate trade balance metrics."""
    total_value = from_value + to_value
    if total_value == 0:
        return {
            "balance_ratio": 1.0,
            "value_difference": 0,
            "is_balanced": True,
            "favor_side": "EVEN"
        }
    
    balance_ratio = min(from_value, to_value) / max(from_value, to_value)
    value_difference = abs(from_value - to_value)
    is_balanced = balance_ratio >= 0.85  # 85% balance threshold
    
    if from_value > to_value:
        favor_side = "FROM"
    elif to_value > from_value:
        favor_side = "TO"
    else:
        favor_side = "EVEN"
    
    return {
        "balance_ratio": balance_ratio,
        "value_difference": value_difference,
        "is_balanced": is_balanced,
        "favor_side": favor_side
    }


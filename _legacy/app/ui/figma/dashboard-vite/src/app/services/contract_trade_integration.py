from __future__ import annotations
from sqlmodel import Session
from app.services.expiring_contracts import is_expiring_this_season, _current_contract

def apply_expiring_contract_discount(sess: Session, player_id: int, base_value: int, season: int) -> int:
    """
    Apply discount to trade value for expiring contracts.
    This integrates with the trade engine to reduce value of expiring players.
    """
    try:
        contract = _current_contract(sess, player_id)
        if not contract:
            return base_value
        
        if is_expiring_this_season(contract, season):
            # Apply 10-25% discount for expiring contracts
            # Longer contracts get less discount
            years_left = max(0, contract.end_season - season)
            if years_left == 0:
                discount_rate = 0.25  # 25% discount for expiring this season
            elif years_left == 1:
                discount_rate = 0.15  # 15% discount for expiring next season
            else:
                discount_rate = 0.10  # 10% discount for expiring in 2+ seasons
            
            discounted_value = int(base_value * (1.0 - discount_rate))
            return max(1, discounted_value)  # Ensure minimum value
        
        return base_value
    
    except Exception:
        # Fallback to base value if any errors
        return base_value

def get_contract_status_for_trade(sess: Session, player_id: int, season: int) -> dict:
    """
    Get contract status information for trade evaluation.
    """
    try:
        contract = _current_contract(sess, player_id)
        if not contract:
            return {
                "has_contract": False,
                "is_expiring": False,
                "years_left": 0,
                "aav": 0,
                "discount_applied": 0.0
            }
        
        years_left = max(0, contract.end_season - season)
        is_expiring = is_expiring_this_season(contract, season)
        
        # Calculate discount rate
        if is_expiring:
            if years_left == 0:
                discount_rate = 0.25
            elif years_left == 1:
                discount_rate = 0.15
            else:
                discount_rate = 0.10
        else:
            discount_rate = 0.0
        
        return {
            "has_contract": True,
            "is_expiring": is_expiring,
            "years_left": years_left,
            "aav": contract.aav,
            "discount_applied": discount_rate
        }
    
    except Exception:
        return {
            "has_contract": False,
            "is_expiring": False,
            "years_left": 0,
            "aav": 0,
            "discount_applied": 0.0
        }

def get_trade_block_players_for_team(sess: Session, team_id: int, season: int) -> list[int]:
    """
    Get list of players on trade block for a team.
    This can be used by the trade engine to identify available players.
    """
    try:
        from app.services.expiring_contracts import get_trade_block_players
        return get_trade_block_players(sess, season, team_id)
    except Exception:
        return []

def is_player_on_trade_block(sess: Session, player_id: int, season: int, team_id: int) -> bool:
    """
    Check if a specific player is on the trade block.
    """
    try:
        from sqlmodel import select
        from app.models.contracts import TeamTradeBlock
        
        block = sess.exec(select(TeamTradeBlock).where(
            TeamTradeBlock.player_id == player_id,
            TeamTradeBlock.season == season,
            TeamTradeBlock.team_id == team_id
        )).first()
        
        return block is not None
    
    except Exception:
        return False

def get_contract_negotiation_status(sess: Session, player_id: int, season: int) -> dict:
    """
    Get contract negotiation status for a player.
    Useful for trade engine to understand contract situation.
    """
    try:
        from app.services.expiring_contracts import get_or_update_ask
        
        # Get player ask
        from app.models.player import Player
        player = sess.get(Player, player_id)
        if not player:
            return {"has_ask": False}
        
        ask = get_or_update_ask(sess, player, season)
        
        return {
            "has_ask": True,
            "desired_years": ask.desired_years,
            "desired_aav": ask.desired_aav,
            "desired_total": ask.desired_years * ask.desired_aav,
            "updated_season": ask.updated_season
        }
    
    except Exception:
        return {"has_ask": False}

def get_team_contract_situation(sess: Session, team_id: int, season: int) -> dict:
    """
    Get comprehensive contract situation for a team.
    Useful for trade engine to understand team's contract needs.
    """
    try:
        from app.services.expiring_contracts import list_team_expiring, get_contract_summary
        
        expiring = list_team_expiring(sess, team_id, season)
        summary = get_contract_summary(sess, team_id, season)
        trade_block = get_trade_block_players_for_team(sess, team_id, season)
        
        return {
            "team_id": team_id,
            "season": season,
            "expiring_players": len(expiring),
            "trade_block_players": len(trade_block),
            "total_ask_value": summary["total_ask_value"],
            "total_cap_hit": summary["total_cap_hit"],
            "avg_ask_aav": summary["avg_ask_aav"],
            "positions": summary["positions"],
            "expiring_details": [
                {
                    "player_id": row.player_id,
                    "name": row.name,
                    "pos": row.pos,
                    "age": row.age,
                    "ask_aav": row.ask_aav,
                    "ask_years": row.ask_years,
                    "ask_total": row.ask_total
                }
                for row in expiring
            ]
        }
    
    except Exception:
        return {
            "team_id": team_id,
            "season": season,
            "expiring_players": 0,
            "trade_block_players": 0,
            "total_ask_value": 0,
            "total_cap_hit": 0,
            "avg_ask_aav": 0,
            "positions": {},
            "expiring_details": []
        }


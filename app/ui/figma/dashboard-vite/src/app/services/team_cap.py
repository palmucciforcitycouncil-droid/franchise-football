from __future__ import annotations
from typing import List, Dict, Any
from sqlmodel import Session, select
from app.services.cap import project_cap_for_year, get_current_league_cap, get_growth_rate

def get_team_cap_obligations_by_year(session: Session, team_id: int, year: int) -> int:
    """
    Sums all countable money in that league year for the team.
    Includes base salary, bonuses that count that year, dead money, etc.
    """
    total_obligations = 0
    
    try:
        # Try to get from PlayerContract model
        from app.models.contracts import PlayerContract
        contracts = session.exec(
            select(PlayerContract).where(
                PlayerContract.team_id == team_id,
                PlayerContract.start_season <= year,
                PlayerContract.end_season >= year,
                PlayerContract.is_active == True
            )
        ).all()
        
        for contract in contracts:
            # For MVP, assume all AAV counts in each year
            # In a more complex system, you'd prorate signing bonuses, etc.
            total_obligations += contract.aav
            
    except ImportError:
        # Contract model doesn't exist, try alternative approach
        pass
    except Exception as e:
        print(f"Error calculating team obligations: {e}")
    
    # Add dead money if available
    try:
        from app.models.dead_money import DeadMoney
        dead_money = session.exec(
            select(DeadMoney).where(
                DeadMoney.team_id == team_id,
                DeadMoney.season == year
            )
        ).all()
        
        for dm in dead_money:
            total_obligations += dm.amount
            
    except ImportError:
        # Dead money model doesn't exist
        pass
    except Exception as e:
        print(f"Error calculating dead money: {e}")
    
    return int(total_obligations)

def build_team_cap_summary(session: Session, team_id: int, base_year: int, horizon: int = 3) -> List[Dict[str, Any]]:
    """
    Returns an array of dicts for [base_year, base_year+1, ..., base_year+horizon]
    with cap information for each year.
    """
    current_cap = get_current_league_cap(session)
    growth_rate = get_growth_rate(session)
    
    summary = []
    
    for i in range(horizon + 1):
        year = base_year + i
        team_obligations = get_team_cap_obligations_by_year(session, team_id, year)
        
        if i == 0:
            # Current year - use actual league cap
            league_cap = current_cap
            is_projected = False
        else:
            # Future years - project the cap
            league_cap = project_cap_for_year(base_year, year, current_cap, growth_rate)
            is_projected = True
        
        cap_space = league_cap - team_obligations
        
        summary.append({
            "year": year,
            "team_obligations": team_obligations,
            "league_cap": league_cap,
            "cap_space": cap_space,
            "is_projected": is_projected
        })
    
    return summary

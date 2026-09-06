from __future__ import annotations
import math
import logging
from typing import Optional
from sqlmodel import Session, select

logger = logging.getLogger(__name__)

def nearest_5_floor(value: float) -> int:
    """
    Round down to the nearest multiple of 5.
    
    Examples:
    - 259 -> 255
    - 260 -> 260  
    - 261 -> 260
    - 264 -> 260
    - 265 -> 265
    """
    return int(math.floor(value / 5) * 5)

def project_cap_for_year(base_year: int, target_year: int, base_cap: int | float, growth_rate_pct: float) -> int:
    """
    Compute compounded growth from base_year to target_year using league logic.
    Apply round-down to nearest multiple of 5.
    
    Args:
        base_year: Starting year for the calculation
        target_year: Target year to project to
        base_cap: Base salary cap amount
        growth_rate_pct: Annual growth rate as percentage (e.g., 5.0 for 5%)
    
    Returns:
        Projected cap amount rounded down to nearest multiple of 5
    """
    if target_year < base_year:
        return int(base_cap)
    
    years_diff = target_year - base_year
    if years_diff == 0:
        return nearest_5_floor(float(base_cap))
    
    # Apply compounded growth: cap * (1 + rate)^years
    growth_factor = (1 + growth_rate_pct / 100) ** years_diff
    projected_cap = float(base_cap) * growth_factor
    
    return nearest_5_floor(projected_cap)

def get_current_league_cap(session: Session) -> int:
    """
    Returns the current league cap from League/Settings table.
    If missing, defaults to 255,000,000 and logs a warning.
    """
    try:
        # Try to get from League table first
        from app.models.league import League
        league = session.exec(select(League)).first()
        if league and hasattr(league, 'salary_cap') and league.salary_cap:
            return int(league.salary_cap)
        
        # Try Settings table as fallback
        from app.models.settings import Settings
        settings = session.exec(select(Settings)).first()
        if settings and hasattr(settings, 'salary_cap') and settings.salary_cap:
            return int(settings.salary_cap)
            
    except ImportError:
        # Models don't exist yet, use default
        pass
    except Exception as e:
        logger.warning(f"Error retrieving league cap: {e}")
    
    logger.warning("League cap not found in database, using default: 255,000,000")
    return 255_000_000

def get_growth_rate(session: Session) -> float:
    """
    Returns configured growth rate from Settings.
    Defaults to 5.0% if missing.
    """
    try:
        from app.models.settings import Settings
        settings = session.exec(select(Settings)).first()
        if settings and hasattr(settings, 'cap_growth_rate') and settings.cap_growth_rate is not None:
            return float(settings.cap_growth_rate)
    except ImportError:
        # Settings model doesn't exist yet, use default
        pass
    except Exception as e:
        logger.warning(f"Error retrieving growth rate: {e}")
    
    return 5.0  # Default 5% growth rate

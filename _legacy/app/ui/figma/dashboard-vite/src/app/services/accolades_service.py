from __future__ import annotations
from typing import Dict, Any
from sqlmodel import Session, select

def _try(path: str, name: str):
    """Defensive import helper - returns None if model doesn't exist."""
    try:
        mod = __import__(path, fromlist=[name])
        return getattr(mod, name)
    except Exception:
        return None

# Defensive imports for models that may not exist yet
AwardsWeekly = _try("app.models.awards", "AwardsWeekly")
AwardsAnnual = _try("app.models.awards", "AwardsAnnual")

def player_accolades(sess: Session, player_id: int) -> Dict[str, int]:
    """
    Get all accolades for a player.
    Returns dict with counts for MVP, OPOY, DPOY, ROY, POW_OFF, POW_DEF, POW_ST, total_awards.
    """
    if not AwardsWeekly or not AwardsAnnual:
        return {
            "mvp": 0,
            "opoy": 0,
            "dpoy": 0,
            "roy": 0,
            "pow_off": 0,
            "pow_def": 0,
            "pow_st": 0,
            "total_awards": 0
        }
    
    # Count weekly awards
    weekly_awards = 0
    if AwardsWeekly:
        weekly_awards = len(list(sess.exec(
            select(AwardsWeekly).where(AwardsWeekly.player_id == player_id)
        )))
    
    # Count annual awards
    annual_awards = 0
    if AwardsAnnual:
        annual_awards = len(list(sess.exec(
            select(AwardsAnnual).where(AwardsAnnual.player_id == player_id)
        )))
    
    # For MVP, we'll count annual awards with specific types
    mvp_count = 0
    opoy_count = 0
    dpoy_count = 0
    roy_count = 0
    
    if AwardsAnnual:
        annual_list = list(sess.exec(
            select(AwardsAnnual).where(AwardsAnnual.player_id == player_id)
        ))
        for award in annual_list:
            award_type = getattr(award, 'award_type', '').lower()
            if 'mvp' in award_type:
                mvp_count += 1
            elif 'opoy' in award_type or 'offensive' in award_type:
                opoy_count += 1
            elif 'dpoy' in award_type or 'defensive' in award_type:
                dpoy_count += 1
            elif 'roy' in award_type or 'rookie' in award_type:
                roy_count += 1
    
    # Count weekly POW awards by type
    pow_off = 0
    pow_def = 0
    pow_st = 0
    
    if AwardsWeekly:
        weekly_list = list(sess.exec(
            select(AwardsWeekly).where(AwardsWeekly.player_id == player_id)
        ))
        for award in weekly_list:
            award_type = getattr(award, 'award_type', '').lower()
            if 'offensive' in award_type:
                pow_off += 1
            elif 'defensive' in award_type:
                pow_def += 1
            elif 'special' in award_type or 'teams' in award_type:
                pow_st += 1
    
    total_awards = weekly_awards + annual_awards
    
    return {
        "mvp": mvp_count,
        "opoy": opoy_count,
        "dpoy": dpoy_count,
        "roy": roy_count,
        "pow_off": pow_off,
        "pow_def": pow_def,
        "pow_st": pow_st,
        "total_awards": total_awards
    }

def coach_accolades(sess: Session, coach_id: int) -> Dict[str, int]:
    """
    Get all accolades for a coach.
    Returns dict with counts for COY, GMOY, rings, conf_titles, div_titles, total_awards.
    """
    if not AwardsWeekly or not AwardsAnnual:
        return {
            "coy": 0,
            "gmoy": 0,
            "rings": 0,
            "conf_titles": 0,
            "div_titles": 0,
            "total_awards": 0
        }
    
    # Count weekly awards
    weekly_awards = 0
    if AwardsWeekly:
        weekly_awards = len(list(sess.exec(
            select(AwardsWeekly).where(AwardsWeekly.coach_id == coach_id)
        )))
    
    # Count annual awards
    annual_awards = 0
    if AwardsAnnual:
        annual_awards = len(list(sess.exec(
            select(AwardsAnnual).where(AwardsAnnual.coach_id == coach_id)
        )))
    
    # Count specific coach awards
    coy_count = 0
    gmoy_count = 0
    rings_count = 0
    conf_titles_count = 0
    div_titles_count = 0
    
    if AwardsAnnual:
        annual_list = list(sess.exec(
            select(AwardsAnnual).where(AwardsAnnual.coach_id == coach_id)
        ))
        for award in annual_list:
            award_type = getattr(award, 'award_type', '').lower()
            if 'coy' in award_type or 'coach' in award_type:
                coy_count += 1
            elif 'gmoy' in award_type or 'general manager' in award_type:
                gmoy_count += 1
            elif 'ring' in award_type or 'championship' in award_type:
                rings_count += 1
            elif 'conference' in award_type:
                conf_titles_count += 1
            elif 'division' in award_type:
                div_titles_count += 1
    
    total_awards = weekly_awards + annual_awards
    
    return {
        "coy": coy_count,
        "gmoy": gmoy_count,
        "rings": rings_count,
        "conf_titles": conf_titles_count,
        "div_titles": div_titles_count,
        "total_awards": total_awards
    }
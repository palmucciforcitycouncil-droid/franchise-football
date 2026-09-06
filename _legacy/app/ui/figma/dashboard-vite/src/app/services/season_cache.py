# app/services/season_cache.py
from __future__ import annotations
from typing import Dict
from sqlmodel import Session, select
from app.services.coach_focus import compute_week_modifiers

def accumulate_team_dev_progress(sess: Session, team_id: int, season: int) -> float:
    """Accumulate weekly development progress for a team over the regular season (18 weeks)."""
    total_dev_progress = 0.0
    
    for week in range(1, 19):  # Regular season weeks 1-18
        mods = compute_week_modifiers(sess, team_id, season, week)
        total_dev_progress += mods.dev_progress_weekly
    
    return total_dev_progress

def get_team_dev_progress_total(sess: Session, team_id: int, season: int) -> Dict[str, float]:
    """Get total development progress for a team in a season."""
    dev_progress_total = accumulate_team_dev_progress(sess, team_id, season)
    
    return {
        "team_id": team_id,
        "season": season,
        "dev_progress_total": dev_progress_total
    }



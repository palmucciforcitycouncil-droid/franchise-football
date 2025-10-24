from __future__ import annotations
from sqlmodel import Session
from app.services.coach_focus_service import aggregate_weekly_effects, development_progression_bonus

def on_week_start(sess: Session, team_id: int, season: int, week: int):
    """
    Call this at the start of each week to ensure coach focus effects are computed and persisted.
    The sim engine can then fetch these effects via focus_hooks.get_focus_bundle().
    """
    # ensures snapshot exists and is persisted; sim can fetch via focus_hooks
    _ = aggregate_weekly_effects(sess, team_id, season, week)

def on_season_progression(sess: Session, team_id: int, season: int) -> float:
    """
    Call during annual progression. Returns a small scalar bonus [0..0.05]
    to add to player development rolls for players on this team.
    
    Returns:
        float: Development bonus multiplier (0.0 to 0.05)
    """
    return development_progression_bonus(sess, team_id, season)

def on_week_start_all_teams(sess: Session, season: int, week: int):
    """
    Convenience function to call on_week_start for all teams.
    Useful for bulk operations at week start.
    """
    from app.models.core_min import Team
    from sqlmodel import select
    
    teams = sess.exec(select(Team)).all()
    for team in teams:
        on_week_start(sess, team.team_id, season, week)

def on_season_progression_all_teams(sess: Session, season: int) -> dict[int, float]:
    """
    Convenience function to get development bonuses for all teams.
    Useful for bulk operations during season progression.
    
    Returns:
        dict[int, float]: Mapping of team_id to development bonus
    """
    from app.models.core_min import Team
    from sqlmodel import select
    
    teams = sess.exec(select(Team)).all()
    bonuses = {}
    for team in teams:
        bonuses[team.team_id] = on_season_progression(sess, team.team_id, season)
    
    return bonuses

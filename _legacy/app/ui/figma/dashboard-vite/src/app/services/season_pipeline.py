from __future__ import annotations
from sqlmodel import Session
from app.services.injury_service import weekly_heal

def on_week_advance(sess: Session, season: int, week: int):
    """
    Called when advancing from one week to the next.
    Heals all teams' injuries when progressing from prior week -> this week.
    """
    # Heal all teams' injuries when progressing from prior week -> this week
    weekly_heal(sess, season, week)

def on_season_advance(sess: Session, season: int):
    """
    Called when advancing from one season to the next.
    Resolves all remaining injuries from the previous season.
    """
    from sqlmodel import select
    from app.models.injury import Injury, InjuryStatus
    
    # Get all unresolved injuries from the previous season
    unresolved_injuries = list(sess.exec(select(Injury).where(
        Injury.season == season - 1,
        Injury.resolved == False  # noqa: E712
    )))
    
    # Resolve all previous season injuries
    for injury in unresolved_injuries:
        injury.resolved = True
        injury.status = InjuryStatus.ACTIVE
        injury.weeks_out_remaining = 0
        sess.add(injury)
    
    sess.commit()

def pregame_injury_setup(sess: Session, season: int, week: int, game_id: int, home_team_id: int, away_team_id: int):
    """
    Called before a game to set up injury checks.
    Returns list of players who should be checked for injuries.
    """
    from sqlmodel import select
    from app.models.player import Player
    
    # Get all active players for both teams
    home_players = list(sess.exec(select(Player).where(Player.team_id == home_team_id)))
    away_players = list(sess.exec(select(Player).where(Player.team_id == away_team_id)))
    
    return {
        "home_players": [{"player_id": p.player_id, "team_id": p.team_id, "pos": p.pos} for p in home_players],
        "away_players": [{"player_id": p.player_id, "team_id": p.team_id, "pos": p.pos} for p in away_players]
    }

def postgame_injury_cleanup(sess: Session, season: int, week: int, game_id: int):
    """
    Called after a game to clean up any injury-related data.
    Currently a placeholder for future functionality.
    """
    # Placeholder for future postgame injury processing
    pass
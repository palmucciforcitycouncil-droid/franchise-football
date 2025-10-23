from __future__ import annotations
from sqlmodel import Session, select
from app.services.boxscore import get_team, get_or_create_team_game, safe_inc
from app.testing.field_alias import incf

# Duck-type model imports (works with your existing models)
def _models():
    out={}
    for mod,name in [("app.models.team","Team"),("app.models.team_stats","TeamGame")]:
        try:
            m=__import__(mod, fromlist=[name]); out[name]=getattr(m,name)
        except Exception:
            out[name]=None
    return out
M=_models()

# Use minimal models if main ones aren't present
if M["Team"] is None:
    from app.models.core_min import Team as _Team
    M["Team"] = _Team
if M["TeamGame"] is None:
    from app.models.core_min import TeamGame as _TeamGame
    M["TeamGame"] = _TeamGame

def apply_touchdown(session: Session, game_id: int, off_team_id: int):
    """Apply touchdown scoring (+6 points to offense)."""
    Team=M["Team"]; TeamGame=M["TeamGame"]; 
    if not Team or not TeamGame: return
    t = get_team(session, Team, off_team_id)
    tg= get_or_create_team_game(session, TeamGame, game_id, off_team_id)
    if t: incf(t,"points",6); session.add(t)
    incf(tg,"points",6); session.add(tg); session.commit()

def apply_pat_or_two(session: Session, game_id: int, off_team_id: int, good: bool, two_point: bool):
    """Apply PAT or 2-point conversion scoring."""
    if not good: return
    pts = 2 if two_point else 1
    Team=M["Team"]; TeamGame=M["TeamGame"]; 
    if not Team or not TeamGame: return
    t = get_team(session, Team, off_team_id)
    tg= get_or_create_team_game(session, TeamGame, game_id, off_team_id)
    if t: incf(t,"points",pts); session.add(t)
    incf(tg,"points",pts); session.add(tg); session.commit()

def apply_field_goal(session: Session, game_id: int, off_team_id: int, good: bool):
    """Apply field goal scoring (+3 points if made)."""
    TeamGame=M["TeamGame"]; 
    if not TeamGame: return
    tg= get_or_create_team_game(session, TeamGame, game_id, off_team_id)
    incf(tg,"fga",1)
    if good: incf(tg,"fgm",1); incf(tg,"points",3)
    session.add(tg); session.commit()

def apply_punt(session: Session, game_id: int, off_team_id: int):
    """Record punt attempt."""
    TeamGame=M["TeamGame"]; 
    if not TeamGame: return
    tg= get_or_create_team_game(session, TeamGame, game_id, off_team_id)
    incf(tg,"punts",1)
    session.add(tg); session.commit()
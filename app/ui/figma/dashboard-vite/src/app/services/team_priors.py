from __future__ import annotations
from typing import Dict
from sqlmodel import Session, select
from app.models.team_priors import TeamPriors

def get_team_priors(session: Session, season: int, team_id: int) -> TeamPriors:
    row = session.exec(
        select(TeamPriors).where(TeamPriors.season==season, TeamPriors.team_id==team_id)
    ).first()
    if row: return row
    # default neutral priors if missing
    row = TeamPriors(season=season, team_id=team_id)
    session.add(row); session.commit()
    return row

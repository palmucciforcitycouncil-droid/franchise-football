# app/api/routes/awards.py
from __future__ import annotations
from typing import List
from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select
from app.db import get_engine
from app.models.awards import AwardResult
from app.api.dto import AwardName, AwardItem, AwardResponse, AwardsAllResponse

router = APIRouter(prefix="/awards", tags=["awards"])

def _session() -> Session:
    return Session(get_engine())

def _award_payload(season: int, award: AwardName, session: Session) -> AwardResponse:
    rows = session.exec(
        select(AwardResult)
        .where(AwardResult.season == season, AwardResult.award == award)
        .order_by(AwardResult.rank)
    ).all()
    items: List[AwardItem] = [
        AwardItem(
            rank=r.rank,
            player_id=r.player_id,
            team_id=r.team_id,
            player_name=r.player_name,
            team_abbr=r.team_abbr,
            position=r.position,
            score=r.score,
            tiebreaker=r.tiebreaker,
        )
        for r in rows
    ]
    return AwardResponse(season=season, award=award, top=items)

@router.get("/{season}", response_model=AwardsAllResponse)
def get_all_awards(season: int) -> AwardsAllResponse:
    with _session() as session:
        awards: List[AwardResponse] = []
        for aw in ["MVP","OPOY","DPOY","ROY","COY","GMOY"]:
            awards.append(_award_payload(season, aw, session))  # type: ignore[arg-type]
        # If all lists are empty, respond 404 to indicate not computed yet
        if all(len(a.top) == 0 for a in awards):
            raise HTTPException(status_code=404, detail="No awards found for season")
        return AwardsAllResponse(season=season, awards=awards)

@router.get("/{season}/{award}", response_model=AwardResponse)
def get_award(season: int, award: AwardName) -> AwardResponse:
    with _session() as session:
        payload = _award_payload(season, award, session)
        if len(payload.top) == 0:
            raise HTTPException(status_code=404, detail=f"No {award} results found for season")
        return payload

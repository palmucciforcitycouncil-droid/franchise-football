# app/api/routes/contracts_api.py
from __future__ import annotations
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.db import get_engine
from app.models.core_min import Player, Team
from app.models.contracts import Contract
from app.services.contracts_service import list_team_expiring, current_active_contract
from app.services.roster_moves import release_player
from app.services.negotiation_logic import player_accepts

router = APIRouter(prefix="/api/v1/contracts", tags=["contracts"])

def get_session():
    from sqlmodel import Session
    return Session(get_engine())

class ExpiringContractDTO(BaseModel):
    player_id: int
    name: str
    position: str
    age: int
    overall: int
    current_cap_hit: int
    desired_years: int
    desired_aav: int

class ExpiringContractsResponse(BaseModel):
    team_id: int
    season: int
    players: List[ExpiringContractDTO]

@router.get("/expiring", response_model=ExpiringContractsResponse)
def get_expiring(team_id: int = Query(...), season: int = Query(...), sess: Session = Depends(get_session)):
    rows = list_team_expiring(sess, team_id, season)
    payload: List[ExpiringContractDTO] = []
    for p, c in rows:
        payload.append(ExpiringContractDTO(
            player_id=p.id,
            name=p.name,
            position=p.pos,
            age=p.age,
            overall=p.rating,
            current_cap_hit=c.aav,
            desired_years=p.desired_years,
            desired_aav=p.desired_aav,
        ))
    return ExpiringContractsResponse(team_id=team_id, season=season, players=payload)

class Offer(BaseModel):
    aav: int = Field(ge=0)
    years: int = Field(ge=1, le=7)

class NegotiateResult(BaseModel):
    accepted: bool
    reason: Optional[str] = None

@router.post("/{player_id}/negotiate", response_model=NegotiateResult)
def negotiate(player_id: int, offer: Offer, season: int, sess: Session = Depends(get_session)):
    p = sess.get(Player, player_id)
    if not p:
        raise HTTPException(404, "PLAYER_NOT_FOUND")
    accepted = player_accepts(offer.aav, offer.years, p)
    if accepted:
        # close old contract
        cur = current_active_contract(sess, player_id)
        if cur:
            cur.is_active = False
            sess.add(cur)
        new_c = Contract(
            player_id=player_id,
            team_id=p.team_id,
            signed_on=date.today(),
            start_season=season,
            end_season=season + offer.years - 1,
            aav=offer.aav,
            is_active=True,
            acquired_via="EXTENSION",
        )
        sess.add(new_c)
        p.desired_aav = offer.aav
        p.desired_years = offer.years
        sess.add(p)
        sess.commit()
        return NegotiateResult(accepted=True)
    else:
        return NegotiateResult(accepted=False, reason="Below expectations")

@router.post("/{player_id}/release")
def release(player_id: int, sess: Session = Depends(get_session)):
    try:
        release_player(sess, player_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(404, str(e))

# Teams list endpoint for dropdown
@router.get("/teams/list")
def get_teams_list(sess: Session = Depends(get_session)):
    teams = sess.exec(select(Team)).all()
    return {
        "teams": [
            {"team_id": t.id, "name": t.name, "abbrev": t.abbrev}
            for t in teams
        ]
    }



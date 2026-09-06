from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session
from app.core.db import get_session
from app.services.cap_compliance import team_cap_summary, roster_size

router = APIRouter(prefix="/api/v1/cap", tags=["cap"])

class CapSummaryDTO(BaseModel):
    season: int
    team_id: int
    cap_limit: int
    active_aav: int
    dead_cap: int
    cap_used: int
    cap_space: int

@router.get("/summary", response_model=CapSummaryDTO)
def cap_summary(team_id: int = Query(...), season: int = Query(...), sess: Session = Depends(get_session)):
    data = team_cap_summary(sess, season, team_id)
    return CapSummaryDTO(**data)

# Roster size helper (QoL)
from fastapi import APIRouter as Rtr
router_roster = Rtr(prefix="/api/v1/roster", tags=["roster"])

@router_roster.get("/size")
def roster_size_api(team_id: int, sess: Session = Depends(get_session)):
    from app.services.cap_compliance import roster_size
    return {"team_id": team_id, "size": roster_size(sess, team_id)}

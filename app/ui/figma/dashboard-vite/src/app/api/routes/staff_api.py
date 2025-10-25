# app/api/routes/staff_api.py
from __future__ import annotations
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.db import get_engine
from app.models.coach import Coach, CoachFocus, CoachRole
from app.services.staff_service import (
    get_team_staff, get_free_agent_coaches, list_non_hc_on_other_teams,
    hire_or_extend, fire_coach, promote, set_coach_focus
)
from app.services.coach_ai import coach_accepts, Offer

router = APIRouter(prefix="/api/v1/staff", tags=["staff"])

def get_session():
    from sqlmodel import Session
    return Session(get_engine())

class CoachDTO(BaseModel):
    coach_id: int
    name: str
    age: int
    role: CoachRole
    team_id: int | None
    overall: int
    off_rating: int
    def_rating: int
    st_rating: int
    dev_rating: int
    discipline: int
    focus: CoachFocus
    seasons: int
    career_wins: int
    career_losses: int
    playoff_wins: int
    conf_titles: int
    div_titles: int
    sb_wins: int
    coach_of_year_awards: int

def to_dto(c: Coach) -> CoachDTO:
    return CoachDTO(
        coach_id=c.coach_id, name=f"{c.first_name} {c.last_name}", age=c.age, role=c.role,
        team_id=c.team_id, overall=c.overall, off_rating=c.off_rating, def_rating=c.def_rating,
        st_rating=c.st_rating, dev_rating=c.dev_rating, discipline=c.discipline, focus=c.focus,
        seasons=c.seasons, career_wins=c.career_wins, career_losses=c.career_losses,
        playoff_wins=c.playoff_wins, conf_titles=c.conf_titles, div_titles=c.div_titles,
        sb_wins=c.sb_wins, coach_of_year_awards=c.coach_of_year_awards
    )

@router.get("/team", response_model=List[CoachDTO])
def api_team_staff(team_id: int, sess: Session = Depends(get_session)):
    return [to_dto(c) for c in get_team_staff(sess, team_id)]

@router.get("/free_agents", response_model=List[CoachDTO])
def api_free_agents(sess: Session = Depends(get_session)):
    return [to_dto(c) for c in get_free_agent_coaches(sess)]

@router.get("/poachable", response_model=List[CoachDTO])
def api_poachable(sess: Session = Depends(get_session)):
    return [to_dto(c) for c in list_non_hc_on_other_teams(sess)]

class OfferBody(BaseModel):
    aav: int = Field(ge=0)
    years: int = Field(ge=1, le=7)
    role: CoachRole   # role being offered (handles promotions)
    team_id: int
    season: int

@router.post("/offer/{coach_id}")
def api_offer(coach_id: int, b: OfferBody, sess: Session = Depends(get_session)):
    c = sess.get(Coach, coach_id)
    if not c:
        raise HTTPException(404, "COACH_NOT_FOUND")
    promotion = (b.role == "HC" and c.role != "HC") or (b.role in ("OC","DC") and c.role == "AC")
    accepted = coach_accepts(Offer(b.aav, b.years), c, promotion)
    if accepted:
        c.role = b.role
        hire_or_extend(sess, c, b.team_id, b.season, b.aav, b.years, via=("PROMOTION" if promotion else "HIRE"))
        return {"accepted": True}
    return {"accepted": False, "reason": "Below expectations"}

class ExtendBody(BaseModel):
    aav: int
    years: int
    season: int

@router.post("/extend/{coach_id}")
def api_extend(coach_id: int, b: ExtendBody, sess: Session = Depends(get_session)):
    c = sess.get(Coach, coach_id)
    if not c:
        raise HTTPException(404, "COACH_NOT_FOUND")
    hire_or_extend(sess, c, c.team_id, b.season, b.aav, b.years, via="EXTENSION")
    return {"ok": True}

@router.post("/fire/{coach_id}")
def api_fire(coach_id: int, sess: Session = Depends(get_session)):
    fire_coach(sess, coach_id)
    return {"ok": True}

class PromoteBody(BaseModel):
    new_role: CoachRole
    season: int

@router.post("/promote/{coach_id}")
def api_promote(coach_id: int, body: PromoteBody, sess: Session = Depends(get_session)):
    promote(sess, coach_id, body.new_role, body.season)
    return {"ok": True}

class FocusBody(BaseModel):
    focus: CoachFocus

@router.post("/focus/{coach_id}")
def api_set_focus(coach_id: int, b: FocusBody, sess: Session = Depends(get_session)):
    set_coach_focus(sess, coach_id, b.focus)
    return {"ok": True}



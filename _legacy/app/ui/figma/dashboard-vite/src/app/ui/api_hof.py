# app/ui/api_hof.py
from __future__ import annotations
from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from app.db import get_session
from app.models.hof import HOFNominee, HOFInductee

router = APIRouter(prefix="/api/v1/hof", tags=["hof"])

class NomineeDTO(BaseModel):
    id: int
    subject_type: str
    subject_id: int
    ballot_class: int
    score: float
    votes_for: int
    votes_against: int
    inducted: bool

@router.get("/nominees", response_model=List[NomineeDTO])
def nominees(ballot_class: int, sess: Session = Depends(get_session)):
    """Get HOF nominees for a specific ballot class."""
    rows = list(sess.exec(select(HOFNominee).where(HOFNominee.ballot_class == ballot_class)))
    return [NomineeDTO(**r.model_dump()) for r in rows]

class InducteeDTO(BaseModel):
    id: int
    subject_type: str
    subject_id: int
    class_year: int
    citation: str

@router.get("/inductees", response_model=List[InducteeDTO])
def inductees(sess: Session = Depends(get_session)):
    """Get all HOF inductees."""
    rows = list(sess.exec(select(HOFInductee)))
    return [InducteeDTO(**r.model_dump()) for r in rows]

@router.get("/inductees/class/{class_year}", response_model=List[InducteeDTO])
def inductees_by_class(class_year: int, sess: Session = Depends(get_session)):
    """Get HOF inductees for a specific class year."""
    rows = list(sess.exec(select(HOFInductee).where(HOFInductee.class_year == class_year)))
    return [InducteeDTO(**r.model_dump()) for r in rows]

@router.get("/inductees/players", response_model=List[InducteeDTO])
def player_inductees(sess: Session = Depends(get_session)):
    """Get all player HOF inductees."""
    rows = list(sess.exec(select(HOFInductee).where(HOFInductee.subject_type == "PLAYER")))
    return [InducteeDTO(**r.model_dump()) for r in rows]

@router.get("/inductees/coaches", response_model=List[InducteeDTO])
def coach_inductees(sess: Session = Depends(get_session)):
    """Get all coach HOF inductees."""
    rows = list(sess.exec(select(HOFInductee).where(HOFInductee.subject_type == "COACH")))
    return [InducteeDTO(**r.model_dump()) for r in rows]



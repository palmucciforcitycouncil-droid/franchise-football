from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.data.session import get_db
from app.services.playoffs_service import build_bracket, run_playoffs, get_bracket_dto

router = APIRouter(prefix="/api/playoffs", tags=["playoffs"])

@router.post("/build/{season}")
def playoffs_build(season: int, session: Session = Depends(get_db)):
    build_bracket(session, season)
    return {"ok": True}

@router.post("/run/{season}")
def playoffs_run(season: int, seed: int = 2025, session: Session = Depends(get_db)):
    run_playoffs(session, season, seed)
    return {"ok": True}

# Read endpoint used by UI (/api/v1/playoffs in old UI; keep a compat alias here)
@router.get("/bracket/{season}")
def playoffs_bracket(season: int, session: Session = Depends(get_db)):
    return get_bracket_dto(session, season)
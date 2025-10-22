from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.data.session import get_db
from app.services.offseason_service import run_offseason
from app.models.season_models import Season

router = APIRouter(prefix="/api/offseason", tags=["offseason"])

@router.post("/run/{season}")
def offseason_run(season: int, seed: int = 2025, session: Session = Depends(get_db)):
    res = run_offseason(session, season, seed)
    return {"ok": True, "retired": res.retired, "progressed": res.progressed, "drafted": res.drafted}

@router.post("/advance-to-preseason/{next_season}")
def advance_to_preseason(next_season: int, seed: int = 2026, session: Session = Depends(get_db)):
    s = Season(season=next_season, current_week=1, phase="preseason", seed=seed)
    session.add(s); session.commit()
    return {"ok": True, "season": s.season, "phase": s.phase}

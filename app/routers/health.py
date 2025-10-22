from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.data.session import get_db
from app.models.sim_models import SimTeam as Team

router = APIRouter(prefix="/api", tags=["health"])

@router.get("/health")
def health(session: Session = Depends(get_db)):
    # simple db smoke
    try:
        count = session.query(Team).count()
    except Exception:
        count = -1
    return {
        "ok": True,
        "db_ok": count >= 0,
        "teams": count,
        "status": "healthy" if count >= 0 else "degraded"
    }

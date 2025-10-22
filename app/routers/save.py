from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.data.session import get_db
from app.services.save_service import export_league, import_league

router = APIRouter(prefix="/api", tags=["save"])

@router.post("/save")
def save_league(session: Session = Depends(get_db)):
    payload = export_league(session)
    return payload

@router.post("/load")
def load_league(payload: dict, session: Session = Depends(get_db)):
    try:
        import_league(session, payload, drop_all=True)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(400, f"LOAD_FAILED: {e}")

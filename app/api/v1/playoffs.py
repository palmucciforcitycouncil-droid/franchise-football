from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.data.session import get_db
from app.models.team import Team
from app.models.dto_playoffs import PlayoffBracketDTO
from app.services.playoffs_service import build_bracket_stub

router = APIRouter(prefix="/api/v1", tags=["playoffs"])

def _error_envelope(code: str, message: str, context: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "context": context or {}}}

@router.get("/playoffs", response_model=PlayoffBracketDTO | dict)
def get_playoff_bracket(db: Session = Depends(get_db)):
    teams = db.query(Team).all()
    if not teams or len(teams) < 32:
        return _error_envelope(
            "NOT_FOUND",
            "Insufficient team data to build playoff picture.",
            {"teams_found": len(teams) if teams else 0}
        )
    # Season year should come from LeagueState; safe default while wiring
    season_year = 2025
    return build_bracket_stub(season_year, teams)


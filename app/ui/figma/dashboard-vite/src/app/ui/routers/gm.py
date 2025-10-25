from __future__ import annotations
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from app.core.db import get_session
from app.services.team_cap import build_team_cap_summary

router = APIRouter(prefix="/api/gm", tags=["gm"])

@router.get("/{team_id}/cap-summary")
def get_cap_summary(
    team_id: int,
    base_year: int = Query(..., description="Base year for cap calculations"),
    horizon: int = Query(3, ge=1, le=5, description="Number of future years to project"),
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    Get salary cap summary for a team across multiple years.
    
    Args:
        team_id: Team ID to get cap summary for
        base_year: Base year for calculations (typically current league year)
        horizon: Number of future years to project (1-5, default 3)
    
    Returns:
        Dictionary with team_id, base_year, and items array
    """
    try:
        # Validate team exists
        from app.models.team import Team
        team = session.get(Team, team_id)
        if not team:
            raise HTTPException(status_code=404, detail=f"Team {team_id} not found")
        
        # Validate base_year is reasonable
        if base_year < 2020 or base_year > 2050:
            raise HTTPException(status_code=400, detail="Base year must be between 2020 and 2050")
        
        # Build cap summary
        items = build_team_cap_summary(session, team_id, base_year, horizon)
        
        return {
            "team_id": team_id,
            "base_year": base_year,
            "items": items
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating cap summary: {str(e)}")

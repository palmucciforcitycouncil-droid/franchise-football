"""
FastAPI endpoints for Advanced Stats API.
Exposes game boxes, leaders, and season/career stats with split/role filters.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, Literal, List
from sqlmodel import Session
from app.ui.dto import (
    GameBoxDTO, PlayerSeasonLineDTO, TeamSeasonLineDTO, LeadersDTO
)
from app.services.stats.rollup import rollup_game_stats
from app.services.stats.materialize import materialize_season, materialize_career
from app.services.stats.validators import validate_game_totals
from app.services.stats.read import (
    get_game_box, get_leaders, get_player_season_lines, get_team_season_lines
)

# Dependency to get database session
def get_session():
    """Get database session - simplified for now"""
    # In a real implementation, this would get the actual session
    return None

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/games/{game_id}", response_model=GameBoxDTO)
def api_get_game_box(game_id: int, session: Session = Depends(get_session)):
    """Get complete game box score with advanced stats."""
    box = get_game_box(game_id, session)
    if not box:
        raise HTTPException(status_code=404, detail="Game not found")
    return box


@router.get("/leaders", response_model=LeadersDTO)
def api_get_leaders(
    year: Optional[int] = None,
    stat: str = Query(..., description="stat key, e.g., 'passing_yards'"),
    top: int = 10,
    split: Optional[Literal["third_down","fourth_down","red_zone","goal_to_go","two_minute"]] = None,
    role: Optional[Literal["ol","dl","lb","db","st","qb","rb","wr","te"]] = None,
    scope: Literal["regular","playoffs","both"] = "regular",
    session: Session = Depends(get_session)
):
    """Get statistical leaders with advanced filtering."""
    return get_leaders(
        year=year, stat=stat, top=top, split=split, role=role, scope=scope, session=session
    )


@router.get("/players/season", response_model=List[PlayerSeasonLineDTO])
def api_get_player_season(
    year: int,
    team_id: Optional[int] = None,
    position: Optional[str] = None,
    split: Optional[Literal["third_down","fourth_down","red_zone","goal_to_go","two_minute"]] = None,
    session: Session = Depends(get_session)
):
    """Get player season stat lines with filtering."""
    return get_player_season_lines(
        year=year, team_id=team_id, position=position, split=split, session=session
    )


@router.get("/teams/season", response_model=List[TeamSeasonLineDTO])
def api_get_team_season(
    year: int,
    conference: Optional[str] = None,
    division: Optional[str] = None,
    split: Optional[Literal["third_down","fourth_down","red_zone","goal_to_go","two_minute"]] = None,
    session: Session = Depends(get_session)
):
    """Get team season stat lines with filtering."""
    return get_team_season_lines(
        year=year, conference=conference, division=division, split=split, session=session
    )


@router.post("/rollup/game/{game_id}")
def api_rollup_game_stats(game_id: int, session: Session = Depends(get_session)):
    """Roll up game stats from PBP events."""
    try:
        result = rollup_game_stats(game_id, session)
        return {"message": f"Successfully rolled up game {game_id}", "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/materialize/season/{year}")
def api_materialize_season(year: int, session: Session = Depends(get_session)):
    """Materialize season stats from game stats."""
    try:
        result = materialize_season(year, session)
        return {"message": f"Successfully materialized season {year}", "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/materialize/career")
def api_materialize_career(session: Session = Depends(get_session)):
    """Materialize career stats from season stats."""
    try:
        result = materialize_career(session)
        return {"message": "Successfully materialized career stats", "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/validate")
def api_validate_stats(game_id: Optional[int] = None, session: Session = Depends(get_session)):
    """Validate stats consistency."""
    try:
        messages = validate_game_totals(game_id, session)
        return {
            "message": "Validation complete",
            "game_id": game_id,
            "messages": messages,
            "total_messages": len(messages),
            "errors": len([m for m in messages if m.level == "error"]),
            "warnings": len([m for m in messages if m.level == "warning"])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/health")
def api_health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "advanced_stats_api"}

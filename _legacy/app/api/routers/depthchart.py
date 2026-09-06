"""
Depth Chart API Router with Persistence and Constraints
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from datetime import datetime
from sqlmodel import Session, create_engine

from app.models.depthchart import (
    DepthChartDTO, 
    AutoFillRequestDTO, 
    AutoFillResponseDTO,
    DepthSlotUpdateDTO,
    DepthChartBulkUpdateDTO
)
from app.services.depthchart_service import DepthChartService

# Database setup (in real app, this would be dependency injection)
engine = create_engine("sqlite:///./franchise_football.db", echo=True)

def get_db():
    with Session(engine) as session:
        yield session

router = APIRouter()

@router.get("/teams/{team_id}/depthchart")
async def get_depth_chart(
    team_id: str,
    season: Optional[int] = Query(None, description="Season year"),
    db: Session = Depends(get_db)
) -> DepthChartDTO:
    """
    Get current depth chart for a team
    
    Args:
        team_id: Team identifier (e.g., "NE")
        season: Season year (defaults to current year)
        db: Database session
    
    Returns:
        Depth chart data with all slots (filled and empty)
    """
    if season is None:
        season = datetime.now().year
    
    try:
        service = DepthChartService(db)
        return service.get_depthchart(team_id, season)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve depth chart: {str(e)}")

@router.put("/teams/{team_id}/depthchart")
async def set_depth_chart_bulk(
    team_id: str,
    request: DepthChartBulkUpdateDTO,
    db: Session = Depends(get_db)
) -> DepthChartDTO:
    """
    Set entire depth chart with bulk validation
    
    Args:
        team_id: Team identifier
        request: Bulk update request with season and slots
        db: Database session
    
    Returns:
        Updated depth chart
    
    Raises:
        409: If duplicate players found in same position group
    """
    try:
        service = DepthChartService(db)
        
        # Convert DTOs to dicts for service
        slots_data = []
        for slot_dto in request.slots:
            slots_data.append({
                "position": slot_dto.position,
                "slot": slot_dto.slot,
                "player_id": slot_dto.player_id
            })
        
        return service.set_depth_bulk(team_id, request.season, slots_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update depth chart: {str(e)}")

@router.patch("/teams/{team_id}/depthchart/slot")
async def set_depth_slot(
    team_id: str,
    request: DepthSlotUpdateDTO,
    db: Session = Depends(get_db)
) -> DepthChartDTO:
    """
    Set a single depth chart slot with constraint validation
    
    Args:
        team_id: Team identifier
        request: Single slot update request
        db: Database session
    
    Returns:
        Updated depth chart
    
    Raises:
        409: If player already assigned to another slot in same position group
    """
    try:
        service = DepthChartService(db)
        return service.set_depth_slot(
            team_id, 
            request.season, 
            request.position, 
            request.slot, 
            request.player_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update depth slot: {str(e)}")

@router.post("/teams/{team_id}/depthchart/auto_fill")
async def auto_fill_depth_chart(
    team_id: str,
    request: AutoFillRequestDTO,
    db: Session = Depends(get_db)
) -> AutoFillResponseDTO:
    """
    Auto-fill empty slots only, preserving user choices
    
    Args:
        team_id: Team identifier
        request: Auto-fill request with season
        db: Database session
    
    Returns:
        Auto-fill response with updated chart and warnings
    """
    try:
        service = DepthChartService(db)
        updated_chart, warnings = service.auto_fill(team_id, request.season)
        
        return AutoFillResponseDTO(
            success=True,
            message=f"Auto-fill completed for {team_id} season {request.season}",
            depth_chart=updated_chart
        )
        
    except Exception as e:
        return AutoFillResponseDTO(
            success=False,
            message=f"Auto-fill failed: {str(e)}",
            depth_chart=None
        )

@router.get("/teams/{team_id}/depthchart/positions")
async def get_position_requirements(team_id: str) -> dict:
    """
    Get position requirements for depth chart
    
    Args:
        team_id: Team identifier
    
    Returns:
        Position requirements mapping
    """
    from app.models.depthchart import DEPTH_CHART_SLOTS
    
    return {
        "team_id": team_id,
        "position_requirements": {pos: len(slots) for pos, slots in DEPTH_CHART_SLOTS.items()}
    }

@router.get("/teams/{team_id}/roster")
async def get_team_roster(
    team_id: str,
    season: Optional[int] = Query(None, description="Season year"),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get team roster for depth chart dropdowns
    
    Args:
        team_id: Team identifier
        season: Season year
        db: Database session
    
    Returns:
        Team roster with player details
    """
    if season is None:
        season = datetime.now().year
    
    try:
        service = DepthChartService(db)
        roster = service._get_team_roster(team_id, season)
        
        return {
            "team_id": team_id,
            "season": season,
            "players": roster
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve roster: {str(e)}")

# Health check endpoint
@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "depth_chart",
        "timestamp": datetime.now().isoformat()
    }
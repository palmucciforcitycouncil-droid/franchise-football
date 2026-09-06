"""
Simulation API endpoints for season orchestration
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, Optional
import tempfile
from pathlib import Path

from ..engine.season_loop import (
    new_league_state, sim_week, sim_season, sim_years, 
    get_resume_point, resume_from_point, SimConfig, ResumePoint
)
from ..engine.save_manager import (
    export_league, import_league, get_state_summary, validate_state_integrity
)
from ..models.league_state import LeagueState

router = APIRouter(prefix="/sim", tags=["simulation"])

# Global league state (in production, this would be stored in database)
_current_state: Optional[LeagueState] = None


def get_current_state() -> LeagueState:
    """Get current league state, creating new one if none exists"""
    global _current_state
    if _current_state is None:
        _current_state = new_league_state(2025, seed=2025)
    return _current_state


def set_current_state(state: LeagueState) -> None:
    """Set current league state"""
    global _current_state
    _current_state = state


@router.post("/week")
async def simulate_week(
    season: Optional[int] = Query(None, description="Season year (uses current if omitted)"),
    week: int = Query(..., description="Week to simulate (1-18)"),
    quarter_length: int = Query(15, description="Quarter length in minutes"),
    apply_sfs: bool = Query(True, description="Apply Score Fidelity System"),
    fail_fast: bool = Query(True, description="Stop on first error")
):
    """Simulate all games for a specific week"""
    try:
        state = get_current_state()
        
        # Use provided season or current season
        if season is not None:
            state.season_year = season
        
        # Validate week
        if week < 1 or week > 18:
            raise HTTPException(status_code=400, detail="Week must be between 1 and 18")
        
        # Create simulation config
        cfg = SimConfig(
            quarter_length_min=quarter_length,
            apply_sfs=apply_sfs,
            fail_fast=fail_fast
        )
        
        # Simulate the week
        state = sim_week(state, week, cfg)
        set_current_state(state)
        
        # Return summary
        return {
            "status": "success",
            "season_year": state.season_year,
            "week": week,
            "games_played": state.metrics.games_played_this_week,
            "total_games": state.metrics.total_games_played,
            "summary": {
                "games_played": state.metrics.games_played_this_week,
                "total_games": state.metrics.total_games_played,
                "average_points": state.metrics.average_points_per_game,
                "plays_per_game": state.metrics.plays_per_game,
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.post("/season")
async def simulate_season(
    season: Optional[int] = Query(None, description="Season year (uses current if omitted)"),
    quarter_length: int = Query(15, description="Quarter length in minutes"),
    enable_preseason: bool = Query(False, description="Enable preseason"),
    apply_sfs: bool = Query(True, description="Apply Score Fidelity System"),
    fail_fast: bool = Query(True, description="Stop on first error")
):
    """Simulate a complete season"""
    try:
        state = get_current_state()
        
        # Use provided season or current season
        if season is not None:
            state.season_year = season
        
        # Create simulation config
        cfg = SimConfig(
            quarter_length_min=quarter_length,
            enable_preseason=enable_preseason,
            apply_sfs=apply_sfs,
            fail_fast=fail_fast
        )
        
        # Simulate the season
        state = sim_season(state, cfg)
        set_current_state(state)
        
        # Return summary
        return {
            "status": "success",
            "season_year": state.season_year,
            "champion_team_id": state.last_champion_team_id,
            "total_games": state.metrics.total_games_played,
            "regular_games": state.metrics.regular_games_played,
            "playoff_games": state.metrics.playoff_games_played,
            "summary": {
                "champion_team_id": state.last_champion_team_id,
                "total_games": state.metrics.total_games_played,
                "regular_games": state.metrics.regular_games_played,
                "playoff_games": state.metrics.playoff_games_played,
                "average_points": state.metrics.average_points_per_game,
                "field_goal_percentage": state.metrics.field_goal_percentage,
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Season simulation failed: {str(e)}")


@router.post("/years")
async def simulate_years(
    n: int = Query(..., description="Number of seasons to simulate"),
    quarter_length: int = Query(15, description="Quarter length in minutes"),
    enable_preseason: bool = Query(False, description="Enable preseason"),
    apply_sfs: bool = Query(True, description="Apply Score Fidelity System"),
    fail_fast: bool = Query(True, description="Stop on first error")
):
    """Simulate multiple consecutive seasons"""
    try:
        if n < 1 or n > 10:
            raise HTTPException(status_code=400, detail="Number of seasons must be between 1 and 10")
        
        state = get_current_state()
        
        # Create simulation config
        cfg = SimConfig(
            quarter_length_min=quarter_length,
            enable_preseason=enable_preseason,
            apply_sfs=apply_sfs,
            fail_fast=fail_fast
        )
        
        # Simulate the years
        state = sim_years(state, n, cfg)
        set_current_state(state)
        
        # Return summary
        return {
            "status": "success",
            "seasons_simulated": n,
            "final_season_year": state.season_year,
            "total_games": state.metrics.total_games_played,
            "champions": state.history.champions[-n:] if len(state.history.champions) >= n else state.history.champions,
            "summary": {
                "seasons_simulated": n,
                "final_season_year": state.season_year,
                "total_games": state.metrics.total_games_played,
                "champions": state.history.champions[-n:] if len(state.history.champions) >= n else state.history.champions,
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multi-season simulation failed: {str(e)}")


@router.post("/save")
async def save_league(
    request: Dict[str, Any] = Body(..., description="Save request with path")
):
    """Save current league state and database"""
    try:
        path = request.get("path")
        if not path:
            raise HTTPException(status_code=400, detail="Path is required")
        
        include_db = request.get("include_db", True)
        
        state = get_current_state()
        export_league(path, state, include_db=include_db)
        
        return {
            "status": "success",
            "path": path,
            "include_db": include_db,
            "message": f"League state saved to {path}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Save failed: {str(e)}")


@router.post("/load")
async def load_league(
    request: Dict[str, Any] = Body(..., description="Load request with path")
):
    """Load league state and optionally restore database"""
    try:
        path = request.get("path")
        if not path:
            raise HTTPException(status_code=400, detail="Path is required")
        
        # Import league state
        state = import_league(path)
        
        # Validate state integrity
        if not validate_state_integrity(state):
            raise HTTPException(status_code=400, detail="Invalid or corrupted league state")
        
        set_current_state(state)
        
        return {
            "status": "success",
            "path": path,
            "message": f"League state loaded from {path}",
            "state_summary": get_state_summary(state)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Load failed: {str(e)}")


@router.get("/state")
async def get_league_state():
    """Get current league state metadata"""
    try:
        state = get_current_state()
        return {
            "status": "success",
            "state": get_state_summary(state),
            "metrics": {
                "total_games": state.metrics.total_games_played,
                "regular_games": state.metrics.regular_games_played,
                "playoff_games": state.metrics.playoff_games_played,
                "average_points": state.metrics.average_points_per_game,
                "field_goal_percentage": state.metrics.field_goal_percentage,
                "plays_per_game": state.metrics.plays_per_game,
                "total_injuries": state.metrics.total_injuries,
            },
            "sfs_knobs": {
                "pace_mult": state.sfs_knobs.pace_mult,
                "fg_bias_mult": state.sfs_knobs.fg_bias_mult,
                "two_point_bias": state.sfs_knobs.two_point_bias,
                "explosive_play_mult": state.sfs_knobs.explosive_play_mult,
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get state: {str(e)}")


@router.post("/resume")
async def resume_simulation(
    request: Dict[str, Any] = Body(..., description="Resume request")
):
    """Resume simulation from a specific point"""
    try:
        # Get resume point from request
        resume_data = request.get("resume_point")
        if not resume_data:
            raise HTTPException(status_code=400, detail="Resume point is required")
        
        rp = ResumePoint(
            season_year=resume_data["season_year"],
            phase=resume_data["phase"],
            week=resume_data["week"],
            game_index=resume_data["game_index"]
        )
        
        # Get simulation config
        cfg_data = request.get("config", {})
        cfg = SimConfig(
            quarter_length_min=cfg_data.get("quarter_length_min", 15),
            enable_preseason=cfg_data.get("enable_preseason", False),
            apply_sfs=cfg_data.get("apply_sfs", True),
            fail_fast=cfg_data.get("fail_fast", True),
            save_every_n_games=cfg_data.get("save_every_n_games", 0)
        )
        
        state = get_current_state()
        state = resume_from_point(state, rp, cfg)
        set_current_state(state)
        
        return {
            "status": "success",
            "message": "Simulation resumed successfully",
            "state_summary": get_state_summary(state)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume failed: {str(e)}")


@router.get("/resume-point")
async def get_current_resume_point():
    """Get current resume point for the league state"""
    try:
        state = get_current_state()
        rp = get_resume_point(state)
        
        return {
            "status": "success",
            "resume_point": {
                "season_year": rp.season_year,
                "phase": rp.phase,
                "week": rp.week,
                "game_index": rp.game_index
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get resume point: {str(e)}")


@router.post("/reset")
async def reset_league(
    season_year: int = Query(2025, description="Starting season year"),
    seed: int = Query(2025, description="Random seed")
):
    """Reset league to a new state"""
    try:
        state = new_league_state(season_year, seed)
        set_current_state(state)
        
        return {
            "status": "success",
            "message": f"League reset to season {season_year} with seed {seed}",
            "state_summary": get_state_summary(state)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")



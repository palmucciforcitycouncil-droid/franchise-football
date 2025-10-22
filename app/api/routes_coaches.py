"""
Coach API routes with modal support
"""
from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import Optional
import json

router = APIRouter()
templates = Jinja2Templates(directory="app/ui/templates")

@router.get("/coaches/{coach_id}")
async def get_coach_card(
    request: Request,
    coach_id: str,
    modal: Optional[int] = Query(None, description="Return modal content if 1")
):
    """
    Get coach card - either full page or modal fragment
    
    Args:
        coach_id: Coach identifier
        modal: If 1, return modal HTML fragment; otherwise return full page
    """
    
    # Mock coach data - replace with actual database query
    coach_data = {
        "id": coach_id,
        "name": "Pat Sample",
        "position": "Head Coach",
        "team_name": "New England Patriots",
        "age": 52,
        "experience": 15,
        "overall_rating": 88,
        "morale": 85,
        "offense_rating": 92,
        "defense_rating": 84,
        "special_teams_rating": 76,
        "leadership": 90,
        "discipline": 87,
        "motivation": 89,
        "player_development": 85,
        "scouting": 82,
        "previous_team": "Tampa Bay Buccaneers",
        "college": "Michigan",
        "career_wins": 156,
        "career_losses": 89,
        "philosophy": "A balanced approach focusing on fundamental football with innovative offensive schemes and aggressive defensive pressure.",
        "traits": ["Offensive Genius", "Player Developer", "Strong Leader"],
        "offensive_scheme": "West Coast",
        "defensive_scheme": "3-4 Base",
        "special_teams_focus": "Return Game",
        "aggressiveness": 75,
        "conservative": 25,
        "clock_management": 85,
        "salary": 12000000,
        "contract_years": 4,
        "signing_bonus": 25000000,
        "job_security": "High",
        "season_wins": 10,
        "season_losses": 7,
        "career_highlights": [
            "Super Bowl Champion (2020)",
            "Coach of the Year (2020)",
            "Led team to 3 consecutive playoff appearances",
            "Developed 5 Pro Bowl players"
        ],
        "offense_change": 8,
        "defense_change": 12,
        "avatar_url": "/static/img/coaches/pat_sample.png"
    }
    
    # If modal=1, return just the modal content fragment
    if modal == 1:
        return templates.TemplateResponse(
            "coach_card_modal.html",
            {"request": request, "coach": coach_data}
        )
    
    # Otherwise return full page (existing behavior)
    return templates.TemplateResponse(
        "coach_card_full.html",  # This would be the full page template
        {
            "request": request,
            "coach": coach_data,
            "page_title": f"{coach_data['name']} - Coach Card"
        }
    )

@router.get("/coaches/{coach_id}/record")
async def get_coach_record(coach_id: str, season: Optional[int] = None):
    """Get coach win/loss record"""
    # Mock record data
    record = {
        "coach_id": coach_id,
        "season": season or 2025,
        "wins": 10,
        "losses": 7,
        "ties": 0,
        "win_percentage": 58.8,
        "playoff_appearances": 3,
        "championships": 1,
        "career_wins": 156,
        "career_losses": 89,
        "career_ties": 2
    }
    
    return record

@router.get("/coaches/{coach_id}/philosophy")
async def get_coach_philosophy(coach_id: str):
    """Get detailed coaching philosophy and scheme information"""
    # Mock philosophy data
    philosophy = {
        "coach_id": coach_id,
        "offensive_philosophy": "West Coast offense with emphasis on quick passes and YAC",
        "defensive_philosophy": "Aggressive 3-4 defense with heavy blitz packages",
        "special_teams_philosophy": "Focus on return game and field position",
        "player_development": "Emphasis on fundamentals and mental toughness",
        "game_management": "Conservative in field position, aggressive in red zone",
        "personnel_preferences": {
            "quarterback": "Pocket passer with quick release",
            "running_back": "Versatile back who can catch",
            "wide_receiver": "Route runners with good hands",
            "defensive_line": "Athletic pass rushers",
            "linebacker": "Versatile coverage and rush ability"
        }
    }
    
    return philosophy

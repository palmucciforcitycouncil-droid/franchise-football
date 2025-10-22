"""
Player API routes with modal support
"""
from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import Optional
import json

router = APIRouter()
templates = Jinja2Templates(directory="app/ui/templates")

@router.get("/players/{player_id}")
async def get_player_card(
    request: Request,
    player_id: str,
    modal: Optional[int] = Query(None, description="Return modal content if 1")
):
    """
    Get player card - either full page or modal fragment
    
    Args:
        player_id: Player identifier
        modal: If 1, return modal HTML fragment; otherwise return full page
    """
    
    # Mock player data - replace with actual database query
    player_data = {
        "id": player_id,
        "name": "John Sample",
        "position": "QB",
        "team_name": "New England Patriots",
        "jersey_number": 12,
        "age": 28,
        "experience": 6,
        "overall_rating": 84,
        "speed": 78,
        "strength": 62,
        "agility": 82,
        "throw_power": 91,
        "throw_accuracy": 86,
        "catching": 48,
        "tackling": 22,
        "awareness": 85,
        "potential": 88,
        "stamina": 92,
        "injury_rating": 18,
        "morale": 74,
        "height": "6'2\"",
        "weight": 215,
        "college": "Alabama",
        "draft_year": 2018,
        "draft_round": 1,
        "traits": ["Clutch Performer", "Strong Arm", "Field General"],
        "current_season": 2025,
        "season_stats": {
            "Games Played": 5,
            "Passing Yards": 1420,
            "Passing TDs": 10,
            "Interceptions": 4,
            "Completion %": "68.6%",
            "Passer Rating": 101.4
        },
        "salary": 8500000,
        "contract_years": 2,
        "signing_bonus": 15000000,
        "trade_value": "High",
        "injury_status": "Healthy",
        "injury_description": None,
        "avatar_url": "/static/img/players/john_sample.png"
    }
    
    # If modal=1, return just the modal content fragment
    if modal == 1:
        return templates.TemplateResponse(
            "player_card_modal.html",
            {"request": request, "player": player_data, "current_season": 2025}
        )
    
    # Otherwise return full page (existing behavior)
    return templates.TemplateResponse(
        "player_card_full.html",  # This would be the full page template
        {
            "request": request,
            "player": player_data,
            "current_season": 2025,
            "page_title": f"{player_data['name']} - Player Card"
        }
    )

@router.get("/players/{player_id}/stats")
async def get_player_stats(player_id: str, season: Optional[int] = None):
    """Get detailed player statistics"""
    # Mock stats data
    stats = {
        "player_id": player_id,
        "season": season or 2025,
        "passing": {
            "attempts": 172,
            "completions": 118,
            "completion_pct": 68.6,
            "yards": 1420,
            "touchdowns": 10,
            "interceptions": 4,
            "rating": 101.4
        },
        "rushing": {
            "attempts": 24,
            "yards": 156,
            "touchdowns": 2,
            "average": 6.5
        },
        "receiving": {
            "targets": 0,
            "receptions": 0,
            "yards": 0,
            "touchdowns": 0
        }
    }
    
    return stats

@router.get("/players/{player_id}/contract")
async def get_player_contract(player_id: str):
    """Get player contract details"""
    # Mock contract data
    contract = {
        "player_id": player_id,
        "salary": 8500000,
        "bonus": 15000000,
        "years_remaining": 2,
        "total_value": 32000000,
        "guaranteed": 20000000,
        "trade_clause": False,
        "no_trade_clause": False
    }
    
    return contract

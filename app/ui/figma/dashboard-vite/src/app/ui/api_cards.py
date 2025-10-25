from __future__ import annotations
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from sqlmodel import Session
from app.core.db import get_session
from app.services.cards_service import (
    build_player_card, 
    build_coach_card, 
    build_team_card,
    get_card_summary
)

router = APIRouter(prefix="/api/v1/cards", tags=["cards"])

class CardRes(BaseModel):
    """Response wrapper for card data."""
    data: Dict[str, Any]

class CardSummaryRes(BaseModel):
    """Response for card summary."""
    summary: Dict[str, Any]

class CardListRes(BaseModel):
    """Response for card lists."""
    cards: List[Dict[str, Any]]
    total: int

@router.get("/player", response_model=CardRes)
def get_player_card(
    player_id: int = Query(..., description="Player ID to get card for"),
    season: int = Query(..., description="Season to get data for"),
    recent: int = Query(3, ge=0, le=10, description="Number of recent games to include"),
    sess: Session = Depends(get_session)
):
    """Get comprehensive player card with bio, contract, stats, market info, and actions."""
    try:
        card_data = build_player_card(sess, player_id, season)
        
        # Check for errors
        if "error" in card_data:
            raise HTTPException(status_code=404, detail=card_data["error"])
        
        # Override recent games with custom limit if different from default
        if recent != 3 and "bio" in card_data:
            try:
                from app.services.recent_games_service import recent_player_games
                pid = card_data["bio"]["player_id"]
                card_data["recent_games"] = recent_player_games(sess, pid, season, limit=recent)
            except Exception:
                pass  # Keep original recent_games if override fails
        
        return CardRes(data=card_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building player card: {str(e)}")

@router.get("/coach", response_model=CardRes)
def get_coach_card(
    coach_id: int = Query(..., description="Coach ID to get card for"),
    season: int = Query(..., description="Season to get data for"),
    recent: int = Query(3, ge=0, le=10, description="Number of recent games to include"),
    sess: Session = Depends(get_session)
):
    """Get comprehensive coach card with bio, contract, stats, focus, and actions."""
    try:
        card_data = build_coach_card(sess, coach_id, season)
        
        # Check for errors
        if "error" in card_data:
            raise HTTPException(status_code=404, detail=card_data["error"])
        
        # Override recent games with custom limit if different from default
        if recent != 3 and "bio" in card_data:
            try:
                from app.services.recent_games_service import recent_coach_games
                cid = card_data["bio"]["coach_id"]
                card_data["recent_games"] = recent_coach_games(sess, cid, season, limit=recent)
            except Exception:
                pass  # Keep original recent_games if override fails
        
        return CardRes(data=card_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building coach card: {str(e)}")

@router.get("/team", response_model=CardRes)
def get_team_card(
    team_id: int = Query(..., description="Team ID to get card for"),
    season: int = Query(..., description="Season to get data for"),
    sess: Session = Depends(get_session)
):
    """Get team card with roster summary and coaching staff."""
    try:
        card_data = build_team_card(sess, team_id, season)
        
        # Check for errors
        if "error" in card_data:
            raise HTTPException(status_code=404, detail=card_data["error"])
        
        return CardRes(data=card_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building team card: {str(e)}")

@router.get("/summary", response_model=CardSummaryRes)
def get_cards_summary(
    season: int = Query(..., description="Season to get summary for"),
    sess: Session = Depends(get_session)
):
    """Get summary of all cards in the system."""
    try:
        summary = get_card_summary(sess, season)
        return CardSummaryRes(summary=summary)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cards summary: {str(e)}")

@router.get("/players/batch", response_model=CardListRes)
def get_player_cards_batch(
    player_ids: str = Query(..., description="Comma-separated list of player IDs"),
    season: int = Query(..., description="Season to get data for"),
    sess: Session = Depends(get_session)
):
    """Get multiple player cards in a single request."""
    try:
        # Parse player IDs
        try:
            ids = [int(x.strip()) for x in player_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid player IDs format")
        
        if len(ids) > 50:  # Limit batch size
            raise HTTPException(status_code=400, detail="Too many player IDs (max 50)")
        
        cards = []
        for player_id in ids:
            card_data = build_player_card(sess, player_id, season)
            if "error" not in card_data:
                cards.append(card_data)
        
        return CardListRes(cards=cards, total=len(cards))
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building player cards batch: {str(e)}")

@router.get("/coaches/batch", response_model=CardListRes)
def get_coach_cards_batch(
    coach_ids: str = Query(..., description="Comma-separated list of coach IDs"),
    season: int = Query(..., description="Season to get data for"),
    sess: Session = Depends(get_session)
):
    """Get multiple coach cards in a single request."""
    try:
        # Parse coach IDs
        try:
            ids = [int(x.strip()) for x in coach_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid coach IDs format")
        
        if len(ids) > 50:  # Limit batch size
            raise HTTPException(status_code=400, detail="Too many coach IDs (max 50)")
        
        cards = []
        for coach_id in ids:
            card_data = build_coach_card(sess, coach_id, season)
            if "error" not in card_data:
                cards.append(card_data)
        
        return CardListRes(cards=cards, total=len(cards))
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building coach cards batch: {str(e)}")

@router.get("/team/{team_id}/roster", response_model=CardListRes)
def get_team_roster_cards(
    team_id: int,
    season: int = Query(..., description="Season to get data for"),
    sess: Session = Depends(get_session)
):
    """Get player cards for all players on a team."""
    try:
        # Import Player model defensively
        try:
            from app.models.player import Player
        except ImportError:
            raise HTTPException(status_code=500, detail="Player model not available")
        
        # Get all players on the team
        players = list(sess.exec(Player.select().where(Player.team_id == team_id)))
        
        cards = []
        for player in players:
            player_id = getattr(player, "player_id", None)
            if player_id:
                card_data = build_player_card(sess, player_id, season)
                if "error" not in card_data:
                    cards.append(card_data)
        
        return CardListRes(cards=cards, total=len(cards))
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building team roster cards: {str(e)}")

@router.get("/team/{team_id}/staff", response_model=CardListRes)
def get_team_staff_cards(
    team_id: int,
    season: int = Query(..., description="Season to get data for"),
    sess: Session = Depends(get_session)
):
    """Get coach cards for all coaches on a team."""
    try:
        # Import Coach model defensively
        try:
            from app.models.coach import Coach
        except ImportError:
            raise HTTPException(status_code=500, detail="Coach model not available")
        
        # Get all coaches on the team
        coaches = list(sess.exec(Coach.select().where(Coach.team_id == team_id)))
        
        cards = []
        for coach in coaches:
            coach_id = getattr(coach, "coach_id", None)
            if coach_id:
                card_data = build_coach_card(sess, coach_id, season)
                if "error" not in card_data:
                    cards.append(card_data)
        
        return CardListRes(cards=cards, total=len(cards))
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building team staff cards: {str(e)}")

@router.get("/free_agents", response_model=CardListRes)
def get_free_agent_cards(
    season: int = Query(..., description="Season to get data for"),
    position: Optional[str] = Query(None, description="Filter by position"),
    min_overall: Optional[int] = Query(None, description="Minimum overall rating"),
    max_overall: Optional[int] = Query(None, description="Maximum overall rating"),
    sess: Session = Depends(get_session)
):
    """Get player cards for all free agents with optional filters."""
    try:
        # Import Player model defensively
        try:
            from app.models.player import Player
        except ImportError:
            raise HTTPException(status_code=500, detail="Player model not available")
        
        # Build query for free agents
        query = Player.select().where(Player.team_id.is_(None))
        
        if position:
            query = query.where(Player.pos == position)
        
        if min_overall is not None:
            query = query.where(Player.overall >= min_overall)
        
        if max_overall is not None:
            query = query.where(Player.overall <= max_overall)
        
        # Get free agents
        players = list(sess.exec(query))
        
        cards = []
        for player in players:
            player_id = getattr(player, "player_id", None)
            if player_id:
                card_data = build_player_card(sess, player_id, season)
                if "error" not in card_data:
                    cards.append(card_data)
        
        return CardListRes(cards=cards, total=len(cards))
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building free agent cards: {str(e)}")

@router.get("/search", response_model=CardListRes)
def search_cards(
    query: str = Query(..., description="Search query"),
    season: int = Query(..., description="Season to get data for"),
    card_type: str = Query("all", description="Type of cards to search (player, coach, team, all)"),
    sess: Session = Depends(get_session)
):
    """Search for cards by name."""
    try:
        cards = []
        
        if card_type in ("player", "all"):
            # Search players
            try:
                from app.models.player import Player
                players = list(sess.exec(Player.select().where(Player.name.ilike(f"%{query}%"))))
                
                for player in players:
                    player_id = getattr(player, "player_id", None)
                    if player_id:
                        card_data = build_player_card(sess, player_id, season)
                        if "error" not in card_data:
                            cards.append(card_data)
            except ImportError:
                pass
        
        if card_type in ("coach", "all"):
            # Search coaches
            try:
                from app.models.coach import Coach
                coaches = list(sess.exec(Coach.select().where(Coach.name.ilike(f"%{query}%"))))
                
                for coach in coaches:
                    coach_id = getattr(coach, "coach_id", None)
                    if coach_id:
                        card_data = build_coach_card(sess, coach_id, season)
                        if "error" not in card_data:
                            cards.append(card_data)
            except ImportError:
                pass
        
        if card_type in ("team", "all"):
            # Search teams
            try:
                from app.models.team import Team
                teams = list(sess.exec(Team.select().where(Team.name.ilike(f"%{query}%"))))
                
                for team in teams:
                    team_id = getattr(team, "team_id", None)
                    if team_id:
                        card_data = build_team_card(sess, team_id, season)
                        if "error" not in card_data:
                            cards.append(card_data)
            except ImportError:
                pass
        
        return CardListRes(cards=cards, total=len(cards))
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching cards: {str(e)}")

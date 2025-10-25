# app/api/routes/draft_integration.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session, select
from app.db import get_engine
from app.services.draft_integration import finalize_draft_class
from app.models.draft import Prospect
from typing import List, Optional
import re

router = APIRouter(prefix="/draft", tags=["draft"])

def _session(): 
    return Session(get_engine())

def _calculate_positional_tier(prospect: Prospect) -> str:
    """Calculate positional tier based on overall rating."""
    overall = prospect.overall
    if overall >= 85:
        return "Elite"
    elif overall >= 80:
        return "High"
    elif overall >= 75:
        return "Good"
    elif overall >= 70:
        return "Average"
    else:
        return "Below Average"

def _get_best_available_prospects(session: Session, season: int, limit: int = 10) -> List[dict]:
    """Get best available prospects sorted by overall rating."""
    prospects = session.exec(
        select(Prospect)
        .where(Prospect.season == season, Prospect.drafted_by_team_id.is_(None))
        .order_by(Prospect.overall.desc())
        .limit(limit)
    ).all()
    
    return [
        {
            **p.model_dump(),
            "tier": _calculate_positional_tier(p),
            "positional_rank": _get_positional_rank(session, season, p.pos, p.overall)
        }
        for p in prospects
    ]

def _get_positional_rank(session: Session, season: int, position: str, overall: int) -> int:
    """Get rank within position (1 = best at position)."""
    better_prospects = session.exec(
        select(Prospect)
        .where(
            Prospect.season == season,
            Prospect.pos == position,
            Prospect.overall > overall
        )
    ).all()
    return len(better_prospects) + 1

@router.post("/{season}/finalize")
def post_finalize(season: int, seed: int = 2025):
    with _session() as s:
        res = finalize_draft_class(s, season, seed=seed)
        if res.get("status") == "no_picks":
            raise HTTPException(status_code=404, detail="No picks assigned for this season")
        return res

@router.get("/{season}/board")
def get_board(
    season: int,
    pos: Optional[str] = Query(None, description="Filter by position (QB, RB, WR, etc.)"),
    min_overall: int = Query(0, ge=0, le=99, description="Minimum overall rating"),
    max_overall: int = Query(99, ge=0, le=99, description="Maximum overall rating"),
    drafted: Optional[bool] = Query(None, description="Filter by drafted status"),
    search: Optional[str] = Query(None, description="Search by player name"),
    sort_by: str = Query("overall", description="Sort field: overall, name, pos, speed, strength, agility, awareness, potential"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    tier: Optional[str] = Query(None, description="Filter by tier: Elite, High, Good, Average, Below Average"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results")
):
    """
    Enhanced draft board with search, sort, and filtering capabilities.
    """
    with _session() as s:
        q = select(Prospect).where(Prospect.season == season)
        
        # Position filter
        if pos:
            q = q.where(Prospect.pos == pos.upper())
        
        # Overall rating range
        if min_overall > 0:
            q = q.where(Prospect.overall >= min_overall)
        if max_overall < 99:
            q = q.where(Prospect.overall <= max_overall)
        
        # Drafted status filter
        if drafted is True:
            q = q.where(Prospect.drafted_by_team_id.is_not(None))
        elif drafted is False:
            q = q.where(Prospect.drafted_by_team_id.is_(None))
        
        # Name search
        if search:
            search_pattern = f"%{search.lower()}%"
            q = q.where(Prospect.name.ilike(search_pattern))
        
        prospects = s.exec(q).all()
        
        # Add computed fields
        enhanced_prospects = []
        for p in prospects:
            enhanced = p.model_dump()
            enhanced["tier"] = _calculate_positional_tier(p)
            enhanced["positional_rank"] = _get_positional_rank(s, season, p.pos, p.overall)
            enhanced_prospects.append(enhanced)
        
        # Tier filter (after computing tiers)
        if tier:
            enhanced_prospects = [p for p in enhanced_prospects if p["tier"] == tier]
        
        # Sorting
        reverse = sort_order.lower() == "desc"
        if sort_by == "overall":
            enhanced_prospects.sort(key=lambda x: x["overall"], reverse=reverse)
        elif sort_by == "name":
            enhanced_prospects.sort(key=lambda x: x["name"].lower(), reverse=reverse)
        elif sort_by == "pos":
            enhanced_prospects.sort(key=lambda x: (x["pos"], -x["overall"]), reverse=reverse)
        elif sort_by in ["speed", "strength", "agility", "awareness", "potential"]:
            enhanced_prospects.sort(key=lambda x: x[sort_by], reverse=reverse)
        elif sort_by == "tier":
            tier_order = {"Elite": 5, "High": 4, "Good": 3, "Average": 2, "Below Average": 1}
            enhanced_prospects.sort(key=lambda x: tier_order.get(x["tier"], 0), reverse=reverse)
        elif sort_by == "positional_rank":
            enhanced_prospects.sort(key=lambda x: x["positional_rank"], reverse=reverse)
        
        # Apply limit
        return enhanced_prospects[:limit]

@router.get("/{season}/best-available")
def get_best_available(
    season: int,
    limit: int = Query(10, ge=1, le=50, description="Number of prospects to return"),
    pos: Optional[str] = Query(None, description="Filter by position")
):
    """
    Get best available prospects sorted by overall rating.
    """
    with _session() as s:
        q = select(Prospect).where(
            Prospect.season == season,
            Prospect.drafted_by_team_id.is_(None)
        )
        
        if pos:
            q = q.where(Prospect.pos == pos.upper())
        
        prospects = s.exec(q.order_by(Prospect.overall.desc()).limit(limit)).all()
        
        return [
            {
                **p.model_dump(),
                "tier": _calculate_positional_tier(p),
                "positional_rank": _get_positional_rank(s, season, p.pos, p.overall)
            }
            for p in prospects
        ]

@router.get("/{season}/positional-tiers")
def get_positional_tiers(season: int):
    """
    Get prospects grouped by position and tier.
    """
    with _session() as s:
        prospects = s.exec(
            select(Prospect).where(Prospect.season == season)
        ).all()
        
        tiers_by_position = {}
        for p in prospects:
            pos = p.pos
            if pos not in tiers_by_position:
                tiers_by_position[pos] = {
                    "Elite": [],
                    "High": [],
                    "Good": [],
                    "Average": [],
                    "Below Average": []
                }
            
            tier = _calculate_positional_tier(p)
            tiers_by_position[pos][tier].append({
                **p.model_dump(),
                "tier": tier,
                "positional_rank": _get_positional_rank(s, season, p.pos, p.overall)
            })
        
        # Sort each tier by overall rating
        for pos in tiers_by_position:
            for tier in tiers_by_position[pos]:
                tiers_by_position[pos][tier].sort(key=lambda x: x["overall"], reverse=True)
        
        return tiers_by_position

@router.get("/{season}/stats")
def get_draft_stats(season: int):
    """
    Get draft statistics and analytics.
    """
    with _session() as s:
        prospects = s.exec(
            select(Prospect).where(Prospect.season == season)
        ).all()
        
        if not prospects:
            return {"error": "No prospects found for this season"}
        
        total_prospects = len(prospects)
        drafted_count = len([p for p in prospects if p.drafted_by_team_id is not None])
        available_count = total_prospects - drafted_count
        
        # Position breakdown
        position_counts = {}
        for p in prospects:
            pos = p.pos
            if pos not in position_counts:
                position_counts[pos] = {"total": 0, "drafted": 0, "available": 0}
            position_counts[pos]["total"] += 1
            if p.drafted_by_team_id is not None:
                position_counts[pos]["drafted"] += 1
            else:
                position_counts[pos]["available"] += 1
        
        # Tier breakdown
        tier_counts = {"Elite": 0, "High": 0, "Good": 0, "Average": 0, "Below Average": 0}
        for p in prospects:
            tier = _calculate_positional_tier(p)
            tier_counts[tier] += 1
        
        # Overall rating stats
        overalls = [p.overall for p in prospects]
        avg_overall = sum(overalls) / len(overalls) if overalls else 0
        
        return {
            "season": season,
            "total_prospects": total_prospects,
            "drafted": drafted_count,
            "available": available_count,
            "draft_percentage": (drafted_count / total_prospects * 100) if total_prospects > 0 else 0,
            "position_breakdown": position_counts,
            "tier_breakdown": tier_counts,
            "average_overall": round(avg_overall, 2),
            "min_overall": min(overalls) if overalls else 0,
            "max_overall": max(overalls) if overalls else 0
        }

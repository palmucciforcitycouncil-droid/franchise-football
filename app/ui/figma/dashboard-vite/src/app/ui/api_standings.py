from __future__ import annotations
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from app.db import get_session
from app.models.standings import Standings
from app.models.playoffs import PlayoffBracket
from app.services.seeding_service import seed_both_conferences, get_playoff_seeds, validate_playoff_seeds
from app.services.standings_service import (
    get_standings, get_power_rankings, get_division_standings, 
    get_conference_standings, get_standings_summary, calculate_win_percentage
)
from app.services.bracket_service import (
    get_bracket_seeds, get_detailed_bracket, create_playoff_matchups,
    get_playoff_summary, is_playoff_team, get_team_playoff_seed
)
from app.services.results_pipeline import (
    get_standings_snapshot, get_weekly_summary, validate_standings
)

router = APIRouter(prefix="/api/v1/standings", tags=["standings"])

class StandingsRow(BaseModel):
    team_id: int
    wins: int
    losses: int
    ties: int
    pf: int
    pa: int
    div_w: int
    div_l: int
    conf_w: int
    conf_l: int
    sos: float
    power_rating: float
    win_percentage: float

@router.get("/league", response_model=List[StandingsRow])
def league(season: int, sess: Session = Depends(get_session)):
    """Get league-wide standings sorted by win percentage and power rating."""
    try:
        rows = list(sess.exec(select(Standings).where(Standings.season == season)))
        rows.sort(key=lambda r: (
            (r.wins + 0.5 * r.ties) / max(1, (r.wins + r.losses + r.ties)), 
            r.power_rating
        ), reverse=True)
        
        return [
            StandingsRow(
                team_id=r.team_id, 
                wins=r.wins, 
                losses=r.losses, 
                ties=r.ties, 
                pf=r.points_for, 
                pa=r.points_against,
                div_w=r.division_wins, 
                div_l=r.division_losses, 
                conf_w=r.conference_wins, 
                conf_l=r.conference_losses,
                sos=r.sos, 
                power_rating=r.power_rating,
                win_percentage=calculate_win_percentage(r)
            ) for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get league standings: {str(e)}")

@router.get("/conference/{conference}", response_model=List[StandingsRow])
def conference_standings(conference: str, season: int, sess: Session = Depends(get_session)):
    """Get standings for a specific conference."""
    try:
        rows = get_conference_standings(sess, season, conference.upper())
        rows.sort(key=lambda r: (
            (r.wins + 0.5 * r.ties) / max(1, (r.wins + r.losses + r.ties)), 
            r.power_rating
        ), reverse=True)
        
        return [
            StandingsRow(
                team_id=r.team_id, 
                wins=r.wins, 
                losses=r.losses, 
                ties=r.ties, 
                pf=r.points_for, 
                pa=r.points_against,
                div_w=r.division_wins, 
                div_l=r.division_losses, 
                conf_w=r.conference_wins, 
                conf_l=r.conference_losses,
                sos=r.sos, 
                power_rating=r.power_rating,
                win_percentage=calculate_win_percentage(r)
            ) for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conference standings: {str(e)}")

@router.get("/division/{conference}/{division}", response_model=List[StandingsRow])
def division_standings(conference: str, division: str, season: int, sess: Session = Depends(get_session)):
    """Get standings for a specific division."""
    try:
        rows = get_division_standings(sess, season, conference.upper(), division.upper())
        rows.sort(key=lambda r: (
            (r.wins + 0.5 * r.ties) / max(1, (r.wins + r.losses + r.ties)), 
            r.power_rating
        ), reverse=True)
        
        return [
            StandingsRow(
                team_id=r.team_id, 
                wins=r.wins, 
                losses=r.losses, 
                ties=r.ties, 
                pf=r.points_for, 
                pa=r.points_against,
                div_w=r.division_wins, 
                div_l=r.division_losses, 
                conf_w=r.conference_wins, 
                conf_l=r.conference_losses,
                sos=r.sos, 
                power_rating=r.power_rating,
                win_percentage=calculate_win_percentage(r)
            ) for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get division standings: {str(e)}")

@router.get("/power_rankings", response_model=List[StandingsRow])
def power_rankings(season: int, sess: Session = Depends(get_session)):
    """Get power rankings sorted by power rating."""
    try:
        rows = get_power_rankings(sess, season)
        
        return [
            StandingsRow(
                team_id=r.team_id, 
                wins=r.wins, 
                losses=r.losses, 
                ties=r.ties, 
                pf=r.points_for, 
                pa=r.points_against,
                div_w=r.division_wins, 
                div_l=r.division_losses, 
                conf_w=r.conference_wins, 
                conf_l=r.conference_losses,
                sos=r.sos, 
                power_rating=r.power_rating,
                win_percentage=calculate_win_percentage(r)
            ) for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get power rankings: {str(e)}")

@router.get("/seeds")
def seeds(season: int, sess: Session = Depends(get_session)):
    """Get playoff seeds for both conferences."""
    try:
        return seed_both_conferences(sess, season)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get playoff seeds: {str(e)}")

class BracketDTO(BaseModel):
    season: int
    afc_seeds: List[int]
    nfc_seeds: List[int]

@router.get("/bracket", response_model=BracketDTO)
def bracket(season: int, sess: Session = Depends(get_session)):
    """Get playoff bracket."""
    try:
        row = sess.exec(select(PlayoffBracket).where(PlayoffBracket.season == season)).first()
        if not row:
            return BracketDTO(season=season, afc_seeds=[], nfc_seeds=[])
        
        to_int = lambda s: [int(x) for x in s.split(",") if x]
        return BracketDTO(
            season=row.season, 
            afc_seeds=to_int(row.afc_seeds_csv), 
            nfc_seeds=to_int(row.nfc_seeds_csv)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get playoff bracket: {str(e)}")

@router.get("/detailed_bracket")
def detailed_bracket(season: int, sess: Session = Depends(get_session)):
    """Get detailed playoff bracket with team information."""
    try:
        return get_detailed_bracket(sess, season)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get detailed bracket: {str(e)}")

@router.get("/matchups")
def playoff_matchups(season: int, sess: Session = Depends(get_session)):
    """Get playoff matchups."""
    try:
        return create_playoff_matchups(sess, season)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get playoff matchups: {str(e)}")

@router.get("/summary")
def standings_summary(season: int, sess: Session = Depends(get_session)):
    """Get standings summary."""
    try:
        return get_standings_summary(sess, season)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get standings summary: {str(e)}")

@router.get("/playoff_summary")
def playoff_summary(season: int, sess: Session = Depends(get_session)):
    """Get playoff summary."""
    try:
        return get_playoff_summary(sess, season)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get playoff summary: {str(e)}")

@router.get("/team/{team_id}")
def team_standings(team_id: int, season: int, sess: Session = Depends(get_session)):
    """Get standings for a specific team."""
    try:
        from app.services.standings_service import get_team_standings
        
        standings = get_team_standings(sess, season, team_id)
        playoff_info = get_team_playoff_seed(sess, season, team_id)
        
        return {
            "team_id": team_id,
            "season": season,
            "standings": {
                "wins": standings.wins,
                "losses": standings.losses,
                "ties": standings.ties,
                "points_for": standings.points_for,
                "points_against": standings.points_against,
                "division_wins": standings.division_wins,
                "division_losses": standings.division_losses,
                "conference_wins": standings.conference_wins,
                "conference_losses": standings.conference_losses,
                "sos": standings.sos,
                "power_rating": standings.power_rating,
                "win_percentage": calculate_win_percentage(standings)
            },
            "playoff_info": playoff_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get team standings: {str(e)}")

@router.get("/snapshot")
def standings_snapshot(season: int, week: int, sess: Session = Depends(get_session)):
    """Get standings snapshot for a specific week."""
    try:
        return get_standings_snapshot(sess, season, week)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get standings snapshot: {str(e)}")

@router.get("/weekly_summary")
def weekly_summary(season: int, week: int, sess: Session = Depends(get_session)):
    """Get weekly summary."""
    try:
        return get_weekly_summary(sess, season, week)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get weekly summary: {str(e)}")

@router.get("/validate")
def validate_standings_endpoint(season: int, sess: Session = Depends(get_session)):
    """Validate standings for consistency."""
    try:
        return validate_standings(sess, season)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate standings: {str(e)}")

class GenerateBracketReq(BaseModel):
    season: int

@router.post("/generate_bracket")
def generate_bracket_endpoint(body: GenerateBracketReq, sess: Session = Depends(get_session)):
    """Generate playoff bracket for a season."""
    try:
        from app.services.bracket_service import generate_bracket
        
        bracket = generate_bracket(sess, body.season)
        return {
            "success": True,
            "season": bracket.season,
            "afc_seeds": bracket.afc_seeds_csv.split(","),
            "nfc_seeds": bracket.nfc_seeds_csv.split(",")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate bracket: {str(e)}")

class ResetStandingsReq(BaseModel):
    season: int

@router.post("/reset")
def reset_standings_endpoint(body: ResetStandingsReq, sess: Session = Depends(get_session)):
    """Reset standings for a season."""
    try:
        from app.services.results_pipeline import reset_standings
        
        success = reset_standings(sess, body.season)
        return {"success": success, "season": body.season}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset standings: {str(e)}")

class InitializeStandingsReq(BaseModel):
    season: int
    team_ids: List[int]

@router.post("/initialize")
def initialize_standings_endpoint(body: InitializeStandingsReq, sess: Session = Depends(get_session)):
    """Initialize standings for teams in a season."""
    try:
        from app.services.results_pipeline import initialize_standings
        
        success = initialize_standings(sess, body.season, body.team_ids)
        return {"success": success, "season": body.season, "teams": len(body.team_ids)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize standings: {str(e)}")

@router.get("/playoff_teams")
def playoff_teams(season: int, sess: Session = Depends(get_session)):
    """Get all playoff teams."""
    try:
        return get_playoff_teams(sess, season)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get playoff teams: {str(e)}")

@router.get("/is_playoff_team/{team_id}")
def is_playoff_team_endpoint(team_id: int, season: int, sess: Session = Depends(get_session)):
    """Check if a team made the playoffs."""
    try:
        is_playoff = is_playoff_team(sess, season, team_id)
        playoff_seed = get_team_playoff_seed(sess, season, team_id)
        
        return {
            "team_id": team_id,
            "season": season,
            "is_playoff_team": is_playoff,
            "playoff_seed": playoff_seed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check playoff status: {str(e)}")


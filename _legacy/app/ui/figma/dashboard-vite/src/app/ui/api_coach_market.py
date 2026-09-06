from __future__ import annotations
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from app.db import get_session
from app.models.coach import CoachRole, CoachJobType, CoachOffer, Coach
from app.services.coach_market import (
    list_free_agents, list_league_assistants, list_team_staff,
    fire_coach, resign_coach, create_coach_offer, rescind_offer,
    cpu_hiring_sweep
)

router = APIRouter(prefix="/api/v1/coaches", tags=["coaches"])

class MarketRowDTO(BaseModel):
    coach_id: int
    name: str
    role: str
    team_id: int | None
    overall: int
    expiring: bool
    desired_years: int
    desired_aav: int
    offers: int

@router.get("/fa", response_model=List[MarketRowDTO])
def list_fa(season: int, sess: Session = Depends(get_session)):
    """Get list of free agent coaches."""
    return [MarketRowDTO(**r.__dict__) for r in list_free_agents(sess, season)]

@router.get("/assistants", response_model=List[MarketRowDTO])
def list_assistants(season: int, sess: Session = Depends(get_session)):
    """Get list of assistant coaches (OC/DC/AC) in the league."""
    return [MarketRowDTO(**r.__dict__) for r in list_league_assistants(sess, season)]

@router.get("/team_staff", response_model=List[MarketRowDTO])
def team_staff(season: int, team_id: int, sess: Session = Depends(get_session)):
    """Get list of staff for a specific team."""
    return [MarketRowDTO(**r.__dict__) for r in list_team_staff(sess, team_id, season)]

class ResignReq(BaseModel):
    coach_id: int
    team_id: int
    season: int
    years: int
    aav: int

@router.post("/resign")
def resign(body: ResignReq, sess: Session = Depends(get_session)):
    """Re-sign a coach to a new contract."""
    try:
        resign_coach(sess, body.coach_id, body.team_id, body.season, body.years, body.aav)
        return {"ok": True, "message": f"Coach {body.coach_id} re-signed to team {body.team_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to re-sign coach: {str(e)}")

@router.post("/fire/{coach_id}")
def fire(coach_id: int, sess: Session = Depends(get_session)):
    """Fire a coach, making them a free agent."""
    try:
        fire_coach(sess, coach_id)
        return {"ok": True, "message": f"Coach {coach_id} fired and made free agent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fire coach: {str(e)}")

class OfferReq(BaseModel):
    season: int
    from_team_id: int
    to_coach_id: int
    job_type: CoachJobType
    years: int
    aav: int

class OfferRes(BaseModel):
    accepted: bool
    min_years: int
    min_aav: int
    reason: str | None = None

@router.post("/offer", response_model=OfferRes)
def offer(body: OfferReq, sess: Session = Depends(get_session)):
    """Make an offer to a coach."""
    try:
        res = create_coach_offer(sess, body.season, body.from_team_id, body.to_coach_id, body.job_type, body.years, body.aav)
        return OfferRes(accepted=res.accepted, min_years=res.min_years, min_aav=res.min_aav, reason=res.reason or None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create offer: {str(e)}")

@router.post("/rescind/{offer_id}")
def rescind(offer_id: int, sess: Session = Depends(get_session)):
    """Rescind an active offer."""
    try:
        rescind_offer(sess, offer_id)
        return {"ok": True, "message": f"Offer {offer_id} rescinded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rescind offer: {str(e)}")

@router.post("/cpu/offseason_sweep")
def cpu_offseason_sweep(season: int, sess: Session = Depends(get_session)):
    """Run CPU offseason hiring sweep to fill all vacancies."""
    try:
        cpu_hiring_sweep(sess, season)
        return {"ok": True, "message": f"CPU offseason sweep completed for season {season}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run CPU sweep: {str(e)}")

# Additional endpoints for enhanced functionality

class CoachDetailDTO(BaseModel):
    coach_id: int
    name: str
    role: str
    team_id: int | None
    overall: int
    age: int
    run_pass_tendency: float
    offensive_aggression: float
    defensive_aggression: float
    blitz_rate: float
    coverage_mix: float
    red_zone_offense: float
    red_zone_defense: float

@router.get("/{coach_id}", response_model=CoachDetailDTO)
def get_coach_detail(coach_id: int, sess: Session = Depends(get_session)):
    """Get detailed information about a specific coach."""
    coach = sess.get(Coach, coach_id)
    if not coach:
        raise HTTPException(status_code=404, detail=f"Coach {coach_id} not found")
    
    return CoachDetailDTO(
        coach_id=coach.coach_id,
        name=coach.name,
        role=coach.role.value,
        team_id=coach.team_id,
        overall=coach.overall,
        age=coach.age,
        run_pass_tendency=coach.run_pass_tendency,
        offensive_aggression=coach.offensive_aggression,
        defensive_aggression=coach.defensive_aggression,
        blitz_rate=coach.blitz_rate,
        coverage_mix=coach.coverage_mix,
        red_zone_offense=coach.red_zone_offense,
        red_zone_defense=coach.red_zone_defense
    )

class OfferDTO(BaseModel):
    offer_id: int
    season: int
    from_team_id: int
    to_coach_id: int
    job_type: str
    years: int
    aav: int
    is_active: bool

@router.get("/offers/{coach_id}", response_model=List[OfferDTO])
def get_coach_offers(coach_id: int, season: int, sess: Session = Depends(get_session)):
    """Get all active offers for a specific coach."""
    offers = list(sess.exec(select(CoachOffer).where(
        CoachOffer.to_coach_id == coach_id,
        CoachOffer.season == season,
        CoachOffer.is_active == True
    )))
    
    return [OfferDTO(
        offer_id=o.offer_id,
        season=o.season,
        from_team_id=o.from_team_id,
        to_coach_id=o.to_coach_id,
        job_type=o.job_type.value,
        years=o.years,
        aav=o.aav,
        is_active=o.is_active
    ) for o in offers]

class ContractDTO(BaseModel):
    contract_id: int
    coach_id: int
    team_id: int
    start_season: int
    end_season: int
    aav: int
    is_active: bool

@router.get("/contracts/{coach_id}", response_model=ContractDTO | None)
def get_coach_contract(coach_id: int, sess: Session = Depends(get_session)):
    """Get the current active contract for a coach."""
    from app.services.coach_market import current_contract
    
    contract = current_contract(sess, coach_id)
    if not contract:
        return None
    
    return ContractDTO(
        contract_id=contract.contract_id,
        coach_id=contract.coach_id,
        team_id=contract.team_id,
        start_season=contract.start_season,
        end_season=contract.end_season,
        aav=contract.aav,
        is_active=contract.is_active
    )

class AskDTO(BaseModel):
    coach_id: int
    desired_years: int
    desired_aav: int
    updated_season: int

@router.get("/ask/{coach_id}", response_model=AskDTO)
def get_coach_ask(coach_id: int, season: int, sess: Session = Depends(get_session)):
    """Get a coach's asking price."""
    from app.services.coach_market import get_or_create_ask
    
    ask = get_or_create_ask(sess, coach_id, season)
    return AskDTO(
        coach_id=ask.coach_id,
        desired_years=ask.desired_years,
        desired_aav=ask.desired_aav,
        updated_season=ask.updated_season
    )

class VacancyDTO(BaseModel):
    team_id: int
    job: str

@router.get("/vacancies", response_model=List[VacancyDTO])
def get_team_vacancies(season: int, sess: Session = Depends(get_session)):
    """Get all team vacancies for a season."""
    from app.services.coach_market import _team_vacancies
    
    vacancies = _team_vacancies(sess, season)
    return [VacancyDTO(team_id=v.team_id, job=v.job.value) for v in vacancies]

class MarketStatsDTO(BaseModel):
    total_coaches: int
    free_agents: int
    total_offers: int
    active_contracts: int
    expiring_contracts: int

@router.get("/stats", response_model=MarketStatsDTO)
def get_market_stats(season: int, sess: Session = Depends(get_session)):
    """Get market statistics for a season."""
    from app.models.coach import CoachContract
    
    total_coaches = len(list(sess.exec(select(Coach))))
    free_agents = len(list(sess.exec(select(Coach).where(Coach.team_id == None))))
    total_offers = len(list(sess.exec(select(CoachOffer).where(CoachOffer.season == season, CoachOffer.is_active == True))))
    active_contracts = len(list(sess.exec(select(CoachContract).where(CoachContract.is_active == True))))
    expiring_contracts = len(list(sess.exec(select(CoachContract).where(CoachContract.is_active == True, CoachContract.end_season == season))))
    
    return MarketStatsDTO(
        total_coaches=total_coaches,
        free_agents=free_agents,
        total_offers=total_offers,
        active_contracts=active_contracts,
        expiring_contracts=expiring_contracts
    )


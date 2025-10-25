from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
from sqlmodel import Session, select
from app.models.coach import Coach, CoachContract, CoachOffer, CoachAsk, CoachRole, CoachJobType

# ---------- Helpers ----------
def current_contract(sess: Session, coach_id: int) -> Optional[CoachContract]:
    """Get the current active contract for a coach."""
    return sess.exec(select(CoachContract).where(CoachContract.coach_id==coach_id, CoachContract.is_active==True)).first()

def is_expiring(contract: CoachContract, season: int) -> bool:
    """Check if a contract is expiring in the given season."""
    return contract.is_active and contract.end_season == season

def get_or_create_ask(sess: Session, coach_id: int, season: int) -> CoachAsk:
    """Get or create a coach's asking price, updating for inflation if needed."""
    ask = sess.exec(select(CoachAsk).where(CoachAsk.coach_id==coach_id)).first()
    if not ask:
        ask = CoachAsk(coach_id=coach_id, updated_season=season)
        sess.add(ask); sess.commit(); sess.refresh(ask)
    if ask.updated_season != season:
        # Simple inflation tick (you can replace with performance-driven update)
        ask.desired_aav = int(max(750_000, ask.desired_aav * 1.03))
        ask.updated_season = season
        sess.add(ask); sess.commit()
    return ask

def reassign_role_allowed(src_role: CoachRole, target_job: CoachJobType) -> bool:
    """Check if a role reassignment is allowed (promotions only in MVP)."""
    # Promotions only (MVP):
    if target_job == CoachJobType.HC:
        return True  # any OC/DC/AC can be promoted to HC
    if target_job in (CoachJobType.OC, CoachJobType.DC):
        return src_role == CoachRole.AC  # AC can be promoted to OC/DC
    if target_job == CoachJobType.AC:
        return False  # no demotions via offers (use Fire/Promote locally)
    return False

def apply_promotion(coach: Coach, target_job: CoachJobType):
    """Apply a promotion to a coach."""
    coach.role = CoachRole[target_job.value]

# ---------- Queries ----------
@dataclass
class MarketRow:
    coach_id: int
    name: str
    role: str
    team_id: Optional[int]
    overall: int
    expiring: bool
    desired_years: int
    desired_aav: int
    offers: int

def list_free_agents(sess: Session, season: int) -> List[MarketRow]:
    """List all free agent coaches with their asking prices and offer counts."""
    rows: List[MarketRow] = []
    fa = list(sess.exec(select(Coach).where(Coach.team_id==None)))
    for c in fa:
        ask = get_or_create_ask(sess, c.coach_id, season)
        offer_count = sess.exec(select(CoachOffer).where(
            CoachOffer.season==season, CoachOffer.to_coach_id==c.coach_id, CoachOffer.is_active==True)).all()
        rows.append(MarketRow(c.coach_id, c.name, c.role.value, None, c.overall, False, ask.desired_years, ask.desired_aav, len(offer_count)))
    return rows

def list_league_assistants(sess: Session, season: int) -> List[MarketRow]:
    """List all assistant coaches (OC/DC/AC) in the league with their status."""
    rows: List[MarketRow] = []
    assistants = list(sess.exec(select(Coach).where(Coach.role.in_([CoachRole.OC, CoachRole.DC, CoachRole.AC]))))
    for c in assistants:
        con = current_contract(sess, c.coach_id)
        exp = bool(con and is_expiring(con, season))
        ask = get_or_create_ask(sess, c.coach_id, season)
        offers = list(sess.exec(select(CoachOffer).where(CoachOffer.season==season, CoachOffer.to_coach_id==c.coach_id, CoachOffer.is_active==True)))
        rows.append(MarketRow(c.coach_id, c.name, c.role.value, c.team_id, c.overall, exp, ask.desired_years, ask.desired_aav, len(offers)))
    return rows

def list_team_staff(sess: Session, team_id: int, season: int) -> List[MarketRow]:
    """List all staff for a specific team."""
    rows: List[MarketRow] = []
    staff = list(sess.exec(select(Coach).where(Coach.team_id==team_id)))
    for c in staff:
        con = current_contract(sess, c.coach_id)
        exp = bool(con and is_expiring(con, season))
        ask = get_or_create_ask(sess, c.coach_id, season)
        offers = list(sess.exec(select(CoachOffer).where(CoachOffer.season==season, CoachOffer.to_coach_id==c.coach_id, CoachOffer.is_active==True)))
        rows.append(MarketRow(c.coach_id, c.name, c.role.value, c.team_id, c.overall, exp, ask.desired_years, ask.desired_aav, len(offers)))
    return rows

# ---------- Actions ----------
def fire_coach(sess: Session, coach_id: int):
    """Fire a coach, making them a free agent and deactivating their contract."""
    c = sess.get(Coach, coach_id)
    if not c: return
    con = current_contract(sess, coach_id)
    if con:
        con.is_active = False; sess.add(con)
    c.team_id = None
    sess.add(c); sess.commit()

def resign_coach(sess: Session, coach_id: int, team_id: int, season: int, years: int, aav: int):
    """Re-sign a coach to a new contract."""
    con = current_contract(sess, coach_id)
    if con: con.is_active = False; sess.add(con)
    new_con = CoachContract(coach_id=coach_id, team_id=team_id, start_season=season, end_season=season+years-1, aav=aav, is_active=True)
    c = sess.get(Coach, coach_id)
    if c: c.team_id = team_id; sess.add(c)
    ask = get_or_create_ask(sess, coach_id, season)
    ask.desired_years = years; ask.desired_aav = aav; sess.add(ask)
    sess.add(new_con); sess.commit()

# Offer acceptance logic (instant if threshold met)
@dataclass
class OfferResult:
    accepted: bool
    min_years: int
    min_aav: int
    reason: str = ""

def _accept_logic(ask: CoachAsk, job: CoachJobType, offer_years: int, offer_aav: int) -> OfferResult:
    """Determine if an offer meets the coach's acceptance threshold."""
    # Simple policy: threshold is 96% of desired AAV, and years >= desired_years - 1
    min_years = max(1, ask.desired_years - 1)
    min_aav = int(ask.desired_aav * 0.96)
    accepted = (offer_years >= min_years and offer_aav >= min_aav)
    return OfferResult(accepted=accepted, min_years=min_years, min_aav=min_aav)

def create_coach_offer(sess: Session, season: int, from_team_id: int, to_coach_id: int, job: CoachJobType, years: int, aav: int) -> OfferResult:
    """Create a coach offer, accepting immediately if threshold is met."""
    coach = sess.get(Coach, to_coach_id)
    if not coach: return OfferResult(False, 0, 0, "Coach not found")
    if coach.team_id == from_team_id:
        return OfferResult(False, 0, 0, "Coach already on your team")

    # Role rule: only promotions
    if coach.team_id is not None and not reassign_role_allowed(coach.role, job):
        return OfferResult(False, 0, 0, "Only promotions are allowed for non-FA coaches")

    ask = get_or_create_ask(sess, to_coach_id, season)
    res = _accept_logic(ask, job, years, aav)

    if res.accepted:
        # Accept immediately; create contract and reassign role
        if coach.team_id is not None:
            # moving teams: deactivate old contract
            con = current_contract(sess, coach.coach_id)
            if con: con.is_active = False; sess.add(con)
        apply_promotion(coach, job)
        coach.team_id = from_team_id
        new_con = CoachContract(coach_id=coach.coach_id, team_id=from_team_id, start_season=season, end_season=season+years-1, aav=aav, is_active=True)
        sess.add(coach); sess.add(new_con)
        # cancel other active offers
        others = list(sess.exec(select(CoachOffer).where(CoachOffer.season==season, CoachOffer.to_coach_id==coach.coach_id, CoachOffer.is_active==True)))
        for o in others: o.is_active = False; sess.add(o)
        sess.commit()
        return res

    # Otherwise store the offer (visible as competing offer)
    offer = CoachOffer(season=season, from_team_id=from_team_id, to_coach_id=to_coach_id, job_type=job, years=years, aav=aav, is_active=True)
    sess.add(offer); sess.commit()
    return res

def rescind_offer(sess: Session, offer_id: int):
    """Rescind an active offer."""
    o = sess.get(CoachOffer, offer_id)
    if not o: return
    o.is_active = False; sess.add(o); sess.commit()

# ---------- Vacancy evaluation / CPU sweep ----------
@dataclass
class Vacancy:
    team_id: int
    job: CoachJobType

def _team_vacancies(sess: Session, season: int) -> List[Vacancy]:
    """Find all team vacancies (missing roles or expiring contracts)."""
    # Vacancy = team missing role OR active contract expiring and not re-signed yet.
    vacancies: List[Vacancy] = []
    try:
        from app.models.team import Team  # assume exists
        teams = list(sess.exec(select(Team)))
    except ImportError:
        # Fallback: assume teams 1-32 exist
        teams = [type('Team', (), {'team_id': i}) for i in range(1, 33)]
    
    for t in teams:
        for job in (CoachJobType.HC, CoachJobType.OC, CoachJobType.DC, CoachJobType.AC):
            # find incumbent
            inc = sess.exec(select(Coach).where(Coach.team_id==t.team_id, Coach.role==CoachRole[job.value])).first()
            if not inc:
                vacancies.append(Vacancy(team_id=t.team_id, job=job)); continue
            con = current_contract(sess, inc.coach_id)
            if con and is_expiring(con, season):
                vacancies.append(Vacancy(team_id=t.team_id, job=job))
    return vacancies

def _coach_fit_score(c: Coach, job: CoachJobType) -> float:
    """Calculate how well a coach fits a specific job."""
    # Simple: start from overall, bias by job
    base = float(c.overall)
    if job == CoachJobType.HC:
        return base + 5.0
    if job in (CoachJobType.OC, CoachJobType.DC):
        return base + (c.offensive_aggression if job==CoachJobType.OC else c.defensive_aggression) * 10.0
    return base

def _make_offer(sess: Session, season: int, team_id: int, c: Coach, job: CoachJobType):
    """Make an offer to a coach (CPU logic)."""
    ask = get_or_create_ask(sess, c.coach_id, season)
    years = max(2, ask.desired_years)  # CPU tends to offer close to ask or slightly higher
    aav = int(ask.desired_aav * 1.02)
    create_coach_offer(sess, season, team_id, c.coach_id, job, years, aav)

def cpu_hiring_sweep(sess: Session, season: int):
    """
    Fill vacancies for all teams: promote internal > FA > poach.
    """
    vacs = _team_vacancies(sess, season)
    # Promote internal: AC -> OC/DC; OC/DC/AC -> HC (same team)
    for v in vacs:
        # If team has someone to promote, prefer that:
        if v.job == CoachJobType.HC:
            candidates = list(sess.exec(select(Coach).where(Coach.team_id==v.team_id, Coach.role.in_([CoachRole.OC, CoachRole.DC, CoachRole.AC]))))
        elif v.job in (CoachJobType.OC, CoachJobType.DC):
            candidates = list(sess.exec(select(Coach).where(Coach.team_id==v.team_id, Coach.role==CoachRole.AC)))
        else:
            candidates = []  # AC: no internal source in MVP, will go FA/poach

        if candidates:
            # pick best fit
            best = sorted(candidates, key=lambda x: _coach_fit_score(x, v.job), reverse=True)[0]
            # Treat as instant accept promotion at current team:
            apply_promotion(best, v.job)
            # extend contract lightly if needed
            con = current_contract(sess, best.coach_id)
            if con:
                con.end_season = max(con.end_season, season+2); sess.add(con)
            else:
                new_con = CoachContract(coach_id=best.coach_id, team_id=v.team_id, start_season=season, end_season=season+2, aav=1_800_000, is_active=True)
                sess.add(new_con)
            sess.add(best); sess.commit()
            continue

        # Try FA market
        fa = list(sess.exec(select(Coach).where(Coach.team_id==None)))
        if fa:
            fa_sorted = sorted(fa, key=lambda x: _coach_fit_score(x, v.job), reverse=True)
            # take top N try to sign
            for c in fa_sorted[:5]:
                _make_offer(sess, season, v.team_id, c, v.job)
                # If accepted immediately, stop
                if sess.get(Coach, c.coach_id).team_id == v.team_id:
                    break
            continue

        # Poach assistants from other teams (promotions only)
        pool = list(sess.exec(select(Coach).where(Coach.team_id!=v.team_id)))
        # Filter by allowed promotions
        pool = [c for c in pool if reassign_role_allowed(c.role, v.job)]
        if pool:
            pool_sorted = sorted(pool, key=lambda x: _coach_fit_score(x, v.job), reverse=True)
            for c in pool_sorted[:5]:
                _make_offer(sess, season, v.team_id, c, v.job)
                if sess.get(Coach, c.coach_id).team_id == v.team_id:
                    break


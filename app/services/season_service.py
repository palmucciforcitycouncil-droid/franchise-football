from sqlmodel import Session, select
from app.models.season_models import Season
from app.models.sim_models import SimTeam, SimGame
from app.services.schedule_service import generate_round_robin_16
from app.services.sim_service import sim_week

def init_season(session: Session, season: int, seed: int):
    row = session.query(Season).filter(Season.season == season).first()
    if not row:
        row = Season(season=season, seed=seed, current_week=1, phase="regular")
        session.add(row); session.commit()
    return row

def advance_week(session: Session, season: int):
    s = session.query(Season).filter(Season.season == season).first()
    if not s: raise ValueError("Season not initialized")
    sim_week(session, season, s.current_week, seed=s.seed)
    s.current_week += 1
    session.add(s); session.commit()
    return s

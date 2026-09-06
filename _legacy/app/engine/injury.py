from dataclasses import dataclass
from typing import List, Dict
from sqlmodel import Session, select
from app.engine.rng import RNG
from app.models.player_models import Player, PlayerInjury
from app.engine.tuning import PARAMS as P

@dataclass
class InjuryEvent:
    player_id: int
    team_id: int
    weeks_out: int
    description: str
    severity: str

def simulate_game_injuries(rng: RNG, home_team_id: int, away_team_id: int) -> List[InjuryEvent]:
    """Simulate injuries for a game"""
    injuries = []
    
    # Simple injury simulation - 1-3 injuries per game
    num_injuries = rng.choice([0, 1, 2, 3], weights=[0.7, 0.2, 0.08, 0.02])
    
    for _ in range(num_injuries):
        team_id = rng.choice([home_team_id, away_team_id])
        weeks_out = rng.choice([1, 2, 3, 4, 6, 8], weights=[0.4, 0.3, 0.15, 0.1, 0.03, 0.02])
        severity = "minor" if weeks_out <= 2 else "moderate" if weeks_out <= 4 else "major"
        
        injuries.append(InjuryEvent(
            player_id=0,  # Will be assigned when creating actual injury records
            team_id=team_id,
            weeks_out=weeks_out,
            description=f"{severity.title()} injury",
            severity=severity
        ))
    
    return injuries

def apply_injury_effects(session: Session, season: int, week: int):
    """Apply injury effects and handle RTP weeks"""
    rows: List[PlayerInjury] = session.query(PlayerInjury).filter(PlayerInjury.season == season).all()
    
    for inj in rows:
        remaining = inj.weeks_out - ((week - inj.start_week))
        p: Player = session.get(Player, inj.player_id)
        
        if remaining > 0:
            if p and p.is_active:
                p.is_active = False
                session.add(p)
        else:
            if inj.active:
                inj.active = False
                session.add(inj)
            if p:
                if not p.is_active:
                    p.is_active = True
                    p.rtp_weeks = max(p.rtp_weeks, P.rtp_weeks_default)
                else:
                    # decay RTP weeks each new week while active
                    if p.rtp_weeks > 0:
                        p.rtp_weeks -= 1
                session.add(p)
    
    session.commit()

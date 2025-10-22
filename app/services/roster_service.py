from typing import List, Dict
from sqlmodel import Session, select
from app.models.player import Player
from app.models.depth_chart import DepthChart
from app.models.sim_models import SimTeam
from app.models.coach_models import Coach
from app.engine.tuning import PARAMS as P
import itertools

def seed_fake_rosters(session: Session):
    """Create fake rosters for testing - keep as-is"""
    teams = session.query(SimTeam).all()
    for team in teams:
        # Create basic roster for each team
        positions = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "CB", "S", "K", "P", "RET"]
        for pos in positions:
            count = 3 if pos in ["QB", "K", "P"] else 5
            for i in range(count):
                ovr = 60 + (i * 5) + (hash(team.name + pos + str(i)) % 10)
                player = Player(
                    team_id=team.id,
                    first_name=f"Player{i+1}",
                    last_name=f"{pos}Player",
                    position=pos,
                    jersey_number=i+1,
                    speed=ovr,
                    strength=ovr - 5,
                    agility=ovr + 2,
                    throw_power=ovr if pos == "QB" else 50,
                    throw_accuracy=ovr if pos == "QB" else 50,
                    catching=ovr if pos in ["WR", "TE"] else 50,
                    tackling=ovr if pos in ["DL", "LB", "CB", "S"] else 50,
                    awareness=ovr,
                    potential=ovr + 5,
                    age=24 + i,
                    stamina=ovr,
                    injury_proneness=50,
                    morale=50
                )
                session.add(player)
    session.commit()

def aggregate_team_ratings(session: Session, team_id: int) -> Dict[str,float]:
    from app.engine.depth import starters_for
    lineup = starters_for(session, team_id)
    
    # Apply RTP penalty to players with rtp_weeks > 0
    for group in lineup.values():
        for p in group:
            if hasattr(p, "rtp_weeks") and getattr(p, "rtp_weeks", 0) > 0:
                # Apply penalty to effective OVR without mutating the actual player
                penalty = P.rtp_ovr_penalty_per_week * getattr(p, "rtp_weeks", 0)
                p.effective_ovr = max(40, int(p.awareness - penalty))
            else:
                p.effective_ovr = p.awareness
    
    def avg(pos, n=None):
        arr = lineup.get(pos, [])
        if n: arr = arr[:n]
        return sum(getattr(p, "effective_ovr", p.awareness) for p in arr)/max(1,len(arr))

    offense = (0.35*avg("QB",1) + 0.15*avg("WR",3) + 0.10*avg("RB",1) + 0.15*avg("OL",5) + 0.10*avg("TE",1) + 0.15*avg("RET",1))
    defense = (0.25*avg("DL",4) + 0.20*avg("LB",3) + 0.25*avg("CB",2) + 0.20*avg("S",2) + 0.10*avg("OL",5))
    special = (0.6*avg("K",1) + 0.4*avg("P",1))
    rb_block = 0.5*(avg("RB",1)+avg("OL",5)) - avg("WR",3)
    run_bias = 0.5 + max(-0.2, min(0.2, rb_block/100.0))
    aggression = 0.5 + max(-0.2, min(0.2, (avg("WR",3)-avg("RB",1))/100.0))
    pace = 0.5

    coach = session.query(Coach).filter(Coach.team_id==team_id).first()
    if coach:
        # blend 70% roster-driven + 30% coach profile
        run_bias = 0.7*run_bias + 0.3*coach.run_bias
        aggression = 0.7*aggression + 0.3*coach.aggression
        pace = 0.7*pace + 0.3*coach.pace

    def clamp(x): return max(40.0, min(90.0, x))
    return {
        "offense": clamp(offense/1.0),
        "defense": clamp(defense/1.0),
        "special": clamp(special/1.0),
        "run_bias": max(0.2, min(0.8, run_bias)),
        "aggression": max(0.2, min(0.8, aggression)),
        "pace": max(0.2, min(0.8, pace))
    }

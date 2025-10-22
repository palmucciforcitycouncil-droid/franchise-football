from typing import List
from sqlmodel import Session
from .standings_service import shuffle_seeded

from app.models.sim_models import SimTeam, SimGame

def generate_round_robin_16(session: Session, season: int, seed: int) -> List[SimGame]:
    teams = session.query(SimTeam).all()
    team_ids = [t.id for t in teams]
    # simple shuffle
    order = shuffle_seeded(team_ids, seed)

    games: List[SimGame] = []
    week = 1
    # Pair adjacently; repeat to build ~16 weeks
    for rep in range(16):
        for i in range(0, len(order), 2):
            if i+1 >= len(order): break
            home = order[i]; away = order[i+1]
            games.append(SimGame(week=week, season=season, home_team_id=home, away_team_id=away))
        # rotate
        order = order[1:] + order[:1]
        week += 1
    session.add_all(games)
    session.commit()
    return games

from app.core.db import session_scope
from app.models.sim_models import Game, GameEvent
from sqlmodel import select

with session_scope() as s:
    # Get games for week 1
    games = s.exec(select(Game).where(Game.season == 2025, Game.week == 1)).all()
    game_ids = [g.id for g in games]
    
    # Delete all game events for these games
    events = s.exec(select(GameEvent).where(GameEvent.game_id.in_(game_ids))).all()
    for e in events:
        s.delete(e)
    
    # Reset game status to scheduled
    for g in games:
        g.status = "scheduled"
        g.home_score = 0
        g.away_score = 0
    
    s.commit()
    print(f"Reset {len(games)} games and deleted {len(events)} events")


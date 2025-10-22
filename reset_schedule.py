from app.core.db import session_scope
from app.models.sim_models import Game, GameEvent
from sqlmodel import select

with session_scope() as s:
    # Delete all games and events for 2025 season
    games = s.exec(select(Game).where(Game.season == 2025)).all()
    game_ids = [g.id for g in games]
    
    # Delete all game events for these games
    events = s.exec(select(GameEvent).where(GameEvent.game_id.in_(game_ids))).all()
    for e in events:
        s.delete(e)
    
    # Delete all games
    for g in games:
        s.delete(g)
    
    s.commit()
    print(f"Deleted {len(games)} games and {len(events)} events for 2025 season")

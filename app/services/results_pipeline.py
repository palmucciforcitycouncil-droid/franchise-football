from __future__ import annotations
from sqlmodel import Session

def on_game_final(sess: Session, season: int, game_id: int, week: int):
    """Handle post-game processing like standings updates."""
    # Stub implementation - update standings, power ratings, etc.
    pass

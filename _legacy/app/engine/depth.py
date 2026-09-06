from typing import Dict, List
from sqlmodel import Session
from app.models.player import Player
from app.models.depth_chart import DepthChart

def starters_for(session: Session, team_id: int) -> Dict[str, List[Player]]:
    """Get starting lineup for a team by position"""
    lineup = {}
    
    # Get depth chart entries for this team
    depth_entries = session.query(DepthChart).filter(DepthChart.team_id == team_id).all()
    
    # Group by position and get starters (starter_player_id)
    for entry in depth_entries:
        if entry.starter_player_id:  # Starter
            player = session.query(Player).filter(Player.id == entry.starter_player_id).first()
            if player:
                if entry.position not in lineup:
                    lineup[entry.position] = []
                lineup[entry.position].append(player)
    
    return lineup

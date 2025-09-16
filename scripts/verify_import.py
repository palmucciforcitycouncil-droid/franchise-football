"""
Verify DB contents after roster import.

Checks:
- Total counts for teams, players, depth chart rows
- A few sample teams with roster size and jersey lists
- Ensures each depth chart starter/backup maps to an existing player
"""

from sqlalchemy import select, func
from app.models.database import get_session
from app.models import Team, Player, DepthChart


def main():
    with get_session() as session:
        team_count = session.scalar(select(func.count()).select_from(Team)) or 0
        player_count = session.scalar(select(func.count()).select_from(Player)) or 0
        depth_count = session.scalar(select(func.count()).select_from(DepthChart)) or 0

        print(f"Teams: {team_count}")
        print(f"Players: {player_count}")
        print(f"Depth rows: {depth_count}")

        # Spot-check first 3 teams
        teams = session.execute(
            select(Team).order_by(Team.id).limit(3)
        ).scalars().all()

        for t in teams:
            jerseys = session.execute(
                select(Player.jersey).where(Player.team_id == t.id).order_by(Player.jersey)
            ).scalars().all()
            print(f"\nTeam {t.location_name}|{t.nickname} (id={t.id})")
            print(f"  Roster size: {len(jerseys)}")
            print(f"  Jerseys: {jerseys[:60]}{' ...' if len(jerseys) > 60 else ''}")

        # Verify depth chart mappings
        invalid = []
        rows = session.execute(select(DepthChart)).scalars().all()
        for dc in rows:
            team = sessio

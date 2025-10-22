from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.data.session import get_db
from app.models.team import Team

router = APIRouter(prefix="/api/dev", tags=["dev-seed"])

# Deterministic 32-team seed (private use; NFL names allowed per project notes)
# Format: team_id, name, abbr, conference, division
_TEAMS = [
    # AFC East
    (1, "Buffalo Bills", "BUF", "AFC", "EAST"),
    (2, "Miami Dolphins", "MIA", "AFC", "EAST"),
    (3, "New England Patriots", "NE", "AFC", "EAST"),
    (4, "New York Jets", "NYJ", "AFC", "EAST"),
    # AFC North
    (5, "Baltimore Ravens", "BAL", "AFC", "NORTH"),
    (6, "Cincinnati Bengals", "CIN", "AFC", "NORTH"),
    (7, "Cleveland Browns", "CLE", "AFC", "NORTH"),
    (8, "Pittsburgh Steelers", "PIT", "AFC", "NORTH"),
    # AFC South
    (9, "Houston Texans", "HOU", "AFC", "SOUTH"),
    (10, "Indianapolis Colts", "IND", "AFC", "SOUTH"),
    (11, "Jacksonville Jaguars", "JAX", "AFC", "SOUTH"),
    (12, "Tennessee Titans", "TEN", "AFC", "SOUTH"),
    # AFC West
    (13, "Denver Broncos", "DEN", "AFC", "WEST"),
    (14, "Kansas City Chiefs", "KC", "AFC", "WEST"),
    (15, "Las Vegas Raiders", "LV", "AFC", "WEST"),
    (16, "Los Angeles Chargers", "LAC", "AFC", "WEST"),
    # NFC East
    (17, "Dallas Cowboys", "DAL", "NFC", "EAST"),
    (18, "New York Giants", "NYG", "NFC", "EAST"),
    (19, "Philadelphia Eagles", "PHI", "NFC", "EAST"),
    (20, "Washington Commanders", "WAS", "NFC", "EAST"),
    # NFC North
    (21, "Chicago Bears", "CHI", "NFC", "NORTH"),
    (22, "Detroit Lions", "DET", "NFC", "NORTH"),
    (23, "Green Bay Packers", "GB", "NFC", "NORTH"),
    (24, "Minnesota Vikings", "MIN", "NFC", "NORTH"),
    # NFC South
    (25, "Atlanta Falcons", "ATL", "NFC", "SOUTH"),
    (26, "Carolina Panthers", "CAR", "NFC", "SOUTH"),
    (27, "New Orleans Saints", "NO", "NFC", "SOUTH"),
    (28, "Tampa Bay Buccaneers", "TB", "NFC", "SOUTH"),
    # NFC West
    (29, "Arizona Cardinals", "ARI", "NFC", "WEST"),
    (30, "Los Angeles Rams", "LAR", "NFC", "WEST"),
    (31, "San Francisco 49ers", "SF", "NFC", "WEST"),
    (32, "Seattle Seahawks", "SEA", "NFC", "WEST"),
]

def _rating_for(idx: int) -> int:
    # Simple deterministic spread: 1450..1650 cycling by index
    base = 1450 + ((idx % 11) * 20)
    return min(1700, max(1300, base))

@router.get("/seed")
def dev_seed(db: Session = Depends(get_db)):
    existing = db.query(Team).count()
    if existing and existing >= 32:
        return {"skipped": True, "teams_found": existing}

    # Wipe current teams only if you prefer a clean slate; by default we don't delete.
    # db.query(Team).delete(); db.commit()

    inserted = 0
    for i, (tid, name, abbr, conf, div) in enumerate(_TEAMS):
        found = db.query(Team).filter(Team.id == tid).one_or_none()
        if found:
            continue
        t = Team(
            id=tid,
            location_name=name.split()[-1],  # Extract city/location from full name
            nickname=name.split()[-1],      # Use last part as nickname
            name=name,
            abbr=abbr,
            conference=conf,
            division=div,
            wins=9 - ((i % 5)),           # deterministic but varied
            losses=8 - (9 - ((i % 5))),  # balances to 17-ish season feel
            ties=0,
            points_for=0,
            points_against=0,
            elo=_rating_for(i),  # Use elo instead of power_rating
        )
        # Optional: if Team has logo_url, set None to avoid broken links.
        if hasattr(t, "logo_url"):
            setattr(t, "logo_url", None)
        db.add(t)
        inserted += 1
    db.commit()
    return {"inserted": inserted}

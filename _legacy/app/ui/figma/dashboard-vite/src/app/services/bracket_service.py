from __future__ import annotations
from typing import List, Dict, Any
from sqlmodel import Session, select
from app.models.playoffs import PlayoffBracket
from app.services.seeding_service import seed_both_conferences, get_playoff_bracket_structure

def generate_bracket(sess: Session, season: int) -> PlayoffBracket:
    """Generate playoff bracket for a season."""
    seeds = seed_both_conferences(sess, season)
    row = sess.exec(select(PlayoffBracket).where(PlayoffBracket.season == season)).first()
    
    csv_afc = ",".join(str(x) for x in seeds["AFC"])
    csv_nfc = ",".join(str(x) for x in seeds["NFC"])
    
    if not row:
        row = PlayoffBracket(season=season, afc_seeds_csv=csv_afc, nfc_seeds_csv=csv_nfc)
    else:
        row.afc_seeds_csv = csv_afc
        row.nfc_seeds_csv = csv_nfc
    
    sess.add(row)
    sess.commit()
    sess.refresh(row)
    return row

def get_bracket(sess: Session, season: int) -> PlayoffBracket:
    """Get playoff bracket for a season."""
    return sess.exec(select(PlayoffBracket).where(PlayoffBracket.season == season)).first()

def get_bracket_seeds(sess: Session, season: int) -> Dict[str, List[int]]:
    """Get playoff seeds as lists of team IDs."""
    bracket = get_bracket(sess, season)
    if not bracket:
        return {"AFC": [], "NFC": []}
    
    to_int = lambda s: [int(x) for x in s.split(",") if x]
    return {
        "AFC": to_int(bracket.afc_seeds_csv),
        "NFC": to_int(bracket.nfc_seeds_csv)
    }

def get_detailed_bracket(sess: Session, season: int) -> Dict[str, Any]:
    """Get detailed playoff bracket with team information."""
    bracket_structure = get_playoff_bracket_structure(sess, season)
    bracket_seeds = get_bracket_seeds(sess, season)
    
    return {
        "season": season,
        "seeds": bracket_seeds,
        "detailed_seeds": bracket_structure,
        "generated": bracket_structure is not None
    }

def create_playoff_matchups(sess: Session, season: int) -> List[Dict[str, Any]]:
    """Create playoff matchups based on bracket."""
    seeds = get_bracket_seeds(sess, season)
    
    if len(seeds["AFC"]) < 7 or len(seeds["NFC"]) < 7:
        return []
    
    matchups = []
    
    # Wild Card Round (Week 19)
    # AFC: 2v7, 3v6, 4v5
    # NFC: 2v7, 3v6, 4v5
    for conference in ["AFC", "NFC"]:
        conf_seeds = seeds[conference]
        matchups.extend([
            {
                "week": 19,
                "round": "Wild Card",
                "conference": conference,
                "home_seed": 2,
                "away_seed": 7,
                "home_team_id": conf_seeds[1],  # Seed 2
                "away_team_id": conf_seeds[6],  # Seed 7
            },
            {
                "week": 19,
                "round": "Wild Card",
                "conference": conference,
                "home_seed": 3,
                "away_seed": 6,
                "home_team_id": conf_seeds[2],  # Seed 3
                "away_team_id": conf_seeds[5],  # Seed 6
            },
            {
                "week": 19,
                "round": "Wild Card",
                "conference": conference,
                "home_seed": 4,
                "away_seed": 5,
                "home_team_id": conf_seeds[3],  # Seed 4
                "away_team_id": conf_seeds[4],  # Seed 5
            }
        ])
    
    # Divisional Round (Week 20)
    # AFC: 1v(lowest remaining), (highest remaining)v(other remaining)
    # NFC: 1v(lowest remaining), (highest remaining)v(other remaining)
    for conference in ["AFC", "NFC"]:
        matchups.extend([
            {
                "week": 20,
                "round": "Divisional",
                "conference": conference,
                "home_seed": 1,
                "away_seed": "TBD",
                "home_team_id": seeds[conference][0],  # Seed 1
                "away_team_id": None,  # TBD from Wild Card
            },
            {
                "week": 20,
                "round": "Divisional",
                "conference": conference,
                "home_seed": "TBD",
                "away_seed": "TBD",
                "home_team_id": None,  # TBD from Wild Card
                "away_team_id": None,  # TBD from Wild Card
            }
        ])
    
    # Conference Championship (Week 21)
    for conference in ["AFC", "NFC"]:
        matchups.append({
            "week": 21,
            "round": "Conference Championship",
            "conference": conference,
            "home_seed": "TBD",
            "away_seed": "TBD",
            "home_team_id": None,  # TBD from Divisional
            "away_team_id": None,  # TBD from Divisional
        })
    
    # Super Bowl (Week 22)
    matchups.append({
        "week": 22,
        "round": "Super Bowl",
        "conference": "NFL",
        "home_seed": "TBD",
        "away_seed": "TBD",
        "home_team_id": None,  # TBD from Conference Championships
        "away_team_id": None,  # TBD from Conference Championships
    })
    
    return matchups

def get_playoff_teams(sess: Session, season: int) -> Dict[str, List[int]]:
    """Get all playoff teams by conference."""
    return get_bracket_seeds(sess, season)

def is_playoff_team(sess: Session, season: int, team_id: int) -> bool:
    """Check if a team made the playoffs."""
    seeds = get_bracket_seeds(sess, season)
    return team_id in seeds["AFC"] or team_id in seeds["NFC"]

def get_team_playoff_seed(sess: Session, season: int, team_id: int) -> Dict[str, Any]:
    """Get a team's playoff seed information."""
    seeds = get_bracket_seeds(sess, season)
    
    for conference in ["AFC", "NFC"]:
        if team_id in seeds[conference]:
            seed = seeds[conference].index(team_id) + 1
            return {
                "team_id": team_id,
                "conference": conference,
                "seed": seed,
                "is_division_winner": seed <= 4,
                "is_wildcard": seed > 4
            }
    
    return {
        "team_id": team_id,
        "conference": None,
        "seed": None,
        "is_division_winner": False,
        "is_wildcard": False
    }

def get_playoff_summary(sess: Session, season: int) -> Dict[str, Any]:
    """Get playoff summary for a season."""
    seeds = get_bracket_seeds(sess, season)
    bracket = get_bracket(sess, season)
    
    summary = {
        "season": season,
        "generated": bracket is not None,
        "afc_teams": len(seeds["AFC"]),
        "nfc_teams": len(seeds["NFC"]),
        "total_playoff_teams": len(seeds["AFC"]) + len(seeds["NFC"]),
        "afc_seeds": seeds["AFC"],
        "nfc_seeds": seeds["NFC"]
    }
    
    if bracket:
        summary["generated_at"] = getattr(bracket, "created_at", None)
    
    return summary

def delete_bracket(sess: Session, season: int) -> bool:
    """Delete playoff bracket for a season."""
    bracket = get_bracket(sess, season)
    if not bracket:
        return False
    
    sess.delete(bracket)
    sess.commit()
    return True

def regenerate_bracket(sess: Session, season: int) -> PlayoffBracket:
    """Regenerate playoff bracket for a season."""
    # Delete existing bracket
    delete_bracket(sess, season)
    
    # Generate new bracket
    return generate_bracket(sess, season)


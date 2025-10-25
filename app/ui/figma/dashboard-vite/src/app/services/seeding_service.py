from __future__ import annotations
from typing import List, Tuple
from sqlmodel import Session, select
from app.models.standings import Standings

# MVP NFL-like tiebreakers (simplified order):
# 1) Win%  2) Head-to-head (ignored in MVP unless exactly 2 teams & a game exists)  3) Division W-L
# 4) Common games win% (skip MVP)  5) Conference W-L  6) Strength of Victory (skip)  7) Strength of Schedule (SOS)  8) Power Rating

def _win_pct(s: Standings) -> float:
    """Calculate win percentage."""
    g = s.wins + s.losses + s.ties
    return (s.wins + 0.5 * s.ties) / g if g > 0 else 0.0

def _conference_of(sess: Session, team_id: int) -> str:
    """Get conference for a team."""
    try:
        from app.models.team import Team
        t = sess.get(Team, team_id)
        return getattr(t, "conference", "AFC")
    except Exception:
        return "AFC"

def _division_of(sess: Session, team_id: int) -> str:
    """Get division for a team."""
    try:
        from app.models.team import Team
        t = sess.get(Team, team_id)
        return getattr(t, "division", "E")
    except Exception:
        return "E"

def _sort_key(sess: Session, s: Standings) -> tuple:
    """Create sort key for standings tiebreaking."""
    # Higher is better, so we invert with negatives where needed
    return (
        _win_pct(s),
        s.division_wins - s.division_losses,
        s.conference_wins - s.conference_losses,
        -abs(s.sos),           # smaller magnitude SOS disadvantage first; you can tweak
        s.power_rating,
        -(s.points_against),   # as last whisper
    )

def seed_conference(sess: Session, season: int, conf: str) -> List[int]:
    """Seed a conference for playoffs."""
    rows = [r for r in sess.exec(select(Standings).where(Standings.season == season))]
    rows = [r for r in rows if _conference_of(sess, r.team_id) == conf]
    
    # Division winners first (N,E,S,W), seeded by the same sort key within division
    seeds: List[int] = []
    divisions = ["N", "E", "S", "W"]
    div_winners = []
    
    for d in divisions:
        div_rows = [r for r in rows if _division_of(sess, r.team_id) == d]
        if not div_rows: 
            continue
        div_rows.sort(key=lambda x: _sort_key(sess, x), reverse=True)
        div_winners.append(div_rows[0])
    
    # Rank division winners
    div_winners.sort(key=lambda x: _sort_key(sess, x), reverse=True)
    seeds.extend([r.team_id for r in div_winners])
    
    # Wildcards: next best 3 by sort key among the rest
    winner_ids = set(seeds)
    others = [r for r in rows if r.team_id not in winner_ids]
    others.sort(key=lambda x: _sort_key(sess, x), reverse=True)
    seeds.extend([r.team_id for r in others[:3]])
    
    # Ensure length 7 (pad if DB incomplete)
    return seeds[:7]

def seed_both_conferences(sess: Session, season: int) -> dict:
    """Seed both conferences for playoffs."""
    return {
        "AFC": seed_conference(sess, season, "AFC"), 
        "NFC": seed_conference(sess, season, "NFC")
    }

def get_division_winners(sess: Session, season: int, conference: str) -> List[Standings]:
    """Get division winners for a conference."""
    standings = list(sess.exec(select(Standings).where(Standings.season == season)))
    conference_standings = [s for s in standings if _conference_of(sess, s.team_id) == conference]
    
    division_winners = []
    divisions = ["N", "E", "S", "W"]
    
    for div in divisions:
        div_standings = [s for s in conference_standings if _division_of(sess, s.team_id) == div]
        if div_standings:
            div_standings.sort(key=lambda x: _sort_key(sess, x), reverse=True)
            division_winners.append(div_standings[0])
    
    return division_winners

def get_wildcard_teams(sess: Session, season: int, conference: str) -> List[Standings]:
    """Get wildcard teams for a conference."""
    standings = list(sess.exec(select(Standings).where(Standings.season == season)))
    conference_standings = [s for s in standings if _conference_of(sess, s.team_id) == conference]
    
    # Get division winners
    div_winners = get_division_winners(sess, season, conference)
    winner_ids = {s.team_id for s in div_winners}
    
    # Get non-division winners
    wildcard_candidates = [s for s in conference_standings if s.team_id not in winner_ids]
    wildcard_candidates.sort(key=lambda x: _sort_key(sess, x), reverse=True)
    
    # Return top 3 wildcard teams
    return wildcard_candidates[:3]

def get_playoff_seeds(sess: Session, season: int, conference: str) -> List[dict]:
    """Get detailed playoff seeds for a conference."""
    division_winners = get_division_winners(sess, season, conference)
    wildcard_teams = get_wildcard_teams(sess, season, conference)
    
    # Sort division winners by seed
    division_winners.sort(key=lambda x: _sort_key(sess, x), reverse=True)
    
    seeds = []
    
    # Add division winners (seeds 1-4)
    for i, team in enumerate(division_winners):
        seeds.append({
            "seed": i + 1,
            "team_id": team.team_id,
            "division": _division_of(sess, team.team_id),
            "is_division_winner": True,
            "wins": team.wins,
            "losses": team.losses,
            "ties": team.ties,
            "power_rating": team.power_rating
        })
    
    # Add wildcard teams (seeds 5-7)
    for i, team in enumerate(wildcard_teams):
        seeds.append({
            "seed": i + 5,
            "team_id": team.team_id,
            "division": _division_of(sess, team.team_id),
            "is_division_winner": False,
            "wins": team.wins,
            "losses": team.losses,
            "ties": team.ties,
            "power_rating": team.power_rating
        })
    
    return seeds

def get_playoff_bracket_structure(sess: Session, season: int) -> dict:
    """Get playoff bracket structure."""
    afc_seeds = get_playoff_seeds(sess, season, "AFC")
    nfc_seeds = get_playoff_seeds(sess, season, "NFC")
    
    return {
        "AFC": afc_seeds,
        "NFC": nfc_seeds,
        "season": season
    }

def validate_playoff_seeds(sess: Session, season: int) -> dict:
    """Validate playoff seeds and return any issues."""
    issues = []
    
    try:
        afc_seeds = seed_conference(sess, season, "AFC")
        nfc_seeds = seed_conference(sess, season, "NFC")
        
        # Check if we have enough teams
        if len(afc_seeds) < 7:
            issues.append(f"AFC only has {len(afc_seeds)} playoff teams (need 7)")
        
        if len(nfc_seeds) < 7:
            issues.append(f"NFC only has {len(nfc_seeds)} playoff teams (need 7)")
        
        # Check for duplicate teams
        if len(set(afc_seeds)) != len(afc_seeds):
            issues.append("AFC has duplicate teams in playoff seeds")
        
        if len(set(nfc_seeds)) != len(nfc_seeds):
            issues.append("NFC has duplicate teams in playoff seeds")
        
        # Check division winners
        afc_div_winners = get_division_winners(sess, season, "AFC")
        nfc_div_winners = get_division_winners(sess, season, "NFC")
        
        if len(afc_div_winners) < 4:
            issues.append(f"AFC only has {len(afc_div_winners)} division winners (need 4)")
        
        if len(nfc_div_winners) < 4:
            issues.append(f"NFC only has {len(nfc_div_winners)} division winners (need 4)")
        
    except Exception as e:
        issues.append(f"Error validating playoff seeds: {str(e)}")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "season": season
    }


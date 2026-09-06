from __future__ import annotations
from sqlmodel import Session
from app.services.standings_service import apply_result, recompute_sos
from app.services.bracket_service import generate_bracket

def on_game_final(sess: Session, season: int, game_id: int, week: int):
    """
    Called when a game is finalized.
    Updates standings, power ratings, and generates playoff bracket if needed.
    """
    # Apply game result to standings and power ratings
    apply_result(sess, season, game_id)
    
    # Recompute SOS every couple weeks (cheap operation)
    if week % 2 == 0:
        recompute_sos(sess, season)
    
    # Generate playoff bracket after Week 18
    if week == 18:
        generate_bracket(sess, season)

def on_week_complete(sess: Session, season: int, week: int):
    """
    Called when a week is completed.
    Updates SOS and generates playoff bracket if needed.
    """
    # Recompute SOS at end of each week
    recompute_sos(sess, season)
    
    # Generate playoff bracket after Week 18
    if week == 18:
        generate_bracket(sess, season)

def on_season_complete(sess: Session, season: int):
    """
    Called when a season is completed.
    Final updates and cleanup.
    """
    # Final SOS computation
    recompute_sos(sess, season)
    
    # Ensure playoff bracket is generated
    from app.services.bracket_service import get_bracket
    bracket = get_bracket(sess, season)
    if not bracket:
        generate_bracket(sess, season)

def batch_apply_results(sess: Session, season: int, week: int, game_results: list):
    """
    Apply multiple game results in batch.
    More efficient than calling on_game_final multiple times.
    """
    for game_result in game_results:
        game_id = game_result.get("game_id")
        if game_id:
            apply_result(sess, season, game_id)
    
    # Recompute SOS once after all games
    recompute_sos(sess, season)
    
    # Generate playoff bracket if Week 18
    if week == 18:
        generate_bracket(sess, season)

def get_standings_snapshot(sess: Session, season: int, week: int) -> dict:
    """
    Get standings snapshot for a specific week.
    Useful for historical standings tracking.
    """
    from app.services.standings_service import get_standings, get_power_rankings
    
    standings = get_standings(sess, season)
    power_rankings = get_power_rankings(sess, season)
    
    return {
        "season": season,
        "week": week,
        "standings": [
            {
                "team_id": s.team_id,
                "wins": s.wins,
                "losses": s.losses,
                "ties": s.ties,
                "points_for": s.points_for,
                "points_against": s.points_against,
                "division_wins": s.division_wins,
                "division_losses": s.division_losses,
                "conference_wins": s.conference_wins,
                "conference_losses": s.conference_losses,
                "sos": s.sos,
                "power_rating": s.power_rating
            }
            for s in standings
        ],
        "power_rankings": [
            {
                "team_id": s.team_id,
                "power_rating": s.power_rating,
                "rank": i + 1
            }
            for i, s in enumerate(power_rankings)
        ]
    }

def get_weekly_summary(sess: Session, season: int, week: int) -> dict:
    """
    Get weekly summary including standings changes and power rating movements.
    """
    from app.services.standings_service import get_standings_summary
    from app.services.bracket_service import get_playoff_summary
    
    standings_summary = get_standings_summary(sess, season)
    playoff_summary = get_playoff_summary(sess, season)
    
    return {
        "season": season,
        "week": week,
        "standings_summary": standings_summary,
        "playoff_summary": playoff_summary,
        "bracket_generated": week >= 18 and playoff_summary["generated"]
    }

def validate_standings(sess: Session, season: int) -> dict:
    """
    Validate standings for consistency and return any issues.
    """
    issues = []
    
    try:
        from app.services.standings_service import get_standings
        from app.services.seeding_service import validate_playoff_seeds
        
        standings = get_standings(sess, season)
        
        # Check if we have standings for all teams
        if len(standings) < 32:
            issues.append(f"Only {len(standings)} teams have standings (need 32)")
        
        # Check for negative values
        for s in standings:
            if s.wins < 0 or s.losses < 0 or s.ties < 0:
                issues.append(f"Team {s.team_id} has negative wins/losses/ties")
            
            if s.points_for < 0 or s.points_against < 0:
                issues.append(f"Team {s.team_id} has negative points")
            
            if s.power_rating < 0:
                issues.append(f"Team {s.team_id} has negative power rating")
        
        # Validate playoff seeds if bracket exists
        playoff_validation = validate_playoff_seeds(sess, season)
        if not playoff_validation["valid"]:
            issues.extend(playoff_validation["issues"])
        
    except Exception as e:
        issues.append(f"Error validating standings: {str(e)}")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "season": season
    }

def reset_standings(sess: Session, season: int) -> bool:
    """
    Reset standings for a season.
    Useful for testing or season restart.
    """
    try:
        from sqlmodel import select
        from app.models.standings import Standings
        
        # Delete all standings for the season
        standings = list(sess.exec(select(Standings).where(Standings.season == season)))
        for s in standings:
            sess.delete(s)
        
        sess.commit()
        return True
    
    except Exception:
        return False

def initialize_standings(sess: Session, season: int, team_ids: list) -> bool:
    """
    Initialize standings for all teams in a season.
    """
    try:
        from app.models.standings import Standings
        
        for team_id in team_ids:
            standings = Standings(season=season, team_id=team_id, power_rating=1500.0)
            sess.add(standings)
        
        sess.commit()
        return True
    
    except Exception:
        return False


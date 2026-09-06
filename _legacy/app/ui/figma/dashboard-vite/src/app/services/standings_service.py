from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, List, Dict
from math import erf, sqrt
from sqlmodel import Session, select
from app.models.standings import Standings
from app.models.schedule import Game, GameResult

HOME_FIELD = 55.0      # elo points
K_BASE = 18.0          # base K
MARGIN_MULT = 1.0      # small margin scaling
BLOWOUT_CUT = 17       # treat >17 as capped for margin

def _get_or_init(sess: Session, season: int, team_id: int) -> Standings:
    """Get or initialize standings for a team."""
    row = sess.exec(select(Standings).where(Standings.season == season, Standings.team_id == team_id)).first()
    if not row:
        row = Standings(season=season, team_id=team_id, power_rating=1500.0)
        sess.add(row)
        sess.commit()
        sess.refresh(row)
    return row

def _expected_score(pr_a: float, pr_b: float, home_adv: float) -> float:
    """Calculate expected score with home advantage."""
    # Elo expected with home adv on A
    diff = (pr_a + home_adv) - pr_b
    return 1.0 / (1.0 + 10.0 ** (-diff / 400.0))

def _k_factor(margin: int) -> float:
    """Calculate K factor based on margin of victory."""
    m = min(abs(margin), BLOWOUT_CUT)
    return K_BASE * (1.0 + (m / 21.0) * MARGIN_MULT)

def _conf_div(sess: Session, team_id: int) -> Tuple[str, str]:
    """Get conference and division for a team."""
    try:
        from app.models.team import Team
        t = sess.get(Team, team_id)
        return getattr(t, "conference", "AFC"), getattr(t, "division", "E")
    except Exception:
        return "AFC", "E"

def _game_conf_div(sess: Session, a: int, b: int) -> Tuple[bool, bool]:
    """Check if teams are in same conference and division."""
    ca, da = _conf_div(sess, a)
    cb, db = _conf_div(sess, b)
    return ca == cb, (da == db and ca == cb)

def _update_winloss(sess: Session, s_home: Standings, s_away: Standings, home_score: int, away_score: int):
    """Update win/loss records and conference/division records."""
    same_conf, same_div = _game_conf_div(sess, s_home.team_id, s_away.team_id)
    
    if home_score > away_score:
        s_home.wins += 1
        s_away.losses += 1
        if same_conf: 
            s_home.conference_wins += 1
            s_away.conference_losses += 1
        if same_div:  
            s_home.division_wins += 1
            s_away.division_losses += 1
    elif away_score > home_score:
        s_away.wins += 1
        s_home.losses += 1
        if same_conf: 
            s_away.conference_wins += 1
            s_home.conference_losses += 1
        if same_div:  
            s_away.division_wins += 1
            s_home.division_losses += 1
    else:
        s_home.ties += 1
        s_away.ties += 1
        # Ties don't affect conference/division records

    s_home.points_for += home_score
    s_home.points_against += away_score
    s_away.points_for += away_score
    s_away.points_against += home_score

def apply_result(sess: Session, season: int, game_id: int):
    """Apply a game result to standings and power ratings."""
    g = sess.get(Game, game_id)
    r = sess.exec(select(GameResult).where(GameResult.game_id == game_id)).first()
    if not g or not r:
        return
    
    s_home = _get_or_init(sess, season, g.home_team_id)
    s_away = _get_or_init(sess, season, g.away_team_id)

    # ELO expected & update
    exp_home = _expected_score(s_home.power_rating, s_away.power_rating, HOME_FIELD)
    margin = r.home_score - r.away_score
    score_home = 1.0 if margin > 0 else 0.0 if margin < 0 else 0.5
    K = _k_factor(margin)
    delta = K * (score_home - exp_home)
    s_home.power_rating += delta
    s_away.power_rating -= delta

    # Win/loss, PF/PA, conf/div
    _update_winloss(sess, s_home, s_away, r.home_score, r.away_score)
    sess.add(s_home)
    sess.add(s_away)
    sess.commit()

def recompute_sos(sess: Session, season: int):
    """Recompute strength of schedule for all teams."""
    # Simple: SOS = avg opponents' PR / 1500.0 - 1 (centered), scaled small
    teams = list(sess.exec(select(Standings).where(Standings.season == season)))
    pr_map = {t.team_id: t.power_rating for t in teams}
    
    # Naive schedule pass
    from collections import defaultdict
    opps: Dict[int, List[int]] = defaultdict(list)
    games = list(sess.exec(select(Game).where(Game.season == season)))
    
    for g in games:
        opps[g.home_team_id].append(g.away_team_id)
        opps[g.away_team_id].append(g.home_team_id)
    
    for t in teams:
        opp_prs = [pr_map.get(o, 1500.0) for o in opps.get(t.team_id, [])]
        if opp_prs:
            t.sos = (sum(opp_prs) / len(opp_prs)) / 1500.0 - 1.0
        else:
            t.sos = 0.0
        sess.add(t)
    
    sess.commit()

def get_standings(sess: Session, season: int, conference: str = None, division: str = None) -> List[Standings]:
    """Get standings for a season, optionally filtered by conference/division."""
    query = select(Standings).where(Standings.season == season)
    
    if conference:
        # Filter by conference
        standings = list(sess.exec(query))
        filtered = []
        for s in standings:
            try:
                from app.models.team import Team
                team = sess.get(Team, s.team_id)
                if team and getattr(team, "conference", "AFC") == conference:
                    filtered.append(s)
            except Exception:
                pass
        return filtered
    
    if division:
        # Filter by division
        standings = list(sess.exec(query))
        filtered = []
        for s in standings:
            try:
                from app.models.team import Team
                team = sess.get(Team, s.team_id)
                if team and getattr(team, "division", "E") == division:
                    filtered.append(s)
            except Exception:
                pass
        return filtered
    
    return list(sess.exec(query))

def get_team_standings(sess: Session, season: int, team_id: int) -> Standings:
    """Get standings for a specific team."""
    return _get_or_init(sess, season, team_id)

def get_power_rankings(sess: Session, season: int) -> List[Standings]:
    """Get power rankings sorted by power rating."""
    standings = list(sess.exec(select(Standings).where(Standings.season == season)))
    standings.sort(key=lambda s: s.power_rating, reverse=True)
    return standings

def get_division_standings(sess: Session, season: int, conference: str, division: str) -> List[Standings]:
    """Get standings for a specific division."""
    standings = get_standings(sess, season, conference=conference)
    div_standings = []
    
    for s in standings:
        try:
            from app.models.team import Team
            team = sess.get(Team, s.team_id)
            if team and getattr(team, "division", "E") == division:
                div_standings.append(s)
        except Exception:
            pass
    
    return div_standings

def get_conference_standings(sess: Session, season: int, conference: str) -> List[Standings]:
    """Get standings for a specific conference."""
    return get_standings(sess, season, conference=conference)

def calculate_win_percentage(standings: Standings) -> float:
    """Calculate win percentage for standings."""
    games = standings.wins + standings.losses + standings.ties
    return (standings.wins + 0.5 * standings.ties) / games if games > 0 else 0.0

def get_standings_summary(sess: Session, season: int) -> dict:
    """Get comprehensive standings summary."""
    standings = get_standings(sess, season)
    
    summary = {
        "season": season,
        "total_teams": len(standings),
        "conferences": {"AFC": 0, "NFC": 0},
        "divisions": {"N": 0, "E": 0, "S": 0, "W": 0},
        "avg_power_rating": 0.0,
        "highest_power_rating": 0.0,
        "lowest_power_rating": 0.0
    }
    
    if standings:
        # Calculate averages
        power_ratings = [s.power_rating for s in standings]
        summary["avg_power_rating"] = sum(power_ratings) / len(power_ratings)
        summary["highest_power_rating"] = max(power_ratings)
        summary["lowest_power_rating"] = min(power_ratings)
        
        # Count by conference and division
        for s in standings:
            try:
                from app.models.team import Team
                team = sess.get(Team, s.team_id)
                if team:
                    conf = getattr(team, "conference", "AFC")
                    div = getattr(team, "division", "E")
                    summary["conferences"][conf] += 1
                    summary["divisions"][div] += 1
            except Exception:
                pass
    
    return summary


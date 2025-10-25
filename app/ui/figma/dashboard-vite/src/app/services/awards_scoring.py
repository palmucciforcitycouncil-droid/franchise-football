# app/services/awards_scoring.py
from __future__ import annotations
from typing import Dict

def weekly_offense_score(s: Dict[str, float]) -> float:
    """QB/RB/WR/TE unified: passing + rushing + receiving + ball security"""
    return (
        s.get("pass_yds",0)/4.5 + s.get("pass_td",0)*6 - s.get("pass_int",0)*8 - s.get("sacks_taken",0)*1.5 +
        s.get("rush_yds",0)/9 + s.get("rush_td",0)*6 - s.get("fumbles_lost",0)*8 +
        s.get("rec_yds",0)/9 + s.get("rec_td",0)*6
    )

def weekly_defense_score(s: Dict[str, float]) -> float:
    """Defensive scoring based on tackles, sacks, turnovers, etc."""
    return (
        s.get("tackles",0)*1.0 + s.get("tfl",0)*1.5 + s.get("sacks",0)*6 +
        s.get("ints",0)*8 + s.get("pbus",0)*2 + s.get("ff",0)*5 + s.get("fr",0)*3 + s.get("td_def",0)*12
    )

def weekly_special_teams_score(s: Dict[str, float]) -> float:
    """Special teams scoring: kicking, punting, returns"""
    kicking = s.get("fg_made",0)*4 - (s.get("fg_att",0)-s.get("fg_made",0))*1 + s.get("xp_made",0)*1
    punting = s.get("punts",0)*0.5 + s.get("punt_yds",0)/80
    returns = (s.get("kr_yds",0)+s.get("pr_yds",0))/40
    return kicking + punting + returns

def weekly_rookie_score(s: Dict[str, float]) -> float:
    """Rookie scoring: best of O/D/ST scaled down slightly"""
    return max(weekly_offense_score(s), weekly_defense_score(s), weekly_special_teams_score(s)) * 0.95

def season_player_mvp_score(s: Dict[str, float]) -> float:
    """MVP scoring: blend of box stats; QB-friendly but other stars qualify"""
    return (
        s.get("pass_yds",0)/25 + s.get("pass_td",0)*20 - s.get("pass_int",0)*35 +
        s.get("rush_yds",0)/10 + s.get("rush_td",0)*25 +
        s.get("rec_yds",0)/10 + s.get("rec_td",0)*25 -
        s.get("fumbles_lost",0)*30
    )

def season_opoy_score(s: Dict[str, float]) -> float:
    """Offensive Player of the Year scoring"""
    return (
        s.get("rush_yds",0)/9 + s.get("rush_td",0)*22 +
        s.get("rec_yds",0)/9 + s.get("rec_td",0)*22 +
        s.get("pass_yds",0)/30 + s.get("pass_td",0)*16
    )

def season_dpoy_score(s: Dict[str, float]) -> float:
    """Defensive Player of the Year scoring"""
    return (
        s.get("tackles",0)*1.2 + s.get("tfl",0)*2.5 + s.get("sacks",0)*30 +
        s.get("ints",0)*35 + s.get("pbus",0)*4 + s.get("ff",0)*18 + s.get("fr",0)*10 + s.get("td_def",0)*40
    )

def season_roy_score(s: Dict[str, float]) -> float:
    """Rookie of the Year scoring: similar to MVP but scaled"""
    return season_player_mvp_score(s) * 0.85

def season_coty_score(team: Dict[str, float]) -> float:
    """Coach of the Year scoring: team stats: win pct + point diff + improvement proxy"""
    return (
        team.get("w_pct",0)*400 +
        (team.get("points_for",0) - team.get("points_against",0))*0.5 +
        team.get("improvement",0)*120
    )

def season_gmoty_score(team: Dict[str, float]) -> float:
    """GM of the Year scoring: proxy: outperform talent/cap index (future). For now, win pct + +/- with higher weight on improvement."""
    return (
        team.get("w_pct",0)*350 +
        (team.get("points_for",0) - team.get("points_against",0))*0.4 +
        team.get("improvement",0)*180
    )



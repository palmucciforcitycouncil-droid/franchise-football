# app/services/reports.py
from __future__ import annotations
from typing import Iterable
from pathlib import Path
import csv
from sqlmodel import Session, select
from app.models.awards import AwardResult
from app.models.stats_models import TeamSeasonStats, PlayerSeasonStats

def export_awards_csv(session: Session, season: int, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"awards_{season}.csv"
    rows = session.exec(select(AwardResult).where(AwardResult.season == season).order_by(AwardResult.award, AwardResult.rank)).all()
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["season","award","rank","player_id","team_id","player_name","team_abbr","position","score","tiebreaker"])
        for r in rows:
            w.writerow([r.season, r.award, r.rank, r.player_id, r.team_id, r.player_name, r.team_abbr, r.position, r.score, r.tiebreaker])
    return path

def export_team_season_csv(session: Session, season: int, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"team_season_stats_{season}.csv"
    rows = session.exec(select(TeamSeasonStats).where(TeamSeasonStats.season == season)).all()
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "team_id","season","games","points_for","points_against","plays_offense","pass_attempts","rush_attempts",
            "pass_yards","rush_yards","turnovers","sacks_allowed","penalties","penalty_yards","wins","losses","ties",
            "ppg","plays_per_game","pass_rate"
        ])
        for r in rows:
            games = max(1, r.games_played)
            ppg = r.points_scored / games
            plays_per_game = getattr(r, 'plays_offense', 0) / games
            pass_attempts = getattr(r, 'pass_attempts', 0)
            rush_attempts = getattr(r, 'rush_attempts', 0)
            total_attempts = pass_attempts + rush_attempts
            pass_rate = (pass_attempts / total_attempts) if total_attempts > 0 else 0.0
            
            w.writerow([
                r.team_id, r.season, r.games_played, r.points_scored, r.points_allowed, 
                getattr(r, 'plays_offense', 0), pass_attempts, rush_attempts,
                r.passing_yards, r.rushing_yards, r.turnovers_committed, 
                getattr(r, 'sacks_allowed', 0), getattr(r, 'penalties', 0), getattr(r, 'penalty_yards', 0), 
                r.wins, r.losses, r.ties,
                round(ppg, 3), round(plays_per_game, 3), round(pass_rate, 4)
            ])
    return path

def export_player_season_csv(session: Session, season: int, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"player_season_stats_{season}.csv"
    rows = session.exec(select(PlayerSeasonStats).where(PlayerSeasonStats.season == season)).all()
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "player_id","team_id","season","games","snaps","pass_attempts","completions","pass_yards","pass_tds","interceptions",
            "rush_attempts","rush_yards","rush_tds","targets","receptions","recv_yards","recv_tds","fumbles",
            "tackles","sacks","tfl","qb_hits","interceptions_def","passes_defended","forced_fumbles","fumble_recoveries",
            "defensive_tds","returns","return_yards","return_tds"
        ])
        for r in rows:
            total_snaps = r.snaps_offense + r.snaps_defense + r.snaps_special_teams
            w.writerow([
                r.player_id, r.team_id, r.season, r.games_played, total_snaps, r.pass_attempts, r.pass_completions, r.pass_yards, r.pass_touchdowns, r.interceptions,
                r.rush_attempts, r.rush_yards, r.rush_touchdowns, r.targets, r.receptions, r.receiving_yards, r.receiving_touchdowns, r.fumbles,
                r.tackles, r.sacks, r.tackles_for_loss, r.quarterback_hits, r.interceptions_caught, r.pass_deflections, r.forced_fumbles, r.fumble_recoveries,
                getattr(r, 'defensive_tds', 0), getattr(r, 'returns', 0), getattr(r, 'return_yards', 0), getattr(r, 'return_tds', 0)
            ])
    return path

def export_league_summary_csv(session: Session, season: int, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"league_summary_{season}.csv"
    trs = session.exec(select(TeamSeasonStats).where(TeamSeasonStats.season == season)).all()
    teams = len(trs)
    games = sum(r.games_played for r in trs)
    league_ppg = (sum(r.points_scored for r in trs) / games) if games else 0.0
    plays_total = sum(getattr(r, 'plays_offense', 0) for r in trs)
    plays_per_game = (plays_total / games) if games else 0.0
    pass_att = sum(getattr(r, 'pass_attempts', 0) for r in trs)
    rush_att = sum(getattr(r, 'rush_attempts', 0) for r in trs)
    denom = pass_att + rush_att
    pass_rate = (pass_att / denom) if denom else 0.0
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["season","teams","games_counted","league_ppg","plays_per_game","pass_rate"])
        w.writerow([season, teams, games, round(league_ppg,3), round(plays_per_game,3), round(pass_rate,4)])
    return path

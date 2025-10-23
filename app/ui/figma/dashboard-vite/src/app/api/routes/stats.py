# app/api/routes/stats.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select
from app.db import get_engine
from app.models.stats_models import TeamSeasonStats, PlayerSeasonStats
from app.api.dto import TeamSeasonStatsRead, PlayerSeasonStatsRead, LeagueSummary

router = APIRouter(prefix="/seasons", tags=["stats"])

def _session() -> Session:
    return Session(get_engine())

@router.get("/{season}/teams/{team_id}/stats", response_model=TeamSeasonStatsRead)
def get_team_season_stats(season: int, team_id: int) -> TeamSeasonStatsRead:
    with _session() as session:
        r = session.exec(
            select(TeamSeasonStats).where(
                TeamSeasonStats.season == season, TeamSeasonStats.team_id == team_id
            )
        ).first()
        if not r:
            raise HTTPException(status_code=404, detail="Team season stats not found")
        
        # Calculate computed values
        games = max(1, r.games_played)
        ppg = r.points_scored / games
        plays_per_game = getattr(r, 'plays_offense', 0) / games
        pass_attempts = getattr(r, 'pass_attempts', 0)
        rush_attempts = getattr(r, 'rush_attempts', 0)
        total_attempts = pass_attempts + rush_attempts
        pass_rate = (pass_attempts / total_attempts) if total_attempts > 0 else 0.0
        
        return TeamSeasonStatsRead(
            team_id=r.team_id,
            season=r.season,
            games=r.games_played,
            points_for=r.points_scored,
            points_against=r.points_allowed,
            plays_offense=getattr(r, 'plays_offense', 0),
            pass_attempts=pass_attempts,
            rush_attempts=rush_attempts,
            pass_yards=r.passing_yards,
            rush_yards=r.rushing_yards,
            turnovers=r.turnovers_committed,
            sacks_allowed=getattr(r, 'sacks_allowed', 0),
            penalties=getattr(r, 'penalties', 0),
            penalty_yards=getattr(r, 'penalty_yards', 0),
            wins=r.wins,
            losses=r.losses,
            ties=r.ties,
            ppg=ppg,
            plays_per_game=plays_per_game,
            pass_rate=pass_rate,
        )

@router.get("/{season}/players/{player_id}/stats", response_model=PlayerSeasonStatsRead)
def get_player_season_stats(season: int, player_id: int) -> PlayerSeasonStatsRead:
    with _session() as session:
        r = session.exec(
            select(PlayerSeasonStats).where(
                PlayerSeasonStats.season == season, PlayerSeasonStats.player_id == player_id
            )
        ).first()
        if not r:
            raise HTTPException(status_code=404, detail="Player season stats not found")
        
        # Calculate computed values
        total_snaps = r.snaps_offense + r.snaps_defense + r.snaps_special_teams
        
        return PlayerSeasonStatsRead(
            player_id=r.player_id,
            team_id=r.team_id,
            season=r.season,
            games=r.games_played,
            snaps=total_snaps,
            pass_attempts=r.pass_attempts,
            completions=r.pass_completions,
            pass_yards=r.pass_yards,
            pass_tds=r.pass_touchdowns,
            interceptions=r.interceptions,
            rush_attempts=r.rush_attempts,
            rush_yards=r.rush_yards,
            rush_tds=r.rush_touchdowns,
            targets=r.targets,
            receptions=r.receptions,
            recv_yards=r.receiving_yards,
            recv_tds=r.receiving_touchdowns,
            fumbles=r.fumbles,
            tackles=r.tackles,
            sacks=r.sacks,
            tfl=r.tackles_for_loss,
            qb_hits=r.quarterback_hits,
            interceptions_def=r.interceptions_caught,
            passes_defended=r.pass_deflections,
            forced_fumbles=r.forced_fumbles,
            fumble_recoveries=r.fumble_recoveries,
            defensive_tds=getattr(r, 'defensive_tds', 0),
            returns=getattr(r, 'returns', 0),
            return_yards=getattr(r, 'return_yards', 0),
            return_tds=getattr(r, 'return_tds', 0),
        )

@router.get("/reports/league_summary/{season}", response_model=LeagueSummary)
def get_league_summary(season: int) -> LeagueSummary:
    with _session() as session:
        rows = session.exec(
            select(TeamSeasonStats).where(TeamSeasonStats.season == season)
        ).all()
        if not rows:
            raise HTTPException(status_code=404, detail="No league data for season")

        teams = len(rows)
        games = sum(r.games_played for r in rows)
        league_ppg = (sum(r.points_scored for r in rows) / games) if games else 0.0
        plays_total = sum(getattr(r, 'plays_offense', 0) for r in rows)
        plays_per_game = (plays_total / games) if games else 0.0
        pass_att = sum(getattr(r, 'pass_attempts', 0) for r in rows)
        rush_att = sum(getattr(r, 'rush_attempts', 0) for r in rows)
        denom = pass_att + rush_att
        pass_rate = (pass_att / denom) if denom else 0.0

        return LeagueSummary(
            season=season,
            teams=teams,
            games_counted=games,
            league_ppg=round(league_ppg, 3),
            plays_per_game=round(plays_per_game, 3),
            pass_rate=round(pass_rate, 4),
        )

# app/services/awards.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional
from sqlmodel import Session, select, delete
from statistics import mean

from app.models.stats_models import TeamSeasonStats, PlayerSeasonStats
from app.models.core_min import Player  # core Player owner
from app.models.awards import AwardResult

# ---------- Utility types

@dataclass(frozen=True)
class CandidatePlayer:
    player_id: int
    team_id: Optional[int]
    season: int
    position: Optional[str]
    player_name: Optional[str]
    score: float
    tieb: Tuple   # tie-breaker tuple


@dataclass(frozen=True)
class CandidateTeam:
    team_id: int
    season: int
    team_abbr: Optional[str]
    score: float
    tieb: Tuple   # tie-breaker tuple


# ---------- Public API

def compute_and_persist_awards(session: Session, season: int, top_n: int = 5) -> None:
    """
    Compute all seasonal awards and persist top N for each award.
    Idempotent: deletes prior season results and rewrites them.
    """
    # Wipe existing rows for season
    session.exec(delete(AwardResult).where(AwardResult.season == season))

    league_avg_ppg = _league_avg_ppg(session, season)

    # Players
    mvp = _rank_mvp(session, season, league_avg_ppg, top_n)
    opoy = _rank_opoy(session, season, top_n)
    dpoy = _rank_dpoy(session, season, top_n)
    roy = _rank_roy(session, season, top_n)

    # Teams
    coy = _rank_coy(session, season, league_avg_ppg, top_n)
    gmoy = _rank_gmoy(session, season, top_n)

    # Persist all lists
    _persist_player_award(session, season, "MVP", mvp)
    _persist_player_award(session, season, "OPOY", opoy)
    _persist_player_award(session, season, "DPOY", dpoy)
    _persist_player_award(session, season, "ROY", roy)

    _persist_team_award(session, season, "COY", coy)
    _persist_team_award(session, season, "GMOY", gmoy)

    session.commit()


# ---------- Scoring helpers

def _league_avg_ppg(session: Session, season: int) -> float:
    rows = session.exec(select(TeamSeasonStats).where(TeamSeasonStats.season == season)).all()
    if not rows:
        return 0.0
    return sum(r.points_scored for r in rows) / max(1, sum(r.games_played for r in rows))


def _safe_name(session: Session, pid: int) -> str:
    p = session.get(Player, pid)
    if not p:
        return ""
    try:
        return f"{p.first_name} {p.last_name}".strip()
    except Exception:
        return getattr(p, "name", "") or ""


def _safe_pos(session: Session, pid: int) -> str:
    p = session.get(Player, pid)
    return getattr(p, "position", None) or getattr(p, "pos", None) or ""


def _rookie_filter(session: Session, season: int, pss: PlayerSeasonStats) -> bool:
    # Preferred: explicit flag on Player
    p = session.get(Player, pss.player_id)
    if p is not None:
        if hasattr(p, "is_rookie") and getattr(p, "is_rookie") is True:
            return True
        if hasattr(p, "years_pro") and getattr(p, "years_pro") == 0:
            return True
    # Fallback: treat the minimum season for this player_id as rookie year
    seasons = session.exec(select(PlayerSeasonStats.season).where(
        PlayerSeasonStats.player_id == pss.player_id
    )).all()
    return seasons and pss.season == min(seasons)


# ---- Player award ranking

def _rank_mvp(session: Session, season: int, league_avg_ppg: float, top_n: int) -> List[CandidatePlayer]:
    rows = session.exec(select(PlayerSeasonStats).where(PlayerSeasonStats.season == season)).all()
    # Weighted composite; QB-centric but allows exceptional RB/WR/DEF to contend.
    cands: List[CandidatePlayer] = []
    for r in rows:
        off_yards = r.pass_yards + r.rush_yards + r.receiving_yards
        off_tds = r.pass_touchdowns + r.rush_touchdowns + r.receiving_touchdowns
        turnovers = r.interceptions + r.fumbles_lost

        # Simple positional prior: QBs get a mild base bump
        pos = _safe_pos(session, r.player_id)
        pos_prior = 10.0 if pos == "QB" else 0.0

        score = (
            off_yards * 0.02 +
            off_tds * 6.0 -
            turnovers * 8.0 +
            r.tackles * 0.2 +             # allow IDP outliers a path
            r.sacks * 3.0 +
            r.interceptions_caught * 8.0 +
            pos_prior
        )
        # Tie-breakers: more games played, team wins, player_id asc
        team_wins = _team_wins(session, season, r.team_id)
        tieb = (r.games_played, team_wins, -off_tds, -off_yards, -turnovers, r.player_id)
        name = _safe_name(session, r.player_id)
        cands.append(CandidatePlayer(r.player_id, r.team_id, season, pos, name, score, tieb))

    return _topn_stable(cands, top_n)


def _rank_opoy(session: Session, season: int, top_n: int) -> List[CandidatePlayer]:
    rows = session.exec(select(PlayerSeasonStats).where(PlayerSeasonStats.season == season)).all()
    cands: List[CandidatePlayer] = []
    for r in rows:
        off_yards = r.pass_yards + r.rush_yards + r.receiving_yards
        off_tds = r.pass_touchdowns + r.rush_touchdowns + r.receiving_touchdowns
        turnovers = r.interceptions + r.fumbles_lost
        pos = _safe_pos(session, r.player_id)

        # Offensive weighting, position-agnostic
        score = off_yards * 0.03 + off_tds * 7.0 - turnovers * 6.0
        tieb = (r.games_played, -off_tds, -off_yards, -turnovers, r.player_id)
        name = _safe_name(session, r.player_id)
        cands.append(CandidatePlayer(r.player_id, r.team_id, season, pos, name, score, tieb))

    return _topn_stable(cands, top_n)


def _rank_dpoy(session: Session, season: int, top_n: int) -> List[CandidatePlayer]:
    rows = session.exec(select(PlayerSeasonStats).where(PlayerSeasonStats.season == season)).all()
    cands: List[CandidatePlayer] = []
    for r in rows:
        # Defense-centric
        score = (
            r.tackles * 0.5 +
            r.sacks * 5.0 +
            r.tackles_for_loss * 1.0 +
            r.quarterback_hits * 0.5 +
            r.interceptions_caught * 9.0 +
            r.pass_deflections * 1.5 +
            r.forced_fumbles * 6.0 +
            r.fumble_recoveries * 3.0
        )
        tieb = (r.games_played, r.tackles, r.sacks, r.interceptions_caught, r.player_id)
        name = _safe_name(session, r.player_id)
        pos = _safe_pos(session, r.player_id)
        cands.append(CandidatePlayer(r.player_id, r.team_id, season, pos, name, score, tieb))
    return _topn_stable(cands, top_n)


def _rank_roy(session: Session, season: int, top_n: int) -> List[CandidatePlayer]:
    rows = session.exec(select(PlayerSeasonStats).where(PlayerSeasonStats.season == season)).all()
    cands: List[CandidatePlayer] = []
    for r in rows:
        if not _rookie_filter(session, season, r):
            continue
        off_yards = r.pass_yards + r.rush_yards + r.receiving_yards
        off_tds = r.pass_touchdowns + r.rush_touchdowns + r.receiving_touchdowns
        # Balanced rookie measure
        score = off_yards * 0.025 + off_tds * 6.0 + r.tackles * 0.25 + r.sacks * 3.0 + r.interceptions_caught * 7.0
        tieb = (r.games_played, -off_tds, -off_yards, r.player_id)
        name = _safe_name(session, r.player_id)
        pos = _safe_pos(session, r.player_id)
        cands.append(CandidatePlayer(r.player_id, r.team_id, season, pos, name, score, tieb))
    return _topn_stable(cands, top_n)


# ---- Team award ranking

def _rank_coy(session: Session, season: int, league_avg_ppg: float, top_n: int) -> List[CandidateTeam]:
    rows = session.exec(select(TeamSeasonStats).where(TeamSeasonStats.season == season)).all()
    if not rows:
        return []
    # league stats
    avg_ppg = league_avg_ppg or (sum(r.points_scored for r in rows) / max(1, sum(r.games_played for r in rows)))
    cands: List[CandidateTeam] = []
    for r in rows:
        games = max(1, r.games_played)
        win_pct = (r.wins + 0.5 * r.ties) / games
        ppg = r.points_scored / games
        papg = r.points_allowed / games
        pdpg = ppg - papg
        ppg_above = max(0.0, ppg - avg_ppg)  # modest reward for exceeding league avg
        score = win_pct * 100.0 + pdpg * 2.0 + ppg_above * 1.0
        tieb = (win_pct, pdpg, r.wins, -r.losses, r.team_id)
        cands.append(CandidateTeam(r.team_id, season, None, score, tieb))
    return _topn_stable(cands, top_n)


def _rank_gmoy(session: Session, season: int, top_n: int) -> List[CandidateTeam]:
    rows = session.exec(select(TeamSeasonStats).where(TeamSeasonStats.season == season)).all()
    cands: List[CandidateTeam] = []
    for r in rows:
        games = max(1, r.games_played)
        win_pct = (r.wins + 0.5 * r.ties) / games
        yards = r.passing_yards + r.rushing_yards
        # Estimate plays from yards (rough approximation: ~5 yards per play)
        plays = max(1, yards // 5)
        yards_per_play = yards / plays
        ppg = r.points_scored / games
        papg = r.points_allowed / games
        pdpg = ppg - papg
        score = win_pct * 50.0 + pdpg * 2.0 + yards_per_play * 5.0
        tieb = (win_pct, pdpg, yards_per_play, r.team_id)
        cands.append(CandidateTeam(r.team_id, season, None, score, tieb))
    return _topn_stable(cands, top_n)


# ---- Shared helpers

def _team_wins(session: Session, season: int, team_id: Optional[int]) -> int:
    if not team_id:
        return 0
    r = session.exec(select(TeamSeasonStats).where(
        TeamSeasonStats.season == season, TeamSeasonStats.team_id == team_id
    )).first()
    return r.wins if r else 0


def _topn_stable(cands, top_n: int):
    # Deterministic: sort by (-score, tie-break tuple)
    return sorted(cands, key=lambda c: (-c.score, c.tieb))[:top_n]


def _persist_player_award(session: Session, season: int, name: str, cands: List[CandidatePlayer]) -> None:
    for idx, c in enumerate(cands, start=1):
        session.add(AwardResult(
            season=season, award=name, rank=idx,
            player_id=c.player_id, team_id=c.team_id,
            player_name=c.player_name, position=c.position,
            team_abbr=None, score=float(c.score),
            tiebreaker=",".join(map(str, c.tieb))
        ))


def _persist_team_award(session: Session, season: int, name: str, cands: List[CandidateTeam]) -> None:
    for idx, c in enumerate(cands, start=1):
        session.add(AwardResult(
            season=season, award=name, rank=idx,
            player_id=None, team_id=c.team_id,
            player_name=None, position=None,
            team_abbr=c.team_abbr, score=float(c.score),
            tiebreaker=",".join(map(str, c.tieb))
        ))
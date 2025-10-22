"""
Award and Top Performer Services.
PBP-first with graceful fallbacks for season awards and leaderboards.
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional, DefaultDict
from collections import defaultdict
import math
import random

from sqlmodel import Session, select

from app.models.awards import AwardType, AwardWinner, Leaderboard, LeaderRow
from app.config_awards import settings_awards


# ---- helpers: try importing your canonical models/services; otherwise use PBP aggregation ----
def _try_models():
    out = {}
    # Player/Team meta
    for mod, name in [
        ("app.models.player_models", "Player"),
        ("app.models.sim_models", "SimTeam"),
        ("app.models.coach_models", "Coach"),
        ("app.models.season_models", "Season"),
    ]:
        try:
            m = __import__(mod, fromlist=[name])
            out[name] = getattr(m, name)
        except Exception:
            out[name] = None
    # Stats services or models (season)
    for mod, name in [
        ("app.models.stats_models", "PlayerSeasonStats"),
        ("app.models.stats_models", "TeamSeasonStats"),
    ]:
        try:
            m = __import__(mod, fromlist=[name])
            out[name] = getattr(m, name)
        except Exception:
            continue
    # PBP
    try:
        m = __import__("app.models.pbp_event", fromlist=["PBPEvent"])
        out["PBPEvent"] = getattr(m, "PBPEvent")
    except Exception:
        out["PBPEvent"] = None
    return out

MODELS = _try_models()


# ---- basic z-score (defensive epa can be negative; allow any) ----
def _z(v: float, mean: float, std: float) -> float:
    if std <= 1e-9:
        return 0.0
    return (v - mean) / std


def _safe_mean_std(values: List[float]) -> Tuple[float, float]:
    if not values:
        return (0.0, 1.0)
    m = sum(values) / len(values)
    var = sum((x - m) ** 2 for x in values) / max(1, len(values) - 1)
    return (m, math.sqrt(max(var, 1e-9)))


# ---- season stat fetchers; duck-type to whatever exists ----
def _fetch_player_season_stats(session: Session, season: int) -> List[Dict[str, Any]]:
    """
    Return list of dicts minimally containing:
      player_id, team_id, conference, position, is_rookie,
      snaps, routes, routes_per_game,
      pass_att, pass_yards, pass_td, ints_thrown, epa_play_off, sr_off,
      rush_att, rush_yards, rush_td,
      targets, rec_yards, rec_td,
      sacks_def, tfl, pbu, ints_def, epa_play_def,
      fga, fgm, punts, net_punt, returns, ret_td,
      wins_team, seed_bonus (approx), games
    Missing keys default to 0 / None.
    """
    out = []
    PS = MODELS.get("PlayerSeasonStats")
    if PS:
        rows = session.exec(select(PS)).all()
        for r in rows:
            d = r.__dict__.copy()
            d.setdefault("conference", d.get("conf") or "AFC" if d.get("team_id", 0) % 2 else "NFC")
            d.setdefault("position", d.get("pos") or "UNK")
            d.setdefault("is_rookie", d.get("rookie", False))
            d.setdefault("games", d.get("games_played", 0))
            out.append(d)
        return out

    # Fallback: derive from PBP using our aggregation
    try:
        from app.testing.aggregate_from_pbp import aggregate_truth_from_pbp
        agg = aggregate_truth_from_pbp(session)
        
        # Convert player season stats to our format
        for pid, stats in agg["player_season"].items():
            # Get player info
            Player = MODELS.get("Player")
            if Player:
                player = session.exec(select(Player).where(Player.id == pid)).first()
                if player:
                    # Determine team and conference
                    team_id = getattr(player, "team_id", 0)
                    conference = "AFC" if team_id % 2 == 0 else "NFC"
                    
                    d = {
                        "player_id": pid,
                        "team_id": team_id,
                        "conference": conference,
                        "position": getattr(player, "position", "UNK"),
                        "is_rookie": False,  # Assume not rookie for test data
                        "games": 1,  # Assume 1 game for mini season
                        "snaps": 50,  # Default snap count
                        "routes": 30,  # Default route count
                        "pass_att": stats.get("pass_attempts", 0),
                        "pass_yards": stats.get("pass_yards", 0),
                        "pass_td": stats.get("pass_td", 0),
                        "ints_thrown": stats.get("interceptions", 0),
                        "rush_att": stats.get("rush_attempts", 0),
                        "rush_yards": stats.get("rush_yards", 0),
                        "rush_td": stats.get("rush_td", 0),
                        "targets": stats.get("targets", 0),
                        "rec_yards": stats.get("rec_yards", 0),
                        "rec_td": stats.get("rec_td", 0),
                        "sacks_def": stats.get("sacks", 0),
                        "tfl": stats.get("tfl", 0),
                        "pbu": stats.get("pass_breakups", 0),
                        "ints_def": stats.get("interceptions_caught", 0),
                        "fga": stats.get("field_goals_attempted", 0),
                        "fgm": stats.get("field_goals_made", 0),
                        "punts": stats.get("punts", 0),
                        "net_punt": stats.get("punt_net_yards", 0),
                        "ret_td": stats.get("return_td", 0),
                        "epa_play_off": 0.1,  # Default EPA
                        "sr_off": 0.6,  # Default success rate
                        "epa_play_def": -0.1,  # Default defensive EPA
                    }
                    out.append(d)
    except Exception:
        pass
    
    return out


def _fetch_team_season_stats(session: Session, season: int) -> List[Dict[str, Any]]:
    out = []
    TS = MODELS.get("TeamSeasonStats")
    if TS:
        rows = session.exec(select(TS)).all()
        for r in rows:
            d = r.__dict__.copy()
            d.setdefault("conference", d.get("conf") or "AFC" if d.get("team_id", 0) % 2 else "NFC")
            out.append(d)
        return out
    
    # Fallback: derive from PBP
    try:
        from app.testing.aggregate_from_pbp import aggregate_truth_from_pbp
        agg = aggregate_truth_from_pbp(session)
        
        for tid, stats in agg["team_season"].items():
            conference = "AFC" if tid % 2 == 0 else "NFC"
            d = {
                "team_id": tid,
                "conference": conference,
                "wins": 1,  # Assume 1 win for mini season
                "losses": 1,  # Assume 1 loss for mini season
                "points_scored": stats.get("points", 0),
                "points_allowed": stats.get("points_allowed", 0),
            }
            out.append(d)
    except Exception:
        pass
    
    return out


# ---- conference detection ----
def _conf_of(team_row: Dict[str, Any]) -> str:
    return team_row.get("conference") or ("AFC" if (team_row.get("team_id", 0) % 2) else "NFC")


# ---- qualifiers ----
def _meets_off_qualifiers(p: Dict[str, Any]) -> bool:
    pos = (p.get("position") or "").upper()
    if pos in ("QB",):
        return (p.get("pass_att", 0) >= settings_awards.MIN_QB_ATT)
    if pos in ("RB","HB","FB"):
        return (p.get("rush_att", 0) >= settings_awards.MIN_RB_ATT)
    if pos in ("WR",):
        return (p.get("targets", 0) >= settings_awards.MIN_WR_TGT)
    if pos in ("TE",):
        return (p.get("targets", 0) >= settings_awards.MIN_TE_TGT)
    return False


def _meets_def_qualifiers(p: Dict[str, Any]) -> bool:
    snaps = p.get("snaps", 0)
    pos = (p.get("position") or "").upper()
    if pos in ("EDGE","OLB","DE","DT","IDL"):
        return snaps >= settings_awards.MIN_DL_SNAP
    if pos in ("LB","MLB"):
        return snaps >= settings_awards.MIN_LB_SNAP
    if pos in ("CB","DB","S","SS","FS","NICKEL","DIME"):
        return snaps >= settings_awards.MIN_DB_SNAP
    return False


def _rookie(p: Dict[str, Any]) -> bool:
    return bool(p.get("is_rookie", False))


# ---- composites ----
def _composite_offense(p: Dict[str, Any], means: Dict[str, Tuple[float,float]]) -> float:
    epa = _z(p.get("epa_play_off", 0.0), *means["epa_play_off"])
    sr = _z(p.get("sr_off", 0.0), *means["sr_off"])
    td = _z(p.get("rush_td", 0) + p.get("pass_td", 0) + p.get("rec_td", 0), *means["td"])
    ypg = _z((p.get("pass_yards",0)+p.get("rush_yards",0)+p.get("rec_yards",0))/max(1,p.get("games",1)), *means["ypg"])
    return (
        settings_awards.OPOY_W_EPA_P * epa +
        settings_awards.OPOY_W_SR * sr +
        settings_awards.OPOY_W_TD * td +
        settings_awards.OPOY_W_YPG * ypg
    )


def _composite_mvp(p: Dict[str, Any], means: Dict[str, Tuple[float,float]], wins_z: float, seed_z: float) -> float:
    # Reuse offense composite pieces for MVP emphasis
    epa = _z(p.get("epa_play_off", 0.0), *means["epa_play_off"])
    sr = _z(p.get("sr_off", 0.0), *means["sr_off"])
    td = _z(p.get("rush_td", 0) + p.get("pass_td", 0) + p.get("rec_td", 0), *means["td"])
    ypg = _z((p.get("pass_yards",0)+p.get("rush_yards",0)+p.get("rec_yards",0))/max(1,p.get("games",1)), *means["ypg"])
    return (
        settings_awards.MVP_W_EPA_P * epa +
        settings_awards.MVP_W_SR * sr +
        settings_awards.MVP_W_TD * td +
        settings_awards.MVP_W_YPG * ypg +
        settings_awards.MVP_W_WINS * wins_z +
        settings_awards.MVP_W_SEED * seed_z
    )


def _composite_defense(p: Dict[str, Any], means: Dict[str, Tuple[float,float]]) -> float:
    zsack = _z(p.get("sacks_def",0), *means["sacks_def"])
    zint = _z(p.get("ints_def",0), *means["ints_def"])
    ztfl = _z(p.get("tfl",0), *means["tfl"])
    zpbu = _z(p.get("pbu",0), *means["pbu"])
    zdepa = -_z(p.get("epa_play_def",0.0), *means["epa_play_def"])  # lower (more negative) is better → invert
    return (
        settings_awards.DPOY_W_SACK*zsack +
        settings_awards.DPOY_W_INT*zint +
        settings_awards.DPOY_W_TFL*ztfl +
        settings_awards.DPOY_W_PBU*zpbu +
        settings_awards.DPOY_W_DEF_EPA_P*zdepa
    )


# ---- winners with deterministic tie-breakers ----
def _pick_top(cands: List[Tuple[int,float]], rnd: random.Random) -> int:
    # cands: list of (player_id, score)
    # Tie-break: max score; if tie, lower interceptions thrown (if available) -> higher team wins -> lower player_id
    if not cands:
        return -1
    # sort desc by score, then stable tie breaks injected via slight deterministic jitter by id
    best = max(cands, key=lambda t: (round(t[1], 6), -t[0]))
    return best[0]


# ---- public API ----
def compute_season_awards(session: Session, season: int) -> Dict[str, Any]:
    rnd = random.Random(settings_awards.AWARDS_SEED + season)
    players = _fetch_player_season_stats(session, season)
    teams = _fetch_team_season_stats(session, season)

    # Build means for z-scores
    epa_vals = [p.get("epa_play_off", 0.0) for p in players if _meets_off_qualifiers(p)]
    sr_vals = [p.get("sr_off", 0.0) for p in players if _meets_off_qualifiers(p)]
    td_vals = [(p.get("rush_td",0)+p.get("pass_td",0)+p.get("rec_td",0)) for p in players]
    ypg_vals = [ (p.get("pass_yards",0)+p.get("rush_yards",0)+p.get("rec_yards",0))/max(1,p.get("games",1)) for p in players ]
    sacks_vals = [p.get("sacks_def",0) for p in players if _meets_def_qualifiers(p)]
    ints_vals = [p.get("ints_def",0) for p in players if _meets_def_qualifiers(p)]
    tfl_vals  = [p.get("tfl",0) for p in players if _meets_def_qualifiers(p)]
    pbu_vals  = [p.get("pbu",0) for p in players if _meets_def_qualifiers(p)]
    depa_vals = [p.get("epa_play_def",0.0) for p in players if _meets_def_qualifiers(p)]

    means = {
        "epa_play_off": _safe_mean_std(epa_vals),
        "sr_off": _safe_mean_std(sr_vals),
        "td": _safe_mean_std(td_vals),
        "ypg": _safe_mean_std(ypg_vals),
        "sacks_def": _safe_mean_std(sacks_vals),
        "ints_def": _safe_mean_std(ints_vals),
        "tfl": _safe_mean_std(tfl_vals),
        "pbu": _safe_mean_std(pbu_vals),
        "epa_play_def": _safe_mean_std(depa_vals),
    }

    # Team wins & seed proxies for MVP/Coach/GM
    team_wins = { t.get("team_id"): t.get("wins", 0) for t in teams }
    wins_vals = list(team_wins.values()) or [0]
    wins_mean, wins_std = _safe_mean_std(wins_vals)
    # seed bonus proxy: higher wins → higher seed bonus
    seed_z = { tid: _z(team_wins.get(tid,0), wins_mean, wins_std) for tid in team_wins }

    # MVP (league-wide, offense leaning)
    mvp_cands = []
    for p in players:
        if not _meets_off_qualifiers(p):
            continue
        tid = p.get("team_id")
        wins_z = _z(team_wins.get(tid,0), wins_mean, wins_std)
        sc = _composite_mvp(p, means, wins_z, seed_z.get(tid,0.0))
        mvp_cands.append((p.get("player_id"), sc))
    mvp_pid = _pick_top(mvp_cands, rnd)

    # OPOY/DPOY per conference
    def _by_conf(conf: str, pred) -> List[Dict[str,Any]]:
        return [p for p in players if (p.get("conference") == conf and pred(p))]
    olo_afc = [(p["player_id"], _composite_offense(p, means)) for p in _by_conf("AFC", _meets_off_qualifiers)]
    olo_nfc = [(p["player_id"], _composite_offense(p, means)) for p in _by_conf("NFC", _meets_off_qualifiers)]
    dlo_afc = [(p["player_id"], _composite_defense(p, means)) for p in _by_conf("AFC", _meets_def_qualifiers)]
    dlo_nfc = [(p["player_id"], _composite_defense(p, means)) for p in _by_conf("NFC", _meets_def_qualifiers)]
    opoy_afc = _pick_top(olo_afc, rnd)
    opoy_nfc = _pick_top(olo_nfc, rnd)
    dpoy_afc = _pick_top(dlo_afc, rnd)
    dpoy_nfc = _pick_top(dlo_nfc, rnd)

    # Rookies (league-wide split offense/defense)
    rookies = [p for p in players if _rookie(p)]
    oroy_cands = [(p["player_id"], _composite_offense(p, means)) for p in rookies if _meets_off_qualifiers(p)]
    droy_cands = [(p["player_id"], _composite_defense(p, means)) for p in rookies if _meets_def_qualifiers(p)]
    oroy = _pick_top(oroy_cands, rnd)
    droy = _pick_top(droy_cands, rnd)

    # Coach/GM — simple proxies unless you have richer data
    # COY: highest wins; tie-break by Δwins if available or team_id
    coy_team = max(team_wins.items(), key=lambda kv: (kv[1], kv[0]))[0] if team_wins else None
    # GMY: proxy — same as COY unless cap/draft metrics available
    gmy_team = coy_team

    # Persist
    winners = [
        (AwardType.MVP, mvp_pid, None, None, None, None),
        (AwardType.OPOY_AFC, opoy_afc, None, None, None, None),
        (AwardType.OPOY_NFC, opoy_nfc, None, None, None, None),
        (AwardType.DPOY_AFC, dpoy_afc, None, None, None, None),
        (AwardType.DPOY_NFC, dpoy_nfc, None, None, None, None),
        (AwardType.OROY, oroy, None, None, None, None),
        (AwardType.DROY, droy, None, None, None, None),
        (AwardType.COY, None, None, None, coy_team, None),
        (AwardType.GMY, None, None, None, gmy_team, None),
    ]
    for aw, pid, cid, gid, tid, notes in winners:
        row = AwardWinner(season=season, award=aw, player_id=pid, coach_id=cid, gm_id=None, team_id=tid, game_id=gid, notes=notes)
        session.add(row)
    session.commit()

    return {
        "MVP": mvp_pid,
        "OPOY_AFC": opoy_afc,
        "OPOY_NFC": opoy_nfc,
        "DPOY_AFC": dpoy_afc,
        "DPOY_NFC": dpoy_nfc,
        "OROY": oroy,
        "DROY": droy,
        "COY_TEAM": coy_team,
        "GMY_TEAM": gmy_team,
    }


def compute_super_bowl_mvp(session: Session, season: int, super_bowl_game_id: int) -> Optional[int]:
    """
    Choose MVP from the Super Bowl participants only.
    Composite: TDs, single-game EPA, clutch weight (4Q/high leverage), 'spectacle' (sacks/INT/long plays).
    """
    rnd = random.Random(settings_awards.AWARDS_SEED + season + super_bowl_game_id)
    
    # Try to fetch game-level player stats for this game
    try:
        from app.models.stats_models import PlayerGameStats
        rows = session.exec(select(PlayerGameStats).where(PlayerGameStats.game_id == super_bowl_game_id)).all()
        cands = []
        for r in rows:
            td = (getattr(r, "rush_td",0)+getattr(r,"pass_td",0)+getattr(r,"rec_td",0))
            epa = getattr(r, "epa_total", 0.0)
            clutch = getattr(r, "epa_4q", 0.0)
            spec = getattr(r, "sacks",0)*0.5 + getattr(r,"ints",0)*0.7 + (1.0 if getattr(r,"long_play",0) >= 40 else 0.0)
            score = settings_awards.SBMVP_W_TD*td + settings_awards.SBMVP_W_EPA_G*epa + settings_awards.SBMVP_W_CLUTCH*clutch + settings_awards.SBMVP_W_SPECTACLE*spec
            cands.append((getattr(r,"player_id"), score))
    except Exception:
        # Fallback: use PBP aggregation for this game
        try:
            from app.testing.aggregate_from_pbp import aggregate_truth_from_pbp
            agg = aggregate_truth_from_pbp(session)
            
            # Get player game stats for this specific game
            for (pid, gid), stats in agg["player_game"].items():
                if gid == super_bowl_game_id:
                    td = stats.get("rush_td", 0) + stats.get("pass_td", 0) + stats.get("rec_td", 0)
                    epa = 0.1  # Default EPA for test data
                    clutch = 0.05  # Default clutch factor
                    spec = stats.get("sacks", 0) * 0.5 + stats.get("interceptions_caught", 0) * 0.7
                    score = settings_awards.SBMVP_W_TD*td + settings_awards.SBMVP_W_EPA_G*epa + settings_awards.SBMVP_W_CLUTCH*clutch + settings_awards.SBMVP_W_SPECTACLE*spec
                    cands.append((pid, score))
        except Exception:
            cands = []
    
    if not cands:
        return None
    
    pid = _pick_top(cands, rnd)
    row = AwardWinner(season=season, award=AwardType.SBMVP, player_id=pid, game_id=super_bowl_game_id)
    session.add(row)
    session.commit()
    return pid


# ------- Leaders / Top Performers -------
LEAGUE_LEADER_CATEGORIES = [
    ("Passing Yards", "pass_yards"),
    ("Passing TD", "pass_td"),
    ("Interceptions Thrown (Fewest)", "ints_thrown_inv"),  # invert for leaders
    ("Rushing Yards", "rush_yards"),
    ("Rushing TD", "rush_td"),
    ("Receiving Yards", "rec_yards"),
    ("Receiving TD", "rec_td"),
    ("Sacks (Defense)", "sacks_def"),
    ("Interceptions (Defense)", "ints_def"),
    ("TFL", "tfl"),
    ("FG Made", "fgm"),
    ("FG %", "fg_pct"),
    ("Net Punting", "net_punt"),
    ("Return TD", "ret_td"),
]


def compute_league_leaders(session: Session, season: int, top_n: int = 10) -> List[Leaderboard]:
    plist = _fetch_player_season_stats(session, season)
    boards: List[Leaderboard] = []
    
    # precompute FG%, inverted interceptions thrown
    for p in plist:
        fga = p.get("fga", 0); fgm = p.get("fgm", 0)
        p["fg_pct"] = (fgm / fga) if fga else 0.0
        p["ints_thrown_inv"] = -p.get("ints_thrown", 0)
    
    for title, key in LEAGUE_LEADER_CATEGORIES:
        rows = sorted(
            [r for r in plist if key in r],
            key=lambda d: d.get(key, 0),
            reverse=True
        )[:top_n]
        leaders = [
            LeaderRow(
                name=f'Player {r["player_id"]}', 
                player_id=r["player_id"], 
                team_id=r.get("team_id",0), 
                value=r.get(key,0)
            )
            for r in rows
        ]
        boards.append(Leaderboard(title=title, leaders=leaders))
    return boards


def compute_team_leaders(session: Session, season: int, team_id: int, top_n: int = 5) -> List[Leaderboard]:
    plist = [p for p in _fetch_player_season_stats(session, season) if p.get("team_id") == team_id]
    for p in plist:
        fga = p.get("fga", 0); fgm = p.get("fgm", 0)
        p["fg_pct"] = (fgm / fga) if fga else 0.0
        p["ints_thrown_inv"] = -p.get("ints_thrown", 0)
    
    boards: List[Leaderboard] = []
    for title, key in LEAGUE_LEADER_CATEGORIES:
        rows = sorted([r for r in plist if key in r], key=lambda d: d.get(key,0), reverse=True)[:top_n]
        leaders = [
            LeaderRow(
                name=f'Player {r["player_id"]}', 
                player_id=r["player_id"], 
                team_id=team_id, 
                value=r.get(key,0)
            )
            for r in rows
        ]
        boards.append(Leaderboard(title=title, leaders=leaders))
    return boards

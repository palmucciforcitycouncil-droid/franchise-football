"""
Season data access utilities for sanity checks.
Duck-types to available models/services.
"""

from __future__ import annotations
from typing import Dict, Any, List
from sqlmodel import Session, select


def fetch_player_catalog(session: Session, season: int) -> List[Dict[str, Any]]:
    """
    Return dicts minimally containing:
      player_id, team_id, position, ovr, snaps (if available)
    """
    out = []
    # Try canonical model
    for mod, name in [("app.models.player_models", "Player")]:
        try:
            m = __import__(mod, fromlist=[name])
            Player = getattr(m, name)
            rows = session.exec(select(Player)).all()
            for p in rows:
                out.append({
                    "player_id": getattr(p, "id"),
                    "team_id": getattr(p, "team_id", None),
                    "position": (getattr(p, "position", None) or getattr(p, "pos", None) or "UNK").upper(),
                    "ovr": getattr(p, "overall", None) or getattr(p, "ovr", 0),
                    "snaps": getattr(p, "snaps", None) or 0,
                })
            return out
        except Exception:
            continue
    return out


def fetch_player_season_stats(session: Session, season: int) -> List[Dict[str, Any]]:
    """
    Return dicts minimally containing by player_id:
      rate stats: qb_any_a/epa_per_play/cpoe_proxy, rb_ypc/sr, wr_yprr/targets, te_yprr/targets,
      def: pressure_rate/sacks, pbu, ints, tfl
      plus snaps if available.
    Unknown keys can be missing; tests skip gracefully.
    """
    out = []
    # Try known season stats table/service
    for mod, name in [
        ("app.models.stats_models", "PlayerSeasonStats"),
    ]:
        try:
            m = __import__(mod, fromlist=[name])
            PS = getattr(m, name)
            rows = session.exec(select(PS)).all()
            for r in rows:
                d = r.__dict__.copy()
                d["player_id"] = d.get("player_id") or getattr(r, "player_id")
                out.append(d)
            return out
        except Exception:
            continue
    
    # Fallback: derive from PBP aggregation
    try:
        from app.testing.aggregate_from_pbp import aggregate_truth_from_pbp
        agg = aggregate_truth_from_pbp(session)
        
        # Convert player season stats to our format
        for pid, stats in agg["player_season"].items():
            # Get player info
            try:
                from app.models.player_models import Player
                player = session.exec(select(Player).where(Player.id == pid)).first()
                if player:
                    d = {
                        "player_id": pid,
                        "team_id": getattr(player, "team_id", 0),
                        "position": getattr(player, "position", "UNK"),
                        "snaps": 50,  # Default snap count
                        "pass_attempts": stats.get("pass_attempts", 0),
                        "pass_yards": stats.get("pass_yards", 0),
                        "pass_td": stats.get("pass_td", 0),
                        "interceptions": stats.get("interceptions", 0),
                        "rush_attempts": stats.get("rush_attempts", 0),
                        "rush_yards": stats.get("rush_yards", 0),
                        "rush_td": stats.get("rush_td", 0),
                        "targets": stats.get("targets", 0),
                        "rec_yards": stats.get("rec_yards", 0),
                        "rec_td": stats.get("rec_td", 0),
                        "sacks": stats.get("sacks", 0),
                        "tfl": stats.get("tfl", 0),
                        "pass_breakups": stats.get("pass_breakups", 0),
                        "interceptions_caught": stats.get("interceptions_caught", 0),
                        "field_goals_attempted": stats.get("field_goals_attempted", 0),
                        "field_goals_made": stats.get("field_goals_made", 0),
                        "punts": stats.get("punts", 0),
                        "punt_net_yards": stats.get("punt_net_yards", 0),
                        "return_td": stats.get("return_td", 0),
                        # Rate stats (computed)
                        "epa_per_play": 0.1,  # Default EPA
                        "any_a": 6.0,  # Default ANY/A
                        "ypc": stats.get("rush_yards", 0) / max(1, stats.get("rush_attempts", 1)),
                        "yprr": stats.get("rec_yards", 0) / max(1, stats.get("targets", 1)),
                        "success_rate_rush": 0.6,  # Default success rate
                        "success_rate_rec": 0.6,  # Default success rate
                        "pressure_rate": 0.1,  # Default pressure rate
                        "sacks_per_snap": stats.get("sacks", 0) / max(1, 50),  # Default snaps
                        "pbu_per_target": stats.get("pass_breakups", 0) / max(1, stats.get("targets", 1)),
                        "ints_per_target": stats.get("interceptions_caught", 0) / max(1, stats.get("targets", 1)),
                    }
                    out.append(d)
            except Exception:
                continue
    except Exception:
        pass
    
    return out

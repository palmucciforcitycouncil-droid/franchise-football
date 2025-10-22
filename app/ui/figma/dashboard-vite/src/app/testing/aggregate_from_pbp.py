"""
PBP Aggregation Utilities - Build ground truth stats directly from PBP events.
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple, DefaultDict
from collections import defaultdict

from sqlmodel import Session, select

try:
    from app.models.pbp_event import PBPEvent
except Exception as e:
    PBPEvent = None


def _safe(v, default=0):
    """Safely get value with default."""
    return v if v is not None else default


def aggregate_truth_from_pbp(session: Session) -> Dict[str, Any]:
    """
    Build 'truth' dicts directly from PBPEvent.
    Returns:
      {
        "team_game": {(team_id, game_id): {...}},
        "team_season": {team_id: {...}},
        "player_game": {(player_id, game_id): {...}},
        "player_season": {player_id: {...}},
        "game_score": {game_id: {"home_points":int,"away_points":int}},
      }
    Stats included (if fields exist): points, rush_yards, pass_yards, rec_yards,
    sacks_def, interceptions_def, punts, fgm, fga, penalties_yards.
    """
    if PBPEvent is None:
        raise RuntimeError("PBPEvent model not found. Please ensure app/models/pbp_event.py exists.")

    team_game: DefaultDict[Tuple[int,int], Dict[str,int]] = defaultdict(lambda: defaultdict(int))
    player_game: DefaultDict[Tuple[int,int], Dict[str,int]] = defaultdict(lambda: defaultdict(int))
    game_score: DefaultDict[int, Dict[str,int]] = defaultdict(lambda: defaultdict(int))

    events = session.exec(select(PBPEvent)).all()
    
    for ev in events:
        gid = getattr(ev, "game_id", None)
        off = getattr(ev, "offense_team_id", None)
        deff = getattr(ev, "defense_team_id", None)
        yards = _safe(getattr(ev, "yards_gained", 0))
        play_type = getattr(ev, "play_type", None)

        # Points (if present)
        pts_off = _safe(getattr(ev, "points_offense", 0))
        pts_def = _safe(getattr(ev, "points_defense", 0))
        
        if gid is not None:
            # Track game scores
            if pts_off > 0:
                game_score[gid]["total_points"] += pts_off
        
        if off is not None:
            team_game[(off, gid)]["plays"] += 1
            team_game[(off, gid)]["yards_total"] += yards
            team_game[(off, gid)]["points"] += pts_off
            
        if deff is not None:
            team_game[(deff, gid)]["points_allowed"] += pts_off

        # Rushing
        rusher_id = getattr(ev, "rusher_id", None)
        if rusher_id and play_type == "run":
            # Only count rushing yards for the offensive team
            player_game[(rusher_id, gid)]["rush_yards"] += yards
            team_game[(off, gid)]["rush_yards"] += yards
            
            if getattr(ev, "is_scoring_play", False) and pts_off > 0:
                player_game[(rusher_id, gid)]["rush_td"] += 1
                team_game[(off, gid)]["rush_td"] += 1

        # Passing/Receiving
        passer_id = getattr(ev, "passer_id", None)
        receiver_id = getattr(ev, "receiver_id", None)
        target_id = getattr(ev, "target_id", None)
        completed = getattr(ev, "completed", False)
        
        if passer_id and play_type == "pass":
            player_game[(passer_id, gid)]["pass_attempts"] += 1
            team_game[(off, gid)]["pass_attempts"] += 1
            
            if completed:
                player_game[(passer_id, gid)]["pass_completions"] += 1
                player_game[(passer_id, gid)]["pass_yards"] += yards
                team_game[(off, gid)]["pass_completions"] += 1
                team_game[(off, gid)]["pass_yards"] += yards
                
                if getattr(ev, "is_scoring_play", False) and pts_off > 0:
                    player_game[(passer_id, gid)]["pass_td"] += 1
                    team_game[(off, gid)]["pass_td"] += 1
            
            # Interceptions
            if getattr(ev, "interception", False):
                player_game[(passer_id, gid)]["interceptions"] += 1
                team_game[(off, gid)]["interceptions"] += 1
            
            # Sacks
            if getattr(ev, "sack", False):
                sack_yards = _safe(getattr(ev, "sack_yards", 0))
                player_game[(passer_id, gid)]["sacks_taken"] += 1.0
                player_game[(passer_id, gid)]["sack_yards"] += sack_yards
                team_game[(off, gid)]["sacks_taken"] += 1.0
        
        if target_id and play_type == "pass":
            player_game[(target_id, gid)]["targets"] += 1
            team_game[(off, gid)]["targets"] += 1
            
            if completed:
                player_game[(target_id, gid)]["receptions"] += 1
                player_game[(target_id, gid)]["rec_yards"] += yards
                team_game[(off, gid)]["receptions"] += 1
                team_game[(off, gid)]["rec_yards"] += yards
                
                if getattr(ev, "is_scoring_play", False) and pts_off > 0:
                    player_game[(target_id, gid)]["rec_td"] += 1
                    team_game[(off, gid)]["rec_td"] += 1

        # Defense: sacks & interceptions (support split sacks if present)
        sack_split = getattr(ev, "sack_split", None)
        if sack_split:
            try:
                import json
                sack_data = json.loads(sack_split) if isinstance(sack_split, str) else sack_split
                total_share = 0.0
                for pid, share in sack_data:
                    player_game[(pid, gid)]["sacks"] += share
                    total_share += share
                team_game[(deff, gid)]["sacks_def"] += int(round(total_share))
            except (json.JSONDecodeError, TypeError):
                pass
        
        intercepted_by_id = getattr(ev, "intercepted_by_id", None)
        if intercepted_by_id:
            player_game[(intercepted_by_id, gid)]["interceptions_caught"] += 1
            team_game[(deff, gid)]["interceptions_def"] += 1

        # Special teams
        if play_type == "punt":
            punter_id = getattr(ev, "punter_id", None)
            if punter_id:
                player_game[(punter_id, gid)]["punts"] += 1
                player_game[(punter_id, gid)]["punt_yards"] += _safe(getattr(ev, "kick_distance", 0))
                player_game[(punter_id, gid)]["punt_net_yards"] += _safe(getattr(ev, "net_yards", 0))
                player_game[(punter_id, gid)]["punts_in_20"] += 1 if getattr(ev, "in_20", False) else 0
            
            team_game[(off, gid)]["punts"] += 1
            team_game[(off, gid)]["punt_yards"] += _safe(getattr(ev, "kick_distance", 0))
            team_game[(off, gid)]["punt_net_yards"] += _safe(getattr(ev, "net_yards", 0))
            team_game[(off, gid)]["punts_in_20"] += 1 if getattr(ev, "in_20", False) else 0
        
        if play_type == "fg":
            kicker_id = getattr(ev, "kicker_id", None)
            if kicker_id:
                player_game[(kicker_id, gid)]["field_goals_attempted"] += 1
                if getattr(ev, "is_scoring_play", False):
                    player_game[(kicker_id, gid)]["field_goals_made"] += 1
            
            team_game[(off, gid)]["field_goals_attempted"] += 1
            if getattr(ev, "is_scoring_play", False):
                team_game[(off, gid)]["field_goals_made"] += 1

        # Penalties (team totals only)
        penalty = getattr(ev, "penalty", None)
        if penalty and isinstance(penalty, dict):
            pen_yds = penalty.get("yards", 0)
            if pen_yds and off is not None:
                team_game[(off, gid)]["penalty_yards"] += pen_yds

        # Situational splits
        if getattr(ev, "is_third_down", False):
            if off is not None:
                team_game[(off, gid)]["third_down_attempts"] += 1
                if yards >= getattr(ev, "distance", 0):
                    team_game[(off, gid)]["third_down_conversions"] += 1
        
        if getattr(ev, "is_fourth_down", False):
            if off is not None:
                team_game[(off, gid)]["fourth_down_attempts"] += 1
                if yards >= getattr(ev, "distance", 0):
                    team_game[(off, gid)]["fourth_down_conversions"] += 1
        
        if getattr(ev, "is_red_zone", False):
            if off is not None:
                team_game[(off, gid)]["red_zone_attempts"] += 1
                if getattr(ev, "is_scoring_play", False) and pts_off > 0:
                    team_game[(off, gid)]["red_zone_touchdowns"] += 1

    # Roll up to season
    team_season: DefaultDict[int, Dict[str,int]] = defaultdict(lambda: defaultdict(int))
    for (tid, gid), row in team_game.items():
        for k, v in row.items():
            team_season[tid][k] += v

    player_season: DefaultDict[int, Dict[str,float]] = defaultdict(lambda: defaultdict(float))
    for (pid, gid), row in player_game.items():
        for k, v in row.items():
            player_season[pid][k] += v

    return {
        "team_game": dict(team_game),
        "team_season": dict(team_season),
        "player_game": dict(player_game),
        "player_season": dict(player_season),
        "game_score": dict(game_score),
    }

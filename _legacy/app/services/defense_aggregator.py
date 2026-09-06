from __future__ import annotations
from typing import Optional, Dict, Any, Iterable, Tuple
import json
from sqlalchemy.orm import Session
from app.models.sim_models import GameEvent, Game  # adjust import path if needed
from app.models.defense_stats import TeamDefenseStatsWeekly, PlayerDefenseStatsWeekly

def _ensure_zero_row_team(d:dict, key:tuple[int,int,int]):
    if key not in d:
        d[key] = {
            "tackles_solo":0,"tackles_ast":0,"tfl":0,
            "sacks":0,"qb_hits":0,"pressures":0,"blitzes":0,
            "interceptions":0,"int_yards":0,"int_td":0,
            "pbus":0,"targets":0,"completions_allowed":0,"yards_allowed":0,"yac_allowed":0,"td_allowed":0,
            "forced_fumbles":0,"fumble_recoveries":0,"fr_yards":0,"fr_td":0,
            "penalties":0,"penalty_yards":0,
        }

def _ensure_zero_row_player(d:dict, key:tuple[int,int,int]):
    if key not in d:
        d[key] = {
            "role":"DB",
            "tackles_solo":0,"tackles_ast":0,"tfl":0,
            "sacks":0,"qb_hits":0,"pressures":0,"blitzes":0,
            "interceptions":0,"int_yards":0,"int_td":0,
            "pbus":0,"targets":0,"completions_allowed":0,"yards_allowed":0,"yac_allowed":0,"td_allowed":0,
            "forced_fumbles":0,"fumble_recoveries":0,"fr_yards":0,"fr_td":0,
            "penalties":0,"penalty_yards":0,
        }

def _bump_team(team_buckets, season:int, week:int, team_id:int, field:str, delta:int=1):
    key=(season,week,team_id)
    _ensure_zero_row_team(team_buckets, key)
    team_buckets[key][field]+=delta

def _bump_player(player_buckets, season:int, week:int, team_id:int, player_id:int|None, field:str, delta:int=1):
    if player_id is None: return
    key=(season,week,player_id)
    _ensure_zero_row_player(player_buckets, key)
    player_buckets[key][field]+=delta
    # stash team_id onto each row so we can persist later
    player_buckets[key]["team_id"]=team_id

def aggregate_defense_for(s:Session, season:int, week:Optional[int]=None) -> tuple[list[TeamDefenseStatsWeekly], list[PlayerDefenseStatsWeekly]]:
    q = s.query(GameEvent).join(Game, Game.id==GameEvent.game_id).filter(Game.season==season)
    if week is not None:
        q = q.filter(Game.week==week)

    team_buckets: Dict[tuple[int,int,int], Dict[str,int]] = {}
    player_buckets: Dict[tuple[int,int,int], Dict[str,int|str]] = {}

    for ge in q.all():
        if ge.event_type not in ("play","punt","turnover","td","fg","safety","final"):
            continue
        try:
            payload = json.loads(ge.description) if ge.description else {}
        except Exception:
            payload = {}

        # Get game info separately since GameEvent doesn't have a relationship
        game = s.query(Game).filter(Game.id == ge.game_id).first()
        if not game:
            continue

        # Determine offense/defense by ge.score context is tricky;
        # we rely on payload["team"] = offense side for actions.
        team = payload.get("team")
        if team not in ("home","away"):
            team = None

        # who is defense team_id? We need Game to map home/away to IDs.
        home_id = game.home_team_id
        away_id = game.away_team_id
        offense_tid = home_id if team=="home" else (away_id if team=="away" else None)
        defense_tid = away_id if team=="home" else (home_id if team=="away" else None)

        # parse common participant fields
        target_id = payload.get("target_id")
        primary_def_id = payload.get("primary_defender_id")
        tackler_id = payload.get("tackler_id")
        assist_tackler_id = payload.get("assist_tackler_id")
        pressure_by = payload.get("pressure_by")
        blitz_by = payload.get("blitz_by")
        is_pd = payload.get("is_pd", False)
        is_missed = payload.get("is_missed_tackle", False)

        # coverage fields (counts apply to defense)
        targets = int(payload.get("targets", 0))
        comp_allowed = int(payload.get("completions_allowed", 0))
        yards_allowed = int(payload.get("yards_allowed", 0))
        yac_allowed = int(payload.get("yac_allowed", 0))
        td_allowed = int(payload.get("td_allowed", 0))

        # penalties against defense
        pen = payload.get("penalty") or {}
        pen_yards = int(pen.get("yards", 0))
        pen_on = pen.get("on_player_id")

        # TEAM aggregations
        if defense_tid:
            if ge.event_type == "play":
                # tackles
                if tackler_id is not None:
                    _bump_team(team_buckets, season, game.week, defense_tid, "tackles_solo", 1)
                if assist_tackler_id is not None:
                    _bump_team(team_buckets, season, game.week, defense_tid, "tackles_ast", 1)

                # sacks/pressures
                if payload.get("is_sack"):
                    _bump_team(team_buckets, season, game.week, defense_tid, "sacks", 1)
                    _bump_team(team_buckets, season, game.week, defense_tid, "qb_hits", 1)
                if pressure_by is not None:
                    _bump_team(team_buckets, season, game.week, defense_tid, "pressures", 1)
                if blitz_by is not None:
                    _bump_team(team_buckets, season, game.week, defense_tid, "blitzes", 1)

                # coverage
                if targets: _bump_team(team_buckets, season, game.week, defense_tid, "targets", targets)
                if comp_allowed: _bump_team(team_buckets, season, game.week, defense_tid, "completions_allowed", comp_allowed)
                if yards_allowed: _bump_team(team_buckets, season, game.week, defense_tid, "yards_allowed", yards_allowed)
                if yac_allowed: _bump_team(team_buckets, season, game.week, defense_tid, "yac_allowed", yac_allowed)
                if td_allowed: _bump_team(team_buckets, season, game.week, defense_tid, "td_allowed", td_allowed)
                if is_pd: _bump_team(team_buckets, season, game.week, defense_tid, "pbus", 1)

                # penalties
                if pen_yards:
                    _bump_team(team_buckets, season, game.week, defense_tid, "penalties", 1)
                    _bump_team(team_buckets, season, game.week, defense_tid, "penalty_yards", pen_yards)

            elif ge.event_type == "turnover":
                to_type = (payload.get("type") or "").lower()
                if to_type == "interception":
                    _bump_team(team_buckets, season, game.week, defense_tid, "interceptions", 1)
                    _bump_team(team_buckets, season, game.week, defense_tid, "int_yards", int(payload.get("return_yards", 0)))
                    if payload.get("return_td"): _bump_team(team_buckets, season, game.week, defense_tid, "int_td", 1)
                elif to_type == "fumble":
                    _bump_team(team_buckets, season, game.week, defense_tid, "forced_fumbles", 1)
                    if payload.get("recovered_by_defense"):
                        _bump_team(team_buckets, season, game.week, defense_tid, "fumble_recoveries", 1)
                        _bump_team(team_buckets, season, game.week, defense_tid, "fr_yards", int(payload.get("return_yards", 0)))
                        if payload.get("return_td"): _bump_team(team_buckets, season, game.week, defense_tid, "fr_td", 1)

        # PLAYER aggregations (only when IDs exist and defense_tid known)
        if defense_tid:
            if tackler_id is not None:
                _bump_player(player_buckets, season, game.week, defense_tid, tackler_id, "tackles_solo", 1)
            if assist_tackler_id is not None:
                _bump_player(player_buckets, season, game.week, defense_tid, assist_tackler_id, "tackles_ast", 1)
            if payload.get("is_sack") and pressure_by is not None:
                _bump_player(player_buckets, season, game.week, defense_tid, pressure_by, "sacks", 1)
                _bump_player(player_buckets, season, game.week, defense_tid, pressure_by, "qb_hits", 1)
            if pressure_by is not None:
                _bump_player(player_buckets, season, game.week, defense_tid, pressure_by, "pressures", 1)
            if blitz_by is not None:
                _bump_player(player_buckets, season, game.week, defense_tid, blitz_by, "blitzes", 1)

            if targets and (primary_def_id is not None):
                _bump_player(player_buckets, season, game.week, defense_tid, primary_def_id, "targets", targets)
            if comp_allowed and (primary_def_id is not None):
                _bump_player(player_buckets, season, game.week, defense_tid, primary_def_id, "completions_allowed", comp_allowed)
            if yards_allowed and (primary_def_id is not None):
                _bump_player(player_buckets, season, game.week, defense_tid, primary_def_id, "yards_allowed", yards_allowed)
            if yac_allowed and (primary_def_id is not None):
                _bump_player(player_buckets, season, game.week, defense_tid, primary_def_id, "yac_allowed", yac_allowed)
            if td_allowed and (primary_def_id is not None):
                _bump_player(player_buckets, season, game.week, defense_tid, primary_def_id, "td_allowed", td_allowed)
            if is_pd and (primary_def_id is not None):
                _bump_player(player_buckets, season, game.week, defense_tid, primary_def_id, "pbus", 1)

            if pen_yards and (pen_on is not None):
                _bump_player(player_buckets, season, game.week, defense_tid, pen_on, "penalties", 1)
                _bump_player(player_buckets, season, game.week, defense_tid, pen_on, "penalty_yards", pen_yards)

            if ge.event_type == "turnover":
                to_type = (payload.get("type") or "").lower()
                if to_type == "interception":
                    pick_by = payload.get("intercepted_by")
                    if pick_by is not None:
                        _bump_player(player_buckets, season, game.week, defense_tid, pick_by, "interceptions", 1)
                        _bump_player(player_buckets, season, game.week, defense_tid, pick_by, "int_yards", int(payload.get("return_yards", 0)))
                        if payload.get("return_td"):
                            _bump_player(player_buckets, season, game.week, defense_tid, pick_by, "int_td", 1)
                elif to_type == "fumble":
                    ff_by = payload.get("forced_by")
                    fr_by = payload.get("recovered_by")
                    if ff_by is not None:
                        _bump_player(player_buckets, season, game.week, defense_tid, ff_by, "forced_fumbles", 1)
                    if fr_by is not None:
                        _bump_player(player_buckets, season, game.week, defense_tid, fr_by, "fumble_recoveries", 1)
                        _bump_player(player_buckets, season, game.week, defense_tid, fr_by, "fr_yards", int(payload.get("return_yards", 0)))
                        if payload.get("return_td"):
                            _bump_player(player_buckets, season, game.week, defense_tid, fr_by, "fr_td", 1)

    # Materialize to ORM lists
    team_models: list[TeamDefenseStatsWeekly] = []
    for (season_, week_, team_id), vals in team_buckets.items():
        team_models.append(TeamDefenseStatsWeekly(season=season_, week=week_, team_id=team_id, **vals))

    player_models: list[PlayerDefenseStatsWeekly] = []
    for (season_, week_, player_id), vals in player_buckets.items():
        team_id = vals.pop("team_id")
        player_models.append(PlayerDefenseStatsWeekly(season=season_, week=week_, team_id=team_id, player_id=player_id, **vals))

    return team_models, player_models

from __future__ import annotations
from typing import Any, Dict, List, Optional
from sqlmodel import Session, select

def _try(path: str, name: str):
    """Defensive import helper - returns None if model doesn't exist."""
    try:
        mod = __import__(path, fromlist=[name])
        return getattr(mod, name)
    except Exception:
        return None

# Common models (best-effort)
Team = _try("app.models.team", "Team")

# Player domain
Player = _try("app.models.player", "Player")
PlayerContract = _try("app.models.contracts", "PlayerContract")
PlayerContractAsk = _try("app.models.contracts", "PlayerContractAsk")
TeamTradeBlock = _try("app.models.contracts", "TeamTradeBlock")
PlayerOffer = _try("app.models.player_market", "PlayerOffer")
Injury = _try("app.models.injury", "Injury")
InjuryStatus = _try("app.models.injury", "InjuryStatus")

PlayerSeasonStats = _try("app.models.stats", "PlayerSeasonStats")
PlayerCareerAgg = _try("app.models.stats", "PlayerCareerAgg")

# Coach domain
Coach = _try("app.models.coach", "Coach")
CoachRole = _try("app.models.coach", "CoachRole")
CoachContract = _try("app.models.coach", "CoachContract")
CoachAsk = _try("app.models.coach", "CoachAsk")
CoachOffer = _try("app.models.coach", "CoachOffer")
CoachFocusAssignment = _try("app.models.coach_focus", "CoachFocusAssignment")
TeamSeasonFocusTally = _try("app.models.coach_focus", "TeamSeasonFocusTally")

CoachSeasonStats = _try("app.models.stats", "CoachSeasonStats")
CoachCareerAgg = _try("app.models.stats", "CoachCareerAgg")
AwardsWeekly = _try("app.models.awards", "AwardsWeekly")
AwardsAnnual = _try("app.models.awards", "AwardsAnnual")

# ---------- Helpers ----------
def _team_name(sess: Session, team_id: Optional[int]) -> str:
    """Get team name safely."""
    if not Team or not team_id:
        return ""
    t = sess.get(Team, team_id)
    return getattr(t, "name", "") if t else ""

def _active_contract(sess: Session, model, player_or_coach_id: int):
    """Get active contract for player or coach."""
    if not model:
        return None
    
    # Determine the ID field based on model type
    if hasattr(model, "player_id"):
        row = sess.exec(select(model).where(
            model.is_active == True,  # noqa: E712
            model.player_id == player_or_coach_id
        )).first()
    elif hasattr(model, "coach_id"):
        row = sess.exec(select(model).where(
            model.is_active == True,  # noqa: E712
            model.coach_id == player_or_coach_id
        )).first()
    else:
        return None
    
    return row

def _contract_ask(sess: Session, model, obj_id: int):
    """Get contract ask for player or coach."""
    if not model:
        return None
    
    # Determine the ID field based on model type
    if hasattr(model, "player_id"):
        key = "player_id"
    elif hasattr(model, "coach_id"):
        key = "coach_id"
    else:
        return None
    
    return sess.exec(select(model).where(getattr(model, key) == obj_id)).first()

def _trade_block(sess: Session, season: int, team_id: int, player_id: int) -> bool:
    """Check if player is on trade block."""
    if not TeamTradeBlock or not team_id:
        return False
    
    row = sess.exec(select(TeamTradeBlock).where(
        TeamTradeBlock.season == season,
        TeamTradeBlock.team_id == team_id,
        TeamTradeBlock.player_id == player_id
    )).first()
    
    return bool(row)

def _player_offers(sess: Session, season: int, player_id: int) -> List[Dict[str, Any]]:
    """Get competing offers for a player."""
    if not PlayerOffer:
        return []
    
    rows = list(sess.exec(select(PlayerOffer).where(
        PlayerOffer.season == season,
        PlayerOffer.to_player_id == player_id
    )))
    
    out = []
    for r in rows:
        out.append({
            "offer_id": getattr(r, "offer_id", 0),
            "from_team_id": getattr(r, "from_team_id", 0),
            "from_team_name": _team_name(sess, getattr(r, "from_team_id", None)),
            "years": getattr(r, "years", 0),
            "aav": getattr(r, "aav", 0),
            "status": getattr(r, "status", None).value if getattr(r, "status", None) else ""
        })
    
    return out

def _injury_bundle(sess: Session, player_id: int) -> Dict[str, Any]:
    """Get injury information for a player."""
    if not Injury:
        return {"active": False, "rtp_penalty_overall": 0.0}
    
    row = sess.exec(select(Injury).where(
        Injury.player_id == player_id,
        Injury.resolved == False  # noqa: E712
    )).first()
    
    if not row:
        # Optional RTP: we can expose a small penalty if recently resolved; reuse service if present
        try:
            from app.services.injury_service import active_penalty_for_player
            penalty = active_penalty_for_player(sess, player_id)
        except Exception:
            penalty = 0.0
        
        return {"active": False, "rtp_penalty_overall": penalty}
    
    return {
        "active": True,
        "injury_type": getattr(row, "injury_type", None).value if getattr(row, "injury_type", None) else "",
        "severity": getattr(row, "severity", 0),
        "weeks_out_remaining": getattr(row, "weeks_out_remaining", 0),
        "status": getattr(row, "status", None).value if getattr(row, "status", None) else ""
    }

def _player_stats(sess: Session, player_id: int, season: int) -> Dict[str, Any]:
    """Get player statistics."""
    out: Dict[str, Any] = {"season": {}, "career": {}}
    
    if PlayerSeasonStats:
        s = sess.exec(select(PlayerSeasonStats).where(
            PlayerSeasonStats.player_id == player_id,
            PlayerSeasonStats.season == season
        )).first()
        if s:
            # Get all fields except id
            out["season"] = {k: getattr(s, k) for k in dir(s) if not k.startswith('_') and k != 'id'}
    
    if PlayerCareerAgg:
        c = sess.exec(select(PlayerCareerAgg).where(
            PlayerCareerAgg.player_id == player_id
        )).first()
        if c:
            # Get all fields except id
            out["career"] = {k: getattr(c, k) for k in dir(c) if not k.startswith('_') and k != 'id'}
    
    return out

def _coach_stats(sess: Session, coach_id: int, season: int) -> Dict[str, Any]:
    """Get coach statistics."""
    out: Dict[str, Any] = {"season": {}, "career": {}}
    
    if CoachSeasonStats:
        s = sess.exec(select(CoachSeasonStats).where(
            CoachSeasonStats.coach_id == coach_id,
            CoachSeasonStats.season == season
        )).first()
        if s:
            # Get all fields except id
            out["season"] = {k: getattr(s, k) for k in dir(s) if not k.startswith('_') and k != 'id'}
    
    if CoachCareerAgg:
        c = sess.exec(select(CoachCareerAgg).where(
            CoachCareerAgg.coach_id == coach_id
        )).first()
        if c:
            # Get all fields except id
            out["career"] = {k: getattr(c, k) for k in dir(c) if not k.startswith('_') and k != 'id'}
    
    return out

def _coach_focus(sess: Session, coach_id: int, season: int) -> Dict[str, Any]:
    """Get coach focus information."""
    if not CoachFocusAssignment:
        return {}
    
    row = sess.exec(select(CoachFocusAssignment).where(
        CoachFocusAssignment.coach_id == coach_id,
        CoachFocusAssignment.season == season
    )).first()
    
    if not row:
        return {}
    
    return {
        "focus": getattr(row, "focus", ""),
        "weeks_assigned": getattr(row, "weeks_assigned", 0)
    }

def _player_accolades(sess: Session, player_id: int) -> Dict[str, Any]:
    """Get player accolades/awards."""
    accolades = {
        "mvp_count": 0,
        "opoy_count": 0,
        "droy_count": 0,
        "pro_bowl_count": 0,
        "all_pro_count": 0,
        "total_awards": 0
    }
    
    if AwardsAnnual:
        # Count various awards
        mvp_awards = sess.exec(select(AwardsAnnual).where(
            AwardsAnnual.player_id == player_id,
            AwardsAnnual.award_type == "MVP"
        )).all()
        accolades["mvp_count"] = len(mvp_awards)
        
        opoy_awards = sess.exec(select(AwardsAnnual).where(
            AwardsAnnual.player_id == player_id,
            AwardsAnnual.award_type == "OPOY"
        )).all()
        accolades["opoy_count"] = len(opoy_awards)
        
        droy_awards = sess.exec(select(AwardsAnnual).where(
            AwardsAnnual.player_id == player_id,
            AwardsAnnual.award_type == "DROY"
        )).all()
        accolades["droy_count"] = len(droy_awards)
        
        # Count total awards
        all_awards = sess.exec(select(AwardsAnnual).where(
            AwardsAnnual.player_id == player_id
        )).all()
        accolades["total_awards"] = len(all_awards)
    
    return accolades

def _coach_accolades(sess: Session, coach_id: int) -> Dict[str, Any]:
    """Get coach accolades/awards."""
    accolades = {
        "coy_count": 0,
        "total_awards": 0
    }
    
    if AwardsAnnual:
        # Count Coach of the Year awards
        coy_awards = sess.exec(select(AwardsAnnual).where(
            AwardsAnnual.coach_id == coach_id,
            AwardsAnnual.award_type == "COY"
        )).all()
        accolades["coy_count"] = len(coy_awards)
        
        # Count total awards
        all_awards = sess.exec(select(AwardsAnnual).where(
            AwardsAnnual.coach_id == coach_id
        )).all()
        accolades["total_awards"] = len(all_awards)
    
    return accolades

# ---------- Public assemblers ----------
def build_player_card(sess: Session, player_id: int, season: int) -> Dict[str, Any]:
    """Build complete player card with all information."""
    if not Player:
        return {"error": "Player model missing"}
    
    p = sess.get(Player, player_id)
    if not p:
        return {"error": "Player not found"}

    team_id = getattr(p, "team_id", None)
    contract = _active_contract(sess, PlayerContract, player_id)
    ask = _contract_ask(sess, PlayerContractAsk, player_id)
    injury = _injury_bundle(sess, player_id)
    stats = _player_stats(sess, player_id, season)
    offers = _player_offers(sess, season, player_id)
    accolades = _player_accolades(sess, player_id)

    is_fa = (team_id is None)
    on_trade_block = _trade_block(sess, season, team_id, player_id) if (team_id is not None) else False

    # Actions visibility
    actions = {
        "trade_for": not is_fa,            # trade only if under contract
        "negotiate": True,                  # FA sign OR re-sign; UI picks endpoint based on is_fa
        "release": not is_fa               # only if on your roster (UI will check team)
    }

    card = {
        "bio": {
            "player_id": player_id,
            "name": getattr(p, "name", ""),
            "pos": getattr(p, "pos", ""),
            "age": getattr(p, "age", 0),
            "overall": getattr(p, "overall", 0),
            "team_id": team_id,
            "team_name": _team_name(sess, team_id)
        },
        "contract": {
            "active": ({
                "start_season": getattr(contract, "start_season", 0),
                "end_season": getattr(contract, "end_season", 0),
                "aav": getattr(contract, "aav", 0),
                "guaranteed": getattr(contract, "guaranteed", 0)
            } if contract else None),
            "ask": ({
                "desired_years": getattr(ask, "desired_years", 0),
                "desired_aav": getattr(ask, "desired_aav", 0),
                "desired_total": (getattr(ask, "desired_years", 0) * getattr(ask, "desired_aav", 0))
            } if ask else None),
            "is_free_agent": is_fa,
            "on_trade_block": on_trade_block
        },
        "status": {**injury},
        "stats": stats,
        "market": {
            "offers": offers
        },
        "accolades": accolades,
        "actions": actions
    }
    
    return card

def build_coach_card(sess: Session, coach_id: int, season: int) -> Dict[str, Any]:
    """Build complete coach card with all information."""
    if not Coach:
        return {"error": "Coach model missing"}
    
    c = sess.get(Coach, coach_id)
    if not c:
        return {"error": "Coach not found"}

    team_id = getattr(c, "team_id", None)
    contract = _active_contract(sess, CoachContract, coach_id)
    ask = _contract_ask(sess, CoachAsk, coach_id)
    stats = _coach_stats(sess, coach_id, season)
    focus = _coach_focus(sess, coach_id, season)
    accolades = _coach_accolades(sess, coach_id)

    role = getattr(c, "role", None).value if getattr(c, "role", None) else "HC"

    # Actions (UI decides which to show based on role/team context)
    actions = {
        "promote": role in ("AC1", "AC2", "OC", "DC"),  # eligible for promotion
        "fire": team_id is not None,
        "resign": True  # extend contract
    }

    card = {
        "bio": {
            "coach_id": coach_id,
            "name": getattr(c, "name", ""),
            "role": role,
            "overall": getattr(c, "overall", 0),
            "team_id": team_id,
            "team_name": _team_name(sess, team_id)
        },
        "contract": {
            "active": ({
                "start_season": getattr(contract, "start_season", 0),
                "end_season": getattr(contract, "end_season", 0),
                "aav": getattr(contract, "aav", 0)
            } if contract else None),
            "ask": ({
                "desired_years": getattr(ask, "desired_years", 0),
                "desired_aav": getattr(ask, "desired_aav", 0),
                "desired_total": (getattr(ask, "desired_years", 0) * getattr(ask, "desired_aav", 0))
            } if ask else None)
        },
        "status": {**focus},
        "stats": stats,
        "accolades": accolades,
        "actions": actions
    }
    
    return card

def build_team_card(sess: Session, team_id: int, season: int) -> Dict[str, Any]:
    """Build team card with roster summary and key information."""
    if not Team:
        return {"error": "Team model missing"}
    
    team = sess.get(Team, team_id)
    if not team:
        return {"error": "Team not found"}
    
    # Get roster counts
    roster_counts = {}
    if Player:
        players = list(sess.exec(select(Player).where(Player.team_id == team_id)))
        roster_counts["total_players"] = len(players)
        
        # Count by position
        position_counts = {}
        for player in players:
            pos = getattr(player, "pos", "Unknown")
            position_counts[pos] = position_counts.get(pos, 0) + 1
        roster_counts["by_position"] = position_counts
    
    # Get coaching staff
    coaching_staff = []
    if Coach:
        coaches = list(sess.exec(select(Coach).where(Coach.team_id == team_id)))
        for coach in coaches:
            coaching_staff.append({
                "coach_id": getattr(coach, "coach_id", 0),
                "name": getattr(coach, "name", ""),
                "role": getattr(coach, "role", None).value if getattr(coach, "role", None) else "Unknown",
                "overall": getattr(coach, "overall", 0)
            })
    
    card = {
        "bio": {
            "team_id": team_id,
            "name": getattr(team, "name", ""),
            "conference": getattr(team, "conference", ""),
            "division": getattr(team, "division", "")
        },
        "roster": roster_counts,
        "coaching_staff": coaching_staff,
        "season": season
    }
    
    return card

def get_card_summary(sess: Session, season: int) -> Dict[str, Any]:
    """Get summary of all cards in the system."""
    summary = {
        "season": season,
        "players": 0,
        "coaches": 0,
        "teams": 0,
        "free_agents": 0
    }
    
    if Player:
        all_players = list(sess.exec(select(Player)))
        summary["players"] = len(all_players)
        summary["free_agents"] = len([p for p in all_players if getattr(p, "team_id", None) is None])
    
    if Coach:
        all_coaches = list(sess.exec(select(Coach)))
        summary["coaches"] = len(all_coaches)
    
    if Team:
        all_teams = list(sess.exec(select(Team)))
        summary["teams"] = len(all_teams)
    
    return summary

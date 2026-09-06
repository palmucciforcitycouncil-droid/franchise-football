from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
from random import Random
from sqlmodel import Session, select
from app.models.injury import Injury, InjuryType, InjuryStatus

# ---- Base incidence by position (per 60 minutes per player) ----
BASE_INJURY_PER_GAME: Dict[str, float] = {
    # offense
    "QB": 0.015, "RB": 0.045, "WR": 0.035, "TE": 0.030, "OL": 0.028,
    # defense
    "DL": 0.030, "EDGE": 0.040, "LB": 0.038, "CB": 0.036, "S": 0.032,
    # special teams fallback
    "K": 0.006, "P": 0.006, "LS": 0.004,
}

# Injury type distribution & typical severity bands (weeks)
TYPE_PROFILE: Dict[InjuryType, Tuple[float, Tuple[int, int]]] = {
    InjuryType.HAMSTRING: (0.16, (1, 4)),
    InjuryType.ANKLE_SPR: (0.17, (1, 3)),
    InjuryType.MCL_SPR:   (0.12, (2, 5)),
    InjuryType.SHOULDER:  (0.12, (1, 4)),
    InjuryType.CONCUSSION:(0.10, (0, 2)),
    InjuryType.GROIN:     (0.08, (1, 3)),
    InjuryType.BACK:      (0.08, (1, 4)),
    InjuryType.FOOT:      (0.07, (2, 5)),
    InjuryType.HAND:      (0.05, (0, 2)),
    InjuryType.ACL_TEAR:  (0.05, (8, 20)), # season-ender often
}

# RTP penalty multipliers by type (fraction of overall penalty baseline)
RTP_MULTIPLIER: Dict[InjuryType, Tuple[float, float]] = {
    InjuryType.HAMSTRING: (0.08, 0.10),
    InjuryType.ANKLE_SPR: (0.06, 0.08),
    InjuryType.MCL_SPR:   (0.08, 0.10),
    InjuryType.SHOULDER:  (0.06, 0.08),
    InjuryType.CONCUSSION:(0.03, 0.05),
    InjuryType.GROIN:     (0.08, 0.10),
    InjuryType.BACK:      (0.05, 0.07),
    InjuryType.FOOT:      (0.07, 0.10),
    InjuryType.HAND:      (0.02, 0.03),
    InjuryType.ACL_TEAR:  (0.15, 0.20),
}

@dataclass
class InjuryOddsCtx:
    """Context for injury odds calculation."""
    base_per_game: float
    focus_injury_mult: float
    gameplan_aggr_bump: float
    fatigue_bump: float

def _pos_base_rate(pos: str) -> float:
    """Get base injury rate for a position."""
    return BASE_INJURY_PER_GAME.get(pos, 0.03)

def _draw_type_and_duration(rnd: Random) -> Tuple[InjuryType, int, int]:
    """Draw injury type, duration, and severity."""
    # pick type
    r = rnd.random()
    cum = 0.0
    chosen: Optional[InjuryType] = None
    for t, (p, rng) in TYPE_PROFILE.items():
        cum += p
        if r <= cum:
            chosen = t
            lo, hi = rng
            break
    
    if chosen is None:
        chosen = InjuryType.ANKLE_SPR
        lo, hi = (1, 3)
    
    weeks = rnd.randint(lo, hi)
    severity = min(10, max(1, int((weeks / max(1, hi)) * 10)))
    return chosen, weeks, severity

def _rtp_penalties_for(t: InjuryType) -> Tuple[float, float]:
    """Get RTP penalty multipliers for injury type."""
    return RTP_MULTIPLIER.get(t, (0.05, 0.08))

# ---- Public API ----

def compute_player_injury_odds(sess: Session, season: int, week: int, game_id: int, team_id: int, opponent_id: int, pos: str, base_minutes: float = 60.0) -> InjuryOddsCtx:
    """
    Return per-game odds context factoring focus, aggression, and fatigue.
    """
    try:
        # Focus (team/week)
        from app.services.coach_focus_service import aggregate_weekly_effects
        focus = aggregate_weekly_effects(sess, team_id, season, week)
        focus_injury_mult = getattr(focus, 'injury_prob_multiplier', 1.0)
        stamina_drain_mult = getattr(focus, 'stamina_drain_multiplier', 1.0)
    except ImportError:
        # Fallback if coach focus doesn't exist
        focus_injury_mult = 1.0
        stamina_drain_mult = 1.0

    try:
        # Gameplan/HC (composed engine config)
        from app.engine.gameplan_compose import compose_final_engine_config
        cfg = compose_final_engine_config(sess, game_id, season, week, team_id, opponent_id)
        
        # Aggression proxy: deeper shots, blitz rate and pace
        aggr = abs(cfg.depth_bias) * 0.04 + cfg.blitz_rate * 0.05 + max(0.0, cfg.pass_bias) * 0.02
        
        # Fatigue proxy: higher pace + stamina drain multiplier; clamp small
        pace = getattr(cfg, 'pace', 0.0)
        fatigue = max(0.0, pace * 0.02) + (stamina_drain_mult - 1.0) * (-0.5)
    except ImportError:
        # Fallback if gameplan compose doesn't exist
        aggr = 0.0
        fatigue = 0.0

    base = _pos_base_rate(pos)
    return InjuryOddsCtx(
        base_per_game=base,
        focus_injury_mult=focus_injury_mult,
        gameplan_aggr_bump=aggr,
        fatigue_bump=fatigue
    )

def maybe_injure_player(sess: Session, rnd: Random, season: int, week: int, game_id: int, team_id: int, opponent_id: int, player_id: int, pos: str) -> Optional[Injury]:
    """
    Roll an injury for a single player once per game (you can call more often per snap if desired).
    Returns Injury row if created.
    """
    ctx = compute_player_injury_odds(sess, season, week, game_id, team_id, opponent_id, pos)
    
    # Effective per-game prob
    p = ctx.base_per_game * ctx.focus_injury_mult
    p += ctx.gameplan_aggr_bump + ctx.fatigue_bump
    p = max(0.002, min(0.20, p))  # safety clamp

    if rnd.random() < p:
        itype, weeks, severity = _draw_type_and_duration(rnd)
        rtp_ov, rtp_pos = _rtp_penalties_for(itype)
        
        inj = Injury(
            season=season, week=week, player_id=player_id, team_id=team_id,
            injury_type=itype, severity=severity, weeks_out_total=weeks,
            weeks_out_remaining=weeks, rtp_penalty_overall=rtp_ov, rtp_penalty_pos=rtp_pos,
            status=InjuryStatus.OUT, placed_on_ir=(weeks >= 8)
        )
        sess.add(inj)
        sess.commit()
        sess.refresh(inj)
        return inj
    
    return None

def weekly_heal(sess: Session, season: int, week: int, team_id: Optional[int] = None):
    """
    Advance week for all injuries; update status flags and resolve finished entries.
    """
    q = select(Injury).where(Injury.resolved == False)  # noqa: E712
    if team_id is not None:
        q = q.where(Injury.team_id == team_id)
    
    rows = list(sess.exec(q))
    for inj in rows:
        if inj.season > season or (inj.season == season and inj.week >= week):
            continue  # injuries from this week not healing yet (heal next rollover)
        
        if inj.weeks_out_remaining > 0:
            inj.weeks_out_remaining -= 1
        
        if inj.weeks_out_remaining <= 0:
            inj.status = InjuryStatus.ACTIVE
            inj.resolved = True
        else:
            # Set tentative availability tiers
            if inj.weeks_out_remaining >= 2:
                inj.status = InjuryStatus.OUT
            elif inj.weeks_out_remaining == 1:
                inj.status = InjuryStatus.DOUBTFUL
            else:
                inj.status = InjuryStatus.QUESTIONABLE
        
        sess.add(inj)
    
    sess.commit()

def active_penalty_for_player(sess: Session, player_id: int) -> float:
    """
    If a player has a *recently resolved* injury with RTP penalty, return OV penalty fraction.
    In MVP we apply the *worst* RTP penalty among injuries from the current season that have resolved in the last 2 weeks.
    """
    # Fetch resolved injuries for this player
    rows = list(sess.exec(select(Injury).where(Injury.player_id == player_id)))
    penalty = 0.0
    
    for inj in rows:
        if inj.resolved and inj.status == InjuryStatus.ACTIVE:
            penalty = max(penalty, inj.rtp_penalty_overall)
    
    return penalty

def is_player_active(sess: Session, player_id: int) -> bool:
    """Check if a player is active (no unresolved injuries)."""
    row = sess.exec(select(Injury).where(Injury.player_id == player_id, Injury.resolved == False)).first()  # noqa: E712
    return row is None  # active if no unresolved injury

def get_player_injury_status(sess: Session, player_id: int) -> Optional[InjuryStatus]:
    """Get the current injury status of a player."""
    row = sess.exec(select(Injury).where(Injury.player_id == player_id, Injury.resolved == False)).first()  # noqa: E712
    return row.status if row else InjuryStatus.ACTIVE

def get_team_injuries(sess: Session, team_id: int, season: Optional[int] = None, resolved_only: bool = False) -> list[Injury]:
    """Get all injuries for a team."""
    q = select(Injury).where(Injury.team_id == team_id)
    
    if season is not None:
        q = q.where(Injury.season == season)
    
    if resolved_only:
        q = q.where(Injury.resolved == True)  # noqa: E712
    else:
        q = q.where(Injury.resolved == False)  # noqa: E712
    
    return list(sess.exec(q))

def get_injury_stats(sess: Session, team_id: int, season: int) -> dict:
    """Get injury statistics for a team."""
    injuries = get_team_injuries(sess, team_id, season)
    
    stats = {
        "total_injuries": len(injuries),
        "active_injuries": len([i for i in injuries if not i.resolved]),
        "ir_players": len([i for i in injuries if i.placed_on_ir]),
        "by_status": {},
        "by_type": {},
        "avg_severity": 0.0,
        "total_weeks_lost": 0
    }
    
    if injuries:
        # Status breakdown
        for status in InjuryStatus:
            stats["by_status"][status.value] = len([i for i in injuries if i.status == status])
        
        # Type breakdown
        for injury_type in InjuryType:
            stats["by_type"][injury_type.value] = len([i for i in injuries if i.injury_type == injury_type])
        
        # Average severity
        stats["avg_severity"] = sum(i.severity for i in injuries) / len(injuries)
        
        # Total weeks lost
        stats["total_weeks_lost"] = sum(i.weeks_out_total for i in injuries)
    
    return stats

def simulate_injury_odds(sess: Session, season: int, week: int, game_id: int, team_id: int, opponent_id: int, pos: str, simulations: int = 1000) -> dict:
    """Simulate injury odds for analysis."""
    rnd = Random(42)  # Fixed seed for reproducible results
    injuries = 0
    
    for _ in range(simulations):
        if maybe_injure_player(sess, rnd, season, week, game_id, team_id, opponent_id, 99999, pos):
            injuries += 1
    
    ctx = compute_player_injury_odds(sess, season, week, game_id, team_id, opponent_id, pos)
    
    return {
        "simulated_rate": injuries / simulations,
        "calculated_rate": ctx.base_per_game * ctx.focus_injury_mult + ctx.gameplan_aggr_bump + ctx.fatigue_bump,
        "base_rate": ctx.base_per_game,
        "focus_multiplier": ctx.focus_injury_mult,
        "aggression_bump": ctx.gameplan_aggr_bump,
        "fatigue_bump": ctx.fatigue_bump
    }


from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from random import Random
from sqlmodel import Session, select
from app.models.gameplan import GameplanSelection, OffAgg, DefAgg, Coverage, BlitzStrategy, RZOff, RZDef

# --------- Lightweight opponent scouting interface (MVP) ----------
@dataclass
class OpponentProfile:
    """Scouting profile of an opponent team for gameplan decisions."""
    pass_rate: float             # 0..1
    deep_rate: float             # 0..1
    sack_rate_allowed: float     # 0..1 of dropbacks
    run_success_rate: float      # 0..1
    rz_td_offense: float         # 0..1
    rz_td_defense_allowed: float # 0..1
    explosives_rate: float       # 0..1 (gains >=20)
    ol_strength: float           # 0..1 (0 weak)
    dl_strength: float           # 0..1
    secondary_strength: float    # 0..1

def _fallback_profile() -> OpponentProfile:
    """Return a neutral opponent profile for MVP fallback."""
    return OpponentProfile(
        pass_rate=0.54, deep_rate=0.12, sack_rate_allowed=0.075, run_success_rate=0.42,
        rz_td_offense=0.56, rz_td_defense_allowed=0.52, explosives_rate=0.105,
        ol_strength=0.50, dl_strength=0.50, secondary_strength=0.50)

# You can swap this out to pull from real stats tables:
def load_opponent_profile(sess: Session, season: int, week: int, team_id: int) -> OpponentProfile:
    """
    Load opponent profile from stats. For MVP, returns fallback profile.
    In production, this would query TeamSeasonStats or rolling averages.
    """
    try:
        # Example: read TeamSeasonStats or rolling last-3; for MVP return fallback
        # This is where you'd integrate with your actual stats system
        return _fallback_profile()
    except Exception:
        return _fallback_profile()

# --------- Policy: convert profile into dropdown choices ----------
def choose_cpu_gameplan(sess: Session, season: int, week: int, team_id: int, opp_id: int, seed: Optional[int]=None) -> GameplanSelection:
    """
    Choose a CPU gameplan based on opponent scouting profile.
    Uses deterministic randomness with optional seed for reproducibility.
    """
    rnd = Random(seed if seed is not None else (season*10_000 + week*100 + team_id))
    opp = load_opponent_profile(sess, season, week, opp_id)

    # Offensive plan vs opponent defense
    if opp.dl_strength >= 0.60 and opp.secondary_strength < 0.55:
        off_agg = OffAgg.AGGRESSIVE  # attack secondary
        rz_off = RZOff.SPREAD_SHOT
    elif opp.secondary_strength >= 0.65:
        off_agg = OffAgg.CONSERVATIVE if opp.dl_strength > 0.55 else OffAgg.BALANCED
        rz_off = RZOff.PLAY_ACTION_HEAVY
    else:
        off_agg = OffAgg.BALANCED
        rz_off = RZOff.BALANCED

    # Defensive plan vs opponent offense
    if opp.sack_rate_allowed >= 0.085 or opp.ol_strength <= 0.45:
        def_agg = DefAgg.AGGRESSIVE
        blitz = BlitzStrategy.BLITZ_HEAVY
        coverage = Coverage.HYBRID if opp.deep_rate > 0.14 else Coverage.MAN_HEAVY
    elif opp.deep_rate >= 0.16 or opp.explosives_rate >= 0.13:
        def_agg = DefAgg.CONSERVATIVE
        blitz = BlitzStrategy.SELECTIVE
        coverage = Coverage.ZONE_HEAVY
    else:
        def_agg = DefAgg.BALANCED
        blitz = BlitzStrategy.STANDARD
        coverage = Coverage.HYBRID

    # Red Zone defense
    if opp.rz_td_offense >= 0.60:
        rz_def = RZDef.PRESSURE_QB if def_agg in (DefAgg.AGGRESSIVE, DefAgg.VERY_AGGRESSIVE) else RZDef.BEND
    else:
        rz_def = RZDef.BALANCED

    # Small randomness to avoid monotony
    if rnd.random() < 0.10:
        # flip between HYBRID/ZONE on the margin
        coverage = Coverage.ZONE_HEAVY if coverage == Coverage.HYBRID else Coverage.HYBRID
    if rnd.random() < 0.08 and blitz == BlitzStrategy.STANDARD:
        blitz = BlitzStrategy.SELECTIVE

    # Persist selection
    row = sess.exec(select(GameplanSelection).where(
        GameplanSelection.season==season, 
        GameplanSelection.week==week,
        GameplanSelection.team_id==team_id, 
        GameplanSelection.opponent_team_id==opp_id
    )).first()
    if not row:
        row = GameplanSelection(season=season, week=week, team_id=team_id, opponent_team_id=opp_id)
    row.off_agg = off_agg
    row.def_agg = def_agg
    row.coverage = coverage
    row.blitz_strategy = blitz
    row.rz_off = rz_off
    row.rz_def = rz_def
    sess.add(row); sess.commit(); sess.refresh(row)
    return row

def choose_cpu_gameplan_for_week(sess: Session, season: int, week: int, seed: Optional[int]=None):
    """
    Batch-pick gameplans for every CPU-vs-any matchup.
    You should replace the schedule iteration with your real schedule model.
    """
    # Example schedule iteration stub (replace with your Schedule table)
    try:
        from app.models.schedule import Game
        games = list(sess.exec(select(Game).where(Game.season==season, Game.week==week)))
        for g in games:
            # For both teams (even if user controls one; harmless to overwrite if user plans saved after)
            choose_cpu_gameplan(sess, season, week, g.home_team_id, g.away_team_id, seed=seed)
            choose_cpu_gameplan(sess, season, week, g.away_team_id, g.home_team_id, seed=seed+1 if seed is not None else None)
    except Exception:
        # If no schedule model yet, do nothing gracefully
        return

def choose_cpu_gameplan_for_team(sess: Session, season: int, week: int, team_id: int, opponents: list[int], seed: Optional[int]=None):
    """
    Choose CPU gameplans for a specific team against multiple opponents.
    Useful for batch operations on specific teams.
    """
    for opp_id in opponents:
        choose_cpu_gameplan(sess, season, week, team_id, opp_id, seed=seed)
        if seed is not None:
            seed += 1

def get_cpu_gameplan_reasoning(sess: Session, season: int, week: int, team_id: int, opp_id: int) -> dict:
    """
    Get the reasoning behind a CPU gameplan choice for debugging/transparency.
    """
    opp = load_opponent_profile(sess, season, week, opp_id)
    
    reasoning = {
        "opponent_profile": opp.__dict__,
        "offensive_reasoning": "",
        "defensive_reasoning": "",
        "red_zone_reasoning": "",
    }
    
    # Offensive reasoning
    if opp.dl_strength >= 0.60 and opp.secondary_strength < 0.55:
        reasoning["offensive_reasoning"] = "Attack weak secondary (strength < 0.55) despite strong DL"
    elif opp.secondary_strength >= 0.65:
        reasoning["offensive_reasoning"] = "Conservative approach vs strong secondary (strength >= 0.65)"
    else:
        reasoning["offensive_reasoning"] = "Balanced approach vs average defense"
    
    # Defensive reasoning
    if opp.sack_rate_allowed >= 0.085 or opp.ol_strength <= 0.45:
        reasoning["defensive_reasoning"] = "Aggressive pass rush vs weak OL or high sack rate"
    elif opp.deep_rate >= 0.16 or opp.explosives_rate >= 0.13:
        reasoning["defensive_reasoning"] = "Conservative coverage vs explosive offense"
    else:
        reasoning["defensive_reasoning"] = "Balanced defense vs average offense"
    
    # Red zone reasoning
    if opp.rz_td_offense >= 0.60:
        reasoning["red_zone_reasoning"] = "Pressure QB in red zone vs high TD offense"
    else:
        reasoning["red_zone_reasoning"] = "Balanced red zone defense"
    
    return reasoning


from __future__ import annotations
from dataclasses import dataclass
from sqlmodel import Session, select
from app.services.gameplan_mapping import GameplanDeltas

@dataclass
class HCProfile:
    """
    Head Coach profile containing their coaching tendencies.
    These values influence the base gameplan before user selections.
    """
    # core we actually use here (expand later if you want):
    run_pass_tendency: float = 0.0     # -1..+1 (negative = run)
    offensive_aggression: float = 0.5  # 0..1
    defensive_aggression: float = 0.5  # 0..1
    blitz_rate: float = 0.12           # 0..1 baseline
    coverage_mix: float = 0.5          # 0..1 zone lean
    red_zone_offense: float = 0.0      # -0.5..+0.5 pass lean
    red_zone_defense: float = 0.0      # -0.5..+0.5 pressure vs shell

def get_hc_profile(sess: Session, team_id: int) -> HCProfile:
    """
    Fetch coach & map to a normalized profile. For MVP, return neutral if missing.
    """
    try:
        # Try to import Coach model - if it doesn't exist, return neutral profile
        from app.models.coach import Coach, CoachRole
        row = sess.exec(
            select(Coach).where(Coach.team_id==team_id, Coach.role==CoachRole.HC)
        ).first()
        if not row: 
            return HCProfile()
        
        return HCProfile(
            run_pass_tendency = getattr(row, "run_pass_tendency", 0.0),
            offensive_aggression = getattr(row, "offensive_aggression", 0.5),
            defensive_aggression = getattr(row, "defensive_aggression", 0.5),
            blitz_rate = getattr(row, "blitz_rate", 0.12),
            coverage_mix = getattr(row, "coverage_mix", 0.5),
            red_zone_offense = getattr(row, "red_zone_offense", 0.0),
            red_zone_defense = getattr(row, "red_zone_defense", 0.0),
        )
    except (ImportError, AttributeError):
        # Coach model doesn't exist or missing fields - return neutral profile
        return HCProfile()

def map_hc_to_deltas(hc: HCProfile) -> GameplanDeltas:
    """
    Convert HC profile into small deltas that bias the base plan.
    Aggression around 0.5 is neutral; we scale modestly.
    """
    from math import copysign
    oa = (hc.offensive_aggression - 0.5) * 0.22  # ±0.11 pass_bias, ±~0.088 depth
    da = (hc.defensive_aggression - 0.5) * 0.10  # ±0.05 base blitz, ± cushion
    rz_o = hc.red_zone_offense * 0.18            # ±0.09 rz pass bias
    rz_d = hc.red_zone_defense                   # map to shell/blitz modestly

    return GameplanDeltas(
        # offense
        pass_bias_delta = oa,
        depth_bias_delta = oa * 0.8,
        trick_play_rate_delta = oa * 0.01,
        go4it_cutoff_delta = -oa * 0.9,
        two_point_tendency_delta = oa * 0.25,
        # defense
        base_blitz_rate_delta = da,
        press_cushion_delta = -da * 10.0,   # tighten when aggressive
        run_blitz_rate_delta = da * 0.6,
        coverage_mix = hc.coverage_mix,
        # rz offense/defense
        rz_pass_bias_delta = rz_o,
        rz_shot_play_rate_delta = max(0.0, oa) * 0.02,
        te_rb_target_share_delta = (-rz_o) * 0.1,
        qb_run_keepers_rate_delta = max(0.0, -rz_o) * 0.02,
        rz_shell_depth_delta = -rz_d * 0.4,
        rz_run_box_rate_delta = max(0.0, rz_d) * 0.04,
        rz_blitz_rate_delta = max(0.0, rz_d) * 0.03,
    )


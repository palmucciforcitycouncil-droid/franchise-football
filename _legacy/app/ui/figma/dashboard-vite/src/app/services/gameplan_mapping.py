from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
from app.models.gameplan import OffAgg, DefAgg, Coverage, BlitzStrategy, RZOff, RZDef

@dataclass
class GameplanDeltas:
    # offense
    pass_bias_delta: float = 0.0
    depth_bias_delta: float = 0.0
    trick_play_rate_delta: float = 0.0
    go4it_cutoff_delta: float = 0.0
    two_point_tendency_delta: float = 0.0
    # defense
    base_blitz_rate_delta: float = 0.0
    blitz_rate_multiplier: float = 1.0
    press_cushion_delta: float = 0.0      # + yards cushion, − tighter
    run_blitz_rate_delta: float = 0.0
    coverage_mix: float | None = None     # 0=man, 1=zone
    # red zone offense
    rz_pass_bias_delta: float = 0.0
    rz_shot_play_rate_delta: float = 0.0
    te_rb_target_share_delta: float = 0.0
    qb_run_keepers_rate_delta: float = 0.0
    # red zone defense
    rz_shell_depth_delta: float = 0.0
    rz_run_box_rate_delta: float = 0.0
    rz_blitz_rate_delta: float = 0.0
    # qualitative risks (for engine heuristics, use as tiny weights 0..1)
    explosive_play_risk_weight: float = 0.0
    screen_draw_susceptibility_weight: float = 0.0

def merge(a: GameplanDeltas, b: GameplanDeltas) -> GameplanDeltas:
    # shallow merge numeric fields
    out = GameplanDeltas(
        pass_bias_delta=a.pass_bias_delta + b.pass_bias_delta,
        depth_bias_delta=a.depth_bias_delta + b.depth_bias_delta,
        trick_play_rate_delta=a.trick_play_rate_delta + b.trick_play_rate_delta,
        go4it_cutoff_delta=a.go4it_cutoff_delta + b.go4it_cutoff_delta,
        two_point_tendency_delta=a.two_point_tendency_delta + b.two_point_tendency_delta,
        base_blitz_rate_delta=a.base_blitz_rate_delta + b.base_blitz_rate_delta,
        blitz_rate_multiplier=a.blitz_rate_multiplier * b.blitz_rate_multiplier,
        press_cushion_delta=a.press_cushion_delta + b.press_cushion_delta,
        run_blitz_rate_delta=a.run_blitz_rate_delta + b.run_blitz_rate_delta,
        coverage_mix=b.coverage_mix if b.coverage_mix is not None else a.coverage_mix,
        rz_pass_bias_delta=a.rz_pass_bias_delta + b.rz_pass_bias_delta,
        rz_shot_play_rate_delta=a.rz_shot_play_rate_delta + b.rz_shot_play_rate_delta,
        te_rb_target_share_delta=a.te_rb_target_share_delta + b.te_rb_target_share_delta,
        qb_run_keepers_rate_delta=a.qb_run_keepers_rate_delta + b.qb_run_keepers_rate_delta,
        rz_shell_depth_delta=a.rz_shell_depth_delta + b.rz_shell_depth_delta,
        rz_run_box_rate_delta=a.rz_run_box_rate_delta + b.rz_run_box_rate_delta,
        rz_blitz_rate_delta=a.rz_blitz_rate_delta + b.rz_blitz_rate_delta,
        explosive_play_risk_weight=a.explosive_play_risk_weight + b.explosive_play_risk_weight,
        screen_draw_susceptibility_weight=a.screen_draw_susceptibility_weight + b.screen_draw_susceptibility_weight,
    )
    return out

# ---------- OFFENSIVE AGGRESSIVENESS ----------
OFF_AGG_MAP: Dict[OffAgg, GameplanDeltas] = {
    OffAgg.VERY_CONSERVATIVE: GameplanDeltas(
        pass_bias_delta=-0.10, depth_bias_delta=-0.08, trick_play_rate_delta=-0.005,
        go4it_cutoff_delta=+0.12, two_point_tendency_delta=-0.03),
    OffAgg.CONSERVATIVE: GameplanDeltas(
        pass_bias_delta=-0.05, depth_bias_delta=-0.04, trick_play_rate_delta=-0.0025,
        go4it_cutoff_delta=+0.06, two_point_tendency_delta=-0.01),
    OffAgg.BALANCED: GameplanDeltas(),
    OffAgg.AGGRESSIVE: GameplanDeltas(
        pass_bias_delta=+0.05, depth_bias_delta=+0.04, trick_play_rate_delta=+0.0025,
        go4it_cutoff_delta=-0.06, two_point_tendency_delta=+0.01),
    OffAgg.VERY_AGGRESSIVE: GameplanDeltas(
        pass_bias_delta=+0.10, depth_bias_delta=+0.08, trick_play_rate_delta=+0.005,
        go4it_cutoff_delta=-0.12, two_point_tendency_delta=+0.03),
}

# ---------- DEFENSIVE AGGRESSIVENESS ----------
DEF_AGG_MAP: Dict[DefAgg, GameplanDeltas] = {
    DefAgg.VERY_CONSERVATIVE: GameplanDeltas(
        base_blitz_rate_delta=-0.06, press_cushion_delta=+1.5, run_blitz_rate_delta=-0.04),
    DefAgg.CONSERVATIVE: GameplanDeltas(
        base_blitz_rate_delta=-0.03, press_cushion_delta=+0.75, run_blitz_rate_delta=-0.02),
    DefAgg.BALANCED: GameplanDeltas(),
    DefAgg.AGGRESSIVE: GameplanDeltas(
        base_blitz_rate_delta=+0.03, press_cushion_delta=-0.75, run_blitz_rate_delta=+0.02,
        explosive_play_risk_weight=0.5),
    DefAgg.VERY_AGGRESSIVE: GameplanDeltas(
        base_blitz_rate_delta=+0.06, press_cushion_delta=-1.5, run_blitz_rate_delta=+0.04,
        explosive_play_risk_weight=1.0),
}

# ---------- COVERAGE SCHEME ----------
COVERAGE_MAP: Dict[Coverage, GameplanDeltas] = {
    Coverage.MAN_HEAVY: GameplanDeltas(coverage_mix=0.15, press_cushion_delta=-0.25),
    Coverage.HYBRID: GameplanDeltas(coverage_mix=0.50),
    Coverage.ZONE_HEAVY: GameplanDeltas(coverage_mix=0.85, press_cushion_delta=+0.25),
}

# ---------- BLITZ STRATEGY ----------
BLITZ_MAP: Dict[BlitzStrategy, GameplanDeltas] = {
    BlitzStrategy.SELECTIVE: GameplanDeltas(blitz_rate_multiplier=0.85),
    BlitzStrategy.STANDARD: GameplanDeltas(blitz_rate_multiplier=1.00),
    BlitzStrategy.BLITZ_HEAVY: GameplanDeltas(blitz_rate_multiplier=1.20,
                                              explosive_play_risk_weight=0.6,
                                              screen_draw_susceptibility_weight=0.8),
}

# ---------- RED ZONE OFFENSE ----------
RZ_OFF_MAP: Dict[RZOff, GameplanDeltas] = {
    RZOff.POWER_RUN: GameplanDeltas(rz_pass_bias_delta=-0.12, rz_shot_play_rate_delta=-0.02,
                                    te_rb_target_share_delta=-0.03, qb_run_keepers_rate_delta=+0.02),
    RZOff.BALANCED: GameplanDeltas(),
    RZOff.PLAY_ACTION_HEAVY: GameplanDeltas(rz_pass_bias_delta=+0.06, rz_shot_play_rate_delta=+0.02,
                                            te_rb_target_share_delta=+0.02),
    RZOff.SPREAD_SHOT: GameplanDeltas(rz_pass_bias_delta=+0.10, rz_shot_play_rate_delta=+0.03,
                                      te_rb_target_share_delta=-0.01),
}

# ---------- RED ZONE DEFENSE ----------
RZ_DEF_MAP: Dict[RZDef, GameplanDeltas] = {
    RZDef.BEND: GameplanDeltas(rz_shell_depth_delta=+0.5, rz_blitz_rate_delta=-0.03),
    RZDef.BALANCED: GameplanDeltas(),
    RZDef.RUN_SELLOUT: GameplanDeltas(rz_shell_depth_delta=-0.2, rz_run_box_rate_delta=+0.06, rz_blitz_rate_delta=+0.01),
    RZDef.PRESSURE_QB: GameplanDeltas(rz_shell_depth_delta=-0.3, rz_blitz_rate_delta=+0.04),
}

def build_deltas(off_agg: OffAgg, def_agg: DefAgg, coverage: Coverage, blitz: BlitzStrategy, rz_off: RZOff, rz_def: RZDef) -> GameplanDeltas:
    out = GameplanDeltas()
    out = merge(out, OFF_AGG_MAP[off_agg])
    out = merge(out, DEF_AGG_MAP[def_agg])
    out = merge(out, COVERAGE_MAP[coverage])
    out = merge(out, BLITZ_MAP[blitz])
    out = merge(out, RZ_OFF_MAP[rz_off])
    out = merge(out, RZ_DEF_MAP[rz_def])
    return out


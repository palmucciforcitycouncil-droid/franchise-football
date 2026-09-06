from __future__ import annotations
from dataclasses import dataclass
from app.services.gameplan_mapping import GameplanDeltas

@dataclass
class EngineConfig:
    pass_bias: float = 0.0
    depth_bias: float = 0.0
    trick_play_rate: float = 0.0
    go4it_cutoff: float = 0.0
    two_point_bias: float = 0.0
    base_blitz_rate: float = 0.12
    blitz_rate: float = 0.12
    press_cushion: float = 5.0
    run_blitz_rate: float = 0.06
    coverage_mix: float = 0.50
    rz_off_pass_bias: float = 0.0
    rz_shot_rate: float = 0.03
    te_rb_share: float = 0.0
    qb_keeper_rate: float = 0.02
    rz_shell_depth: float = 0.0
    rz_box_rate: float = 0.0
    rz_blitz_rate: float = 0.08
    explosive_risk_weight: float = 0.0
    screen_sus_weight: float = 0.0

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def apply_gameplan(cfg: EngineConfig, d: GameplanDeltas) -> EngineConfig:
    cfg.pass_bias      = clamp(cfg.pass_bias + d.pass_bias_delta, -0.5, 0.5)
    cfg.depth_bias     = clamp(cfg.depth_bias + d.depth_bias_delta, -0.4, 0.4)
    cfg.trick_play_rate= clamp(cfg.trick_play_rate + d.trick_play_rate_delta, 0.0, 0.02)
    cfg.go4it_cutoff   = clamp(cfg.go4it_cutoff + d.go4it_cutoff_delta, -0.2, 0.2)
    cfg.two_point_bias = clamp(cfg.two_point_bias + d.two_point_tendency_delta, -0.06, 0.06)

    cfg.base_blitz_rate= clamp(cfg.base_blitz_rate + d.base_blitz_rate_delta, 0.02, 0.35)
    cfg.blitz_rate     = clamp((cfg.base_blitz_rate) * d.blitz_rate_multiplier, 0.02, 0.45)
    cfg.press_cushion  = clamp(cfg.press_cushion + d.press_cushion_delta, 2.0, 8.0)
    cfg.run_blitz_rate = clamp(cfg.run_blitz_rate + d.run_blitz_rate_delta, 0.0, 0.20)

    if d.coverage_mix is not None:
        cfg.coverage_mix = clamp(d.coverage_mix, 0.0, 1.0)

    cfg.rz_off_pass_bias   = clamp(cfg.rz_off_pass_bias + d.rz_pass_bias_delta, -0.4, 0.4)
    cfg.rz_shot_rate       = clamp(cfg.rz_shot_rate + d.rz_shot_play_rate_delta, 0.0, 0.10)
    cfg.te_rb_share        = clamp(cfg.te_rb_share + d.te_rb_target_share_delta, -0.1, 0.2)
    cfg.qb_keeper_rate     = clamp(cfg.qb_keeper_rate + d.qb_run_keepers_rate_delta, 0.0, 0.10)

    cfg.rz_shell_depth     = clamp(cfg.rz_shell_depth + d.rz_shell_depth_delta, -1.0, 1.0)
    cfg.rz_box_rate        = clamp(cfg.rz_box_rate + d.rz_run_box_rate_delta, 0.0, 0.25)
    cfg.rz_blitz_rate      = clamp(cfg.rz_blitz_rate + d.rz_blitz_rate_delta, 0.0, 0.35)

    cfg.explosive_risk_weight += d.explosive_play_risk_weight
    cfg.screen_sus_weight     += d.screen_draw_susceptibility_weight
    return cfg

def create_default_config() -> EngineConfig:
    """Create a default engine configuration."""
    return EngineConfig()

def apply_gameplan_to_default(d: GameplanDeltas) -> EngineConfig:
    """Apply gameplan deltas to default configuration."""
    default_cfg = create_default_config()
    return apply_gameplan(default_cfg, d)


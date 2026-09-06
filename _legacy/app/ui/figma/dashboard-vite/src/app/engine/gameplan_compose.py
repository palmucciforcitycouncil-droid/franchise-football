from __future__ import annotations
import json
from sqlmodel import Session, select
from app.engine.gameplan_apply import EngineConfig, apply_gameplan
from app.services.hc_influence import get_hc_profile, map_hc_to_deltas
from app.services.coach_focus_service import aggregate_weekly_effects
from app.services.gameplan_mapping import build_deltas, GameplanDeltas
from app.models.gameplan import GameplanSelection
from app.models.gameplan_trace import GameplanTrace

def _d_to_dict(d: GameplanDeltas) -> dict:
    """Convert GameplanDeltas to dictionary for JSON serialization."""
    return {
        "pass_bias_delta": d.pass_bias_delta,
        "depth_bias_delta": d.depth_bias_delta,
        "trick_play_rate_delta": d.trick_play_rate_delta,
        "go4it_cutoff_delta": d.go4it_cutoff_delta,
        "two_point_tendency_delta": d.two_point_tendency_delta,
        "base_blitz_rate_delta": d.base_blitz_rate_delta,
        "blitz_rate_multiplier": d.blitz_rate_multiplier,
        "press_cushion_delta": d.press_cushion_delta,
        "run_blitz_rate_delta": d.run_blitz_rate_delta,
        "coverage_mix": d.coverage_mix,
        "rz_pass_bias_delta": d.rz_pass_bias_delta,
        "rz_shot_play_rate_delta": d.rz_shot_play_rate_delta,
        "te_rb_target_share_delta": d.te_rb_target_share_delta,
        "qb_run_keepers_rate_delta": d.qb_run_keepers_rate_delta,
        "rz_shell_depth_delta": d.rz_shell_depth_delta,
        "rz_run_box_rate_delta": d.rz_run_box_rate_delta,
        "rz_blitz_rate_delta": d.rz_blitz_rate_delta,
        "explosive_play_risk_weight": d.explosive_play_risk_weight,
        "screen_draw_susceptibility_weight": d.screen_draw_susceptibility_weight,
    }

def compose_final_engine_config(sess: Session, game_id: int, season: int, week: int, team_id: int, opponent_team_id: int) -> EngineConfig:
    """
    Compose the final engine configuration by combining:
    1. HC influence (baseline coaching tendencies)
    2. User gameplan selections (per-opponent strategy)
    3. Coach focus effects (weekly coaching focus)
    
    Returns the final EngineConfig and stores a trace for debugging.
    """
    # 1) HC → deltas (baseline coaching tendencies)
    hc = get_hc_profile(sess, team_id)
    hc_d = map_hc_to_deltas(hc)

    # 2) Coach Focus bundle (already persisted per team/week)
    focus = aggregate_weekly_effects(sess, team_id, season, week)

    # 3) User per-opponent selection
    row = sess.exec(select(GameplanSelection).where(
        GameplanSelection.season==season, 
        GameplanSelection.week==week,
        GameplanSelection.team_id==team_id, 
        GameplanSelection.opponent_team_id==opponent_team_id
    )).first()
    if not row:
        # create default if missing
        row = GameplanSelection(season=season, week=week, team_id=team_id, opponent_team_id=opponent_team_id)
        sess.add(row); sess.commit(); sess.refresh(row)
    user_d = build_deltas(row.off_agg, row.def_agg, row.coverage, row.blitz_strategy, row.rz_off, row.rz_def)

    # 4) Apply in order: base cfg -> HC -> User -> Focus
    cfg = EngineConfig()
    cfg = apply_gameplan(cfg, hc_d)     # HC baseline
    cfg = apply_gameplan(cfg, user_d)   # user intent
    
    # Map Focus bundle pieces into a minimal GameplanDeltas before applying:
    focus_to_user = GameplanDeltas(
        pass_bias_delta=focus.run_pass_tendency_delta,
        depth_bias_delta=focus.offensive_aggression_delta * 0.6,
        trick_play_rate_delta=focus.offensive_aggression_delta * 0.003,
        go4it_cutoff_delta = -focus.fourth_down_delta,    # more go-for-it reduces cutoff
        two_point_tendency_delta=focus.two_point_delta,
        base_blitz_rate_delta=focus.defensive_aggression_delta,
        blitz_rate_multiplier=1.0,
        press_cushion_delta= -focus.defensive_aggression_delta * 8.0,
        run_blitz_rate_delta=focus.defensive_aggression_delta * 0.5,
        coverage_mix=None,  # focus doesn't choose shells
        rz_pass_bias_delta=0.0,
        rz_shot_play_rate_delta=0.0,
        te_rb_target_share_delta=0.0,
        qb_run_keepers_rate_delta=0.0,
        rz_shell_depth_delta=0.0,
        rz_run_box_rate_delta=0.0,
        rz_blitz_rate_delta=0.0,
    )
    cfg = apply_gameplan(cfg, focus_to_user)

    # 5) Persist trace for debugging
    trace = GameplanTrace(
        game_id=game_id, 
        team_id=team_id, 
        opponent_team_id=opponent_team_id,
        season=season, 
        week=week,
        hc=json.dumps(hc.__dict__),
        focus=json.dumps(focus.__dict__),
        user=json.dumps(_d_to_dict(user_d)),
        final_cfg=json.dumps(cfg.__dict__),
    )
    sess.add(trace); sess.commit()
    return cfg


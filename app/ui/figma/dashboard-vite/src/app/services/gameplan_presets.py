from __future__ import annotations
from sqlmodel import Session, select
from app.models.gameplan import GameplanSelection, OffAgg, DefAgg, Coverage, BlitzStrategy, RZOff, RZDef

def _upsert(sess: Session, season: int, week: int, team_id: int, opponent_team_id: int) -> GameplanSelection:
    """Upsert a gameplan selection for the given matchup."""
    row = sess.exec(select(GameplanSelection).where(
        GameplanSelection.season==season, 
        GameplanSelection.week==week,
        GameplanSelection.team_id==team_id, 
        GameplanSelection.opponent_team_id==opponent_team_id
    )).first()
    if not row:
        row = GameplanSelection(season=season, week=week, team_id=team_id, opponent_team_id=opponent_team_id)
    sess.add(row)
    return row

def apply_preset_balanced(sess: Session, season: int, week: int, team_id: int, opp_id: int) -> GameplanSelection:
    """Apply balanced preset - neutral approach across all areas."""
    row = _upsert(sess, season, week, team_id, opp_id)
    row.off_agg = OffAgg.BALANCED
    row.def_agg = DefAgg.BALANCED
    row.coverage = Coverage.HYBRID
    row.blitz_strategy = BlitzStrategy.STANDARD
    row.rz_off = RZOff.BALANCED
    row.rz_def = RZDef.BALANCED
    sess.commit(); sess.refresh(row); return row

def apply_preset_air_it_out(sess: Session, season: int, week: int, team_id: int, opp_id: int) -> GameplanSelection:
    """Apply air-it-out preset - aggressive passing offense with conservative defense."""
    row = _upsert(sess, season, week, team_id, opp_id)
    row.off_agg = OffAgg.VERY_AGGRESSIVE
    row.def_agg = DefAgg.CONSERVATIVE
    row.coverage = Coverage.ZONE_HEAVY
    row.blitz_strategy = BlitzStrategy.SELECTIVE
    row.rz_off = RZOff.SPREAD_SHOT
    row.rz_def = RZDef.BEND
    sess.commit(); sess.refresh(row); return row

def apply_preset_ground_pound(sess: Session, season: int, week: int, team_id: int, opp_id: int) -> GameplanSelection:
    """Apply ground-pound preset - conservative run-heavy offense with run-stopping defense."""
    row = _upsert(sess, season, week, team_id, opp_id)
    row.off_agg = OffAgg.VERY_CONSERVATIVE
    row.def_agg = DefAgg.BALANCED
    row.coverage = Coverage.HYBRID
    row.blitz_strategy = BlitzStrategy.STANDARD
    row.rz_off = RZOff.POWER_RUN
    row.rz_def = RZDef.RUN_SELLOUT
    sess.commit(); sess.refresh(row); return row

def apply_preset_heat_qb(sess: Session, season: int, week: int, team_id: int, opp_id: int) -> GameplanSelection:
    """Apply heat-QB preset - balanced offense with aggressive pass rush defense."""
    row = _upsert(sess, season, week, team_id, opp_id)
    row.off_agg = OffAgg.BALANCED
    row.def_agg = DefAgg.AGGRESSIVE
    row.coverage = Coverage.HYBRID
    row.blitz_strategy = BlitzStrategy.BLITZ_HEAVY
    row.rz_off = RZOff.BALANCED
    row.rz_def = RZDef.PRESSURE_QB
    sess.commit(); sess.refresh(row); return row

def apply_preset_bend_rz(sess: Session, season: int, week: int, team_id: int, opp_id: int) -> GameplanSelection:
    """Apply bend-don't-break preset - conservative approach with bend-don't-break red zone defense."""
    row = _upsert(sess, season, week, team_id, opp_id)
    row.off_agg = OffAgg.CONSERVATIVE
    row.def_agg = DefAgg.CONSERVATIVE
    row.coverage = Coverage.ZONE_HEAVY
    row.blitz_strategy = BlitzStrategy.SELECTIVE
    row.rz_off = RZOff.PLAY_ACTION_HEAVY
    row.rz_def = RZDef.BEND
    sess.commit(); sess.refresh(row); return row

# Preset registry for easy access
PRESET_FUNCTIONS = {
    "balanced": apply_preset_balanced,
    "air_it_out": apply_preset_air_it_out,
    "ground_pound": apply_preset_ground_pound,
    "heat_qb": apply_preset_heat_qb,
    "bend_rz": apply_preset_bend_rz,
}

def get_available_presets() -> list[str]:
    """Get list of available preset names."""
    return list(PRESET_FUNCTIONS.keys())

def apply_preset(sess: Session, preset_name: str, season: int, week: int, team_id: int, opp_id: int) -> GameplanSelection:
    """Apply a preset by name."""
    if preset_name not in PRESET_FUNCTIONS:
        raise ValueError(f"Unknown preset: {preset_name}")
    return PRESET_FUNCTIONS[preset_name](sess, season, week, team_id, opp_id)


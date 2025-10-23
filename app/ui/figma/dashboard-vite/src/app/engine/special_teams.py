from __future__ import annotations
import random
from sqlmodel import Session
from app.config_sim_calibration import weather as W
from app.engine.scoring import apply_field_goal

def fg_distance_from_yardline(yardline:int)->int: 
    """Calculate field goal distance from yardline."""
    return 17 + (100 - yardline)

def fg_make_probability(base_make_40_49: float, dist: int, kicker_power: float, wx_shift: float=0.0) -> float:
    """Calculate field goal make probability based on distance, kicker skill, and weather."""
    if dist<=29: 
        base=min(0.99, base_make_40_49+0.06)
    elif dist<=39: 
        base=min(0.99, base_make_40_49+0.03)
    elif dist<=49: 
        base=base_make_40_49
    elif dist<=55: 
        base=max(0.05, base_make_40_49-0.12)
    else: 
        base=max(0.02, base_make_40_49-0.25)
    
    power_bonus=0.0
    if dist>=50: 
        power_bonus=0.01*((dist-50)/2.0)*(0.5+0.5*kicker_power)
    
    p=base+power_bonus+wx_shift
    return max(0.01,min(0.99,p))

def attempt_field_goal(rng:random.Random, session:Session, game_id:int, yardline:int, kicker_power:float, kicker_base_40_49:float, wx:dict, off_team_id:int):
    """Attempt a field goal and apply scoring."""
    dist=fg_distance_from_yardline(yardline)
    p_make=fg_make_probability(kicker_base_40_49, dist, kicker_power, wx.get("fg_make_shift",0.0))
    made = (rng.random()<p_make)
    apply_field_goal(session, game_id, off_team_id, made)
    return made, dist, p_make
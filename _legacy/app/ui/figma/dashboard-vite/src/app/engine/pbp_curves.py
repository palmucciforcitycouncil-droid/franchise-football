from __future__ import annotations
import math, random
from app.config_sim_calibration import cal, fdown, weather as W

def sigmoid(x: float)->float: return 1/(1+math.exp(-x))

def third_down_logit(ytg: int) -> float:
    if ytg <= 1: return cal.THIRD_DOWN_LOGIT_TABLE["1"]
    if ytg <= 3: return cal.THIRD_DOWN_LOGIT_TABLE["2-3"]
    if ytg <= 6: return cal.THIRD_DOWN_LOGIT_TABLE["4-6"]
    if ytg <= 9: return cal.THIRD_DOWN_LOGIT_TABLE["7-9"]
    return cal.THIRD_DOWN_LOGIT_TABLE["10+"]

def red_zone_td_prob(yardline: int, team_mod: float) -> float:
    # yardline: 1..99 (100 = TD). RZ inside 20: probability increases as yardline→100, but include GTG failures.
    if yardline < 80: return 0.0
    depth = (yardline - 80) / 20.0  # 0..1
    base = cal.RZ_TD_BASE + 0.15*(depth - 0.5)  # Increased slope for more scoring
    base = max(0.40, min(0.80, base + team_mod))  # Increased range
    # ensure goal-to-go failure exists
    return max(0.0, min(1.0, base*(1.0 - 0.3*cal.GOAL_TO_GO_FAIL_PCT)))  # Reduced failure rate

def fourth_down_decision(rng:random.Random, yardline:int, to_go:int, kicker_max:int, coach_agg:float)->str:
    """Updated 4th down decision logic with reduced punt rate."""
    if yardline<60:
        if to_go<=2 and coach_agg>0.7 and rng.random()<0.25: 
            return "GO"
        return "PUNT"
    
    fg_dist=17+(100-yardline)
    in_range=fg_dist<=kicker_max
    
    if 60<=yardline<=65:
        if to_go<=2 and rng.random()<(0.60+0.20*coach_agg): 
            return "GO"
        if in_range and rng.random()<0.75: 
            return "FG"
        return "PUNT"
    
    if to_go<=2 and rng.random()<(0.65+0.25*coach_agg): 
        return "GO"
    if to_go<=4 and rng.random()<(0.45+0.20*coach_agg): 
        return "GO"
    if in_range: 
        return "FG"
    return "PUNT"

def weather_adjustments(is_indoor: bool, wind_mph: float, precip: str):
    # Returns dict of small penalties/bonuses applied downstream
    if W.INDOOR_NULLS_WEATHER and is_indoor: return {"pass_logit":0.0, "fg_make_shift":0.0, "punt_net_shift":0.0}
    pen_pass = 0.0; fg_shift=0.0; punt_shift=0.0
    if wind_mph>=10:
        fg_shift += W.WIND_FG_MAKE_PCT_SHIFT_PER_10MPH*(wind_mph/10.0)
        punt_shift += random.uniform(-W.WIND_PUNT_NET_YDS_STD, W.WIND_PUNT_NET_YDS_STD)
    if precip=="rain":
        pen_pass += W.RAIN_PASS_LOGIT_PENALTY
    if precip=="snow":
        pen_pass += W.SNOW_KICK_PENALTY_LOGIT
        fg_shift += -0.05
    return {"pass_logit":pen_pass, "fg_make_shift":fg_shift, "punt_net_shift":punt_shift}

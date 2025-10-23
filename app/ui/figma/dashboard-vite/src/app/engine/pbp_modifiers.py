from __future__ import annotations
import math, random
from dataclasses import dataclass
from app.config_sim_calibration import varset

def sigmoid(x): return 1/(1+math.exp(-x))

@dataclass
class PosVarianceCaps:
    qb: float = varset.LOGIT_CAP_QB
    rb: float = varset.LOGIT_CAP_RB
    wr: float = varset.LOGIT_CAP_WR
    te: float = varset.LOGIT_CAP_TE
    d: float  = varset.LOGIT_CAP_DEF
    st: float = varset.LOGIT_CAP_ST

def draw_pos_noise(rng: random.Random, cap: float)->float:
    # small mean-zero noise with hard cap
    val = rng.normalvariate(0.0, cap/2.0)
    return max(-cap, min(cap, val))

def compose_pass_complete_logit(qb_cov: float, wr_db: float, ol_dl: float,
                                off_priors: dict, def_priors: dict,
                                situational_logit: float,
                                rand_off: float, rand_def: float,
                                weather_pass_penalty: float)->float:
    base = 0.60*qb_cov + 0.30*wr_db + 0.20*ol_dl
    priors = off_priors.get("third_down_mod",0.0) + off_priors.get("off_epa_mod",0.0) - def_priors.get("def_stop_mod",0.0)
    rand = rand_off - rand_def
    logit = base + priors + situational_logit + rand + weather_pass_penalty
    return logit

def pressure_probability_logit(ol_dl: float, depth_secs: float, def_pressure_mod: float, rand_def: float)->float:
    base = 0.2*(-ol_dl) + 0.2*(depth_secs - 2.5)  # Further reduced coefficients
    return base + def_pressure_mod + 0.2*rand_def  # Further reduced random component

def sack_prob_from_pressure(p_pressure: float, depth_secs: float)->float:
    # Target sack rate to match NFL averages (2.0-2.5 sacks per team per game)
    p_sack_given_pressure = 0.08 + 0.01*max(0, depth_secs - 2.6)  # Further reduced to target range
    return max(0.0, min(1.0, p_pressure * p_sack_given_pressure))

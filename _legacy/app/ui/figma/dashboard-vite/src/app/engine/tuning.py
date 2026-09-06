from dataclasses import dataclass

@dataclass(frozen=True)
class Targets:
    pts_per_team_min: float = 20.0
    pts_per_team_max: float = 28.0
    plays_per_team_min: float = 55.0
    plays_per_team_max: float = 75.0
    ypp_min: float = 5.0
    ypp_max: float = 6.5
    to_per_team_min: float = 0.8
    to_per_team_max: float = 2.2

@dataclass(frozen=True)
class Params:
    ep_pos_scale: float = 0.048   # field position → expected points slope
    ep_rating_scale: float = 0.032
    base_variance: float = 1.0
    aggro_variance_scale: float = 0.9
    td_threshold: float = 3.6
    fg_threshold: float = 1.0
    pat_make: float = 0.94
    punt_net_mu: float = 45.0
    punt_net_sigma: float = 5.0
    two_min_pass_bias: float = 0.18   # additional pass weighting in 2-minute
    two_min_aggression: float = 0.15  # extra aggression late
    fourth_down_boost: float = 0.12   # chance to "extend" a stalled drive
    rtp_weeks_default: int = 2
    rtp_ovr_penalty_per_week: float = 5.0

TARGETS = Targets()
PARAMS = Params()

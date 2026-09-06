from __future__ import annotations

class SimBands:
    # Per-GAME targets (TOTAL, both teams combined) used ONLY for guardrail triggers.
    # Use conservative hard caps so guardrails rarely engage.
    YARDS_MIN: int = 300
    YARDS_MAX: int = 800
    POINTS_MIN: int = 24
    POINTS_MAX: int = 90
    PUNTS_MIN: float = 2.0
    PUNTS_MAX: float = 10.0
    FG_ATT_MIN: float = 2.0
    FG_ATT_MAX: float = 9.0
    SACKS_MIN: float = 2.0
    SACKS_MAX: float = 10.0

class VarianceSettings:
    # Position CV multipliers (week-to-week randomness amplitude).
    CV_QB: float = 0.36
    CV_RB: float = 0.54
    CV_WR: float = 0.58
    CV_TE: float = 0.63
    CV_DEF: float = 0.45   # blended front/back
    CV_ST: float = 0.40

    # Convert CVs to per-game random-effects magnitudes (small, additive on logits).
    # These are caps, actual per-game draw is ~N(0, cap/2).
    LOGIT_CAP_QB: float = 0.05
    LOGIT_CAP_RB: float = 0.08
    LOGIT_CAP_WR: float = 0.09
    LOGIT_CAP_TE: float = 0.10
    LOGIT_CAP_DEF: float = 0.07
    LOGIT_CAP_ST: float = 0.06

class FourthDownSettings:
    # Modern analytics envelope (opponent territory go tendencies).
    BASE_GO_PROB_4TH1_2_OPP35_50: float = 0.55  # grows with yardline and coach_agg
    BASE_GO_PROB_4TH3_4_OPP40_50: float = 0.35
    BASE_GO_PROB_4TH5_6_OPP45_50: float = 0.18
    # Conservative own-territory limits:
    DISALLOW_GO_OWN_TERRITORY_TO_GO: int = 3     # allow only 4th<=2 in own territory else punt

class WeatherSettings:
    # "4 = frequently" → weather impacts apply fairly often outdoors
    ENABLE_WEATHER: bool = True
    WIND_PUNT_NET_YDS_STD: float = 3.0
    WIND_FG_MAKE_PCT_SHIFT_PER_10MPH: float = -0.04  # -4% per 10 mph
    RAIN_PASS_LOGIT_PENALTY: float = -0.10
    SNOW_KICK_PENALTY_LOGIT: float = -0.12
    INDOOR_NULLS_WEATHER: bool = True

class SafetyControllerSettings:
    # Gentle guardrails (Option C): off until Q3; hard caps ±3% on success logits when triggered.
    ENABLE: bool = True
    START_QUARTER: int = 3
    MAX_LOGIT_NUDGE: float = 0.03  # ±3% on the probability domain approx
    # Trigger only if metrics exceed hard bounds:
    REQUIRE_EXCEED_BAND: bool = True

class SimCalSettings:
    # Third down and RZ baselines (recent NFL-like shapes)
    THIRD_DOWN_LOGIT_TABLE = {
        "1":  +0.70,   # ~67%
        "2-3": +0.30,  # ~58%
        "4-6": -0.20,  # ~45%
        "7-9": -0.80,  # ~31%
        "10+": -1.30,  # ~21%
    }
    RZ_TD_BASE: float = 0.56  # league average TD% in RZ, will be curved by yardline
    GOAL_TO_GO_FAIL_PCT: float = 0.28  # non-trivial GTG fail rate

bands = SimBands()
varset = VarianceSettings()
fdown = FourthDownSettings()
weather = WeatherSettings()
safety = SafetyControllerSettings()
cal = SimCalSettings()

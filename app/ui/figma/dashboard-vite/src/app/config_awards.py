"""
Award Configuration Settings.
Defines weights, minimum qualifiers, and deterministic settings for awards.
"""


class AwardSettings:
    # Determinism
    AWARDS_SEED: int = 2025

    # Minimum qualifiers to mimic NFL-style thresholds (tune as needed)
    MIN_QB_ATT: int = 200           # pass attempts
    MIN_RB_ATT: int = 100           # rush attempts
    MIN_WR_TGT: int = 50            # targets
    MIN_TE_TGT: int = 40
    MIN_EDGE_SNAP: int = 250
    MIN_DL_SNAP: int = 250
    MIN_LB_SNAP: int = 300
    MIN_DB_SNAP: int = 300
    MIN_K_FGA: int = 16
    MIN_P_PUNTS: int = 25
    MIN_RET_ATT: int = 15

    # Composite scoring weights by category (z-scores; per-snap/per-route where available)
    # MVP (offense-leaning, but team success matters)
    MVP_W_EPA_P: float = 0.45     # EPA per play (qb/off)
    MVP_W_SR: float = 0.20        # Success Rate
    MVP_W_TD: float = 0.10
    MVP_W_YPG: float = 0.10       # yards per game equivalent
    MVP_W_WINS: float = 0.10      # team wins z-score
    MVP_W_SEED: float = 0.05      # conf seed bonus (approx via record tiebreaker)

    # OPOY (per conference)
    OPOY_W_EPA_P: float = 0.50
    OPOY_W_SR: float = 0.20
    OPOY_W_TD: float = 0.15
    OPOY_W_YPG: float = 0.15

    # DPOY (per conference)
    DPOY_W_SACK: float = 0.35
    DPOY_W_INT: float = 0.35
    DPOY_W_TFL: float = 0.15
    DPOY_W_PBU: float = 0.10
    DPOY_W_DEF_EPA_P: float = 0.05  # if available (negative EPA allowed → invert sign)

    # ROY (offense/defense) — rookies only; looser qualifiers
    ROY_W_PRIMARY: float = 0.65     # primary production stat group (EPA/SR for O, sacks/INT for D)
    ROY_W_SECONDARY: float = 0.25   # secondary group (TDs, TFL, PBU, YPG)
    ROY_W_TEAM: float = 0.10        # team wins effect

    # Coach/GM of the Year
    COY_W_WINS: float = 0.60
    COY_W_DELTA_WINS: float = 0.30  # vs previous season (if not available, use seed bonus proxy)
    COY_W_SEED: float = 0.10

    GM_W_DRAFT_HITS: float = 0.40   # rookie WAR proxy (EPA added)
    GM_W_CAP_EFF: float = 0.30      # cap efficiency proxy if available
    GM_W_DELTA_WINS: float = 0.30

    # Super Bowl MVP — single game composite
    SBMVP_W_TD: float = 0.35
    SBMVP_W_EPA_G: float = 0.35
    SBMVP_W_CLUTCH: float = 0.15    # 4Q / high-leverage weighting
    SBMVP_W_SPECTACLE: float = 0.15 # sacks/INTs/long plays bonus


settings_awards = AwardSettings()

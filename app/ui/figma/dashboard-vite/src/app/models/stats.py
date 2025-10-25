# app/models/stats.py
from __future__ import annotations
from typing import Optional, Literal
from sqlmodel import SQLModel, Field

# --- EXTENDED PLAYER GAME STATS ---
class PlayerGameStats(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    week: int = Field(index=True)
    game_id: int = Field(index=True)
    team_id: int = Field(index=True)
    player_id: int = Field(index=True)

    # Availability / participation
    games_played: int = 1
    games_started: int = 0
    snaps_off: int = 0
    snaps_def: int = 0
    snaps_st: int = 0

    # Passing
    pass_att: int = 0
    pass_cmp: int = 0
    pass_yds: int = 0
    pass_td: int = 0
    pass_int: int = 0
    sacks_taken: int = 0
    air_yds: int = 0
    yac_gained: int = 0
    throwaways: int = 0
    spikes: int = 0
    batted_passes: int = 0
    drops_forced: int = 0
    play_action_att: int = 0
    screen_att: int = 0
    deep_att: int = 0           # air_yds >= 20
    pressure_dropbacks: int = 0
    hits_on_qb: int = 0

    # Rushing
    rush_att: int = 0
    rush_yds: int = 0
    rush_td: int = 0
    yards_before_contact: int = 0
    yards_after_contact: int = 0
    designed_rush_att: int = 0
    scramble_att: int = 0

    # Receiving
    tar: int = 0
    rec: int = 0
    rec_yds: int = 0
    rec_td: int = 0
    air_yds_for: int = 0
    yac: int = 0
    drops: int = 0
    contested_catches_won: int = 0
    receptions_deep: int = 0

    # Ball security
    fumbles: int = 0
    fumbles_lost: int = 0

    # Defense — tackling
    tackles: int = 0
    assists: int = 0
    missed_tackles: int = 0
    tfl: int = 0

    # Defense — pressure
    sacks: float = 0.0
    qb_hits: int = 0
    pressures: int = 0
    hurries: int = 0
    chases: int = 0

    # Defense — coverage / turnovers
    ints: int = 0
    pbus: int = 0
    ff: int = 0
    fr: int = 0
    td_def: int = 0
    targets_defended: int = 0
    receptions_allowed: int = 0
    rec_yds_allowed: int = 0
    yacs_allowed: int = 0
    penalties_committed_def: int = 0

    # Special teams — kicking
    fg_made: int = 0
    fg_att: int = 0
    xp_made: int = 0
    xp_att: int = 0
    long_fg_made: int = 0

    # Special teams — punting
    punts: int = 0
    punt_yds: int = 0
    long_punt: int = 0
    punts_inside_20: int = 0
    punt_touchbacks: int = 0
    punt_returns_allowed: int = 0
    punt_return_yds_allowed: int = 0

    # Special teams — kickoffs
    kickoffs: int = 0
    touchbacks: int = 0
    avg_kickoff_yds: float = 0.0
    kickoff_returns_allowed: int = 0
    kickoff_return_yds_allowed: int = 0

    # Special teams — returns & coverage
    kr: int = 0
    kr_yds: int = 0
    kr_td: int = 0
    pr: int = 0
    pr_yds: int = 0
    pr_td: int = 0
    st_tackles: int = 0
    st_missed_tackles: int = 0
    st_forced_fumbles: int = 0
    st_fumble_recoveries: int = 0

    # Discipline (player)
    penalties: int = 0
    penalty_yds: int = 0

# ===== Per-game team stats =====
class TeamGameStats(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    week: int = Field(index=True)
    game_id: int = Field(index=True)
    team_id: int = Field(index=True)
    opp_team_id: int = Field(index=True)
    
    points_for: int = 0
    points_against: int = 0
    total_yds: int = 0
    pass_yds: int = 0
    rush_yds: int = 0
    plays: int = 0
    ypp: float = 0.0
    top_seconds: int = 0
    turnovers: int = 0
    takeaways: int = 0
    penalties: int = 0
    penalty_yds: int = 0
    sacks: float = 0.0
    sacks_allowed: float = 0.0
    third_md: int = 0
    third_att: int = 0
    fourth_md: int = 0
    fourth_att: int = 0
    rz_trips: int = 0
    rz_tds: int = 0
    st_fg_made: int = 0
    st_fg_att: int = 0
    st_xp_made: int = 0
    st_xp_att: int = 0
    st_punts: int = 0

# --- EXTENDED PLAYER SEASON STATS ---
class PlayerSeasonStats(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    team_id: int = Field(index=True)
    player_id: int = Field(index=True)

    # copy fields from PlayerGameStats, all as sums/max where applicable
    games_played: int = 0
    games_started: int = 0
    snaps_off: int = 0
    snaps_def: int = 0
    snaps_st: int = 0

    pass_att: int = 0; pass_cmp: int = 0; pass_yds: int = 0; pass_td: int = 0; pass_int: int = 0; sacks_taken: int = 0
    air_yds: int = 0; yac_gained: int = 0; throwaways: int = 0; spikes: int = 0; batted_passes: int = 0; drops_forced: int = 0
    play_action_att: int = 0; screen_att: int = 0; deep_att: int = 0; pressure_dropbacks: int = 0; hits_on_qb: int = 0

    rush_att: int = 0; rush_yds: int = 0; rush_td: int = 0
    yards_before_contact: int = 0; yards_after_contact: int = 0
    designed_rush_att: int = 0; scramble_att: int = 0

    tar: int = 0; rec: int = 0; rec_yds: int = 0; rec_td: int = 0
    air_yds_for: int = 0; yac: int = 0; drops: int = 0; contested_catches_won: int = 0; receptions_deep: int = 0

    fumbles: int = 0; fumbles_lost: int = 0

    tackles: int = 0; assists: int = 0; missed_tackles: int = 0; tfl: int = 0
    sacks: float = 0.0; qb_hits: int = 0; pressures: int = 0; hurries: int = 0; chases: int = 0

    ints: int = 0; pbus: int = 0; ff: int = 0; fr: int = 0; td_def: int = 0
    targets_defended: int = 0; receptions_allowed: int = 0; rec_yds_allowed: int = 0; yacs_allowed: int = 0; penalties_committed_def: int = 0

    fg_made: int = 0; fg_att: int = 0; xp_made: int = 0; xp_att: int = 0; long_fg_made: int = 0

    punts: int = 0; punt_yds: int = 0; long_punt: int = 0; punts_inside_20: int = 0; punt_touchbacks: int = 0
    punt_returns_allowed: int = 0; punt_return_yds_allowed: int = 0

    kickoffs: int = 0; touchbacks: int = 0; avg_kickoff_yds: float = 0.0
    kickoff_returns_allowed: int = 0; kickoff_return_yds_allowed: int = 0

    kr: int = 0; kr_yds: int = 0; kr_td: int = 0; pr: int = 0; pr_yds: int = 0; pr_td: int = 0
    st_tackles: int = 0; st_missed_tackles: int = 0; st_forced_fumbles: int = 0; st_fumble_recoveries: int = 0

    penalties: int = 0; penalty_yds: int = 0

# --- EXTENDED PLAYER CAREER STATS ---
class PlayerCareerStats(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(index=True)
    seasons: int = 0

    games_played: int = 0; games_started: int = 0
    snaps_off: int = 0; snaps_def: int = 0; snaps_st: int = 0

    pass_att: int = 0; pass_cmp: int = 0; pass_yds: int = 0; pass_td: int = 0; pass_int: int = 0; sacks_taken: int = 0
    air_yds: int = 0; yac_gained: int = 0; throwaways: int = 0; spikes: int = 0; batted_passes: int = 0; drops_forced: int = 0
    play_action_att: int = 0; screen_att: int = 0; deep_att: int = 0; pressure_dropbacks: int = 0; hits_on_qb: int = 0

    rush_att: int = 0; rush_yds: int = 0; rush_td: int = 0
    yards_before_contact: int = 0; yards_after_contact: int = 0
    designed_rush_att: int = 0; scramble_att: int = 0

    tar: int = 0; rec: int = 0; rec_yds: int = 0; rec_td: int = 0
    air_yds_for: int = 0; yac: int = 0; drops: int = 0; contested_catches_won: int = 0; receptions_deep: int = 0

    fumbles: int = 0; fumbles_lost: int = 0

    tackles: int = 0; assists: int = 0; missed_tackles: int = 0; tfl: int = 0
    sacks: float = 0.0; qb_hits: int = 0; pressures: int = 0; hurries: int = 0; chases: int = 0

    ints: int = 0; pbus: int = 0; ff: int = 0; fr: int = 0; td_def: int = 0
    targets_defended: int = 0; receptions_allowed: int = 0; rec_yds_allowed: int = 0; yacs_allowed: int = 0; penalties_committed_def: int = 0

    fg_made: int = 0; fg_att: int = 0; xp_made: int = 0; xp_att: int = 0; long_fg_made: int = 0

    punts: int = 0; punt_yds: int = 0; long_punt: int = 0; punts_inside_20: int = 0; punt_touchbacks: int = 0
    punt_returns_allowed: int = 0; punt_return_yds_allowed: int = 0

    kickoffs: int = 0; touchbacks: int = 0; avg_kickoff_yds: float = 0.0
    kickoff_returns_allowed: int = 0; kickoff_return_yds_allowed: int = 0

    kr: int = 0; kr_yds: int = 0; kr_td: int = 0; pr: int = 0; pr_yds: int = 0; pr_td: int = 0
    st_tackles: int = 0; st_missed_tackles: int = 0; st_forced_fumbles: int = 0; st_fumble_recoveries: int = 0

    penalties: int = 0; penalty_yds: int = 0

class TeamSeasonStats(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int = Field(index=True)
    team_id: int = Field(index=True)
    
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points_for: int = 0
    points_against: int = 0
    total_yds: int = 0
    pass_yds: int = 0
    rush_yds: int = 0
    plays: int = 0
    ypp: float = 0.0
    turnovers: int = 0
    takeaways: int = 0
    penalties: int = 0
    penalty_yds: int = 0
    sacks: float = 0.0
    sacks_allowed: float = 0.0
    rz_trips: int = 0
    rz_tds: int = 0
    third_md: int = 0
    third_att: int = 0
    fourth_md: int = 0
    fourth_att: int = 0

# ===== Records / Leaderboards =====
class RecordType(str):
    SINGLE_SEASON = "SINGLE_SEASON"
    CAREER = "CAREER"

class RecordCategory(str):
    PASS_YDS = "PASS_YDS"; PASS_TD = "PASS_TD"; RUSH_YDS = "RUSH_YDS"; RUSH_TD = "RUSH_TD"
    REC_YDS = "REC_YDS"; REC_TD = "REC_TD"; SACKS = "SACKS"; INTS = "INTS"
    FGM = "FGM"; PUNTS = "PUNTS"; TACKLES = "TACKLES"
    # Extended categories
    PRESSURES = "PRESSURES"; PBU = "PBU"; KR_TD = "KR_TD"; PR_TD = "PR_TD"
    I20_PUNTS = "I20_PUNTS"; LONG_FG = "LONG_FG"

class RecordEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    record_type: str = Field(index=True)   # SINGLE_SEASON | CAREER
    category: str = Field(index=True)
    season: Optional[int] = Field(default=None, index=True)  # for single-season
    player_id: int = Field(index=True)
    value: float = 0.0

from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field
from decimal import Decimal

class PlayerGameStats(SQLModel, table=True):
    """Player statistics for a single game"""
    __tablename__ = "player_game_stats"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    player_id: int = Field(index=True)
    team_id: int = Field(index=True)
    
    # Game participation
    gp: bool = Field(default=True, description="Game played")
    gs: bool = Field(default=False, description="Game started")
    snaps_offense: int = Field(default=0, description="Offensive snaps")
    snaps_defense: int = Field(default=0, description="Defensive snaps")
    snaps_st: int = Field(default=0, description="Special teams snaps")
    
    # Passing stats
    pass_attempts: int = Field(default=0)
    pass_completions: int = Field(default=0)
    pass_yards: int = Field(default=0)
    pass_td: int = Field(default=0)
    pass_int: int = Field(default=0)
    sacks: float = Field(default=0.0, description="Sacks (supports half-sacks)")
    sack_yards: int = Field(default=0)
    qb_hits: int = Field(default=0)
    pressures: int = Field(default=0)
    
    # Rushing stats
    rush_attempts: int = Field(default=0)
    rush_yards: int = Field(default=0)
    rush_td: int = Field(default=0)
    broken_tackles: int = Field(default=0)
    
    # Receiving stats
    targets: int = Field(default=0)
    receptions: int = Field(default=0)
    receiving_yards: int = Field(default=0)
    receiving_td: int = Field(default=0)
    yac: int = Field(default=0, description="Yards after catch")
    
    # Defense stats
    tackles_solo: int = Field(default=0)
    tackles_assist: int = Field(default=0)
    tfl: int = Field(default=0, description="Tackles for loss")
    sacks_defense: float = Field(default=0.0, description="Sacks by defender")
    qb_hits_defense: int = Field(default=0)
    pressures_defense: int = Field(default=0)
    interceptions: int = Field(default=0)
    int_yards: int = Field(default=0)
    int_td: int = Field(default=0)
    pbus: int = Field(default=0, description="Pass breakups")
    forced_fumbles: int = Field(default=0)
    fumble_recoveries: int = Field(default=0)
    fr_yards: int = Field(default=0)
    fr_td: int = Field(default=0)
    
    # Special teams
    kickoffs: int = Field(default=0)
    kickoff_touchbacks: int = Field(default=0)
    punts: int = Field(default=0)
    punt_yards: int = Field(default=0)
    punts_in_20: int = Field(default=0)
    punt_touchbacks: int = Field(default=0)
    punt_returns: int = Field(default=0)
    punt_return_yards: int = Field(default=0)
    punt_return_td: int = Field(default=0)
    kickoff_returns: int = Field(default=0)
    kickoff_return_yards: int = Field(default=0)
    kickoff_return_td: int = Field(default=0)
    
    # Kicking
    fg_attempts: int = Field(default=0)
    fg_made: int = Field(default=0)
    fg_yards: int = Field(default=0)
    xp_attempts: int = Field(default=0)
    xp_made: int = Field(default=0)
    
    # Turnovers
    fumbles: int = Field(default=0)
    fumbles_lost: int = Field(default=0)
    
    # Penalties
    penalties: int = Field(default=0)
    penalty_yards: int = Field(default=0)
    
    # Advanced metrics
    epa: float = Field(default=0.0, description="Expected Points Added")
    success_rate: float = Field(default=0.0, description="Success rate")
    explosives: int = Field(default=0, description="Explosive plays (20+ yards)")
    third_down_conversions: int = Field(default=0)
    third_down_attempts: int = Field(default=0)
    
    # GDD v3.2 Stat Catalog Add-On Fields
    
    # Offensive Line fields
    sacks_allowed: float = Field(default=0.0, description="Sacks allowed (supports half-sacks)")
    hits_allowed: int = Field(default=0, description="QB hits allowed")
    pressures_allowed: int = Field(default=0, description="Pressures allowed")
    tfl_allowed: int = Field(default=0, description="Tackles for loss allowed")
    run_block_wins: int = Field(default=0, description="Successful run blocks")
    pass_block_wins: int = Field(default=0, description="Successful pass blocks")
    penalties_ol: int = Field(default=0, description="Offensive line penalties")
    
    # Enhanced Defense fields
    targets_faced: int = Field(default=0, description="Pass targets faced")
    completions_allowed: int = Field(default=0, description="Completions allowed")
    yards_allowed: int = Field(default=0, description="Yards allowed")
    yac_allowed: int = Field(default=0, description="YAC allowed")
    td_allowed: int = Field(default=0, description="Touchdowns allowed")
    passer_rating_against: float = Field(default=0.0, description="Passer rating against")
    missed_tackles: int = Field(default=0, description="Missed tackles")
    run_stops: int = Field(default=0, description="Run stops")
    
    # Enhanced Special Teams fields
    punt_net_avg: float = Field(default=0.0, description="Punt net average")
    hang_time_avg: float = Field(default=0.0, description="Average hang time (seconds)")
    kick_distance_avg: float = Field(default=0.0, description="Average kick distance")
    blocked_kicks: int = Field(default=0, description="Blocked kicks")
    return_avg: float = Field(default=0.0, description="Return average")
    return_td: int = Field(default=0, description="Return touchdowns")
    fair_catches: int = Field(default=0, description="Fair catches")
    
    # Situational splits
    fourth_down_conversions: int = Field(default=0)
    fourth_down_attempts: int = Field(default=0)
    red_zone_td: int = Field(default=0, description="Red zone touchdowns")
    red_zone_attempts: int = Field(default=0, description="Red zone attempts")
    goal_to_go_td: int = Field(default=0, description="Goal-to-go touchdowns")
    goal_to_go_attempts: int = Field(default=0, description="Goal-to-go attempts")
    two_minute_plays: int = Field(default=0, description="Two-minute drill plays")
    hurry_up_plays: int = Field(default=0, description="Hurry-up plays")
    garbage_time_excluded: int = Field(default=0, description="Garbage time plays excluded")

class TeamGameStats(SQLModel, table=True):
    """Team statistics for a single game"""
    __tablename__ = "team_game_stats"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    team_id: int = Field(index=True)
    
    # Game participation
    gp: bool = Field(default=True, description="Game played")
    snaps_offense: int = Field(default=0)
    snaps_defense: int = Field(default=0)
    snaps_st: int = Field(default=0)
    
    # Offensive stats
    pass_attempts: int = Field(default=0)
    pass_completions: int = Field(default=0)
    pass_yards: int = Field(default=0)
    pass_td: int = Field(default=0)
    pass_int: int = Field(default=0)
    sacks_allowed: float = Field(default=0.0)
    sack_yards_allowed: int = Field(default=0)
    qb_hits_allowed: int = Field(default=0)
    pressures_allowed: int = Field(default=0)
    
    rush_attempts: int = Field(default=0)
    rush_yards: int = Field(default=0)
    rush_td: int = Field(default=0)
    
    total_yards: int = Field(default=0)
    total_td: int = Field(default=0)
    turnovers: int = Field(default=0)
    
    # Defensive stats
    tackles_solo: int = Field(default=0)
    tackles_assist: int = Field(default=0)
    tfl: int = Field(default=0)
    sacks: float = Field(default=0.0)
    qb_hits: int = Field(default=0)
    pressures: int = Field(default=0)
    interceptions: int = Field(default=0)
    int_yards: int = Field(default=0)
    int_td: int = Field(default=0)
    pbus: int = Field(default=0)
    forced_fumbles: int = Field(default=0)
    fumble_recoveries: int = Field(default=0)
    fr_yards: int = Field(default=0)
    fr_td: int = Field(default=0)
    
    # Special teams
    kickoffs: int = Field(default=0)
    kickoff_touchbacks: int = Field(default=0)
    punts: int = Field(default=0)
    punt_yards: int = Field(default=0)
    punts_in_20: int = Field(default=0)
    punt_touchbacks: int = Field(default=0)
    punt_returns: int = Field(default=0)
    punt_return_yards: int = Field(default=0)
    punt_return_td: int = Field(default=0)
    kickoff_returns: int = Field(default=0)
    kickoff_return_yards: int = Field(default=0)
    kickoff_return_td: int = Field(default=0)
    
    # Kicking
    fg_attempts: int = Field(default=0)
    fg_made: int = Field(default=0)
    fg_yards: int = Field(default=0)
    xp_attempts: int = Field(default=0)
    xp_made: int = Field(default=0)
    
    # Penalties
    penalties: int = Field(default=0)
    penalty_yards: int = Field(default=0)
    
    # Advanced metrics
    epa: float = Field(default=0.0)
    success_rate: float = Field(default=0.0)
    explosives: int = Field(default=0)
    third_down_conversions: int = Field(default=0)
    third_down_attempts: int = Field(default=0)
    
    # GDD v3.2 Stat Catalog Add-On Fields
    
    # Offensive Line fields
    run_block_wins: int = Field(default=0, description="Successful run blocks")
    pass_block_wins: int = Field(default=0, description="Successful pass blocks")
    penalties_ol: int = Field(default=0, description="Offensive line penalties")
    
    # Enhanced Defense fields
    targets_faced: int = Field(default=0, description="Pass targets faced")
    completions_allowed: int = Field(default=0, description="Completions allowed")
    yards_allowed: int = Field(default=0, description="Yards allowed")
    yac_allowed: int = Field(default=0, description="YAC allowed")
    td_allowed: int = Field(default=0, description="Touchdowns allowed")
    passer_rating_against: float = Field(default=0.0, description="Passer rating against")
    missed_tackles: int = Field(default=0, description="Missed tackles")
    run_stops: int = Field(default=0, description="Run stops")
    
    # Enhanced Special Teams fields
    punt_net_avg: float = Field(default=0.0, description="Punt net average")
    hang_time_avg: float = Field(default=0.0, description="Average hang time (seconds)")
    kick_distance_avg: float = Field(default=0.0, description="Average kick distance")
    blocked_kicks: int = Field(default=0, description="Blocked kicks")
    return_avg: float = Field(default=0.0, description="Return average")
    return_td: int = Field(default=0, description="Return touchdowns")
    fair_catches: int = Field(default=0, description="Fair catches")
    
    # Situational splits
    fourth_down_conversions: int = Field(default=0)
    fourth_down_attempts: int = Field(default=0)
    red_zone_td: int = Field(default=0, description="Red zone touchdowns")
    red_zone_attempts: int = Field(default=0, description="Red zone attempts")
    goal_to_go_td: int = Field(default=0, description="Goal-to-go touchdowns")
    goal_to_go_attempts: int = Field(default=0, description="Goal-to-go attempts")
    two_minute_plays: int = Field(default=0, description="Two-minute drill plays")
    hurry_up_plays: int = Field(default=0, description="Hurry-up plays")
    garbage_time_excluded: int = Field(default=0, description="Garbage time plays excluded")

class PlayerSeasonStats(SQLModel, table=True):
    """Player statistics aggregated for a season"""
    __tablename__ = "player_season_stats"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(index=True)
    team_id: int = Field(index=True)
    season: int = Field(index=True)
    
    # Games
    gp: int = Field(default=0, description="Games played")
    gs: int = Field(default=0, description="Games started")
    
    # All other fields same as PlayerGameStats but aggregated
    snaps_offense: int = Field(default=0)
    snaps_defense: int = Field(default=0)
    snaps_st: int = Field(default=0)
    
    # Passing stats
    pass_attempts: int = Field(default=0)
    pass_completions: int = Field(default=0)
    pass_yards: int = Field(default=0)
    pass_td: int = Field(default=0)
    pass_int: int = Field(default=0)
    sacks: float = Field(default=0.0)
    sack_yards: int = Field(default=0)
    qb_hits: int = Field(default=0)
    pressures: int = Field(default=0)
    
    # Rushing stats
    rush_attempts: int = Field(default=0)
    rush_yards: int = Field(default=0)
    rush_td: int = Field(default=0)
    broken_tackles: int = Field(default=0)
    
    # Receiving stats
    targets: int = Field(default=0)
    receptions: int = Field(default=0)
    receiving_yards: int = Field(default=0)
    receiving_td: int = Field(default=0)
    yac: int = Field(default=0)
    
    # Defense stats
    tackles_solo: int = Field(default=0)
    tackles_assist: int = Field(default=0)
    tfl: int = Field(default=0)
    sacks_defense: float = Field(default=0.0)
    qb_hits_defense: int = Field(default=0)
    pressures_defense: int = Field(default=0)
    interceptions: int = Field(default=0)
    int_yards: int = Field(default=0)
    int_td: int = Field(default=0)
    pbus: int = Field(default=0)
    forced_fumbles: int = Field(default=0)
    fumble_recoveries: int = Field(default=0)
    fr_yards: int = Field(default=0)
    fr_td: int = Field(default=0)
    
    # Special teams
    kickoffs: int = Field(default=0)
    kickoff_touchbacks: int = Field(default=0)
    punts: int = Field(default=0)
    punt_yards: int = Field(default=0)
    punts_in_20: int = Field(default=0)
    punt_touchbacks: int = Field(default=0)
    punt_returns: int = Field(default=0)
    punt_return_yards: int = Field(default=0)
    punt_return_td: int = Field(default=0)
    kickoff_returns: int = Field(default=0)
    kickoff_return_yards: int = Field(default=0)
    kickoff_return_td: int = Field(default=0)
    
    # Kicking
    fg_attempts: int = Field(default=0)
    fg_made: int = Field(default=0)
    fg_yards: int = Field(default=0)
    xp_attempts: int = Field(default=0)
    xp_made: int = Field(default=0)
    
    # Turnovers
    fumbles: int = Field(default=0)
    fumbles_lost: int = Field(default=0)
    
    # Penalties
    penalties: int = Field(default=0)
    penalty_yards: int = Field(default=0)
    
    # Advanced metrics
    epa: float = Field(default=0.0)
    success_rate: float = Field(default=0.0)
    explosives: int = Field(default=0)
    third_down_conversions: int = Field(default=0)
    third_down_attempts: int = Field(default=0)
    
    # GDD v3.2 Stat Catalog Add-On Fields
    
    # Offensive Line fields
    sacks_allowed: float = Field(default=0.0, description="Sacks allowed (supports half-sacks)")
    hits_allowed: int = Field(default=0, description="QB hits allowed")
    pressures_allowed: int = Field(default=0, description="Pressures allowed")
    tfl_allowed: int = Field(default=0, description="Tackles for loss allowed")
    run_block_wins: int = Field(default=0, description="Successful run blocks")
    pass_block_wins: int = Field(default=0, description="Successful pass blocks")
    penalties_ol: int = Field(default=0, description="Offensive line penalties")
    
    # Enhanced Defense fields
    targets_faced: int = Field(default=0, description="Pass targets faced")
    completions_allowed: int = Field(default=0, description="Completions allowed")
    yards_allowed: int = Field(default=0, description="Yards allowed")
    yac_allowed: int = Field(default=0, description="YAC allowed")
    td_allowed: int = Field(default=0, description="Touchdowns allowed")
    passer_rating_against: float = Field(default=0.0, description="Passer rating against")
    missed_tackles: int = Field(default=0, description="Missed tackles")
    run_stops: int = Field(default=0, description="Run stops")
    
    # Enhanced Special Teams fields
    punt_net_avg: float = Field(default=0.0, description="Punt net average")
    hang_time_avg: float = Field(default=0.0, description="Average hang time (seconds)")
    kick_distance_avg: float = Field(default=0.0, description="Average kick distance")
    blocked_kicks: int = Field(default=0, description="Blocked kicks")
    return_avg: float = Field(default=0.0, description="Return average")
    return_td: int = Field(default=0, description="Return touchdowns")
    fair_catches: int = Field(default=0, description="Fair catches")
    
    # Situational splits
    fourth_down_conversions: int = Field(default=0)
    fourth_down_attempts: int = Field(default=0)
    red_zone_td: int = Field(default=0, description="Red zone touchdowns")
    red_zone_attempts: int = Field(default=0, description="Red zone attempts")
    goal_to_go_td: int = Field(default=0, description="Goal-to-go touchdowns")
    goal_to_go_attempts: int = Field(default=0, description="Goal-to-go attempts")
    two_minute_plays: int = Field(default=0, description="Two-minute drill plays")
    hurry_up_plays: int = Field(default=0, description="Hurry-up plays")
    garbage_time_excluded: int = Field(default=0, description="Garbage time plays excluded")
    
    # Derived properties (computed on materialize)
    @property
    def ypa(self) -> float:
        """Yards per attempt"""
        return self.pass_yards / max(1, self.pass_attempts)
    
    @property
    def ypc(self) -> float:
        """Yards per carry"""
        return self.rush_yards / max(1, self.rush_attempts)
    
    @property
    def ypr(self) -> float:
        """Yards per reception"""
        return self.receiving_yards / max(1, self.receptions)
    
    @property
    def completion_pct(self) -> float:
        """Completion percentage"""
        return (self.pass_completions / max(1, self.pass_attempts)) * 100
    
    @property
    def td_pct(self) -> float:
        """Touchdown percentage"""
        return (self.pass_td / max(1, self.pass_attempts)) * 100
    
    @property
    def int_pct(self) -> float:
        """Interception percentage"""
        return (self.pass_int / max(1, self.pass_attempts)) * 100
    
    @property
    def fg_pct(self) -> float:
        """Field goal percentage"""
        return (self.fg_made / max(1, self.fg_attempts)) * 100
    
    @property
    def xp_pct(self) -> float:
        """Extra point percentage"""
        return (self.xp_made / max(1, self.xp_attempts)) * 100
    
    @property
    def passer_rating(self) -> float:
        """NFL Passer Rating"""
        if self.pass_attempts == 0:
            return 0.0
        
        # NFL Passer Rating formula
        a = ((self.pass_completions / self.pass_attempts) - 0.3) * 5
        b = ((self.pass_yards / self.pass_attempts) - 3) * 0.25
        c = (self.pass_td / self.pass_attempts) * 20
        d = 2.375 - ((self.pass_int / self.pass_attempts) * 25)
        
        return max(0, min(158.3, (a + b + c + d) * 100 / 6))
    
    @property
    def third_down_pct(self) -> float:
        """Third down conversion percentage"""
        return (self.third_down_conversions / max(1, self.third_down_attempts)) * 100
    
    @property
    def explosives_rate(self) -> float:
        """Explosive plays rate"""
        total_plays = self.pass_attempts + self.rush_attempts + self.targets
        return (self.explosives / max(1, total_plays)) * 100
    
    @property
    def fourth_down_pct(self) -> float:
        """Fourth down conversion percentage"""
        return (self.fourth_down_conversions / max(1, self.fourth_down_attempts)) * 100
    
    @property
    def red_zone_td_pct(self) -> float:
        """Red zone touchdown percentage"""
        return (self.red_zone_td / max(1, self.red_zone_attempts)) * 100
    
    @property
    def goal_to_go_td_pct(self) -> float:
        """Goal-to-go touchdown percentage"""
        return (self.goal_to_go_td / max(1, self.goal_to_go_attempts)) * 100
    
    @property
    def two_minute_eff(self) -> float:
        """Two-minute drill efficiency"""
        return self.two_minute_plays / max(1, self.gp)
    
    @property
    def hurry_up_rate(self) -> float:
        """Hurry-up plays rate"""
        total_plays = self.pass_attempts + self.rush_attempts + self.targets
        return (self.hurry_up_plays / max(1, total_plays)) * 100

class TeamSeasonStats(SQLModel, table=True):
    """Team statistics aggregated for a season"""
    __tablename__ = "team_season_stats"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(index=True)
    season: int = Field(index=True)
    
    # Games
    gp: int = Field(default=0, description="Games played")
    
    # All other fields same as TeamGameStats but aggregated
    snaps_offense: int = Field(default=0)
    snaps_defense: int = Field(default=0)
    snaps_st: int = Field(default=0)
    
    # Offensive stats
    pass_attempts: int = Field(default=0)
    pass_completions: int = Field(default=0)
    pass_yards: int = Field(default=0)
    pass_td: int = Field(default=0)
    pass_int: int = Field(default=0)
    sacks_allowed: float = Field(default=0.0)
    sack_yards_allowed: int = Field(default=0)
    qb_hits_allowed: int = Field(default=0)
    pressures_allowed: int = Field(default=0)
    
    rush_attempts: int = Field(default=0)
    rush_yards: int = Field(default=0)
    rush_td: int = Field(default=0)
    
    total_yards: int = Field(default=0)
    total_td: int = Field(default=0)
    turnovers: int = Field(default=0)
    
    # Defensive stats
    tackles_solo: int = Field(default=0)
    tackles_assist: int = Field(default=0)
    tfl: int = Field(default=0)
    sacks: float = Field(default=0.0)
    qb_hits: int = Field(default=0)
    pressures: int = Field(default=0)
    interceptions: int = Field(default=0)
    int_yards: int = Field(default=0)
    int_td: int = Field(default=0)
    pbus: int = Field(default=0)
    forced_fumbles: int = Field(default=0)
    fumble_recoveries: int = Field(default=0)
    fr_yards: int = Field(default=0)
    fr_td: int = Field(default=0)
    
    # Special teams
    kickoffs: int = Field(default=0)
    kickoff_touchbacks: int = Field(default=0)
    punts: int = Field(default=0)
    punt_yards: int = Field(default=0)
    punts_in_20: int = Field(default=0)
    punt_touchbacks: int = Field(default=0)
    punt_returns: int = Field(default=0)
    punt_return_yards: int = Field(default=0)
    punt_return_td: int = Field(default=0)
    kickoff_returns: int = Field(default=0)
    kickoff_return_yards: int = Field(default=0)
    kickoff_return_td: int = Field(default=0)
    
    # Kicking
    fg_attempts: int = Field(default=0)
    fg_made: int = Field(default=0)
    fg_yards: int = Field(default=0)
    xp_attempts: int = Field(default=0)
    xp_made: int = Field(default=0)
    
    # Penalties
    penalties: int = Field(default=0)
    penalty_yards: int = Field(default=0)
    
    # Advanced metrics
    epa: float = Field(default=0.0)
    success_rate: float = Field(default=0.0)
    explosives: int = Field(default=0)
    third_down_conversions: int = Field(default=0)
    third_down_attempts: int = Field(default=0)
    
    # GDD v3.2 Stat Catalog Add-On Fields
    
    # Offensive Line fields
    run_block_wins: int = Field(default=0, description="Successful run blocks")
    pass_block_wins: int = Field(default=0, description="Successful pass blocks")
    penalties_ol: int = Field(default=0, description="Offensive line penalties")
    
    # Enhanced Defense fields
    targets_faced: int = Field(default=0, description="Pass targets faced")
    completions_allowed: int = Field(default=0, description="Completions allowed")
    yards_allowed: int = Field(default=0, description="Yards allowed")
    yac_allowed: int = Field(default=0, description="YAC allowed")
    td_allowed: int = Field(default=0, description="Touchdowns allowed")
    passer_rating_against: float = Field(default=0.0, description="Passer rating against")
    missed_tackles: int = Field(default=0, description="Missed tackles")
    run_stops: int = Field(default=0, description="Run stops")
    
    # Enhanced Special Teams fields
    punt_net_avg: float = Field(default=0.0, description="Punt net average")
    hang_time_avg: float = Field(default=0.0, description="Average hang time (seconds)")
    kick_distance_avg: float = Field(default=0.0, description="Average kick distance")
    blocked_kicks: int = Field(default=0, description="Blocked kicks")
    return_avg: float = Field(default=0.0, description="Return average")
    return_td: int = Field(default=0, description="Return touchdowns")
    fair_catches: int = Field(default=0, description="Fair catches")
    
    # Situational splits
    fourth_down_conversions: int = Field(default=0)
    fourth_down_attempts: int = Field(default=0)
    red_zone_td: int = Field(default=0, description="Red zone touchdowns")
    red_zone_attempts: int = Field(default=0, description="Red zone attempts")
    goal_to_go_td: int = Field(default=0, description="Goal-to-go touchdowns")
    goal_to_go_attempts: int = Field(default=0, description="Goal-to-go attempts")
    two_minute_plays: int = Field(default=0, description="Two-minute drill plays")
    hurry_up_plays: int = Field(default=0, description="Hurry-up plays")
    garbage_time_excluded: int = Field(default=0, description="Garbage time plays excluded")

class PlayerCareerStats(SQLModel, table=True):
    """Player statistics aggregated across entire career"""
    __tablename__ = "player_career_stats"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(index=True)
    
    # Career totals (same fields as PlayerSeasonStats)
    gp: int = Field(default=0)
    gs: int = Field(default=0)
    snaps_offense: int = Field(default=0)
    snaps_defense: int = Field(default=0)
    snaps_st: int = Field(default=0)
    
    # Passing stats
    pass_attempts: int = Field(default=0)
    pass_completions: int = Field(default=0)
    pass_yards: int = Field(default=0)
    pass_td: int = Field(default=0)
    pass_int: int = Field(default=0)
    sacks: float = Field(default=0.0)
    sack_yards: int = Field(default=0)
    qb_hits: int = Field(default=0)
    pressures: int = Field(default=0)
    
    # Rushing stats
    rush_attempts: int = Field(default=0)
    rush_yards: int = Field(default=0)
    rush_td: int = Field(default=0)
    broken_tackles: int = Field(default=0)
    
    # Receiving stats
    targets: int = Field(default=0)
    receptions: int = Field(default=0)
    receiving_yards: int = Field(default=0)
    receiving_td: int = Field(default=0)
    yac: int = Field(default=0)
    
    # Defense stats
    tackles_solo: int = Field(default=0)
    tackles_assist: int = Field(default=0)
    tfl: int = Field(default=0)
    sacks_defense: float = Field(default=0.0)
    qb_hits_defense: int = Field(default=0)
    pressures_defense: int = Field(default=0)
    interceptions: int = Field(default=0)
    int_yards: int = Field(default=0)
    int_td: int = Field(default=0)
    pbus: int = Field(default=0)
    forced_fumbles: int = Field(default=0)
    fumble_recoveries: int = Field(default=0)
    fr_yards: int = Field(default=0)
    fr_td: int = Field(default=0)
    
    # Special teams
    kickoffs: int = Field(default=0)
    kickoff_touchbacks: int = Field(default=0)
    punts: int = Field(default=0)
    punt_yards: int = Field(default=0)
    punts_in_20: int = Field(default=0)
    punt_touchbacks: int = Field(default=0)
    punt_returns: int = Field(default=0)
    punt_return_yards: int = Field(default=0)
    punt_return_td: int = Field(default=0)
    kickoff_returns: int = Field(default=0)
    kickoff_return_yards: int = Field(default=0)
    kickoff_return_td: int = Field(default=0)
    
    # Kicking
    fg_attempts: int = Field(default=0)
    fg_made: int = Field(default=0)
    fg_yards: int = Field(default=0)
    xp_attempts: int = Field(default=0)
    xp_made: int = Field(default=0)
    
    # Turnovers
    fumbles: int = Field(default=0)
    fumbles_lost: int = Field(default=0)
    
    # Penalties
    penalties: int = Field(default=0)
    penalty_yards: int = Field(default=0)
    
    # Advanced metrics
    epa: float = Field(default=0.0)
    success_rate: float = Field(default=0.0)
    explosives: int = Field(default=0)
    third_down_conversions: int = Field(default=0)
    third_down_attempts: int = Field(default=0)
    
    # GDD v3.2 Stat Catalog Add-On Fields
    
    # Offensive Line fields
    sacks_allowed: float = Field(default=0.0, description="Sacks allowed (supports half-sacks)")
    hits_allowed: int = Field(default=0, description="QB hits allowed")
    pressures_allowed: int = Field(default=0, description="Pressures allowed")
    tfl_allowed: int = Field(default=0, description="Tackles for loss allowed")
    run_block_wins: int = Field(default=0, description="Successful run blocks")
    pass_block_wins: int = Field(default=0, description="Successful pass blocks")
    penalties_ol: int = Field(default=0, description="Offensive line penalties")
    
    # Enhanced Defense fields
    targets_faced: int = Field(default=0, description="Pass targets faced")
    completions_allowed: int = Field(default=0, description="Completions allowed")
    yards_allowed: int = Field(default=0, description="Yards allowed")
    yac_allowed: int = Field(default=0, description="YAC allowed")
    td_allowed: int = Field(default=0, description="Touchdowns allowed")
    passer_rating_against: float = Field(default=0.0, description="Passer rating against")
    missed_tackles: int = Field(default=0, description="Missed tackles")
    run_stops: int = Field(default=0, description="Run stops")
    
    # Enhanced Special Teams fields
    punt_net_avg: float = Field(default=0.0, description="Punt net average")
    hang_time_avg: float = Field(default=0.0, description="Average hang time (seconds)")
    kick_distance_avg: float = Field(default=0.0, description="Average kick distance")
    blocked_kicks: int = Field(default=0, description="Blocked kicks")
    return_avg: float = Field(default=0.0, description="Return average")
    return_td: int = Field(default=0, description="Return touchdowns")
    fair_catches: int = Field(default=0, description="Fair catches")
    
    # Situational splits
    fourth_down_conversions: int = Field(default=0)
    fourth_down_attempts: int = Field(default=0)
    red_zone_td: int = Field(default=0, description="Red zone touchdowns")
    red_zone_attempts: int = Field(default=0, description="Red zone attempts")
    goal_to_go_td: int = Field(default=0, description="Goal-to-go touchdowns")
    goal_to_go_attempts: int = Field(default=0, description="Goal-to-go attempts")
    two_minute_plays: int = Field(default=0, description="Two-minute drill plays")
    hurry_up_plays: int = Field(default=0, description="Hurry-up plays")
    garbage_time_excluded: int = Field(default=0, description="Garbage time plays excluded")
    
    # Same derived properties as PlayerSeasonStats
    @property
    def ypa(self) -> float:
        return self.pass_yards / max(1, self.pass_attempts)
    
    @property
    def ypc(self) -> float:
        return self.rush_yards / max(1, self.rush_attempts)
    
    @property
    def ypr(self) -> float:
        return self.receiving_yards / max(1, self.receptions)
    
    @property
    def completion_pct(self) -> float:
        return (self.pass_completions / max(1, self.pass_attempts)) * 100
    
    @property
    def td_pct(self) -> float:
        return (self.pass_td / max(1, self.pass_attempts)) * 100
    
    @property
    def int_pct(self) -> float:
        return (self.pass_int / max(1, self.pass_attempts)) * 100
    
    @property
    def fg_pct(self) -> float:
        return (self.fg_made / max(1, self.fg_attempts)) * 100
    
    @property
    def xp_pct(self) -> float:
        return (self.xp_made / max(1, self.xp_attempts)) * 100
    
    @property
    def passer_rating(self) -> float:
        if self.pass_attempts == 0:
            return 0.0
        
        a = ((self.pass_completions / self.pass_attempts) - 0.3) * 5
        b = ((self.pass_yards / self.pass_attempts) - 3) * 0.25
        c = (self.pass_td / self.pass_attempts) * 20
        d = 2.375 - ((self.pass_int / self.pass_attempts) * 25)
        
        return max(0, min(158.3, (a + b + c + d) * 100 / 6))
    
    @property
    def third_down_pct(self) -> float:
        return (self.third_down_conversions / max(1, self.third_down_attempts)) * 100
    
    @property
    def explosives_rate(self) -> float:
        total_plays = self.pass_attempts + self.rush_attempts + self.targets
        return (self.explosives / max(1, total_plays)) * 100
    
    @property
    def fourth_down_pct(self) -> float:
        """Fourth down conversion percentage"""
        return (self.fourth_down_conversions / max(1, self.fourth_down_attempts)) * 100
    
    @property
    def red_zone_td_pct(self) -> float:
        """Red zone touchdown percentage"""
        return (self.red_zone_td / max(1, self.red_zone_attempts)) * 100
    
    @property
    def goal_to_go_td_pct(self) -> float:
        """Goal-to-go touchdown percentage"""
        return (self.goal_to_go_td / max(1, self.goal_to_go_attempts)) * 100
    
    @property
    def two_minute_eff(self) -> float:
        """Two-minute drill efficiency"""
        return self.two_minute_plays / max(1, self.gp)
    
    @property
    def hurry_up_rate(self) -> float:
        """Hurry-up plays rate"""
        total_plays = self.pass_attempts + self.rush_attempts + self.targets
        return (self.hurry_up_plays / max(1, total_plays)) * 100
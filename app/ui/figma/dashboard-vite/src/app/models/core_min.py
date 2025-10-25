from typing import Optional
from sqlmodel import SQLModel, Field

class Team(SQLModel, table=True):
    __tablename__ = "core_teams"
    id: Optional[int] = Field(default=None, primary_key=True)
    abbrev: str
    name: str
    points: int = 0  # scoreboard total (season-level convenience)

class Game(SQLModel, table=True):
    __tablename__ = "core_games"
    id: Optional[int] = Field(default=None, primary_key=True)
    season: int
    week: int
    home_team_id: int
    away_team_id: int

class TeamGame(SQLModel, table=True):
    __tablename__ = "core_team_games"
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int
    team_id: int
    is_home: bool = False
    points: int = 0
    fga: int = 0
    fgm: int = 0
    punts: int = 0
    yards_total: int = 0
    sacks_def: int = 0

class Player(SQLModel, table=True):
    __tablename__ = "players"
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: Optional[int] = None
    pos: str                      # canonical
    name: str
    first_name: str = ""
    last_name: str = ""
    rating: int = 60
    kicker_power: float = 0.5
    kicker_base_40_49: float = 0.82
    
    # Progression attributes (required for progression system)
    awareness: int = 50
    speed: int = 50
    strength: int = 50
    agility: int = 50
    throw_power: int = 50
    throw_accuracy: int = 50
    catching: int = 50
    tackling: int = 50
    stamina: int = 50
    morale: int = 50
    
    # Additional progression-related attributes
    age: int = 25
    years_pro: int = 0
    potential: int = 50
    injury_proneness: int = 50
    
    # Rookie flags
    is_rookie: bool = False
    rookie_season: Optional[int] = None
    
    # Contract demand fields
    desired_years: int = Field(default=3)
    desired_aav: int = Field(default=5_000_000)  # per-year ask
    trade_block: bool = Field(default=False, index=True)
    cap_hit_current: int = 0  # computed from active contract; persisted for quick UI

    # ---- Compatibility aliases (do NOT create new columns) ----
    @property
    def position(self) -> str:    # legacy code reads .position
        return self.pos
    @position.setter
    def position(self, v: str):   # legacy code sets .position
        self.pos = v

    @property
    def full_name(self) -> str:   # sometimes legacy uses full_name
        return self.name
    @full_name.setter
    def full_name(self, v: str):
        self.name = v
    
    @property
    def overall(self) -> int:     # legacy code reads .overall
        return self.rating
    @overall.setter
    def overall(self, v: int):    # legacy code sets .overall
        self.rating = v

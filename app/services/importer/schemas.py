from typing import Optional, Literal
from pydantic import BaseModel, field_validator

# Allowed positions
POSITIONS = [
    "QB","RB","WR","TE","OL","DL","LB","CB","S","K","P","LS"
]

class TeamIn(BaseModel):
    location_name: str
    nickname: str
    conference: str
    division: str
    power_rating: int
    cap_space: int

    @property
    def natural_key(self) -> tuple[str, str]:
        return (self.location_name.strip(), self.nickname.strip())

class PlayerIn(BaseModel):
    first_name: str
    last_name: str
    position: Literal["QB","RB","WR","TE","OL","DL","LB","CB","S","K","P","LS"]
    jersey: int
    age: int
    salary: int
    contract_years: int
    team_key: str  # "location|nickname"

    # Ratings 0..100
    speed: int
    strength: int
    agility: int
    throw_power: int
    throw_accuracy: int
    catching: int
    tackling: int
    awareness: int
    potential: int
    stamina: int
    injury_proneness: int  # 0 good, 100 fragile
    morale: int

    @field_validator("age")
    @classmethod
    def age_ok(cls, v: int) -> int:
        if v < 18:
            raise ValueError("age must be >= 18")
        return v

    @field_validator(
        "speed","strength","agility","throw_power","throw_accuracy",
        "catching","tackling","awareness","potential","stamina",
        "injury_proneness","morale"
    )
    @classmethod
    def rating_0_100(cls, v: int) -> int:
        if not (0 <= v <= 100):
            raise ValueError("rating fields must be in 0..100")
        return v

class DepthChartIn(BaseModel):
    team_key: str  # "location|nickname"
    position: Literal["QB","RB","WR","TE","OL","DL","LB","CB","S","K","P","LS"]
    starter_jersey: int
    backup_jersey: Optional[int] = None

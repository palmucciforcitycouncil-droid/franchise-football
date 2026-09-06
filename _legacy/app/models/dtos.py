from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict

# --- Team DTO ---
class TeamDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    location_name: str
    nickname: str
    conference: str
    division: str
    power_rating: int
    cap_space: int

# --- Player DTO ---
class PlayerDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    team_id: Optional[int]
    first_name: str
    last_name: str
    position: str
    jersey: int
    age: int
    salary: int
    contract_years: int
    # Ratings
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
    injury_proneness: int
    morale: int

# --- Depth Chart DTO ---
class DepthChartDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    team_id: int
    position: str
    starter_player_id: Optional[int]
    backup_player_id: Optional[int]

# --- Game Result DTO ---
class GameResultDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    week: int
    season: int
    home_team_id: int
    away_team_id: int
    winner_team_id: Optional[int]
    home_score: int
    away_score: int

# --- User Profile DTO ---
class UserProfileDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    display_name: str
    preferred_team_id: Optional[int]

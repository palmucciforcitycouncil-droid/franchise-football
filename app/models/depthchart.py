"""
Depth Chart Models and DTOs
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, UniqueConstraint

class DepthChartEntry(SQLModel, table=True):
    """SQLModel table for depth chart entries"""
    __tablename__ = "depth_chart_entries"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: str = Field(index=True)
    season: int = Field(index=True)
    position: str = Field(index=True)
    slot: str = Field(index=True)
    player_id: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("team_id", "season", "slot", name="unique_team_season_slot"),
    )

class DepthSlotDTO(BaseModel):
    """Individual depth chart slot"""
    position: str
    slot: str
    player_id: Optional[int] = None
    name: Optional[str] = None
    ovr: Optional[int] = None
    
    class Config:
        json_encoders = {
            # Add any custom encoders if needed
        }

class DepthChartDTO(BaseModel):
    """Complete depth chart for a team"""
    team_id: str
    season: int
    slots: List[DepthSlotDTO]
    warnings: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class AutoFillRequestDTO(BaseModel):
    """Request body for auto-fill depth chart"""
    season: int

class AutoFillResponseDTO(BaseModel):
    """Response from auto-fill operation"""
    success: bool
    message: str
    depth_chart: Optional[DepthChartDTO] = None

class DepthSlotUpdateDTO(BaseModel):
    """Request body for updating a single slot"""
    season: int
    position: str
    slot: str
    player_id: Optional[int] = None

class DepthChartBulkUpdateDTO(BaseModel):
    """Request body for bulk updating depth chart"""
    season: int
    slots: List[DepthSlotUpdateDTO]

# Depth chart slot definitions per position group (MVP)
DEPTH_CHART_SLOTS = {
    "QB": ["QB1", "QB2"],
    "RB": ["RB1", "RB2"],
    "WR": ["WR1", "WR2", "WR3"],
    "TE": ["TE1", "TE2"],
    "LT": ["LT"],
    "LG": ["LG"],
    "C": ["C"],
    "RG": ["RG"],
    "RT": ["RT"],
    "LDE": ["LDE"],
    "DT": ["DT"],
    "RDE": ["RDE"],
    "MLB": ["MLB1", "MLB2"],
    "OLB": ["OLB1", "OLB2"],
    "CB": ["CB1", "CB2", "CB3"],
    "FS": ["FS"],
    "SS": ["SS"],
    "K": ["K"],
    "P": ["P"],
    "KR": ["KR1", "KR2"],
    "PR": ["PR1", "PR2"]
}

# Position groups for duplicate prevention
POSITION_GROUPS = {
    "QB": ["QB1", "QB2"],
    "RB": ["RB1", "RB2"],
    "WR": ["WR1", "WR2", "WR3"],
    "TE": ["TE1", "TE2"],
    "LT": ["LT"],
    "LG": ["LG"],
    "C": ["C"],
    "RG": ["RG"],
    "RT": ["RT"],
    "LDE": ["LDE"],
    "DT": ["DT"],
    "RDE": ["RDE"],
    "MLB": ["MLB1", "MLB2"],
    "OLB": ["OLB1", "OLB2"],
    "CB": ["CB1", "CB2", "CB3"],
    "FS": ["FS"],
    "SS": ["SS"],
    "K": ["K"],
    "P": ["P"],
    "KR": ["KR1", "KR2"],
    "PR": ["PR1", "PR2"]
}

def group_for_slot(slot: str) -> str:
    """Map a slot to its position group for duplicate prevention"""
    for group, slots in POSITION_GROUPS.items():
        if slot in slots:
            return group
    return slot  # fallback to slot itself if not found

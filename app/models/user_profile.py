from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field

class UserProfile(SQLModel, table=True):
    __tablename__ = "user_profile"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Minimal identity fields (kept generic so tests won't choke)
    display_name: str = Field(index=True)
    email: Optional[str] = None

    # Optional affinity to a team (safe FK)
    favorite_team_id: Optional[int] = Field(default=None, foreign_key="team.id", index=True)

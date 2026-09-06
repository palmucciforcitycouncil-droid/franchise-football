from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class UserProfile(SQLModel, table=True):
    """
    Minimal user profile model required by tests.
    Kept additive-only to avoid impacting game systems.
    """
    __tablename__ = "user_profiles"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Common identity fields
    username: str = Field(index=True, sa_column_kwargs={"unique": True})
    email: Optional[str] = Field(default=None, index=True)
    display_name: Optional[str] = Field(default=None)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)

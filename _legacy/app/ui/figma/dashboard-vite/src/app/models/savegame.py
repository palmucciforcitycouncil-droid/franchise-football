# app/models/savegame.py
from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field, UniqueConstraint

class SaveGameAudit(SQLModel, table=True):
    __tablename__ = "savegame_audit"
    __table_args__ = (UniqueConstraint("save_name", name="uq_save_name"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    save_name: str = Field(index=True)
    schema_version: str = Field(index=True)
    season: Optional[int] = Field(default=None, index=True)
    sha256: str = Field(index=True)
    bytes_size: int = 0
    objects_count: int = 0
    notes: Optional[str] = None

from __future__ import annotations
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    database_url: str = Field("sqlite:///franchise.db", alias="DATABASE_URL")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    default_seed: int = Field(2025, alias="DEFAULT_SEED")
    gdd_version: str = Field("2.15", alias="GDD_VERSION")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

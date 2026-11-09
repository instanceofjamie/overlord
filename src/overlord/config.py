# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OVERLORD_", env_file=".env", extra="ignore")

    database_path: Path = Path("var/overlord.sqlite3")
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    provider: Literal["mock"] = "mock"

    response_cooldown_seconds: int = Field(default=15, ge=0, le=3600)

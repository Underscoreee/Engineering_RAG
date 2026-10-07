"""Basic application configuration without external service connections."""

import os
from typing import Literal

from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """Settings for the local application runtime."""

    environment: str = Field(default="development", min_length=1)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


def load_config() -> AppConfig:
    """Load basic settings from environment variables, falling back to defaults."""

    return AppConfig(
        environment=os.getenv("ENGINEERING_RAG_ENV", "development"),
        log_level=os.getenv("ENGINEERING_RAG_LOG_LEVEL", "INFO").upper(),
    )

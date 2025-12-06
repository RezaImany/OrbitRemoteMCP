"""Configuration model for OrbitRemoteMCP."""

from __future__ import annotations

import os
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="ORBIT_", case_sensitive=False, extra="ignore")

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    server_name: str = Field(default="orbit-remote-mcp")

    require_auth: bool = Field(default=True)
    auth_key: Optional[str] = Field(default=None)
    allowed_origins: List[str] = Field(default_factory=lambda: ["*"])

    rate_limit: int = Field(default=60, description="Max requests per minute per client.")
    max_body_bytes: int = Field(default=1_048_576, description="Request body limit in bytes.")
    session_ttl_seconds: int = Field(default=1800)

    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=False)

    # Empty list means: auto-discover everything in orbit_remote_mcp.tools/resources
    modules: List[str] = Field(default_factory=list)

    openweather_api_key: Optional[str] = Field(default=None, alias="OPENWEATHER_API_KEY")
    openweather_base_url: str = Field(
        default="https://api.openweathermap.org/data/2.5", alias="OPENWEATHER_BASE_URL"
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return ["*"]

    @field_validator("modules", mode="before")
    @classmethod
    def split_modules(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [module.strip() for module in value.split(",") if module.strip()]
        return []

    @classmethod
    def from_cli(cls, **overrides: object) -> "Settings":
        """Create settings merging environment with CLI overrides."""
        env_settings = cls()
        return env_settings.model_copy(update={k: v for k, v in overrides.items() if v is not None})

    @classmethod
    def raw_env(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        """Helper to fetch raw environment variables (case-insensitive)."""
        return os.getenv(key) or os.getenv(key.lower()) or default

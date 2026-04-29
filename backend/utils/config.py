from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Core credentials
    anthropic_api_key: str = ""
    tavily_api_key: str = ""

    # Infrastructure
    database_url: str = "postgresql://veris:veris@localhost:5433/veris"
    mlflow_tracking_uri: str = "http://localhost:5050"
    otel_exporter_endpoint: str = "http://localhost:4317"
    environment: str = "development"
    testing: bool = False

    # Model overrides — empty means use the default routing table
    # TODO(2026-04-25): verify model IDs at https://docs.anthropic.com/en/docs/models-overview
    veris_model_plan: str = ""
    veris_model_search: str = ""
    veris_model_reason: str = ""
    veris_model_verify: str = ""
    veris_model_answer: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

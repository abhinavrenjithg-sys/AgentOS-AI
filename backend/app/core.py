from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")
    database_url: str = "sqlite:///./agentos.db"
    artifact_dir: str = "./artifacts"
    max_research_urls: int = 5
    app_env: str = "development"
    openai_base_url: str = ""
    openai_api_key: str = ""
    openai_model: str = ""
    frontend_origin: str = "http://localhost:5173"

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value


settings = Settings()
Path(settings.artifact_dir).mkdir(parents=True, exist_ok=True)

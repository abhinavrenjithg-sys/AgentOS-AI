from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")
    database_url: str = "sqlite:///./agentos.db"
    artifact_dir: str = "./artifacts"
    max_research_urls: int = 5
    openai_base_url: str = ""
    openai_api_key: str = ""
    openai_model: str = ""
    frontend_origin: str = "http://localhost:5173"


settings = Settings()
Path(settings.artifact_dir).mkdir(parents=True, exist_ok=True)

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Project X Social Copilot"
    app_env: str = "development"
    database_url: str = f"sqlite:///{(PROJECT_ROOT / 'data' / 'project_x.db').as_posix()}"
    frontend_origin: str = "http://127.0.0.1:5173"
    inference_provider: str = "template"
    inference_base_url: str = ""
    inference_api_key: str = ""
    inference_model: str = ""
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    x_client_id: str = ""
    x_client_secret: str = ""
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_jwt_secret: str = ""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


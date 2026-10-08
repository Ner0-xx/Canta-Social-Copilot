from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Project X Social Copilot"
    app_env: str = "development"
    database_url: str = f"sqlite:///{(PROJECT_ROOT / 'data' / 'project_x.db').as_posix()}"
    backend_base_url: str = "http://127.0.0.1:8000"
    frontend_origin: str = "http://127.0.0.1:5173,http://localhost:5173"
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
    supabase_jwks_url: str = ""
    x_refresh_token_encryption_key: str = ""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ctf-search"
    app_env: str = "development"
    backend_debug: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "sqlite:///./ctf-search.db"
    redis_url: str = "redis://localhost:6379/0"
    admin_api_token: str = "change-me"
    admin_username: str = "admin"
    admin_password: str | None = None
    admin_session_cookie_name: str = "ctf_search_session"
    admin_session_ttl_hours: int = 24 * 7
    admin_session_pepper: str = Field(default="change-me-admin-session", min_length=8)
    data_dir: Path = Path("/data")
    attachment_dir: Path = Path("/data/attachments")
    import_dir: Path = Path("/data/imports")
    model_dir: Path = Path("/models")
    embedding_provider: str = "fake"
    embedding_model_path: Path = Path("/models/embedding-model")
    embedding_dimension: int = 384
    reranker_enabled: bool = False
    reranker_model_path: Path = Path("/models/reranker-model")
    queue_eager: bool = False
    max_upload_bytes: int = 20 * 1024 * 1024
    max_attachment_bytes: int = 10 * 1024 * 1024
    max_extracted_archive_bytes: int = 50 * 1024 * 1024
    agent_token_pepper: str = Field(default="change-me", min_length=8)
    next_public_api_base: str = "http://localhost:8000"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

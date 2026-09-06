"""Environment-backed application configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    app_name: str = "Pulse"
    app_env: str = "development"
    debug: bool = False
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/pulse"
    auto_create_tables: bool = False
    auto_migrate: bool = False
    jwt_secret_key: str = "replace-this-before-deployment"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    market_data_provider: str = "twelve_data"
    market_data_api_key: str = ""
    market_data_base_url: str = "https://www.alphavantage.co/query"
    market_data_timeout_seconds: float = 10.0
    market_data_max_age_seconds: int = 300
    twelve_data_api_key: str = ""
    twelve_data_base_url: str = "https://api.twelvedata.com"
    twelve_data_timeout_seconds: float = 10.0
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "openai/gpt-oss-20b"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Return one immutable settings instance per process."""
    return Settings()


def get_cors_origins() -> list[str]:
    """Convert the comma-separated environment setting to middleware origins."""
    return [origin.strip() for origin in get_settings().cors_origins.split(",") if origin.strip()]

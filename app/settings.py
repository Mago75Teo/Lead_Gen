import os
from pydantic_settings import BaseSettings, SettingsConfigDict


def _is_vercel() -> bool:
    # Vercel sets VERCEL=1 and usually also VERCEL_ENV
    return os.getenv("VERCEL") == "1" or bool(os.getenv("VERCEL_ENV"))


def _default_telemetry_db_path() -> str:
    """Choose a writable default path for telemetry.

    On serverless platforms the project directory is typically read-only.
    /tmp is writable on Vercel and AWS Lambda.
    """
    if _is_vercel():
        return os.getenv("TELEMETRY_DB_PATH", "/tmp/telemetry.sqlite")
    return os.getenv("TELEMETRY_DB_PATH", "data/telemetry.sqlite")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "dev"
    APP_PORT: int = 8000
    FOCUS_CONFIG_PATH: str = "config/focus.yaml"
    API_BEARER_TOKEN: str | None = None

    # Providers
    SERPER_API_KEY: str | None = None
    NEWSAPI_KEY: str | None = None
    OPENCORPORATES_API_KEY: str | None = None

    HUNTER_API_KEY: str | None = None
    EMAIL_VERIFY_PROVIDER: str | None = None
    EMAIL_VERIFY_API_KEY: str | None = None

    # LLM
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Perplexity (optional)
    PERPLEXITY_API_KEY: str | None = None

    # Telemetry
    TELEMETRY_DB_PATH: str = _default_telemetry_db_path()
    TELEMETRY_SALT: str = "change_me"


settings = Settings()

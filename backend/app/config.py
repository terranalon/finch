"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Database
    database_url: str = "postgresql://portfolio_user:dev_password@localhost:5432/portfolio_tracker"

    # API Keys
    exchange_rate_api_key: str = ""
    coingecko_api_key: str = ""

    # IBKR Flex Web Service
    ibkr_flex_token: str = ""
    ibkr_flex_query_id: str = ""

    # TASE Data Hub API (for Israeli securities mapping)
    tase_api_key: str = ""
    tase_api_url: str = "https://datawise.tase.co.il/v1"

    # Authentication
    jwt_secret_key: str = "change-me-in-production"  # Generate with: openssl rand -hex 32
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"

    # Application
    log_level: str = "INFO"
    debug: bool = True

    # CORS
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


settings = Settings()

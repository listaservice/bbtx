from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = Field(
        default="postgresql://betix:betix_dev_pass@localhost:5432/betix_dev",
        description="PostgreSQL Database URL"
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for caching and sessions"
    )

    # Encryption (for Betfair credentials in DB)
    encryption_key: str = Field(
        default="",
        description="32-byte encryption key for sensitive data (Fernet)"
    )

    # JWT Authentication
    jwt_secret: str = Field(
        default="dev-jwt-secret-key-change-in-production",
        description="JWT Secret Key"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT Algorithm")
    jwt_expire_minutes: int = Field(default=1440, description="JWT Token expiration (minutes)")

    # Stripe
    stripe_secret_key: str = Field(default="", description="Stripe Secret Key")
    stripe_publishable_key: str = Field(default="", description="Stripe Publishable Key")
    stripe_webhook_secret: str = Field(default="", description="Stripe Webhook Secret")

    # Betfair API (Master - for testing only, users will have their own)
    betfair_app_key: str = Field(default="", description="Betfair Application Key")
    betfair_username: str = Field(default="", description="Betfair Username")
    betfair_password: str = Field(default="", description="Betfair Password")
    betfair_cert_path: str = Field(default="./certs/betfair.crt", description="Path to Betfair SSL Certificate")
    betfair_key_path: str = Field(default="./certs/betfair.key", description="Path to Betfair SSL Key")

    # Google Sheets
    google_sheets_credentials_path: str = Field(
        default="./credentials/google_service_account.json",
        description="Path to Google Service Account JSON"
    )
    google_sheets_spreadsheet_id: str = Field(default="", description="Google Sheets Spreadsheet ID (legacy)")

    # Bot Configuration
    bot_timezone: str = Field(default="Europe/Bucharest", description="Timezone for bot execution")
    bot_run_hour: int = Field(default=13, ge=0, le=23, description="Hour to run bot (0-23)")
    bot_run_minute: int = Field(default=0, ge=0, le=59, description="Minute to run bot (0-59)")
    bot_initial_stake: float = Field(default=10.0, gt=0, description="Initial stake in RON")
    bot_max_progression_steps: int = Field(default=7, ge=1, le=20, description="Maximum progression steps before stop loss")

    # Server
    api_host: str = Field(default="127.0.0.1", description="API Host")
    api_port: int = Field(default=8000, description="API Port")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        description="Comma-separated list of allowed CORS origins"
    )

    # Legacy Authentication (Dashboard)
    auth_username: str = Field(default="admin", description="Dashboard username")
    auth_password: str = Field(default="admin123", description="Dashboard password")

    # Claude AI
    anthropic_api_key: str = Field(default="", description="Anthropic API Key")

    # Development
    debug: bool = Field(default=True, description="Debug mode")
    environment: str = Field(default="development", description="Environment (development/production)")

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env


@lru_cache
def get_settings() -> Settings:
    return Settings()

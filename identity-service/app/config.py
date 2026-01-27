"""Application configuration management"""

import logging
import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the project root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(BASE_DIR, ".env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    app_name: str = "Identity Service"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 4320  # 3 days
    refresh_token_expire_days: int = 7
    password_reset_token_expire_hours: int = 1

    # Email (for password reset notifications)
    email_enabled: bool = True
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@example.com"
    smtp_from_name: str = "Identity Service"

    # CORS
    cors_origins: str = "http://localhost:3000"
    cors_allow_credentials: bool = True

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, case_sensitive=False, extra="ignore"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()

# Debug: Print loaded settings
logger = logging.getLogger(__name__)
logger.info("=" * 60)
logger.info("Configuration Loaded")
logger.info("=" * 60)
logger.info(f"Config file path: {ENV_FILE}")
logger.info(f"Config file exists: {os.path.exists(ENV_FILE)}")
logger.info(f"Environment: {settings.environment}")
logger.info(f"Debug mode: {settings.debug}")
logger.info(f"Email enabled: {settings.email_enabled}")
logger.info(f"SMTP host: {settings.smtp_host}")
logger.info(f"SMTP port: {settings.smtp_port}")
logger.info(
    f"SMTP username: {settings.smtp_username if settings.smtp_username else 'NOT SET'}"
)
logger.info(
    f"SMTP password: {'SET (length: ' + str(len(settings.smtp_password)) + ')' if settings.smtp_password else 'NOT SET'}"
)
logger.info(f"SMTP from email: {settings.smtp_from_email}")
logger.info(f"SMTP from name: {settings.smtp_from_name}")
logger.info("=" * 60)

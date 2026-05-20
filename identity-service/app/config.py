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
    remember_me_access_token_expire_days: int = 30  # 30 days for remember me
    remember_me_refresh_token_expire_days: int = 90  # 90 days for remember me
    password_reset_token_expire_hours: int = 1
    # Cooldown (in seconds) between password-reset emails for the same account.
    # Within this window the back-end silently skips issuing a new token and
    # sending a new email. Override via the PASSWORD_RESET_COOLDOWN_SECONDS env
    # var (e.g. set to 60 in development for faster iteration).
    password_reset_cooldown_seconds: int = 2 * 60
    password_reset_url: str = "http://localhost:4200/reset-password"
    invitation_url: str = "http://localhost:4200/accept-invitation"

    # Cookie Settings
    cookie_secure: bool = False  # Set to True in production (requires HTTPS)
    cookie_samesite: str = "lax"  # "lax", "strict", or "none"
    cookie_httponly: bool = True  # Prevent JavaScript access

    # Billing Defaults (configurable via env vars)
    default_trial_days: int = 30
    default_billing_cycle: str = "monthly"  # monthly, quarterly, yearly
    default_max_users: int = 10
    default_max_credits: int = 1000
    cookie_domain: str | None = None  # Set to your domain in production

    # Email (for password reset notifications)
    email_enabled: bool = True
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@example.com"
    smtp_from_name: str = "Identity Service"
    smtp_validate_certs: bool = True

    # CORS
    cors_origins: str = "http://localhost:3000"
    cors_allow_credentials: bool = True

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # Logging
    log_level: str = "INFO"

    # Core Service Integration
    core_service_url: str = "http://localhost:8001"
    core_service_timeout: int = 10  # seconds
    enable_auto_chart_creation: bool = True
    chart_creation_retry_attempts: int = 3

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

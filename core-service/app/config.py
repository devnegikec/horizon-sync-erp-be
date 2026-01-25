"""Application configuration management"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the project root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(BASE_DIR, ".env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    app_name: str = "Core Service"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8001

    # Database (shared with identity-service)
    database_url: str
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # Security (must match identity-service for JWT validation)
    secret_key: str
    algorithm: str = "HS256"

    # Identity Service URL (for auth validation and permissions)
    identity_service_url: str = "http://identity-service:8000"

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

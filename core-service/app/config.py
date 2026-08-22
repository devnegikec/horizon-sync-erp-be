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

    # Database (core-service's own database)
    database_url: str
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # Identity Service Database (for seeding - read-only access)
    identity_database_url: str = ""

    # Security (must match identity-service for JWT validation)
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # WMS Worker token (for mobile scanner sessions — long-lived)
    wms_worker_token_expire_hours: int = 20

    # Identity Service URL (for auth validation and permissions)
    identity_service_url: str = "http://identity-service:8000"

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:4200"
    cors_allow_credentials: bool = True

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # Logging
    log_level: str = "INFO"

    # Redis (for event publishing to search-service)
    redis_url: str = "redis://redis:6379/0"
    redis_stream_name: str = "search:events"

    # Redis — 3D Warehouse real-time events (separate DB index for isolation)
    redis_warehouse_url: str = "redis://redis:6379/1"
    redis_warehouse_stream_name: str = "warehouse:3d:events"
    redis_warehouse_stream_maxlen: int = 5000  # Trim stream to keep demo memory bounded

    # Bin reservation global TTL (seconds); configurable via env var
    bin_reservation_ttl_seconds: int = 300  # 5 minutes default (FR-CW-02)

    # Durable QR Block generation worker
    celery_broker_url: str = ""
    celery_qr_queue_name: str = "qr-generation"
    celery_visibility_timeout_seconds: int = 7200

    # Audit Trail
    audit_async_enabled: bool = False
    audit_flush_interval: float = 1.0
    audit_batch_size: int = 50

    # Brand Key Encryption (ECDSA private key encryption at rest)
    brand_key_encryption_secret: str = "3GQ2g9v0Qm1x3vJm9q0c8sQ2xJ5xv9k8aYv4lq3n2hA="

    # QR Domain & object storage
    qr_domain: str = "horizon.ciphercode.ai"
    qr_base_url: str = ""
    qr_shortener_enabled: bool = True
    qr_shortener_url: str = "https://de5be4rdmboho.cloudfront.net/prod/"
    qr_shortener_cdn_prefix: str = "bwqr.me"
    qr_shortener_timeout_seconds: float = 10.0
    qr_shortener_max_retries: int = 3
    # Configure a trusted/self-hosted provider explicitly. Browser GPS must not
    # be disclosed to a third party merely by deploying the application.
    reverse_geocoding_url: str = ""
    reverse_geocoding_timeout_seconds: float = 4.0
    aws_s3_bucket: str = ""
    aws_s3_region: str = "ap-south-1"
    aws_s3_endpoint_url: str = ""
    aws_s3_presigned_expiry_seconds: int = 300
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""
    gcs_bucket: str = ""
    gcs_credentials_path: str = ""  # Path to service account JSON; empty = ADC
    product_image_upload_dir: str = os.path.join(
        BASE_DIR, "uploads", "product-images"
    )
    product_image_max_bytes: int = 5 * 1024 * 1024

    # Upload directory for local file storage (e.g. Railway volume mount)
    # Defaults to <project_root>/uploads/landing-pages when empty
    upload_dir: str = ""

    # Email/SMTP Configuration
    email_enabled: bool = True
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@example.com"
    smtp_from_name: str = "Horizon Sync ERP"
    smtp_validate_certs: bool = True

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, case_sensitive=False, extra="ignore"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()

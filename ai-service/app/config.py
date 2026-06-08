"""AI Service configuration"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """AI service settings loaded from environment variables"""

    # Service
    APP_NAME: str = "ai-service"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8003

    # Database (reuses existing Postgres; optional for Phase 1)
    DATABASE_URL: str = "postgresql://horizon_user:horizon_pass@localhost:5432/ai_db"

    # Core Service integration
    CORE_SERVICE_URL: str = "http://localhost:8001"
    CORE_SERVICE_TIMEOUT: int = 10

    # Identity Service integration
    IDENTITY_SERVICE_URL: str = "http://localhost:8000"
    IDENTITY_SERVICE_TIMEOUT: int = 10

    # Service-to-service auth (client-credentials for machine-to-machine JWT)
    SERVICE_CLIENT_ID: str = "ai-service"
    SERVICE_CLIENT_SECRET: str = ""

    # LLM (configure for OpenAI, Anthropic, or local Ollama)
    LLM_PROVIDER: str = "openai"  # openai | anthropic | ollama
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.3"

    # Embeddings (for RAG / SOP Copilot)
    EMBEDDING_PROVIDER: str = "openai"  # openai | ollama
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMENSIONS: int = 1536  # text-embedding-3-small = 1536, nomic = 768

    # RAG Settings
    RAG_TOP_K: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.75

    # MCP Server
    MCP_SERVER_NAME: str = "horizon-wms-mcp"
    MCP_SERVER_VERSION: str = "1.0.0"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

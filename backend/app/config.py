from pathlib import Path

from pydantic_settings import BaseSettings

# Load .env from project root (parent of backend/) when present
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/cursor_for_pms"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # JWT
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # Slack (Phase 2)
    slack_client_id: str = ""
    slack_client_secret: str = ""
    slack_signing_secret: str = ""

    # CSV ingestion
    max_sync_csv_rows: int = 500
    max_csv_file_size_mb: int = 10
    csv_temp_dir: str | None = None  # optional; default to system temp if unset

    # Encryption (Fernet) for Slack tokens etc.
    encryption_key: str = ""

    # App
    environment: str = "development"
    debug: bool = True
    backend_port: int = 8000
    frontend_port: int = 3000
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # LLM (Phase 3)
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2:3b"
    anthropic_api_key: str = ""
    anthropic_extraction_model: str = "claude-haiku-4-5-20251001"
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 1

    # Phase 5: Embedding and clustering
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    hdbscan_min_cluster_size: int = 3
    hdbscan_min_samples: int = 2
    recluster_threshold: int = 50

    model_config = {"env_file": _env_path if _env_path.exists() else None, "extra": "ignore"}


settings = Settings()

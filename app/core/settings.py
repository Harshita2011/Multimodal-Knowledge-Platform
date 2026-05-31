import logging
import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="rag", alias="APP_NAME")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    cors_allow_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000", alias="CORS_ALLOW_ORIGINS")
    database_url: str = Field(default="sqlite+aiosqlite:///./data/app.db", alias="DATABASE_URL")
    auth_required_for_core_routes: bool = Field(default=False, alias="AUTH_REQUIRED_FOR_CORE_ROUTES")

    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")

    embedding_model: str = Field(default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")
    embedding_batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE")

    chroma_persist_dir: Path = Field(default=Path("./data/chroma"), alias="CHROMA_PERSIST_DIR")
    vector_collection_name: str = Field(default="documents", alias="VECTOR_COLLECTION_NAME")

    pdf_storage_dir: Path = Field(default=Path("./data/documents"), alias="PDF_STORAGE_DIR")

    chunk_size: int = Field(default=800, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=120, alias="CHUNK_OVERLAP")

    top_k_default: int = Field(default=5, alias="TOP_K_DEFAULT")
    min_retrieval_score: float = Field(default=0.0, alias="MIN_RETRIEVAL_SCORE")
    max_context_chars: int | None = Field(default=12000, alias="MAX_CONTEXT_CHARS")
    max_context_tokens: int | None = Field(default=6000, alias="MAX_CONTEXT_TOKENS")
    max_prompt_tokens: int | None = Field(default=8000, alias="MAX_PROMPT_TOKENS")
    reserved_response_tokens: int | None = Field(default=1500, alias="RESERVED_RESPONSE_TOKENS")
    tokenizer_strict: bool = Field(default=False, alias="TOKENIZER_STRICT")
    max_file_size_mb: int = Field(default=25, alias="MAX_FILE_SIZE_MB")

    enable_debug_retrieval: bool = Field(default=True, alias="ENABLE_DEBUG_RETRIEVAL")
    enable_reranking: bool = Field(default=False, alias="ENABLE_RERANKING")
    rerank_top_n: int = Field(default=8, alias="RERANK_TOP_N")
    retrieval_near_duplicate_threshold: float = Field(default=0.94, alias="RETRIEVAL_NEAR_DUPLICATE_THRESHOLD")
    duplicate_similarity_threshold: float = Field(default=0.90, alias="DUPLICATE_SIMILARITY_THRESHOLD")
    enable_diversity_retrieval: bool = Field(default=True, alias="ENABLE_DIVERSITY_RETRIEVAL")
    diversity_lambda: float = Field(default=0.20, alias="DIVERSITY_LAMBDA")
    reranker_model_name: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2", alias="RERANKER_MODEL_NAME")
    reranker_timeout_ms: int = Field(default=120, alias="RERANKER_TIMEOUT_MS")
    reranker_max_latency_ms: int = Field(default=500, alias="RERANKER_MAX_LATENCY_MS")
    external_timeout_seconds: float = Field(default=25.0, alias="EXTERNAL_TIMEOUT_SECONDS")
    retry_max_attempts: int = Field(default=3, alias="RETRY_MAX_ATTEMPTS")
    retry_initial_delay_seconds: float = Field(default=0.5, alias="RETRY_INITIAL_DELAY_SECONDS")
    retry_max_delay_seconds: float = Field(default=8.0, alias="RETRY_MAX_DELAY_SECONDS")
    retry_exponential_backoff: bool = Field(default=True, alias="RETRY_EXPONENTIAL_BACKOFF")
    retry_jitter: bool = Field(default=True, alias="RETRY_JITTER")
    threshold_recall_floor: float = Field(default=0.70, alias="THRESHOLD_RECALL_FLOOR")
    enable_otel: bool = Field(default=False, alias="ENABLE_OTEL")
    otel_service_name: str = Field(default="multimodal-rag-backend", alias="OTEL_SERVICE_NAME")
    otel_exporter_otlp_endpoint: str = Field(default="", alias="OTEL_EXPORTER_OTLP_ENDPOINT")
    jwt_secret_key: str = Field(default="dev_jwt_secret_change_me_please_rotate_123456", alias="JWT_SECRET_KEY")
    jwt_access_token_minutes: int = Field(default=15, alias="JWT_ACCESS_TOKEN_MINUTES")
    jwt_refresh_token_minutes: int = Field(default=10080, alias="JWT_REFRESH_TOKEN_MINUTES")
    jwt_min_secret_length: int = Field(default=32, alias="JWT_MIN_SECRET_LENGTH")
    oauth_state_ttl_minutes: int = Field(default=10, alias="OAUTH_STATE_TTL_MINUTES")
    enable_google_oauth: bool = Field(default=False, alias="ENABLE_GOOGLE_OAUTH")
    enable_github_oauth: bool = Field(default=False, alias="ENABLE_GITHUB_OAUTH")
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    github_client_id: str = Field(default="", alias="GITHUB_CLIENT_ID")
    github_client_secret: str = Field(default="", alias="GITHUB_CLIENT_SECRET")

    @model_validator(mode="after")
    def validate_token_budget(self) -> "Settings":
        if self.max_context_tokens is not None and self.max_context_tokens <= 0:
            raise ValueError("MAX_CONTEXT_TOKENS must be > 0 when configured")
        if self.max_context_tokens is None:
            if self.max_prompt_tokens is None or self.reserved_response_tokens is None:
                raise ValueError(
                    "Token budget resolution failed: configure MAX_CONTEXT_TOKENS or both "
                    "MAX_PROMPT_TOKENS and RESERVED_RESPONSE_TOKENS"
                )
            if self.max_prompt_tokens <= self.reserved_response_tokens:
                raise ValueError("MAX_PROMPT_TOKENS must be greater than RESERVED_RESPONSE_TOKENS")
        return self

    @property
    def resolved_context_token_budget(self) -> int:
        if self.max_context_tokens is not None:
            return self.max_context_tokens
        # deprecated compatibility warning only when legacy field is explicitly configured
        if "MAX_CONTEXT_CHARS" in os.environ:
            logger.warning("MAX_CONTEXT_CHARS is deprecated and ignored for token budgeting")
        assert self.max_prompt_tokens is not None
        assert self.reserved_response_tokens is not None
        return self.max_prompt_tokens - self.reserved_response_tokens

    @property
    def full_collection_name(self) -> str:
        return f"{self.app_env}_{self.app_name}_{self.vector_collection_name}"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if "MAX_CONTEXT_CHARS" in os.environ:
        logger.warning("MAX_CONTEXT_CHARS is deprecated and kept only for compatibility")
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
    settings.pdf_storage_dir.mkdir(parents=True, exist_ok=True)
    return settings

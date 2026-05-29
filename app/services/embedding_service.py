from typing import Protocol

from sentence_transformers import SentenceTransformer

from app.core.exceptions import AppError
from app.core.resilience import RetryPolicy, call_with_timeout, with_retries


class EmbeddingService(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, query: str) -> list[float]:
        ...

    def health_check(self) -> None:
        ...


class SentenceTransformerEmbeddingService:
    def __init__(self, model_name: str, batch_size: int = 32, timeout_seconds: float = 25.0, retry_policy: RetryPolicy | None = None):
        self.model = SentenceTransformer(model_name)
        self.batch_size = batch_size
        self.timeout_seconds = timeout_seconds
        self.retry_policy = retry_policy or RetryPolicy()

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        if isinstance(exc, AppError):
            return exc.code in {"embedding_timeout", "embedding_rate_limited", "embedding_service_unavailable", "embedding_failed"}
        text = str(exc).lower()
        return "429" in text or "503" in text or "timeout" in text

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        def _invoke():
            try:
                return call_with_timeout(
                    lambda: self.model.encode(texts, batch_size=self.batch_size, normalize_embeddings=True),
                    timeout_seconds=self.timeout_seconds,
                    code="embedding_timeout",
                    message="Embedding request timed out",
                )
            except AppError:
                raise
            except Exception as exc:
                low = str(exc).lower()
                if "429" in low:
                    raise AppError("embedding_rate_limited", "Embedding service rate limited", 429) from exc
                if "503" in low:
                    raise AppError("embedding_service_unavailable", "Embedding service unavailable", 503) from exc
                raise AppError("embedding_failed", "Embedding request failed", 502) from exc

        vectors = with_retries(_invoke, policy=self.retry_policy, is_retryable=self._is_retryable)
        return [v.tolist() for v in vectors]

    def embed_query(self, query: str) -> list[float]:
        def _invoke():
            try:
                return call_with_timeout(
                    lambda: self.model.encode([query], normalize_embeddings=True)[0],
                    timeout_seconds=self.timeout_seconds,
                    code="embedding_timeout",
                    message="Embedding request timed out",
                )
            except AppError:
                raise
            except Exception as exc:
                low = str(exc).lower()
                if "429" in low:
                    raise AppError("embedding_rate_limited", "Embedding service rate limited", 429) from exc
                if "503" in low:
                    raise AppError("embedding_service_unavailable", "Embedding service unavailable", 503) from exc
                raise AppError("embedding_failed", "Embedding request failed", 502) from exc

        vec = with_retries(_invoke, policy=self.retry_policy, is_retryable=self._is_retryable)
        return vec.tolist()

    def health_check(self) -> None:
        _ = self.model.get_sentence_embedding_dimension()

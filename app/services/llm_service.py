from typing import Protocol

from google import genai

from app.core.exceptions import AppError
from app.core.resilience import RetryPolicy, call_with_timeout, with_retries


class LLMService(Protocol):
    def generate_answer(self, system_prompt: str, context: str, question: str) -> str:
        ...


def compose_llm_prompt(system_prompt: str, context: str, question: str) -> str:
    return (
        f"{system_prompt}\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION:\n{question}"
    )


class GeminiLLMService:
    def __init__(self, api_key: str, model: str, timeout_seconds: float = 25.0, retry_policy: RetryPolicy | None = None):
        self.model = model
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.timeout_seconds = timeout_seconds
        self.retry_policy = retry_policy or RetryPolicy()

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        if isinstance(exc, AppError):
            if exc.code in {"llm_timeout", "llm_rate_limited", "llm_service_unavailable", "llm_generation_failed"}:
                return True
        text = str(exc).lower()
        return "429" in text or "503" in text or "timeout" in text

    def generate_answer(self, system_prompt: str, context: str, question: str) -> str:
        if self.client is None:
            raise AppError("llm_not_configured", "GEMINI_API_KEY is missing", 500)
        client = self.client

        def _invoke() -> str:
            prompt = compose_llm_prompt(system_prompt, context, question)
            try:
                completion = call_with_timeout(
                    lambda: client.models.generate_content(model=self.model, contents=prompt),
                    timeout_seconds=self.timeout_seconds,
                    code="llm_timeout",
                    message="LLM call timed out",
                )
                return (completion.text or "").strip()
            except AppError:
                raise
            except Exception as exc:
                low = str(exc).lower()
                if "429" in low:
                    raise AppError("llm_rate_limited", "LLM rate limited", 429) from exc
                if "503" in low:
                    raise AppError("llm_service_unavailable", "LLM service unavailable", 503) from exc
                raise AppError("llm_generation_failed", "Failed to generate answer", 502) from exc

        return with_retries(_invoke, policy=self.retry_policy, is_retryable=self._is_retryable)

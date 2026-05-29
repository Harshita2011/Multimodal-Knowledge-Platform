import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.core.otel import emit_otel_event

logger = logging.getLogger("telemetry")


@dataclass(slots=True)
class TelemetryEvent:
    name: str
    status: str = "ok"
    duration_ms: int | None = None
    correlation_id: str | None = None
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class QueryAnalyticsInput:
    endpoint: str
    status: str
    document_filter_present: bool
    reranking_enabled: bool
    answer_non_empty: bool
    citations_count: int
    chunks_retrieved: int
    chunks_after_filtering: int
    threshold_rejections_query_total: int
    threshold_rejections_chunk_total: int
    context_tokens: int
    duplicate_chunks_removed: int
    duplicate_suppression_rate: float
    reranker_fallback: bool


_analytics_state: dict[str, int] = {
    "query_total": 0,
    "query_success_total": 0,
    "grounded_answer_total": 0,
    "empty_retrieval_total": 0,
    "threshold_rejections_query_total": 0,
    "threshold_rejections_chunk_total": 0,
    "chunks_retrieved_total": 0,
    "chunks_after_filtering_total": 0,
    "context_tokens_total": 0,
    "duplicate_chunks_removed_total": 0,
    "reranker_fallback_total": 0,
    "citations_total": 0,
}


def reset_query_analytics_state() -> None:
    for key in _analytics_state:
        _analytics_state[key] = 0


def emit(event: TelemetryEvent) -> None:
    payload: dict[str, Any] = {
        "event": event.name,
        "status": event.status,
        "duration_ms": event.duration_ms,
    }
    if event.correlation_id:
        payload["correlation_id"] = event.correlation_id
    payload.update(event.attrs)
    logger.info("telemetry", extra={"event": event.name, "telemetry": payload})
    emit_otel_event(event.name, event.status, event.duration_ms, event.attrs)


def record_query_analytics(data: QueryAnalyticsInput) -> None:
    _analytics_state["query_total"] += 1
    is_success = data.status == "ok"
    if is_success:
        _analytics_state["query_success_total"] += 1
    grounded = is_success and data.answer_non_empty and data.citations_count > 0
    if grounded:
        _analytics_state["grounded_answer_total"] += 1
    if data.chunks_after_filtering == 0:
        _analytics_state["empty_retrieval_total"] += 1
    _analytics_state["threshold_rejections_query_total"] += data.threshold_rejections_query_total
    _analytics_state["threshold_rejections_chunk_total"] += data.threshold_rejections_chunk_total
    _analytics_state["chunks_retrieved_total"] += data.chunks_retrieved
    _analytics_state["chunks_after_filtering_total"] += data.chunks_after_filtering
    _analytics_state["context_tokens_total"] += data.context_tokens
    _analytics_state["duplicate_chunks_removed_total"] += data.duplicate_chunks_removed
    _analytics_state["reranker_fallback_total"] += 1 if data.reranker_fallback else 0
    _analytics_state["citations_total"] += data.citations_count

    total = max(1, _analytics_state["query_total"])
    attrs = {
        "endpoint": data.endpoint,
        "status": data.status,
        "document_filter_present": data.document_filter_present,
        "reranking_enabled": data.reranking_enabled,
        "query_success_rate": _analytics_state["query_success_total"] / total,
        "grounded_answer_rate": _analytics_state["grounded_answer_total"] / total,
        "empty_retrieval_rate": _analytics_state["empty_retrieval_total"] / total,
        "retrieval_threshold_rejections_query_total": _analytics_state["threshold_rejections_query_total"],
        "retrieval_threshold_rejections_chunk_total": _analytics_state["threshold_rejections_chunk_total"],
        "chunks_retrieved": data.chunks_retrieved,
        "chunks_after_filtering": data.chunks_after_filtering,
        "citations_returned": data.citations_count,
        "avg_chunks_retrieved": _analytics_state["chunks_retrieved_total"] / total,
        "avg_chunks_after_filtering": _analytics_state["chunks_after_filtering_total"] / total,
        "avg_context_tokens": _analytics_state["context_tokens_total"] / total,
        "duplicate_chunks_removed": data.duplicate_chunks_removed,
        "duplicate_suppression_rate": data.duplicate_suppression_rate,
        "reranker_fallback_rate": _analytics_state["reranker_fallback_total"] / total,
        "citation_count_per_answer": _analytics_state["citations_total"] / total,
    }
    emit(TelemetryEvent(name="query.analytics", status=data.status, attrs=attrs))


class StageTimer:
    def __init__(self, name: str, correlation_id: str | None = None, **attrs: Any):
        self.name = name
        self.correlation_id = correlation_id
        self.attrs = attrs
        self.started = 0.0

    def __enter__(self) -> "StageTimer":
        self.started = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, _tb) -> None:
        duration_ms = int((time.perf_counter() - self.started) * 1000)
        emit(
            TelemetryEvent(
                name=self.name,
                status="error" if exc else "ok",
                duration_ms=duration_ms,
                correlation_id=self.correlation_id,
                attrs=self.attrs,
            )
        )

from __future__ import annotations

import logging
from typing import Any

from app.core.settings import Settings

logger = logging.getLogger("otel")
_meter = None
_event_counter = None
_latency_hist = None
_metric_counters: dict[str, Any] = {}
_metric_histograms: dict[str, Any] = {}
_rate_gauges: dict[str, Any] = {}


def setup_otel(settings: Settings) -> None:
    global _meter, _event_counter, _latency_hist, _metric_counters, _metric_histograms
    if not settings.enable_otel or not settings.otel_exporter_otlp_endpoint:
        return
    try:
        from opentelemetry import metrics
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({"service.name": settings.otel_service_name})
        reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
        )
        provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(provider)
        _meter = metrics.get_meter("app.core.telemetry")
        _event_counter = _meter.create_counter("rag_events_total")
        _latency_hist = _meter.create_histogram("rag_stage_duration_ms")
        for name in [
            "retrieval_threshold_rejections_query_total",
            "retrieval_threshold_rejections_chunk_total",
            "chunks_retrieved",
            "chunks_after_filtering",
            "citations_returned",
            "duplicate_chunks_removed",
            "authenticated_queries",
            "oauth_logins",
            "password_logins",
            "refresh_rotations",
            "refresh_replays_detected",
            "session_family_revocations",
        ]:
            _metric_counters[name] = _meter.create_counter(name)
        for name in [
            "query_success_rate",
            "grounded_answer_rate",
            "empty_retrieval_rate",
            "retrieved_context_tokens",
            "prompt_tokens",
            "reserved_completion_tokens",
            "total_prompt_budget",
            "avg_chunks_retrieved",
            "avg_chunks_after_filtering",
            "avg_context_tokens",
            "duplicate_suppression_rate",
            "reranker_fallback_rate",
            "citation_count_per_answer",
            "active_sessions",
        ]:
            _metric_histograms[name] = _meter.create_histogram(name)
        logger.info("otel_enabled")
    except Exception as exc:
        logger.warning("otel_setup_failed", extra={"error": str(exc)})


def emit_otel_event(name: str, status: str, duration_ms: int | None, attrs: dict[str, Any]) -> None:
    if _event_counter is None or _latency_hist is None:
        return
    allowed_tags = {"endpoint", "status", "document_filter_present", "reranking_enabled", "event"}
    tags: dict[str, Any] = {"event": name, "status": status}
    for key, value in attrs.items():
        if key in allowed_tags and isinstance(value, (str, int, float, bool)):
            tags[key] = value
    _event_counter.add(1, tags)
    if duration_ms is not None:
        _latency_hist.record(duration_ms, tags)
    for metric_name, counter in _metric_counters.items():
        value = attrs.get(metric_name)
        if isinstance(value, (int, float)):
            counter.add(value, tags)
    for metric_name, histogram in _metric_histograms.items():
        value = attrs.get(metric_name)
        if isinstance(value, (int, float)):
            histogram.record(value, tags)

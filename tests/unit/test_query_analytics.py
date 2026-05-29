from app.core.telemetry import QueryAnalyticsInput, _analytics_state, record_query_analytics, reset_query_analytics_state


def test_query_analytics_rates_and_threshold_metrics():
    reset_query_analytics_state()
    record_query_analytics(
        QueryAnalyticsInput(
            endpoint="/chat/query",
            status="ok",
            document_filter_present=False,
            reranking_enabled=False,
            answer_non_empty=True,
            citations_count=1,
            chunks_retrieved=3,
            chunks_after_filtering=2,
            threshold_rejections_query_total=0,
            threshold_rejections_chunk_total=1,
            context_tokens=50,
            duplicate_chunks_removed=1,
            duplicate_suppression_rate=0.25,
            reranker_fallback=False,
        )
    )
    assert _analytics_state["query_total"] == 1
    assert _analytics_state["chunks_retrieved_total"] == 3
    assert _analytics_state["duplicate_chunks_removed_total"] == 1

from pathlib import Path

from scripts.generate_retrieval_report import generate_report


def test_generate_report_shape(monkeypatch):
    class DummyRetriever:
        def retrieve_with_stats(self, query, top_k, document_filter, user_scope=None, workspace_scope=None):
            from datetime import datetime, timezone
            from app.models.domain.entities import ChunkMetadata, RetrievedChunk
            from app.rag.retriever import RetrievalStats
            from app.rag.scopes import BENCHMARK_RETRIEVAL_USER_ID

            md = ChunkMetadata(
                document_id="d1",
                filename="f.pdf",
                page_number=1,
                chunk_id="c1",
                ingestion_timestamp=datetime.now(timezone.utc),
                owner_user_id=BENCHMARK_RETRIEVAL_USER_ID,
                workspace_id=BENCHMARK_RETRIEVAL_USER_ID,
            )
            chunk = RetrievedChunk(chunk_id="c1", score=0.9, metadata=md, text="alpha beta")
            return [chunk], RetrievalStats(1, 1, 0, 0, 0, 0.0, False)

    import scripts.generate_retrieval_report as mod
    monkeypatch.setattr(mod, "Retriever", lambda *args, **kwargs: DummyRetriever())
    monkeypatch.setattr(mod, "get_embedding_service", lambda: object())
    monkeypatch.setattr(mod, "get_vector_repository", lambda: object())

    report = generate_report([{"query": "q", "expected_chunk_ids": ["c1"], "k": 1}])
    assert "metrics" in report

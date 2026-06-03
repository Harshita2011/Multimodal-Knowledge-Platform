from datetime import datetime, timezone

from app.models.domain.entities import ChunkMetadata, RetrievedChunk
from app.rag.retriever import Retriever


class DummyEmbedding:
    def embed_query(self, query: str) -> list[float]:
        _ = query
        return [0.1, 0.2]


class DummyRepo:
    def search_similar(self, query_embedding: list[float], top_k: int, document_filter: str | None):
        _ = query_embedding
        _ = top_k
        _ = document_filter
        md = ChunkMetadata(
            document_id="d1",
            filename="f.pdf",
            page_number=1,
            chunk_id="d1_p1_c0",
            ingestion_timestamp=datetime.now(timezone.utc),
            source_type="pdf",
            modality="text",
        )
        return [
            RetrievedChunk(chunk_id="d1_p1_c0", score=0.8, metadata=md, text="high"),
            RetrievedChunk(chunk_id="d1_p1_c1", score=0.2, metadata=md.model_copy(update={"chunk_id": "d1_p1_c1"}), text="low"),
        ]


def test_retriever_applies_min_score_threshold():
    retriever = Retriever(embeddings=DummyEmbedding(), vectors=DummyRepo(), min_score_threshold=0.5)
    chunks = retriever.retrieve(query="q", top_k=5, document_filter=None)
    assert len(chunks) == 1
    assert chunks[0].score >= 0.8


def test_retriever_exposes_threshold_rejection_stats():
    retriever = Retriever(embeddings=DummyEmbedding(), vectors=DummyRepo(), min_score_threshold=0.9)
    chunks, stats = retriever.retrieve_with_stats(query="q", top_k=5, document_filter=None)
    assert chunks == []
    assert stats.chunks_retrieved == 2
    assert stats.chunks_after_filtering == 0
    assert stats.threshold_rejections_chunk_total == 2
    assert stats.threshold_rejections_query_total == 1

from datetime import UTC, datetime

from app.models.domain.entities import ChunkMetadata, RetrievedChunk
from app.rag.evaluation import mean_reciprocal_rank, recall_at_k


def _chunk(chunk_id: str) -> RetrievedChunk:
    md = ChunkMetadata(
        document_id="d1",
        filename="f.pdf",
        page_number=1,
        chunk_id=chunk_id,
        ingestion_timestamp=datetime.now(UTC),
    )
    return RetrievedChunk(chunk_id=chunk_id, score=0.5, metadata=md, text="x")


def test_recall_at_k():
    assert recall_at_k({"a", "b"}, {"b", "c"}) == 0.5


def test_mrr():
    chunks = [_chunk("x"), _chunk("b")]
    assert mean_reciprocal_rank(chunks, {"b"}) == 0.5

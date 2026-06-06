from datetime import UTC, datetime

from app.models.domain.entities import ChunkMetadata, RetrievedChunk
from app.rag.deduplicator import ChunkDeduplicator


def _chunk(cid: str, txt: str) -> RetrievedChunk:
    md = ChunkMetadata(
        document_id="d1", filename="f.pdf", page_number=1, chunk_id=cid, ingestion_timestamp=datetime.now(UTC)
    )
    return RetrievedChunk(chunk_id=cid, score=0.9, metadata=md, text=txt)


def test_deduplicator_removes_similar_chunks_and_preserves_order():
    chunks = [_chunk("c1", "alpha beta gamma"), _chunk("c2", "alpha beta gamma"), _chunk("c3", "delta epsilon")]
    out = ChunkDeduplicator(similarity_threshold=0.9).deduplicate(chunks)
    assert [c.chunk_id for c in out] == ["c1", "c3"]

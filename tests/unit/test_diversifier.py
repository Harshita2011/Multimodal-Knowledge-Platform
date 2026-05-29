from datetime import datetime, timezone

from app.models.domain.entities import ChunkMetadata, RetrievedChunk
from app.rag.diversifier import ChunkDiversifier


def _chunk(cid: str, page: int, score: float) -> RetrievedChunk:
    md = ChunkMetadata(
        document_id="d1", filename="f.pdf", page_number=page, chunk_id=cid, ingestion_timestamp=datetime.now(timezone.utc)
    )
    return RetrievedChunk(chunk_id=cid, score=score, metadata=md, text=f"page {page}")


def test_diversifier_spreads_pages_deterministically():
    chunks = [_chunk("c1", 5, 0.95), _chunk("c2", 5, 0.93), _chunk("c3", 8, 0.92), _chunk("c4", 12, 0.91)]
    out = ChunkDiversifier(diversity_lambda=0.2).diversify(chunks, top_k=3)
    pages = [c.metadata.page_number for c in out]
    assert pages[0] == 5
    assert 8 in pages or 12 in pages

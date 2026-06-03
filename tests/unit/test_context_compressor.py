from datetime import datetime, timezone

from app.models.domain.entities import ChunkMetadata, RetrievedChunk
from app.rag.context_compressor import ContextCompressor


def _chunk(cid: str, text: str) -> RetrievedChunk:
    md = ChunkMetadata(
        document_id="d1",
        filename="f.pdf",
        page_number=1,
        chunk_id=cid,
        ingestion_timestamp=datetime.now(timezone.utc),
    )
    return RetrievedChunk(chunk_id=cid, score=0.9, metadata=md, text=text)


def test_context_compressor_deduplicates():
    chunks = [_chunk("c1", "alpha beta gamma"), _chunk("c2", "alpha beta gamma"), _chunk("c3", "delta epsilon")]
    out, stats = ContextCompressor().compress(chunks, max_units=10)
    assert [c.chunk_id for c in out] == ["c1", "c3"]
    assert stats.input_chunks == 3
    assert stats.output_units == 2

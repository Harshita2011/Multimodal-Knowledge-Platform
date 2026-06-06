from datetime import UTC, datetime

from app.models.domain.entities import ChunkMetadata, RetrievedChunk
from app.rag.document_coherence import DocumentCoherenceFilter


def _chunk(document_id: str, filename: str, chunk_id: str, score: float, page: int = 1) -> RetrievedChunk:
    md = ChunkMetadata(
        document_id=document_id,
        filename=filename,
        page_number=page,
        chunk_id=chunk_id,
        ingestion_timestamp=datetime.now(UTC),
    )
    return RetrievedChunk(chunk_id=chunk_id, score=score, metadata=md, text=f"{filename} {chunk_id}")


def test_document_mode_keeps_dominant_document_only():
    chunks = [
        _chunk("dist", "Distributed.pdf", "dist_1", 0.95),
        _chunk("dist", "Distributed.pdf", "dist_2", 0.93),
        _chunk("dist", "Distributed.pdf", "dist_3", 0.92),
        _chunk("resume", "Resume.pdf", "resume_1", 0.4),
    ]
    result = DocumentCoherenceFilter().filter(
        chunks,
        retrieval_mode="DOCUMENT_MODE",
        active_document_id="dist",
        top_k=10,
    )
    assert [c.metadata.document_id for c in result.chunks] == ["dist", "dist", "dist"]
    assert "resume" in result.dropped_documents


def test_multi_document_mode_drops_low_signal_outlier():
    chunks = [
        _chunk("dist", "Distributed.pdf", "dist_1", 0.95),
        _chunk("dist", "Distributed.pdf", "dist_2", 0.91),
        _chunk("ppt", "Slides.pptx", "ppt_1", 0.55),
        _chunk("resume", "Resume.pdf", "resume_1", 0.12),
    ]
    result = DocumentCoherenceFilter().filter(chunks, retrieval_mode="MULTI_DOCUMENT_MODE", top_k=10)
    assert "resume" in result.dropped_documents
    assert all(chunk.metadata.document_id != "resume" for chunk in result.chunks)
    assert result.document_distribution["dist"] > result.document_distribution["ppt"]

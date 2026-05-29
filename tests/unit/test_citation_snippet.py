from app.rag.citation_mapper import CitationMapper
from datetime import datetime, timezone
from app.models.domain.entities import ChunkMetadata, RetrievedChunk


def test_citation_mapper_uses_sentence_boundary_snippet():
    md = ChunkMetadata(
        document_id="d1",
        filename="f.pdf",
        page_number=1,
        chunk_id="c1",
        ingestion_timestamp=datetime.now(timezone.utc),
    )
    chunk = RetrievedChunk(chunk_id="c1", score=0.8, metadata=md, text="First sentence. Second sentence. Third sentence.")
    citations = CitationMapper().map([chunk])
    assert citations[0].snippet.startswith("First sentence")

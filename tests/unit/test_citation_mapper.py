from datetime import datetime, timezone

from app.models.domain.entities import ChunkMetadata, RetrievedChunk
from app.rag.citation_mapper import CitationMapper


def test_citation_mapper_returns_required_fields():
    md = ChunkMetadata(
        document_id="doc1",
        filename="file.pdf",
        page_number=3,
        chunk_id="doc1_p3_c0",
        ingestion_timestamp=datetime.now(timezone.utc),
        source_type="pdf",
        modality="text",
    )
    chunk = RetrievedChunk(chunk_id="doc1_p3_c0", score=0.9, metadata=md, text="hello world")
    citations = CitationMapper().map([chunk])
    assert citations[0].filename == "file.pdf"
    assert citations[0].page_number == 3
    assert citations[0].chunk_id == "doc1_p3_c0"

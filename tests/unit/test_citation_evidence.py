from datetime import UTC, datetime

from app.models.domain.entities import ChunkMetadata, RetrievedChunk
from app.rag.citation_mapper import CitationMapper


def test_citation_mapper_prefers_query_relevant_sentence():
    md = ChunkMetadata(document_id="d1", filename="f.pdf", page_number=1, chunk_id="c1", ingestion_timestamp=datetime.now(UTC))
    chunk = RetrievedChunk(
        chunk_id="c1",
        score=0.8,
        metadata=md,
        text="General intro sentence. Built a multimodal retrieval system using ChromaDB and Gemini. Closing line."
    )
    citation = CitationMapper().map([chunk], query="What was built using ChromaDB?")[0]
    assert "ChromaDB" in citation.snippet

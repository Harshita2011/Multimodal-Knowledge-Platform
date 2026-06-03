from pydantic import BaseModel

from app.models.domain.entities import Citation


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    pages_processed: int
    chunks_created: int
    ingestion_timestamp: str
    duration_ms: int
    doc_type_detected: str | None = None
    sections_indexed: int | None = None
    entities_indexed: int | None = None


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    quality: dict | None = None
    grounding: dict | None = None
    evidence_warnings: list[str] = []
    retrieval_trace: dict | None = None
    retrieval_debug: dict | None = None

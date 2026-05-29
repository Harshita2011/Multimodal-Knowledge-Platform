from pydantic import BaseModel

from app.models.domain.entities import Citation


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    pages_processed: int
    chunks_created: int
    ingestion_timestamp: str
    duration_ms: int


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    retrieval_debug: dict | None = None

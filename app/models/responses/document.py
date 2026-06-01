from pydantic import BaseModel


class DocumentSummaryResponse(BaseModel):
    id: str
    filename: str
    status: str
    page_count: int
    chunk_count: int
    created_at: str | None = None
    updated_at: str | None = None

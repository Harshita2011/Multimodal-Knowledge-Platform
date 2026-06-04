from pydantic import BaseModel, Field


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="Untitled", min_length=1, max_length=255)


class ConversationStateUpdateRequest(BaseModel):
    active_document_id: str | None = None
    active_chunk_id: str | None = None
    last_clicked_citation: dict | None = None
    last_source_document: str | None = None
    last_retrieval_mode: str | None = None
    last_answer_mode: str | None = None

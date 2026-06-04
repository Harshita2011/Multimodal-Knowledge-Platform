from pydantic import BaseModel, Field

from app.models.domain.entities import Citation


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="Untitled", min_length=1, max_length=255)


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    message_count: int
    last_message_at: str | None


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class ConversationStateResponse(BaseModel):
    active_document_id: str | None = None
    active_chunk_id: str | None = None
    last_clicked_citation: Citation | None = None
    last_source_document: str | None = None
    last_retrieval_mode: str | None = None
    last_answer_mode: str | None = None
    updated_at: str | None = None


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse]
    state: ConversationStateResponse | None = None

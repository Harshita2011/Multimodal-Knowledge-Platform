from pydantic import BaseModel, Field


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


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse]

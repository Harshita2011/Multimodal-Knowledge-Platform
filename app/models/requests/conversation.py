from pydantic import BaseModel, Field


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="Untitled", min_length=1, max_length=255)

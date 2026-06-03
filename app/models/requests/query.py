from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, examples=["What projects did the candidate build?"])
    top_k: int | None = Field(default=None, ge=1, le=200)
    document_filter: str | None = Field(default=None, examples=["resume_123"])
    conversation_id: str | None = Field(default=None, examples=["9d1606c7-9fc1-459c-b777-f5cd3f2b2e68"])
    retrieval_profile: str | None = Field(default=None, examples=["FAST", "BALANCED", "DEEP"])
    answer_mode: str | None = Field(default=None, examples=["direct", "executive_summary", "detailed_analysis"])

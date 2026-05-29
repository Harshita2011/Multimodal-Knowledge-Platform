from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(examples=["invalid_mime"])
    message: str = Field(examples=["Only PDF uploads are supported"])
    details: dict = Field(default_factory=dict)
    correlation_id: str = Field(examples=["f8f4a4d3-2dc2-4f1e-b7ab-2f7d06367e08"])


class ErrorResponse(BaseModel):
    error: ErrorDetail

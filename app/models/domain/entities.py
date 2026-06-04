from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    document_id: str
    filename: str
    page_number: int
    chunk_id: str
    ingestion_timestamp: datetime
    source_type: Literal["pdf", "docx", "pptx"] = "pdf"
    modality: Literal["text"] = "text"
    doc_type: Literal["research_paper", "contract", "technical_doc", "meeting_notes", "presentation", "resume", "policy", "manual", "wiki", "general"] = "general"
    section_path: str = ""
    heading: str = ""
    block_type: Literal["paragraph", "heading", "table", "figure", "caption", "bullet", "other"] = "paragraph"
    entities: list[str] = Field(default_factory=list)


class Document(BaseModel):
    document_id: str
    filename: str
    source_type: Literal["pdf", "docx", "pptx"] = "pdf"
    ingestion_timestamp: datetime


class ParsedPage(BaseModel):
    page_number: int
    text: str


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    page_number: int
    text: str
    metadata: ChunkMetadata


class RetrievedChunk(BaseModel):
    chunk_id: str
    score: float
    metadata: ChunkMetadata
    text: str


class Citation(BaseModel):
    document_id: str
    filename: str
    page_number: int
    chunk_id: str
    snippet: str = Field(max_length=300)

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres.base import Base


class ConversationStateModel(Base):
    __tablename__ = "conversation_states"

    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), primary_key=True)
    active_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    active_chunk_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_clicked_citation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_source_document: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_retrieval_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_answer_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

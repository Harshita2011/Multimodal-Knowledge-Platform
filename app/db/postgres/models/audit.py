from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgres.base import Base


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    session_family_id: Mapped[str] = mapped_column(String(36), index=True)
    parent_session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(255), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    revoked_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class IngestionRecordModel(Base):
    __tablename__ = "ingestion_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(64), ForeignKey("documents.id"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    pages_processed: Mapped[int] = mapped_column(Integer, default=0)
    chunks_created: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

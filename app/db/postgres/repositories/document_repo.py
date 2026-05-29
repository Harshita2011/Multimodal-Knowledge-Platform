import uuid
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.models import DocumentModel


class DocumentPgRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_or_replace(self, *, document_id: str, user_id: str, filename: str, storage_path: str, page_count: int, chunk_count: int) -> DocumentModel:
        existing = await self.session.get(DocumentModel, document_id)
        if existing is None:
            existing = DocumentModel(
                id=document_id,
                user_id=user_id,
                filename=filename,
                storage_path=storage_path,
                status="ingested",
                page_count=page_count,
                chunk_count=chunk_count,
            )
            self.session.add(existing)
        else:
            existing.user_id = user_id
            existing.filename = filename
            existing.storage_path = storage_path
            existing.status = "ingested"
            existing.page_count = page_count
            existing.chunk_count = chunk_count
            existing.deleted_at = None
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def get_owned_active(self, document_id: str, user_id: str) -> DocumentModel | None:
        stmt = select(DocumentModel).where(
            and_(DocumentModel.id == document_id, DocumentModel.user_id == user_id, DocumentModel.deleted_at.is_(None))
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_active_by_user(self, user_id: str) -> list[DocumentModel]:
        stmt = select(DocumentModel).where(and_(DocumentModel.user_id == user_id, DocumentModel.deleted_at.is_(None)))
        return list((await self.session.execute(stmt)).scalars().all())

    async def soft_delete(self, document_id: str, user_id: str) -> bool:
        doc = await self.get_owned_active(document_id, user_id)
        if doc is None:
            return False
        doc.deleted_at = datetime.utcnow()
        doc.status = "deleted"
        await self.session.commit()
        return True

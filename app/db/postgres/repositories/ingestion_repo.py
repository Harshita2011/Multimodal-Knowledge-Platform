import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.models import IngestionRecordModel


class IngestionPgRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_record(self, document_id: str, status: str, duration_ms: int, pages_processed: int, chunks_created: int) -> IngestionRecordModel:
        row = IngestionRecordModel(
            id=str(uuid.uuid4()),
            document_id=document_id,
            status=status,
            duration_ms=duration_ms,
            pages_processed=pages_processed,
            chunks_created=chunks_created,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

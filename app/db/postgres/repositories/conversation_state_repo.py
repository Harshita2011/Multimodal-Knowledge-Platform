from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.models import ConversationStateModel


class ConversationStatePgRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, conversation_id: str) -> ConversationStateModel | None:
        return await self.session.get(ConversationStateModel, conversation_id)

    async def ensure(self, conversation_id: str) -> ConversationStateModel:
        row = await self.get(conversation_id)
        if row is None:
            row = ConversationStateModel(conversation_id=conversation_id)
            self.session.add(row)
            await self.session.commit()
            await self.session.refresh(row)
        return row

    async def patch(
        self,
        conversation_id: str,
        *,
        active_document_id: str | None = None,
        active_chunk_id: str | None = None,
        last_clicked_citation: dict | None = None,
        last_source_document: str | None = None,
        last_retrieval_mode: str | None = None,
        last_answer_mode: str | None = None,
    ) -> ConversationStateModel:
        row = await self.ensure(conversation_id)
        if active_document_id is not None:
            row.active_document_id = active_document_id
        if active_chunk_id is not None:
            row.active_chunk_id = active_chunk_id
        if last_clicked_citation is not None:
            row.last_clicked_citation = last_clicked_citation
        if last_source_document is not None:
            row.last_source_document = last_source_document
        if last_retrieval_mode is not None:
            row.last_retrieval_mode = last_retrieval_mode
        if last_answer_mode is not None:
            row.last_answer_mode = last_answer_mode
        row.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(row)
        return row

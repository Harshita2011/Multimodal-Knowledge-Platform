import uuid
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.models import ConversationModel, MessageModel


class ConversationPgRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: str, title: str) -> ConversationModel:
        conv = ConversationModel(id=str(uuid.uuid4()), user_id=user_id, title=title)
        self.session.add(conv)
        await self.session.commit()
        await self.session.refresh(conv)
        return conv

    async def list_by_user(self, user_id: str) -> list[ConversationModel]:
        stmt = select(ConversationModel).where(ConversationModel.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_owned(self, conversation_id: str, user_id: str) -> ConversationModel | None:
        stmt = select(ConversationModel).where(and_(ConversationModel.id == conversation_id, ConversationModel.user_id == user_id))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def delete_owned(self, conversation_id: str, user_id: str) -> bool:
        conv = await self.get_owned(conversation_id, user_id)
        if conv is None:
            return False
        await self.session.delete(conv)
        await self.session.commit()
        return True

    async def add_message(self, conversation_id: str, role: str, content: str) -> MessageModel:
        msg = MessageModel(id=str(uuid.uuid4()), conversation_id=conversation_id, role=role, content=content)
        self.session.add(msg)
        conv = await self.session.get(ConversationModel, conversation_id)
        if conv is not None:
            conv.message_count += 1
            conv.last_message_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(msg)
        return msg

    async def list_messages(self, conversation_id: str) -> list[MessageModel]:
        stmt = select(MessageModel).where(MessageModel.conversation_id == conversation_id)
        return list((await self.session.execute(stmt)).scalars().all())

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import UserContext, get_current_user
from app.core.exceptions import AppError
from app.db.postgres.repositories.conversation_repo import ConversationPgRepository
from app.db.postgres.session import get_db_session, get_db_unavailable_message
from app.models.requests.conversation import ConversationCreateRequest
from app.models.responses.conversation import ConversationDetailResponse, ConversationResponse, MessageResponse

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(user: UserContext = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)):
    if session is None:
        raise AppError("db_unavailable", get_db_unavailable_message("conversation operations"), 503)
    repo = ConversationPgRepository(session)
    rows = await repo.list_by_user(user.user_id)
    return [
        ConversationResponse(
            id=r.id,
            user_id=r.user_id,
            title=r.title,
            message_count=r.message_count,
            last_message_at=r.last_message_at.isoformat() if r.last_message_at else None,
        )
        for r in rows
    ]


@router.post("", response_model=ConversationResponse)
async def create_conversation(req: ConversationCreateRequest, user: UserContext = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)):
    if session is None:
        raise AppError("db_unavailable", get_db_unavailable_message("conversation operations"), 503)
    repo = ConversationPgRepository(session)
    row = await repo.create(user.user_id, req.title)
    return ConversationResponse(
        id=row.id,
        user_id=row.user_id,
        title=row.title,
        message_count=row.message_count,
        last_message_at=row.last_message_at.isoformat() if row.last_message_at else None,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(conversation_id: str, user: UserContext = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)):
    if session is None:
        raise AppError("db_unavailable", get_db_unavailable_message("conversation operations"), 503)
    repo = ConversationPgRepository(session)
    row = await repo.get_owned(conversation_id, user.user_id)
    if row is None:
        return ConversationDetailResponse(id=conversation_id, user_id=user.user_id, title="", message_count=0, last_message_at=None, messages=[])
    messages = await repo.list_messages(conversation_id)
    return ConversationDetailResponse(
        id=row.id,
        user_id=row.user_id,
        title=row.title,
        message_count=row.message_count,
        last_message_at=row.last_message_at.isoformat() if row.last_message_at else None,
        messages=[MessageResponse(id=m.id, role=m.role, content=m.content, created_at=m.created_at.isoformat()) for m in messages],
    )


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str, user: UserContext = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)):
    if session is None:
        raise AppError("db_unavailable", get_db_unavailable_message("conversation operations"), 503)
    repo = ConversationPgRepository(session)
    ok = await repo.delete_owned(conversation_id, user.user_id)
    return {"ok": ok}

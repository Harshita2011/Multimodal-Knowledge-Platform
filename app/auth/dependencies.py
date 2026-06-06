from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_token
from app.core.exceptions import AppError
from app.core.settings import get_settings
from app.db.postgres.repositories.auth_repo import UserPgRepository
from app.db.postgres.session import get_db_session


class UserContext:
    def __init__(self, user_id: str, email: str):
        self.user_id = user_id
        self.email = email


async def get_current_user(
    authorization: str = Header(default=""),
    session: AsyncSession | None = Depends(get_db_session),
) -> UserContext:
    if not authorization.startswith("Bearer "):
        raise AppError("unauthorized", "Missing bearer token", 401)
    if session is None:
        raise AppError("db_unavailable", "Database session unavailable", 503)
    token = authorization.replace("Bearer ", "", 1)
    settings = get_settings()
    try:
        payload = decode_token(token, settings.jwt_secret_key)
    except Exception as exc:
        raise AppError("invalid_token", "Invalid or expired token", 401) from exc

    user_id = str(payload.get("sub", ""))
    if not user_id:
        raise AppError("invalid_token", "Token subject missing", 401)

    # Ensure user still exists and is active.
    user_repo = UserPgRepository(session)
    user = await user_repo.get_by_email(str(payload.get("email", "")))
    if user is None or user.id != user_id or not user.is_active:
        raise AppError("unauthorized", "User not active", 401)
    return UserContext(user_id=user.id, email=user.email)


async def get_optional_current_user(
    authorization: str = Header(default=""),
    session: AsyncSession | None = Depends(get_db_session),
) -> UserContext | None:
    if session is None:
        return None
    if not authorization.startswith("Bearer "):
        return None
    return await get_current_user(authorization=authorization, session=session)

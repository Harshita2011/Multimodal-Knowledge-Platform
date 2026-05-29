from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.settings import get_settings

_settings = get_settings()
_engine = None
SessionLocal = None
try:
    _engine = create_async_engine(_settings.database_url, future=True, echo=False)
    SessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
except Exception:
    _engine = None
    SessionLocal = None


async def get_db_session() -> AsyncIterator[AsyncSession]:
    if SessionLocal is None:
        yield None
        return
    async with SessionLocal() as session:
        yield session

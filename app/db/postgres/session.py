from collections.abc import AsyncIterator
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.settings import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()
_engine = None
SessionLocal = None
db_init_error: str | None = None


def _normalize_database_url(url: str) -> str:
    if url.startswith("sqlite:///") and not url.startswith("sqlite+aiosqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://") and "+asyncpg" not in url:
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


try:
    normalized_database_url = _normalize_database_url(_settings.database_url)
    _engine = create_async_engine(normalized_database_url, future=True, echo=False)
    SessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
except Exception as exc:
    db_init_error = f"{exc.__class__.__name__}: {exc}"
    logger.exception("Failed to initialize DB session factory from DATABASE_URL")
    _engine = None
    SessionLocal = None


async def get_db_session() -> AsyncIterator[AsyncSession]:
    if SessionLocal is None:
        yield None
        return
    async with SessionLocal() as session:
        yield session


def get_db_unavailable_message(scope: str = "operations") -> str:
    if db_init_error:
        return f"Database unavailable for {scope}: {db_init_error}"
    return f"Database unavailable for {scope}"

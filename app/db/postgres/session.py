import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.settings import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()
_engine: Any = None
SessionLocal: Any = None
_engine_loop: Any = None
db_init_error: str | None = None


def normalize_async_database_url(url: str) -> str:
    if url.startswith("sqlite:///") and not url.startswith("sqlite+aiosqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://") and "+asyncpg" not in url:
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def normalize_sync_database_url(url: str) -> str:
    if url.startswith("sqlite+aiosqlite:///"):
        return url.replace("sqlite+aiosqlite:///", "sqlite:///", 1)
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    return url


def _init_db_factory() -> None:
    global _engine, SessionLocal, _engine_loop, db_init_error
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _engine is None or (current_loop is not None and _engine_loop is not current_loop):
        if _engine is not None:
            try:
                _engine.sync_engine.dispose()
            except Exception:
                pass
        try:
            normalized_database_url = normalize_async_database_url(_settings.database_url)
            _engine = create_async_engine(normalized_database_url, future=True, echo=False)
            SessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
            _engine_loop = current_loop
            db_init_error = None
        except Exception as exc:
            db_init_error = f"{exc.__class__.__name__}: {exc}"
            logger.exception("Failed to initialize DB session factory from DATABASE_URL")
            _engine = None
            SessionLocal = None
            _engine_loop = None


# Static fallback check at import time
try:
    _init_db_factory()
except Exception:
    pass


async def get_db_session() -> AsyncIterator[AsyncSession | None]:
    _init_db_factory()
    if SessionLocal is None:
        yield None
        return
    async with SessionLocal() as session:
        yield session


def get_db_unavailable_message(scope: str = "operations") -> str:
    if db_init_error:
        return f"Database unavailable for {scope}: {db_init_error}"
    return f"Database unavailable for {scope}"

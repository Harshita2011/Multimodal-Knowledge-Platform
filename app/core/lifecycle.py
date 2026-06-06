from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import text

from app.api.dependencies import get_embedding_service, get_vector_repository
from app.core.settings import get_settings
from app.db.postgres import models as _pg_models  # noqa: F401
from app.db.postgres.base import Base
from app.db.postgres.session import _engine
from app.utils.tokenizer import build_tokenizer


@asynccontextmanager
async def lifespan(app: FastAPI):
    embedding_ok = False
    chroma_ok = False
    config_ok = False
    tokenizer_ok = False
    llm_config_ok = False
    storage_ok = False
    model_ok = False
    postgres_ok = False
    security_ok = False
    migrations_ok = False

    settings = get_settings()
    llm_config_ok = bool(settings.gemini_api_key.strip())
    try:
        settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
        settings.pdf_storage_dir.mkdir(parents=True, exist_ok=True)
        storage_ok = Path(settings.chroma_persist_dir).exists() and Path(settings.pdf_storage_dir).exists()
    except Exception:
        storage_ok = False

    try:
        _ = build_tokenizer(strict=settings.tokenizer_strict)
        tokenizer_ok = True
    except Exception:
        tokenizer_ok = False

    try:
        embedding = get_embedding_service()
        embedding.health_check()
        embedding_ok = True
        model_ok = True
    except Exception:
        embedding_ok = False
        model_ok = False

    try:
        repo = get_vector_repository()
        repo.initialize_collection()
        chroma_ok = True
    except Exception:
        chroma_ok = False

    if _engine is not None:
        try:
            async with _engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
                await conn.run_sync(Base.metadata.create_all)
            postgres_ok = True
        except Exception:
            postgres_ok = False
    else:
        postgres_ok = False

    jwt_ok = bool(settings.jwt_secret_key) and len(settings.jwt_secret_key) >= settings.jwt_min_secret_length
    google_oauth_ok = (not settings.enable_google_oauth) or bool(settings.google_client_id and settings.google_client_secret)
    github_oauth_ok = (not settings.enable_github_oauth) or bool(settings.github_client_id and settings.github_client_secret)
    security_ok = jwt_ok and google_oauth_ok and github_oauth_ok
    migrations_ok = postgres_ok
    config_ok = llm_config_ok and storage_ok and tokenizer_ok and security_ok and migrations_ok

    app.state.health_status = {
        "boot_ok": True,
        "config_ok": config_ok,
        "llm_config_ok": llm_config_ok,
        "storage_ok": storage_ok,
        "tokenizer_ok": tokenizer_ok,
        "model_ok": model_ok,
        "embedding_ok": embedding_ok,
        "chroma_ok": chroma_ok,
        "postgres_ok": postgres_ok,
        "security_ok": security_ok,
        "migrations_ok": migrations_ok,
    }
    yield

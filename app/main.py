from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware.correlation import CorrelationIdMiddleware
from app.api.routers import api_router
from app.core.exceptions import register_exception_handlers
from app.core.lifecycle import lifespan
from app.core.logging import configure_logging
from app.core.otel import setup_otel
from app.core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    setup_otel(settings)
    app = FastAPI(title="Multimodal RAG Backend", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationIdMiddleware)
    app.include_router(api_router, prefix=settings.api_prefix)
    register_exception_handlers(app)
    return app


app = create_app()

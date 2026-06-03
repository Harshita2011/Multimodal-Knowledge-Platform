from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_ingestion_orchestrator
from app.auth.dependencies import UserContext, get_current_user, get_optional_current_user
from app.core.settings import get_settings
from app.db.postgres.repositories.document_repo import DocumentPgRepository
from app.db.postgres.repositories.ingestion_repo import IngestionPgRepository
from app.db.postgres.session import get_db_session, get_db_unavailable_message
from app.ingestion.orchestrator import IngestionOrchestrator
from app.models.responses.document import DocumentSummaryResponse
from app.models.responses.error import ErrorResponse
from app.models.responses.rag import UploadResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentSummaryResponse])
async def list_documents(
    current_user: UserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    if session is None:
        from app.core.exceptions import AppError

        raise AppError("db_unavailable", get_db_unavailable_message("document operations"), 503)
    repo = DocumentPgRepository(session)
    rows = await repo.list_active_by_user(current_user.user_id)
    return [
        DocumentSummaryResponse(
            id=row.id,
            filename=row.filename,
            status=row.status,
            page_count=row.page_count,
            chunk_count=row.chunk_count,
            created_at=row.created_at.isoformat() if row.created_at else None,
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
        )
        for row in rows
    ]


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload and ingest a PDF",
    description="Uploads a PDF, parses/chunks/embeds it, and replaces vectors if the same document_id is reused.",
    responses={
        200: {
            "description": "Document ingested successfully",
            "content": {
                "application/json": {
                    "example": {
                        "document_id": "resume_123",
                        "filename": "resume.pdf",
                        "pages_processed": 2,
                        "chunks_created": 8,
                        "ingestion_timestamp": "2026-05-29T10:00:00+00:00",
                        "duration_ms": 482,
                    }
                }
            },
        },
        400: {"model": ErrorResponse, "description": "Invalid filename or empty file"},
        413: {"model": ErrorResponse, "description": "File too large"},
        415: {"model": ErrorResponse, "description": "Unsupported media type"},
        422: {"model": ErrorResponse, "description": "PDF has no extractable text"},
    },
)
async def upload_pdf(
    file: UploadFile = File(...),
    document_id: str | None = Form(default=None),
    orchestrator: IngestionOrchestrator = Depends(get_ingestion_orchestrator),
    current_user: UserContext | None = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    settings = get_settings()
    if settings.auth_required_for_core_routes and current_user is None:
        from app.core.exceptions import AppError

        raise AppError("unauthorized", "Authentication required", 401)
    response = await orchestrator.ingest_pdf(file=file, document_id=document_id)
    if current_user is not None and session is not None:
        doc_repo = DocumentPgRepository(session)
        ingestion_repo = IngestionPgRepository(session)
        await doc_repo.create_or_replace(
            document_id=response.document_id,
            user_id=current_user.user_id,
            filename=response.filename,
            storage_path=f"{response.document_id}_{response.filename}",
            page_count=response.pages_processed,
            chunk_count=response.chunks_created,
        )
        await ingestion_repo.create_record(
            document_id=response.document_id,
            status="success",
            duration_ms=response.duration_ms,
            pages_processed=response.pages_processed,
            chunks_created=response.chunks_created,
        )
    return response

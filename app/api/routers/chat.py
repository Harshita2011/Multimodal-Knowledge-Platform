from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_rag_orchestrator
from app.auth.dependencies import UserContext, get_optional_current_user
from app.core.exceptions import AppError
from app.core.settings import get_settings
from app.core.telemetry import TelemetryEvent, emit
from app.db.postgres.repositories.auth_repo import UserPgRepository
from app.db.postgres.repositories.conversation_repo import ConversationPgRepository
from app.db.postgres.repositories.conversation_state_repo import ConversationStatePgRepository
from app.db.postgres.repositories.document_repo import DocumentPgRepository
from app.db.postgres.session import get_db_session
from app.models.requests.query import QueryRequest
from app.models.responses.error import ErrorResponse
from app.models.responses.rag import QueryResponse
from app.rag.orchestrator import RagOrchestrator
from app.rag.query_strategy import ConversationMemory, build_query_plan, resolve_document_reference

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Ask a grounded question",
    description=(
        "Runs retrieval with optional document filter and score thresholding, assembles context with citation IDs, "
        "and generates a grounded answer."
    ),
    responses={
        200: {
            "description": "Grounded answer with citations",
            "content": {
                "application/json": {
                    "example": {
                        "answer": "Newton's second law states force equals mass times acceleration.",
                        "citations": [
                            {
                                "filename": "physics_notes.pdf",
                                "page_number": 1,
                                "chunk_id": "physics_notes_p1_c0",
                                "snippet": "Newton's second law states force equals mass times acceleration.",
                            }
                        ],
                        "retrieval_debug": {
                            "top_k": 3,
                            "total_latency_ms": 131,
                            "scores": [0.92, 0.74],
                            "chunk_ids": ["physics_notes_p1_c0", "physics_notes_p2_c0"],
                            "citations_count": 1,
                        },
                    }
                }
            },
        },
        500: {"model": ErrorResponse, "description": "Internal or downstream failure"},
        502: {"model": ErrorResponse, "description": "Upstream model/vector failure"},
        504: {"model": ErrorResponse, "description": "Timeout"},
    },
)
async def query_rag(
    req: QueryRequest,
    orchestrator: RagOrchestrator = Depends(get_rag_orchestrator),
    current_user: UserContext | None = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    settings = get_settings()
    if settings.auth_required_for_core_routes and current_user is None:
        raise AppError("unauthorized", "Authentication required", 401)
    user_scope = current_user.user_id if current_user is not None else UserPgRepository.ANONYMOUS_USER_ID
    workspace_scope = user_scope
    conv_repo = ConversationPgRepository(session) if current_user is not None and session is not None and req.conversation_id else None
    state_repo = ConversationStatePgRepository(session) if current_user is not None and session is not None and req.conversation_id else None
    resolved_document = None
    doc_repo = None
    if session is not None:
        doc_repo = DocumentPgRepository(session)
        owned_docs = await doc_repo.list_active_by_user(user_scope)
        resolved_document = resolve_document_reference(req.query, owned_docs)
    memory = None
    if current_user is not None and session is not None and req.document_filter:
        doc_repo = doc_repo or DocumentPgRepository(session)
        owned = await doc_repo.get_owned_active(req.document_filter, current_user.user_id)
        if owned is None:
            raise AppError("forbidden_document", "Document not found for current user", 403)

    if conv_repo is not None and state_repo is not None and req.conversation_id:
        conversation = await conv_repo.get_owned(req.conversation_id, current_user.user_id)
        if conversation is None:
            raise AppError("conversation_not_found", "Conversation not found for current user", 404)
        state = await state_repo.ensure(req.conversation_id)
        memory = ConversationMemory(
            active_document_id=state.active_document_id,
            active_chunk_id=state.active_chunk_id,
            last_clicked_citation=state.last_clicked_citation,
            last_source_document=state.last_source_document,
            last_retrieval_mode=state.last_retrieval_mode,
            last_answer_mode=state.last_answer_mode,
        )

    plan = build_query_plan(
        req.query,
        explicit_answer_mode=req.answer_mode,
        explicit_document_filter=req.document_filter,
        resolved_document=resolved_document,
        memory=memory,
    )

    response = orchestrator.answer(req, plan=plan, user_scope=user_scope, workspace_scope=workspace_scope)
    if current_user is not None:
        emit(TelemetryEvent(name="auth.query", attrs={"authenticated_queries": 1}))
    if current_user is not None and session is not None and req.conversation_id:
        conv = await conv_repo.get_owned(req.conversation_id, current_user.user_id)
        if conv is None:
            raise AppError("conversation_not_found", "Conversation not found for current user", 404)
        await conv_repo.add_message(req.conversation_id, "user", req.query)
        await conv_repo.add_message(req.conversation_id, "assistant", response.answer)
        if state_repo is not None:
            try:
                primary = response.citations[0] if response.citations else None
                await state_repo.patch(
                    req.conversation_id,
                    active_document_id=primary.document_id if primary and (plan.retrieval_mode == "DOCUMENT_MODE" or memory is None or memory.active_document_id is None) else (memory.active_document_id if memory else None),
                    active_chunk_id=primary.chunk_id if primary and (plan.retrieval_mode == "DOCUMENT_MODE" or memory is None or memory.active_chunk_id is None) else (memory.active_chunk_id if memory else None),
                    last_source_document=primary.filename if primary else (memory.last_source_document if memory else None),
                    last_retrieval_mode=plan.retrieval_mode,
                    last_answer_mode=plan.answer_mode,
                )
            except Exception:
                pass
    return response

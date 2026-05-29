import time

from app.core.telemetry import QueryAnalyticsInput, StageTimer, TelemetryEvent, emit, record_query_analytics
from app.models.requests.query import QueryRequest
from app.models.responses.rag import QueryResponse
from app.rag.citation_mapper import CitationMapper
from app.rag.prompt_builder import PromptBuilder
from app.rag.retriever import Retriever
from app.services.llm_service import LLMService


class RagOrchestrator:
    def __init__(
        self,
        retriever: Retriever,
        llm_service: LLMService,
        prompt_builder: PromptBuilder,
        citation_mapper: CitationMapper,
        top_k_default: int,
        debug_enabled: bool,
    ):
        self.retriever = retriever
        self.llm_service = llm_service
        self.prompt_builder = prompt_builder
        self.citation_mapper = citation_mapper
        self.top_k_default = top_k_default
        self.debug_enabled = debug_enabled

    def answer(self, req: QueryRequest) -> QueryResponse:
        started = time.perf_counter()
        top_k = req.top_k or self.top_k_default
        try:
            with StageTimer("retrieval.stage", top_k=top_k):
                chunks, retrieval_stats = self.retriever.retrieve_with_stats(req.query, top_k=top_k, document_filter=req.document_filter)
            with StageTimer("prompt_build.stage", chunk_count=len(chunks)):
                context_payload = self.prompt_builder.build_context_payload(chunks)
                context = context_payload.context
            emit(
                TelemetryEvent(
                    name="prompt.tokens",
                    attrs={
                        "retrieved_context_tokens": context_payload.retrieved_context_tokens,
                        "prompt_tokens": context_payload.prompt_tokens,
                        "reserved_completion_tokens": context_payload.reserved_completion_tokens,
                        "total_prompt_budget": context_payload.total_prompt_budget,
                    },
                )
            )
            with StageTimer("llm.stage"):
                answer = self.llm_service.generate_answer(
                    system_prompt=self.prompt_builder.SYSTEM_PROMPT,
                    context=context,
                    question=req.query,
                )
            citations = self.citation_mapper.map(chunks, query=req.query)
            record_query_analytics(
                QueryAnalyticsInput(
                    endpoint="/chat/query",
                    status="ok",
                    document_filter_present=req.document_filter is not None,
                    reranking_enabled=self.retriever.enable_reranking,
                    answer_non_empty=bool(answer.strip()),
                    citations_count=len(citations),
                    chunks_retrieved=retrieval_stats.chunks_retrieved,
                    chunks_after_filtering=retrieval_stats.chunks_after_filtering,
                    threshold_rejections_query_total=retrieval_stats.threshold_rejections_query_total,
                    threshold_rejections_chunk_total=retrieval_stats.threshold_rejections_chunk_total,
                    context_tokens=context_payload.retrieved_context_tokens,
                    duplicate_chunks_removed=retrieval_stats.duplicate_chunks_removed,
                    duplicate_suppression_rate=retrieval_stats.duplicate_suppression_rate,
                    reranker_fallback=retrieval_stats.reranker_fallback,
                )
            )
        except Exception:
            record_query_analytics(
                QueryAnalyticsInput(
                    endpoint="/chat/query",
                    status="error",
                    document_filter_present=req.document_filter is not None,
                    reranking_enabled=self.retriever.enable_reranking,
                    answer_non_empty=False,
                    citations_count=0,
                    chunks_retrieved=0,
                    chunks_after_filtering=0,
                    threshold_rejections_query_total=0,
                    threshold_rejections_chunk_total=0,
                    context_tokens=0,
                    duplicate_chunks_removed=0,
                    duplicate_suppression_rate=0.0,
                    reranker_fallback=False,
                )
            )
            raise
        debug = None
        if self.debug_enabled:
            debug = {
                "top_k": top_k,
                "total_latency_ms": int((time.perf_counter() - started) * 1000),
                "scores": [round(c.score, 4) for c in chunks],
                "chunk_ids": [c.chunk_id for c in chunks],
                "citations_count": len(citations),
                "duplicates_removed": retrieval_stats.duplicate_chunks_removed,
                "diversity_applied": True,
                "reranker_fallback": retrieval_stats.reranker_fallback,
            }
        return QueryResponse(answer=answer, citations=citations, retrieval_debug=debug)

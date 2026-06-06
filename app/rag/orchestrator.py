import time

from app.core.telemetry import QueryAnalyticsInput, StageTimer, TelemetryEvent, emit, record_query_analytics
from app.models.requests.query import QueryRequest
from app.models.responses.rag import QueryResponse
from app.rag.citation_mapper import CitationMapper
from app.rag.context_compressor import ContextCompressor
from app.rag.document_coherence import DocumentCoherenceFilter
from app.rag.prompt_builder import PromptBuilder
from app.rag.query_strategy import QueryPlan, build_query_plan
from app.rag.retriever import Retriever
from app.services.llm_service import LLMService, compose_llm_prompt


class RagOrchestrator:
    def __init__(
        self,
        retriever: Retriever,
        llm_service: LLMService,
        prompt_builder: PromptBuilder,
        citation_mapper: CitationMapper,
        top_k_default: int,
        debug_enabled: bool,
        context_compressor: ContextCompressor,
        coherence_filter: DocumentCoherenceFilter | None = None,
    ):
        self.retriever = retriever
        self.llm_service = llm_service
        self.prompt_builder = prompt_builder
        self.citation_mapper = citation_mapper
        self.top_k_default = top_k_default
        self.debug_enabled = debug_enabled
        self.context_compressor = context_compressor
        self.coherence_filter = coherence_filter or DocumentCoherenceFilter()

    def _grounding_quality(self, answer: str, chunks_text: str) -> tuple[float, list[str]]:
        claims = [c.strip() for c in answer.replace("\n", " ").split(".") if c.strip()]
        if not claims:
            return 0.0, []
        warnings: list[str] = []
        supported = 0
        corpus = chunks_text.lower()
        for claim in claims:
            tokens = [t.lower() for t in claim.split() if len(t) >= 5]
            if not tokens:
                supported += 1
                continue
            overlap = sum(1 for t in tokens if t in corpus)
            if overlap / max(1, len(tokens)) >= 0.35:
                supported += 1
            else:
                warnings.append(f"Low evidence support for claim: {claim[:120]}")
        return supported / len(claims), warnings

    def answer(
        self,
        req: QueryRequest,
        plan: QueryPlan | None = None,
        user_scope: str | None = None,
        workspace_scope: str | None = None,
    ) -> QueryResponse:
        started = time.perf_counter()
        top_k = req.top_k or self.top_k_default
        effective_plan = plan or build_query_plan(
            req.query,
            explicit_answer_mode=req.answer_mode,
            explicit_document_filter=req.document_filter,
            memory=None,
        )
        retrieval_query = effective_plan.query
        try:
            with StageTimer("retrieval.stage", top_k=top_k):
                chunks, retrieval_stats = self.retriever.retrieve_with_stats(
                    retrieval_query,
                    top_k=top_k,
                    document_filter=effective_plan.document_filter,
                    retrieval_profile=req.retrieval_profile,
                    answer_mode=effective_plan.answer_mode,
                    user_scope=user_scope,
                    workspace_scope=workspace_scope,
                )
            coherence = self.coherence_filter.filter(
                chunks,
                retrieval_mode=effective_plan.retrieval_mode,
                active_document_id=effective_plan.active_document_id,
                explicit_document_filter=effective_plan.document_filter,
                top_k=top_k,
                answer_mode=effective_plan.answer_mode,
            )
            chunks = coherence.chunks
            with StageTimer("compression.stage", chunk_count=len(chunks)):
                chunks, compression = self.context_compressor.compress(chunks, max_units=10)
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
            system_prompt = self.prompt_builder.build_system_prompt(
                effective_plan.answer_mode,
                effective_plan.retrieval_mode,
                single_document=len(coherence.document_distribution) <= 1,
            )
            final_prompt = compose_llm_prompt(system_prompt, context, retrieval_query)
            with StageTimer("llm.stage"):
                answer = self.llm_service.generate_answer(
                    system_prompt=system_prompt,
                    context=context,
                    question=retrieval_query,
                )
            citations = self.citation_mapper.map(chunks, query=retrieval_query)
            grounding_score, evidence_warnings = self._grounding_quality(answer=answer, chunks_text=context)
            citation_coverage = len({c.chunk_id for c in citations}.intersection({c.chunk_id for c in chunks})) / max(1, len(citations))
            evidence_coverage = min(1.0, context_payload.retrieved_context_tokens / max(1, context_payload.max_prompt_tokens if hasattr(context_payload, "max_prompt_tokens") else context_payload.total_prompt_budget))
            claim_support_rate = grounding_score
            quality = {
                "retrieval_score": round(retrieval_stats.retrieval_score, 4),
                "rerank_score": round(retrieval_stats.rerank_score, 4),
                "grounding_score": round(grounding_score, 4),
                "citation_coverage": round(citation_coverage, 4),
            }
            grounding = {
                "grounding_score": round(grounding_score, 4),
                "citation_coverage": round(citation_coverage, 4),
                "evidence_coverage": round(evidence_coverage, 4),
                "claim_support_rate": round(claim_support_rate, 4),
            }
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
        trace = dict(retrieval_stats.trace or {})
        trace.update(
            {
                "original_query": req.query,
                "rewritten_query": retrieval_query,
                "user_scope": user_scope,
                "workspace_scope": workspace_scope or user_scope,
                "resolved_document": effective_plan.resolved_document,
                "document_resolution_confidence": effective_plan.document_resolution_confidence,
                "answer_mode": effective_plan.answer_mode,
                "retrieval_mode": effective_plan.retrieval_mode,
                "active_document": effective_plan.active_document_id,
                "active_chunk": effective_plan.active_chunk_id,
                "source_document": effective_plan.source_document,
                "document_filter": effective_plan.document_filter,
                "rewritten": effective_plan.rewritten,
                "rewrite_reason": effective_plan.rewrite_reason,
                "document_distribution": coherence.document_distribution,
                "document_scores": coherence.document_scores,
                "chunk_distribution": coherence.chunk_distribution,
                "dropped_documents": coherence.dropped_documents,
                "dropped_chunks": coherence.dropped_chunks,
                "final_context_documents": list(dict.fromkeys(c.metadata.filename for c in chunks)),
                "assembled_context": context,
                "system_prompt": system_prompt,
                "final_prompt": final_prompt,
            }
        )
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
                "profile_used": retrieval_stats.profile_used,
                "retrieval_mode": effective_plan.retrieval_mode,
                "answer_mode": effective_plan.answer_mode,
                "active_document": effective_plan.active_document_id,
                "resolved_document": effective_plan.resolved_document,
                "document_resolution_confidence": effective_plan.document_resolution_confidence,
                "document_distribution": coherence.document_distribution,
                "document_scores": coherence.document_scores,
                "chunk_distribution": coherence.chunk_distribution,
                "dropped_documents": coherence.dropped_documents,
                "dropped_chunks": coherence.dropped_chunks,
                "rewritten_query": retrieval_query,
                "final_context_documents": list(dict.fromkeys(c.metadata.filename for c in chunks)),
                "assembled_context": context,
                "system_prompt": system_prompt,
                "final_prompt": final_prompt,
                "compression": {
                    "input_chunks": compression.input_chunks,
                    "output_units": compression.output_units,
                    "compression_ratio": round(compression.compression_ratio, 4),
                },
            }
        return QueryResponse(
            answer=answer,
            citations=citations,
            quality=quality,
            grounding=grounding,
            evidence_warnings=evidence_warnings,
            retrieval_trace=trace,
            retrieval_debug=debug,
        )

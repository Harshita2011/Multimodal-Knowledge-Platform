from dataclasses import dataclass
from typing import Any

from app.db.postgres.repositories.lexical_repo import LexicalPgRepository
from app.db.repositories.vector_repository import VectorRepository
from app.models.domain.entities import RetrievedChunk
from app.rag.channels import BM25Retriever, EntityRetriever
from app.rag.deduplicator import ChunkDeduplicator
from app.rag.diversifier import ChunkDiversifier
from app.rag.query_strategy import PROFILES, classify_query_intent, expand_queries, heading_bias_score, pick_profile
from app.rag.reranker import Reranker, SemanticReranker, suppress_near_duplicates
from app.rag.retrieval_cache import RetrievalCache
from app.rag.rrf import RRFMerger
from app.rag.text_normalizer import normalize_query_text
from app.services.embedding_service import EmbeddingService


@dataclass(slots=True)
class RetrievalStats:
    chunks_retrieved: int
    chunks_after_filtering: int
    threshold_rejections_chunk_total: int
    threshold_rejections_query_total: int
    duplicate_chunks_removed: int
    duplicate_suppression_rate: float
    reranker_fallback: bool
    retrieval_score: float = 0.0
    rerank_score: float = 0.0
    profile_used: str = "FAST"
    trace: dict | None = None


class Retriever:
    def __init__(
        self,
        embeddings: EmbeddingService,
        vectors: VectorRepository,
        min_score_threshold: float = 0.0,
        enable_reranking: bool = False,
        rerank_top_n: int = 8,
        duplicate_threshold: float = 0.90,
        enable_diversity: bool = True,
        diversity_lambda: float = 0.2,
        reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        reranker_timeout_ms: int = 120,
        lexical: LexicalPgRepository | None = None,
        retrieval_cache: RetrievalCache | None = None,
        rrf_k: int = 60,
        enable_bm25: bool = True,
        enable_entity: bool = True,
        enable_rrf: bool = True,
    ):
        self.embeddings = embeddings
        self.vectors = vectors
        self.min_score_threshold = min_score_threshold
        self.enable_reranking = enable_reranking
        self.rerank_top_n = rerank_top_n
        self.enable_diversity = enable_diversity
        self.deduplicator = ChunkDeduplicator(similarity_threshold=duplicate_threshold)
        self.diversifier = ChunkDiversifier(diversity_lambda=diversity_lambda)
        self.reranker: Reranker = SemanticReranker(model_name=reranker_model_name, timeout_ms=reranker_timeout_ms, top_n=rerank_top_n)
        self.lexical = lexical
        self.bm25 = BM25Retriever(lexical) if lexical is not None else None
        self.entity = EntityRetriever(lexical) if lexical is not None else None
        self.cache = retrieval_cache or RetrievalCache()
        self.rrf = RRFMerger(k=rrf_k)
        self.enable_bm25 = enable_bm25
        self.enable_entity = enable_entity
        self.enable_rrf = enable_rrf

    def _keyword_entity_boost(self, query: str, chunk: RetrievedChunk) -> float:
        q_terms = {t.lower() for t in query.split() if len(t) >= 3}
        text = chunk.text.lower()
        term_hits = sum(1 for t in q_terms if t in text)
        entity_hits = sum(1 for e in chunk.metadata.entities if e.lower() in query.lower())
        return min(0.25, 0.02 * term_hits + 0.05 * entity_hits)

    def retrieve_with_stats(
        self,
        query: str,
        top_k: int,
        document_filter: str | None,
        retrieval_profile: str | None = None,
        answer_mode: str | None = None,
        user_scope: str | None = None,
        workspace_scope: str | None = None,
    ) -> tuple[list[RetrievedChunk], RetrievalStats]:
        if user_scope is None:
            raise ValueError("user_scope is required for retrieval")
        workspace_scope = workspace_scope or user_scope
        intent = classify_query_intent(query)
        doc_type = None
        profile_key: Any = retrieval_profile.upper() if retrieval_profile else None
        profile = PROFILES.get(profile_key, None) if profile_key else None
        if profile is None:
            profile = pick_profile(intent=intent, answer_mode=answer_mode, doc_type=doc_type)
        queries = expand_queries(query)
        cache_key = (
            f"q={normalize_query_text(query)}|doc={document_filter or '*'}|user={user_scope}|ws={workspace_scope}|profile={profile.name}|mode={answer_mode or 'direct'}|"
            f"vec={profile.vector_top_k}|bm25={profile.bm25_top_k}|ent={profile.entity_top_k}"
        )
        cached = self.cache.get(cache_key)
        raw_chunks: list[RetrievedChunk] = []
        per_query_counts: dict[str, int] = {}
        entity_terms: list[str] = []
        rrf_trace: dict[str, dict] = {}
        if cached is not None:
            raw_chunks = [RetrievedChunk.model_validate(c) for c in cached.get("raw_chunks", [])]
            per_query_counts = cached.get("per_query_counts", {})
            entity_terms = cached.get("entity_terms", [])
            rrf_trace = cached.get("rrf_trace", {})
        else:
            vector_chunks: list[RetrievedChunk] = []
            for q in queries:
                query_embedding = self.embeddings.embed_query(q)
                got = self.vectors.search_similar(
                    query_embedding,
                    top_k=profile.vector_top_k,
                    document_filter=document_filter,
                    user_scope=user_scope,
                    workspace_scope=workspace_scope,
                )
                per_query_counts[q] = len(got)
                vector_chunks.extend(got)
            bm25_chunks: list[RetrievedChunk] = []
            entity_chunks: list[RetrievedChunk] = []
            if self.enable_bm25 and self.bm25 is not None:
                bm25_chunks = self.bm25.retrieve(
                    query=query,
                    top_k=profile.bm25_top_k,
                    document_filter=document_filter,
                    user_scope=user_scope,
                    workspace_scope=workspace_scope,
                )
            if self.enable_entity and self.entity is not None:
                entity_chunks, entity_terms = self.entity.retrieve(
                    query=query,
                    top_k=profile.entity_top_k,
                    document_filter=document_filter,
                    user_scope=user_scope,
                    workspace_scope=workspace_scope,
                )
            if self.enable_rrf:
                merged, rrf_trace = self.rrf.merge({"vector": vector_chunks, "bm25": bm25_chunks, "entity": entity_chunks})
                raw_chunks = merged
            else:
                merged = vector_chunks + bm25_chunks + entity_chunks
                merged.sort(key=lambda c: (-c.score, c.chunk_id))
                seen: set[str] = set()
                raw_chunks = []
                for c in merged:
                    if c.chunk_id in seen:
                        continue
                    seen.add(c.chunk_id)
                    raw_chunks.append(c)
            self.cache.put(
                cache_key,
                {
                    "raw_chunks": [c.model_dump(mode="json") for c in raw_chunks],
                    "per_query_counts": per_query_counts,
                    "entity_terms": entity_terms,
                    "rrf_trace": rrf_trace,
                },
            )

        rescored_raw: list[RetrievedChunk] = []
        for c in raw_chunks:
            bias = heading_bias_score(c.metadata.doc_type, c.metadata.heading, c.metadata.section_path)
            boost = self._keyword_entity_boost(query, c)
            rescored_raw.append(c.model_copy(update={"score": min(1.0, c.score + bias + boost)}))

        filtered = [c for c in rescored_raw if c.score >= self.min_score_threshold]
        chunks = sorted(filtered, key=lambda c: (-c.score, c.chunk_id))
        deduped = self.deduplicator.deduplicate(chunks)
        duplicate_removed = max(0, len(chunks) - len(deduped))
        if self.enable_diversity:
            try:
                deduped = self.diversifier.diversify(deduped, top_k=max(top_k, profile.rerank_top_k))
            except Exception:
                pass
        reranker_fallback = False
        chunks = deduped
        if self.enable_reranking and chunks:
            try:
                self.reranker.top_n = profile.rerank_top_k  # type: ignore[attr-defined]
                chunks = self.reranker.rerank(query, chunks)
            except Exception:
                # Fail-open to cosine baseline ordering for reliability.
                reranker_fallback = True
        chunks = suppress_near_duplicates(chunks, threshold=0.99999)
        out = chunks[:top_k]
        dropped = max(0, len(raw_chunks) - len(filtered))
        suppression_rate = (duplicate_removed / len(chunks)) if chunks else 0.0
        explainability: dict[str, dict] = {}
        for c in out:
            details = rrf_trace.get(c.chunk_id, {}).copy()
            details.update({"chunk_id": c.chunk_id, "rerank_score": round(c.score, 6)})
            explainability[c.chunk_id] = details

        stats = RetrievalStats(
            chunks_retrieved=len(raw_chunks),
            chunks_after_filtering=len(filtered),
            threshold_rejections_chunk_total=dropped,
            threshold_rejections_query_total=1 if len(raw_chunks) > 0 and len(filtered) == 0 else 0,
            duplicate_chunks_removed=duplicate_removed,
            duplicate_suppression_rate=suppression_rate,
            reranker_fallback=reranker_fallback,
            retrieval_score=(sum(c.score for c in out) / len(out)) if out else 0.0,
            rerank_score=(sum(c.score for c in chunks[: profile.rerank_top_k]) / max(1, min(len(chunks), profile.rerank_top_k))) if chunks else 0.0,
            profile_used=profile.name,
            trace={
                "intent": intent,
                "expanded_queries": queries,
                "entity_terms": entity_terms,
                "per_query_counts": per_query_counts,
                "vector_top_k": profile.vector_top_k,
                "bm25_top_k": profile.bm25_top_k,
                "entity_top_k": profile.entity_top_k,
                "rerank_top_k": profile.rerank_top_k,
                "user_scope": user_scope,
                "workspace_scope": workspace_scope,
                "explainability": explainability,
            },
        )
        return out, stats

    def retrieve(
        self,
        query: str,
        top_k: int,
        document_filter: str | None,
        retrieval_profile: str | None = None,
        answer_mode: str | None = None,
        user_scope: str | None = None,
        workspace_scope: str | None = None,
    ) -> list[RetrievedChunk]:
        chunks, _ = self.retrieve_with_stats(
            query,
            top_k=top_k,
            document_filter=document_filter,
            retrieval_profile=retrieval_profile,
            answer_mode=answer_mode,
            user_scope=user_scope,
            workspace_scope=workspace_scope,
        )
        return chunks

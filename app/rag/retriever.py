from dataclasses import dataclass

from app.db.repositories.vector_repository import VectorRepository
from app.models.domain.entities import RetrievedChunk
from app.rag.deduplicator import ChunkDeduplicator
from app.rag.diversifier import ChunkDiversifier
from app.rag.reranker import Reranker, SemanticReranker, suppress_near_duplicates
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

    def retrieve_with_stats(self, query: str, top_k: int, document_filter: str | None) -> tuple[list[RetrievedChunk], RetrievalStats]:
        query_embedding = self.embeddings.embed_query(query)
        raw_chunks = self.vectors.search_similar(query_embedding, top_k=top_k, document_filter=document_filter)
        filtered = [c for c in raw_chunks if c.score >= self.min_score_threshold]
        chunks = sorted(filtered, key=lambda c: (-c.score, c.chunk_id))
        deduped = self.deduplicator.deduplicate(chunks)
        duplicate_removed = max(0, len(chunks) - len(deduped))
        if self.enable_diversity:
            try:
                deduped = self.diversifier.diversify(deduped, top_k=max(top_k, self.rerank_top_n))
            except Exception:
                pass
        reranker_fallback = False
        chunks = deduped
        if self.enable_reranking and chunks:
            try:
                chunks = self.reranker.rerank(query, chunks)
            except Exception:
                # Fail-open to cosine baseline ordering for reliability.
                reranker_fallback = True
        chunks = suppress_near_duplicates(chunks, threshold=0.99999)
        out = chunks[:top_k]
        dropped = max(0, len(raw_chunks) - len(filtered))
        suppression_rate = (duplicate_removed / len(chunks)) if chunks else 0.0
        stats = RetrievalStats(
            chunks_retrieved=len(raw_chunks),
            chunks_after_filtering=len(filtered),
            threshold_rejections_chunk_total=dropped,
            threshold_rejections_query_total=1 if len(raw_chunks) > 0 and len(filtered) == 0 else 0,
            duplicate_chunks_removed=duplicate_removed,
            duplicate_suppression_rate=suppression_rate,
            reranker_fallback=reranker_fallback,
        )
        return out, stats

    def retrieve(self, query: str, top_k: int, document_filter: str | None) -> list[RetrievedChunk]:
        chunks, _ = self.retrieve_with_stats(query, top_k=top_k, document_filter=document_filter)
        return chunks

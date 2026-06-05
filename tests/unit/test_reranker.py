from datetime import datetime, timezone

from app.models.domain.entities import ChunkMetadata, RetrievedChunk
from app.rag.scopes import BENCHMARK_RETRIEVAL_USER_ID
from app.rag.retriever import Retriever
from app.rag.reranker import suppress_near_duplicates


def _chunk(chunk_id: str, text: str, score: float = 0.8) -> RetrievedChunk:
    md = ChunkMetadata(
        document_id="d1",
        filename="f.pdf",
        page_number=1,
        chunk_id=chunk_id,
        ingestion_timestamp=datetime.now(timezone.utc),
        owner_user_id=BENCHMARK_RETRIEVAL_USER_ID,
        workspace_id=BENCHMARK_RETRIEVAL_USER_ID,
    )
    return RetrievedChunk(chunk_id=chunk_id, score=score, metadata=md, text=text)


def test_duplicate_suppression_removes_near_duplicates():
    chunks = [
        _chunk("c1", "alpha beta gamma delta"),
        _chunk("c2", "alpha beta gamma delta"),
        _chunk("c3", "different content entirely"),
    ]
    out = suppress_near_duplicates(chunks, threshold=0.9)
    assert [c.chunk_id for c in out] == ["c1", "c3"]


class DummyEmbedding:
    def embed_query(self, query: str) -> list[float]:
        _ = query
        return [0.1]


class DummyRepo:
    def search_similar(
        self,
        query_embedding: list[float],
        top_k: int,
        document_filter: str | None,
        user_scope: str | None = None,
        workspace_scope: str | None = None,
    ):
        _ = query_embedding, top_k, document_filter
        _ = user_scope, workspace_scope
        return [_chunk("c2", "text two", 0.6), _chunk("c1", "text one", 0.6)]


class RaisingReranker:
    def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        _ = query, chunks
        raise RuntimeError("boom")


class IdentityReranker:
    def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        _ = query
        return chunks


def test_retriever_reranker_fail_open_behavior():
    retriever = Retriever(embeddings=DummyEmbedding(), vectors=DummyRepo(), enable_reranking=True)
    retriever.reranker = RaisingReranker()
    chunks = retriever.retrieve(
        "q",
        2,
        None,
        user_scope=BENCHMARK_RETRIEVAL_USER_ID,
        workspace_scope=BENCHMARK_RETRIEVAL_USER_ID,
    )
    assert [c.chunk_id for c in chunks] == ["c1", "c2"]


def test_retriever_keeps_deterministic_order_on_score_tie():
    retriever = Retriever(embeddings=DummyEmbedding(), vectors=DummyRepo(), enable_reranking=True)
    retriever.reranker = IdentityReranker()
    chunks = retriever.retrieve(
        "q",
        2,
        None,
        user_scope=BENCHMARK_RETRIEVAL_USER_ID,
        workspace_scope=BENCHMARK_RETRIEVAL_USER_ID,
    )
    assert [c.chunk_id for c in chunks] == ["c1", "c2"]

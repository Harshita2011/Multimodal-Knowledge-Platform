from __future__ import annotations

from datetime import datetime, timezone

from app.models.domain.entities import ChunkMetadata, RetrievedChunk
from app.rag.retriever import Retriever


class RecordingEmbedding:
    def embed_query(self, query: str) -> list[float]:
        _ = query
        return [1.0, 0.0, 0.0]


class RecordingVectorRepo:
    def __init__(self):
        self.calls: list[dict] = []

    def search_similar(self, query_embedding: list[float], top_k: int, document_filter: str | None = None, user_scope: str | None = None, workspace_scope: str | None = None):
        self.calls.append(
            {
                "query_embedding": query_embedding,
                "top_k": top_k,
                "document_filter": document_filter,
                "user_scope": user_scope,
                "workspace_scope": workspace_scope,
            }
        )
        md = ChunkMetadata(
            document_id="user_doc",
            filename="user.pdf",
            page_number=1,
            chunk_id="vector_c1",
            ingestion_timestamp=datetime.now(timezone.utc),
            owner_user_id=user_scope,
            workspace_id=workspace_scope,
        )
        return [RetrievedChunk(chunk_id="vector_c1", score=0.9, metadata=md, text="vector")]


class RecordingLexicalRepo:
    def __init__(self):
        self.bm25_calls: list[dict] = []
        self.entity_calls: list[dict] = []

    def search_bm25(self, query: str, top_k: int, document_filter: str | None = None, user_scope: str | None = None, workspace_scope: str | None = None):
        self.bm25_calls.append(
            {
                "query": query,
                "top_k": top_k,
                "document_filter": document_filter,
                "user_scope": user_scope,
                "workspace_scope": workspace_scope,
            }
        )
        md = ChunkMetadata(
            document_id="user_doc",
            filename="user.pdf",
            page_number=1,
            chunk_id="bm25_c1",
            ingestion_timestamp=datetime.now(timezone.utc),
            owner_user_id=user_scope,
            workspace_id=workspace_scope,
        )
        return [RetrievedChunk(chunk_id="bm25_c1", score=0.8, metadata=md, text="bm25")]

    def search_entities(self, query: str, top_k: int, document_filter: str | None = None, user_scope: str | None = None, workspace_scope: str | None = None):
        self.entity_calls.append(
            {
                "query": query,
                "top_k": top_k,
                "document_filter": document_filter,
                "user_scope": user_scope,
                "workspace_scope": workspace_scope,
            }
        )
        md = ChunkMetadata(
            document_id="user_doc",
            filename="user.pdf",
            page_number=1,
            chunk_id="entity_c1",
            ingestion_timestamp=datetime.now(timezone.utc),
            owner_user_id=user_scope,
            workspace_id=workspace_scope,
        )
        return [RetrievedChunk(chunk_id="entity_c1", score=0.7, metadata=md, text="entity")], ["alias"]


def test_retriever_threads_scope_through_every_channel():
    vectors = RecordingVectorRepo()
    lexical = RecordingLexicalRepo()
    retriever = Retriever(embeddings=RecordingEmbedding(), vectors=vectors, lexical=lexical, enable_reranking=False)

    chunks, stats = retriever.retrieve_with_stats(
        "query",
        top_k=3,
        document_filter="doc-a",
        user_scope="user-a",
        workspace_scope="workspace-a",
    )

    assert vectors.calls[0]["user_scope"] == "user-a"
    assert vectors.calls[0]["workspace_scope"] == "workspace-a"
    assert lexical.bm25_calls[0]["user_scope"] == "user-a"
    assert lexical.bm25_calls[0]["workspace_scope"] == "workspace-a"
    assert lexical.entity_calls[0]["user_scope"] == "user-a"
    assert lexical.entity_calls[0]["workspace_scope"] == "workspace-a"
    assert stats.trace["user_scope"] == "user-a"
    assert stats.trace["workspace_scope"] == "workspace-a"
    assert all(chunk.metadata.owner_user_id == "user-a" for chunk in chunks)


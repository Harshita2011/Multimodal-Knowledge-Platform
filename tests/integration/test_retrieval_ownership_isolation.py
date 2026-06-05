from __future__ import annotations

import asyncio
from pathlib import Path

import fitz
import pytest

from app.db.chroma_client import build_chroma_client
from app.db.repositories.chroma_repository import ChromaVectorRepository
from app.ingestion.chunker import PDFChunker
from app.ingestion.orchestrator import IngestionOrchestrator
from app.ingestion.parser import PDFParser
from app.models.domain.entities import ChunkMetadata, RetrievedChunk
from app.rag.retriever import Retriever
from app.rag.scopes import BENCHMARK_RETRIEVAL_USER_ID
from app.services.storage_service import LocalFileStorage


class FakeEmbeddingService:
    def _embed(self, text: str) -> list[float]:
        low = text.lower()
        return [
            1.0 if "alpha" in low else 0.0,
            1.0 if "beta" in low else 0.0,
            1.0 if "benchmark" in low else 0.0,
        ]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, query: str) -> list[float]:
        return self._embed(query)


class AsyncFile:
    def __init__(self, path: Path, filename: str):
        self._path = path
        self.filename = filename

    async def read(self) -> bytes:
        return self._path.read_bytes()


def _create_pdf(path: Path, lines: list[str]) -> None:
    doc = fitz.open()
    for line in lines:
        page = doc.new_page()
        page.insert_text((72, 72), line)
    doc.save(path)
    doc.close()


@pytest.fixture
def retriever_stack(tmp_path: Path):
    chroma_dir = tmp_path / "chroma"
    docs_dir = tmp_path / "docs"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    client = build_chroma_client(str(chroma_dir))
    vectors = ChromaVectorRepository(client=client, collection_name="test_retrieval_ownership")
    vectors.initialize_collection()
    embeddings = FakeEmbeddingService()

    ingestion = IngestionOrchestrator(
        parser=PDFParser(),
        chunker=PDFChunker(chunk_size=220, chunk_overlap=40),
        embedding_service=embeddings,
        vector_repository=vectors,
        storage=LocalFileStorage(base_dir=docs_dir),
        max_file_size_mb=25,
    )
    retriever = Retriever(embeddings=embeddings, vectors=vectors)
    return ingestion, retriever


def test_users_and_benchmark_corpus_are_isolated(retriever_stack, tmp_path: Path):
    ingestion, retriever = retriever_stack

    user_a_pdf = tmp_path / "user_a.pdf"
    user_b_pdf = tmp_path / "user_b.pdf"
    benchmark_pdf = tmp_path / "benchmark.pdf"
    _create_pdf(user_a_pdf, ["Alpha control for user A."])
    _create_pdf(user_b_pdf, ["Beta control for user B."])
    _create_pdf(benchmark_pdf, ["Benchmark corpus control for regression testing."])

    async def _ingest_all() -> None:
        await ingestion.ingest_pdf(AsyncFile(user_a_pdf, "user_a.pdf"), document_id="doc_a", owner_user_id="user-a", workspace_id="user-a")
        await ingestion.ingest_pdf(AsyncFile(user_b_pdf, "user_b.pdf"), document_id="doc_b", owner_user_id="user-b", workspace_id="user-b")
        await ingestion.ingest_pdf(
            AsyncFile(benchmark_pdf, "benchmark.pdf"),
            document_id="benchmark_doc",
            owner_user_id=BENCHMARK_RETRIEVAL_USER_ID,
            workspace_id=BENCHMARK_RETRIEVAL_USER_ID,
        )

    asyncio.run(_ingest_all())

    user_a_results = retriever.retrieve(
        "alpha control",
        top_k=5,
        document_filter=None,
        user_scope="user-a",
        workspace_scope="user-a",
    )
    user_b_results = retriever.retrieve(
        "beta control",
        top_k=5,
        document_filter=None,
        user_scope="user-b",
        workspace_scope="user-b",
    )

    assert user_a_results
    assert user_b_results
    assert all(chunk.metadata.owner_user_id == "user-a" for chunk in user_a_results)
    assert all(chunk.metadata.owner_user_id == "user-b" for chunk in user_b_results)
    assert all(chunk.metadata.document_id != "benchmark_doc" for chunk in user_a_results)
    assert all(chunk.metadata.document_id != "benchmark_doc" for chunk in user_b_results)

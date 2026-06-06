from __future__ import annotations

from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_ingestion_orchestrator, get_rag_orchestrator
from app.core.settings import get_settings
from app.core.telemetry import _analytics_state, reset_query_analytics_state
from app.db.chroma_client import build_chroma_client
from app.db.repositories.chroma_repository import ChromaVectorRepository
from app.ingestion.chunker import PDFChunker
from app.ingestion.orchestrator import IngestionOrchestrator
from app.ingestion.parser import PDFParser
from app.main import create_app
from app.rag.citation_mapper import CitationMapper
from app.rag.context_compressor import ContextCompressor
from app.rag.orchestrator import RagOrchestrator
from app.rag.prompt_builder import PromptBuilder
from app.rag.retriever import Retriever
from app.services.storage_service import LocalFileStorage


class FakeEmbeddingService:
    """Keyword-aware deterministic embeddings for integration tests."""

    def _embed(self, text: str) -> list[float]:
        t = text.lower()
        vec = [
            1.0 if "newton" in t or "physics" in t or "force" in t else 0.0,
            1.0 if "biology" in t or "cell" in t else 0.0,
            float(len(t) % 7) / 7.0,
        ]
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, query: str) -> list[float]:
        return self._embed(query)

    def health_check(self) -> None:
        return None


class FakeLLMService:
    def generate_answer(self, system_prompt: str, context: str, question: str) -> str:
        _ = system_prompt
        return f"Grounded answer for: {question}\n{context[:220]}"


def _create_fixture_pdf(path: Path, lines: list[str]) -> None:
    doc = fitz.open()
    for line in lines:
        page = doc.new_page()
        page.insert_text((72, 72), line)
    doc.save(path)
    doc.close()


@pytest.fixture
def client(tmp_path: Path):
    settings = get_settings()
    chroma_dir = tmp_path / "chroma"
    pdf_dir = tmp_path / "docs"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    client_chroma = build_chroma_client(str(chroma_dir))
    vector_repo = ChromaVectorRepository(
        client=client_chroma,
        collection_name=f"{settings.app_env}_{settings.app_name}_integration",
    )
    vector_repo.initialize_collection()

    embedding = FakeEmbeddingService()
    llm = FakeLLMService()
    storage = LocalFileStorage(base_dir=pdf_dir)

    ingestion_orchestrator = IngestionOrchestrator(
        parser=PDFParser(),
        chunker=PDFChunker(chunk_size=220, chunk_overlap=40),
        embedding_service=embedding,
        vector_repository=vector_repo,
        storage=storage,
        max_file_size_mb=25,
    )

    rag_orchestrator = RagOrchestrator(
        retriever=Retriever(embeddings=embedding, vectors=vector_repo),
        llm_service=llm,
        prompt_builder=PromptBuilder(max_context_chars=2500),
        citation_mapper=CitationMapper(),
        top_k_default=4,
        debug_enabled=True,
        context_compressor=ContextCompressor(),
    )

    app = create_app()
    app.dependency_overrides[get_ingestion_orchestrator] = lambda: ingestion_orchestrator
    app.dependency_overrides[get_rag_orchestrator] = lambda: rag_orchestrator

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_upload_ingest_query_returns_grounded_answer_and_citations(client: TestClient, tmp_path: Path):
    reset_query_analytics_state()
    pdf_path = tmp_path / "physics_notes.pdf"
    _create_fixture_pdf(
        pdf_path,
        [
            "Newton second law states force equals mass times acceleration.",
            "Biology studies cells and living organisms.",
        ],
    )

    with pdf_path.open("rb") as f:
        upload = client.post(
            "/api/v1/documents/upload",
            files={"file": ("physics_notes.pdf", f, "application/pdf")},
            data={"document_id": "physics_notes"},
        )

    assert upload.status_code == 200
    body = upload.json()
    assert body["document_id"] == "physics_notes"
    assert body["pages_processed"] == 2
    assert body["chunks_created"] >= 2

    query = client.post(
        "/api/v1/chat/query",
        json={"query": "What does Newton's second law describe?", "top_k": 3},
    )

    assert query.status_code == 200
    response = query.json()
    assert "Grounded answer" in response["answer"]
    assert len(response["citations"]) >= 1
    assert response["citations"][0]["filename"] == "physics_notes.pdf"
    assert response["retrieval_debug"]["top_k"] == 3
    assert _analytics_state["query_success_total"] >= 1
    assert _analytics_state["grounded_answer_total"] >= 1


def test_reupload_same_document_id_replaces_vectors(client: TestClient, tmp_path: Path):
    reset_query_analytics_state()
    first_pdf = tmp_path / "doc_v1.pdf"
    second_pdf = tmp_path / "doc_v2.pdf"

    _create_fixture_pdf(first_pdf, ["Biology is the study of cells and organisms."])
    _create_fixture_pdf(second_pdf, ["Newton's second law relates force, mass, and acceleration."])

    with first_pdf.open("rb") as f1:
        resp1 = client.post(
            "/api/v1/documents/upload",
            files={"file": ("doc_v1.pdf", f1, "application/pdf")},
            data={"document_id": "shared_doc"},
        )
    assert resp1.status_code == 200

    with second_pdf.open("rb") as f2:
        resp2 = client.post(
            "/api/v1/documents/upload",
            files={"file": ("doc_v2.pdf", f2, "application/pdf")},
            data={"document_id": "shared_doc"},
        )
    assert resp2.status_code == 200

    query = client.post(
        "/api/v1/chat/query",
        json={"query": "What is Newton's second law?", "document_filter": "shared_doc", "top_k": 2},
    )

    assert query.status_code == 200
    data = query.json()
    assert len(data["citations"]) >= 1
    assert all(c["chunk_id"].startswith("shared_doc_") for c in data["citations"])
    assert any("newton" in c["snippet"].lower() for c in data["citations"])


def test_query_with_high_threshold_tracks_empty_retrieval_and_rejections(client: TestClient, tmp_path: Path):
    reset_query_analytics_state()
    pdf_path = tmp_path / "threshold_doc.pdf"
    _create_fixture_pdf(pdf_path, ["Newton second law states force equals mass times acceleration."])

    with pdf_path.open("rb") as f:
        upload = client.post(
            "/api/v1/documents/upload",
            files={"file": ("threshold_doc.pdf", f, "application/pdf")},
            data={"document_id": "threshold_doc"},
        )
    assert upload.status_code == 200

    query = client.post(
        "/api/v1/chat/query",
        json={"query": "What does Newton's second law describe?", "document_filter": "missing_doc", "top_k": 3},
    )
    assert query.status_code == 200
    assert _analytics_state["empty_retrieval_total"] >= 1


def test_query_all_filtered_tracks_threshold_rejections(tmp_path: Path):
    reset_query_analytics_state()
    settings = get_settings()
    chroma_dir = tmp_path / "chroma_filtered"
    pdf_dir = tmp_path / "docs_filtered"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    client_chroma = build_chroma_client(str(chroma_dir))
    vector_repo = ChromaVectorRepository(
        client=client_chroma,
        collection_name=f"{settings.app_env}_{settings.app_name}_integration_filtered",
    )
    vector_repo.initialize_collection()

    embedding = FakeEmbeddingService()
    llm = FakeLLMService()
    storage = LocalFileStorage(base_dir=pdf_dir)

    ingestion_orchestrator = IngestionOrchestrator(
        parser=PDFParser(),
        chunker=PDFChunker(chunk_size=220, chunk_overlap=40),
        embedding_service=embedding,
        vector_repository=vector_repo,
        storage=storage,
        max_file_size_mb=25,
    )
    rag_orchestrator = RagOrchestrator(
        retriever=Retriever(embeddings=embedding, vectors=vector_repo, min_score_threshold=1.01),
        llm_service=llm,
        prompt_builder=PromptBuilder(max_context_chars=2500),
        citation_mapper=CitationMapper(),
        top_k_default=4,
        debug_enabled=True,
        context_compressor=ContextCompressor(),
    )

    app = create_app()
    app.dependency_overrides[get_ingestion_orchestrator] = lambda: ingestion_orchestrator
    app.dependency_overrides[get_rag_orchestrator] = lambda: rag_orchestrator

    pdf_path = tmp_path / "all_filtered.pdf"
    _create_fixture_pdf(pdf_path, ["Newton second law states force equals mass times acceleration."])
    with TestClient(app) as test_client:
        with pdf_path.open("rb") as f:
            upload = test_client.post(
                "/api/v1/documents/upload",
                files={"file": ("all_filtered.pdf", f, "application/pdf")},
                data={"document_id": "all_filtered"},
            )
        assert upload.status_code == 200
        query = test_client.post("/api/v1/chat/query", json={"query": "What does Newton's second law describe?", "top_k": 3})
        assert query.status_code == 200

    app.dependency_overrides.clear()
    assert _analytics_state["empty_retrieval_total"] >= 1
    assert _analytics_state["threshold_rejections_query_total"] >= 1
    assert _analytics_state["threshold_rejections_chunk_total"] >= 1

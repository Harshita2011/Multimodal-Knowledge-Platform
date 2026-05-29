import time
import uuid

from app.core.exceptions import AppError
from app.core.telemetry import StageTimer
from app.ingestion.chunker import PDFChunker
from app.ingestion.parser import PDFParser
from app.models.responses.rag import UploadResponse
from app.services.embedding_service import EmbeddingService
from app.services.storage_service import DocumentStorage
from app.db.repositories.vector_repository import VectorRepository
from app.ingestion.validators import validate_upload


class IngestionOrchestrator:
    def __init__(
        self,
        parser: PDFParser,
        chunker: PDFChunker,
        embedding_service: EmbeddingService,
        vector_repository: VectorRepository,
        storage: DocumentStorage,
        max_file_size_mb: int,
    ):
        self.parser = parser
        self.chunker = chunker
        self.embedding_service = embedding_service
        self.vector_repository = vector_repository
        self.storage = storage
        self.max_file_size_mb = max_file_size_mb

    async def ingest_pdf(self, file, document_id: str | None = None) -> UploadResponse:
        started = time.perf_counter()
        payload = await file.read()
        validate_upload(file, self.max_file_size_mb, len(payload))

        doc_id = document_id or str(uuid.uuid4())
        path = None

        try:
            # Idempotency policy: replace existing vectors on re-upload for same document_id.
            with StageTimer("ingestion.vector_delete", document_id=doc_id):
                self.vector_repository.delete_document(doc_id)
            with StageTimer("ingestion.file_save", document_id=doc_id):
                path = self.storage.save(payload, file.filename, doc_id)
            with StageTimer("ingestion.pdf_parse", document_id=doc_id):
                pages = self.parser.parse(path)
            if not pages:
                raise AppError("empty_pdf", "No extractable text found in PDF", 422)

            with StageTimer("ingestion.chunk", document_id=doc_id):
                chunks = self.chunker.chunk_pages(doc_id, file.filename, pages)
            with StageTimer("ingestion.embed", document_id=doc_id, chunk_count=len(chunks)):
                embeddings = self.embedding_service.embed_texts([c.text for c in chunks])
            with StageTimer("ingestion.vector_upsert", document_id=doc_id, chunk_count=len(chunks)):
                self.vector_repository.upsert_chunks(chunks, embeddings)
        except Exception:
            self.vector_repository.delete_document(doc_id)
            if path is not None:
                self.storage.delete(path)
            raise

        duration_ms = int((time.perf_counter() - started) * 1000)
        return UploadResponse(
            document_id=doc_id,
            filename=file.filename,
            pages_processed=len(pages),
            chunks_created=len(chunks),
            ingestion_timestamp=chunks[0].metadata.ingestion_timestamp.isoformat(),
            duration_ms=duration_ms,
        )

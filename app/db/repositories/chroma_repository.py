from datetime import datetime

from app.core.exceptions import AppError
from app.db.repositories.vector_repository import VectorRepository
from app.models.domain.entities import ChunkMetadata, DocumentChunk, RetrievedChunk


class ChromaVectorRepository(VectorRepository):
    def __init__(self, client, collection_name: str):
        self.client = client
        self.collection_name = collection_name
        self.collection = None

    def initialize_collection(self) -> None:
        self.collection = self.client.get_or_create_collection(name=self.collection_name, metadata={"hnsw:space": "cosine"})

    def collection_exists(self) -> bool:
        return self.collection is not None

    def upsert_chunks(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        if self.collection is None:
            self.initialize_collection()
        ids = [c.chunk_id for c in chunks]
        docs = [c.text for c in chunks]
        metas = []
        for c in chunks:
            md = c.metadata.model_dump(mode="json")
            md["entities"] = ",".join(c.metadata.entities)
            metas.append(md)
        self.collection.upsert(ids=ids, documents=docs, embeddings=embeddings, metadatas=metas)

    def search_similar(self, query_embedding: list[float], top_k: int, document_filter: str | None = None) -> list[RetrievedChunk]:
        if self.collection is None:
            self.initialize_collection()

        where = {"document_id": document_filter} if document_filter else None
        result = self.collection.query(query_embeddings=[query_embedding], n_results=top_k, where=where)

        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]

        output: list[RetrievedChunk] = []
        for idx, chunk_id in enumerate(ids):
            if idx >= len(docs) or idx >= len(metas):
                continue
            md = metas[idx]
            if not md:
                raise AppError("invalid_metadata", "Retrieved chunk metadata missing", 500)
            metadata = ChunkMetadata(
                document_id=md["document_id"],
                filename=md["filename"],
                page_number=int(md["page_number"]),
                chunk_id=md["chunk_id"],
                ingestion_timestamp=datetime.fromisoformat(md["ingestion_timestamp"]),
                source_type=md.get("source_type", "pdf"),
                modality=md.get("modality", "text"),
                doc_type=md.get("doc_type", "general"),
                section_path=md.get("section_path", ""),
                heading=md.get("heading", ""),
                block_type=md.get("block_type", "paragraph"),
                entities=[e.strip() for e in str(md.get("entities", "")).split(",") if e.strip()],
            )
            distance = float(distances[idx]) if idx < len(distances) else 1.0
            output.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    score=max(0.0, 1.0 - distance),
                    metadata=metadata,
                    text=docs[idx],
                )
            )
        return output

    def delete_document(self, document_id: str) -> None:
        if self.collection is None:
            self.initialize_collection()
        try:
            self.collection.delete(where={"document_id": document_id})
        except Exception as exc:
            raise AppError("vector_delete_failed", "Failed to delete existing document vectors", 500) from exc

from abc import ABC, abstractmethod

from app.models.domain.entities import DocumentChunk, RetrievedChunk


class VectorRepository(ABC):
    @abstractmethod
    def initialize_collection(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def collection_exists(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def upsert_chunks(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        raise NotImplementedError

    @abstractmethod
    def search_similar(
        self,
        query_embedding: list[float],
        top_k: int,
        document_filter: str | None = None,
        user_scope: str | None = None,
        workspace_scope: str | None = None,
    ) -> list[RetrievedChunk]:
        raise NotImplementedError

    @abstractmethod
    def delete_document(self, document_id: str) -> None:
        raise NotImplementedError

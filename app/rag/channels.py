from app.db.postgres.repositories.lexical_repo import LexicalPgRepository
from app.models.domain.entities import RetrievedChunk


class BM25Retriever:
    def __init__(self, lexical_repo: LexicalPgRepository):
        self.lexical_repo = lexical_repo

    def retrieve(self, query: str, top_k: int, document_filter: str | None = None) -> list[RetrievedChunk]:
        return self.lexical_repo.search_bm25(query=query, top_k=top_k, document_filter=document_filter)


class EntityRetriever:
    def __init__(self, lexical_repo: LexicalPgRepository):
        self.lexical_repo = lexical_repo

    def retrieve(self, query: str, top_k: int, document_filter: str | None = None) -> tuple[list[RetrievedChunk], list[str]]:
        return self.lexical_repo.search_entities(query=query, top_k=top_k, document_filter=document_filter)

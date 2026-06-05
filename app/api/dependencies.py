from functools import lru_cache
from sqlalchemy import create_engine

from app.core.resilience import RetryPolicy
from app.core.settings import get_settings
from app.db.postgres.repositories.lexical_repo import LexicalPgRepository
from app.db.postgres.session import normalize_sync_database_url
from app.db.chroma_client import build_chroma_client
from app.db.repositories.chroma_repository import ChromaVectorRepository
from app.ingestion.chunker import PDFChunker
from app.ingestion.orchestrator import IngestionOrchestrator
from app.ingestion.parser import PDFParser
from app.rag.citation_mapper import CitationMapper
from app.rag.context_compressor import ContextCompressor
from app.rag.orchestrator import RagOrchestrator
from app.rag.prompt_builder import PromptBuilder
from app.rag.retrieval_cache import RetrievalCache
from app.rag.retriever import Retriever
from app.services.embedding_service import SentenceTransformerEmbeddingService
from app.services.llm_service import GeminiLLMService
from app.services.storage_service import LocalFileStorage
from app.utils.tokenizer import build_tokenizer


@lru_cache
def get_embedding_service():
    s = get_settings()
    retry_policy = RetryPolicy(
        max_attempts=s.retry_max_attempts,
        initial_delay=s.retry_initial_delay_seconds,
        max_delay=s.retry_max_delay_seconds,
        exponential_backoff=s.retry_exponential_backoff,
        jitter=s.retry_jitter,
    )
    return SentenceTransformerEmbeddingService(
        model_name=s.embedding_model,
        batch_size=s.embedding_batch_size,
        timeout_seconds=s.external_timeout_seconds,
        retry_policy=retry_policy,
    )


@lru_cache
def get_vector_repository():
    s = get_settings()
    client = build_chroma_client(str(s.chroma_persist_dir))
    repo = ChromaVectorRepository(client=client, collection_name=s.full_collection_name)
    repo.initialize_collection()
    return repo


@lru_cache
def get_llm_service():
    s = get_settings()
    retry_policy = RetryPolicy(
        max_attempts=s.retry_max_attempts,
        initial_delay=s.retry_initial_delay_seconds,
        max_delay=s.retry_max_delay_seconds,
        exponential_backoff=s.retry_exponential_backoff,
        jitter=s.retry_jitter,
    )
    return GeminiLLMService(
        api_key=s.gemini_api_key,
        model=s.gemini_model,
        timeout_seconds=s.external_timeout_seconds,
        retry_policy=retry_policy,
    )


@lru_cache
def get_storage_service():
    s = get_settings()
    return LocalFileStorage(base_dir=s.pdf_storage_dir)


@lru_cache
def get_retrieval_cache() -> RetrievalCache:
    s = get_settings()
    return RetrievalCache(ttl_seconds=s.retrieval_cache_ttl_seconds, max_entries=s.retrieval_cache_max_entries)


@lru_cache
def get_lexical_repository() -> LexicalPgRepository:
    s = get_settings()
    engine = create_engine(normalize_sync_database_url(s.database_url), future=True)
    return LexicalPgRepository(engine=engine)


def get_ingestion_orchestrator() -> IngestionOrchestrator:
    s = get_settings()
    return IngestionOrchestrator(
        parser=PDFParser(),
        chunker=PDFChunker(chunk_size=s.chunk_size, chunk_overlap=s.chunk_overlap),
        embedding_service=get_embedding_service(),
        vector_repository=get_vector_repository(),
        storage=get_storage_service(),
        max_file_size_mb=s.max_file_size_mb,
        lexical_repository=get_lexical_repository(),
        retrieval_cache=get_retrieval_cache(),
    )


def get_rag_orchestrator() -> RagOrchestrator:
    s = get_settings()
    retriever = Retriever(
        embeddings=get_embedding_service(),
        vectors=get_vector_repository(),
        min_score_threshold=s.min_retrieval_score,
        enable_reranking=s.enable_reranking,
        rerank_top_n=s.rerank_top_n,
        duplicate_threshold=s.duplicate_similarity_threshold,
        enable_diversity=s.enable_diversity_retrieval,
        diversity_lambda=s.diversity_lambda,
        reranker_model_name=s.reranker_model_name,
        reranker_timeout_ms=s.reranker_max_latency_ms,
        lexical=get_lexical_repository(),
        retrieval_cache=get_retrieval_cache(),
        rrf_k=s.rrf_k,
    )
    return RagOrchestrator(
        retriever=retriever,
        llm_service=get_llm_service(),
        prompt_builder=PromptBuilder(
            max_context_chars=s.max_context_chars,
            max_context_tokens=s.resolved_context_token_budget,
            max_prompt_tokens=s.max_prompt_tokens or 8000,
            reserved_response_tokens=s.reserved_response_tokens or 1500,
            tokenizer=build_tokenizer(strict=s.tokenizer_strict),
        ),
        citation_mapper=CitationMapper(),
        top_k_default=s.top_k_default,
        debug_enabled=s.enable_debug_retrieval,
        context_compressor=ContextCompressor(),
    )

from datetime import datetime, timezone

from app.models.domain.entities import ChunkMetadata, RetrievedChunk
from app.rag.prompt_builder import PromptBuilder
from app.utils.tokenizer import HeuristicTokenizer


def _chunk(chunk_id: str, score: float, text: str) -> RetrievedChunk:
    md = ChunkMetadata(
        document_id="d1",
        filename="f.pdf",
        page_number=1,
        chunk_id=chunk_id,
        ingestion_timestamp=datetime.now(timezone.utc),
    )
    return RetrievedChunk(chunk_id=chunk_id, score=score, metadata=md, text=text)


def test_prompt_builder_enforces_token_budget_and_preserves_citation_ids():
    builder = PromptBuilder(
        max_context_tokens=10,
        max_prompt_tokens=20,
        reserved_response_tokens=5,
        tokenizer=HeuristicTokenizer(),
    )
    chunks = [
        _chunk("c1", 0.9, "alpha beta gamma delta epsilon zeta"),
        _chunk("c2", 0.8, "theta iota kappa lambda"),
    ]
    payload = builder.build_context_payload(chunks)
    assert payload.retrieved_context_tokens <= 15
    assert payload.context.startswith("[c1]")

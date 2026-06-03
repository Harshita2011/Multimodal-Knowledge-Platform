# RAG Architecture Audit

## Current Retrieval Flow (Before Upgrade)
- Query embedding -> vector similarity search (Chroma) -> threshold filter -> dedup/diversity -> optional reranker -> prompt build -> LLM -> citation snippets.
- Single retrieval path (dense vector), no query expansion, no profile routing.

## Upgraded MVP Flow (Implemented)
- Query understanding (intent heuristic) and profile routing (`FAST`, `BALANCED`, `DEEP`).
- Query expansion (multi-intent variants) and multi-pass vector retrieval.
- Hybrid-style boosting path via keyword/entity boosts and document-type heading bias.
- Dedup/diversity -> optional reranking -> context compression -> grounded generation.
- Quality scoring returned with response:
  - `retrieval_score`
  - `rerank_score`
  - `grounding_score`
  - `citation_coverage`

## Chunking & Document Understanding
- Previous: recursive split with light resume section hints.
- Upgraded:
  - document type detection (research paper, contract, technical docs, meeting notes, presentation, resume, general)
  - richer metadata on chunks: `doc_type`, `section_path`, `heading`, `block_type`, `entities`
  - entity extraction during ingestion.

## Embeddings / Vector Store / Reranker
- Embeddings: SentenceTransformers (`all-MiniLM-L6-v2` by default).
- Vector store: Chroma collection.
- Reranker: Cross-encoder (fail-open).
- Upgraded retriever now adapts candidate depth and rerank depth by retrieval profile.

## Prompting & Grounding
- System prompt upgraded from conservative fallback to enterprise grounded behavior:
  - answer when evidence exists
  - explain conflicts
  - state missing evidence explicitly
- Added soft-warn grounding checker for unsupported claims.

## Bottlenecks and Risks
- Chroma-only backend can become a bottleneck at very large scale without sharding/index tiering.
- Intent and doc-type classification are heuristic; should be upgraded to model-driven classification later.
- Entity indexing is currently lightweight string-based, not full NER ontology.
- Keyword/BM25 path is approximated via boosts in this MVP slice; dedicated lexical index is next step.

## Scalability Concerns
- Millions of chunks will require:
  - dedicated lexical store (Postgres FTS/BM25 or OpenSearch),
  - background indexing pipelines,
  - ANN tuning + partitioning,
  - cache layers for hot queries.

## Hallucination Risks
- Reduced by grounding prompt, citation generation, and claim support checks.
- Residual risk remains for abstractive synthesis when evidence is sparse or conflicting.

## Next Priorities
1. Add true Postgres FTS/BM25 channel + RRF fusion.
2. Promote entity index into dedicated searchable table.
3. Add strict grounding mode toggle (prune unsupported claims).
4. Expand evaluation harness with groundedness/faithfulness against labeled sets.

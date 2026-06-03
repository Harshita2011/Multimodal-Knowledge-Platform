# Enterprise RAG V1.1

## Architecture Diagram
```text
User Query
  -> Query Planner (intent + profile + expansion)
  -> Retrieval Cache lookup
    -> Vector Retrieval (Chroma)
    -> BM25 Retrieval (Postgres FTS + trigram)
    -> Entity Retrieval (Postgres entities/chunk_entities)
  -> RRF Fusion (k-configurable)
  -> Reranker (cross-encoder)
  -> Context Compression
  -> Grounded Generation
  -> Grounding Evaluator
  -> Response (+quality +grounding +retrieval_trace)
```

## New DB Schema
- `chunks` (authoritative lexical/entity retrieval chunk index; no parallel retrieval table)
- `entities` (normalized entity dictionary)
- `chunk_entities` (entity-to-chunk mapping)

## Migration
- `alembic/versions/0003_fts_entities_chunks.py`
- Enables `pg_trgm`, `unaccent`
- Adds FTS/trigram/indexes for lexical retrieval and fuzzy matching.

## New Retrieval Components
- `BM25Retriever` (`app/rag/channels.py`)
- `EntityRetriever` (`app/rag/channels.py`)
- `RRFMerger` (`app/rag/rrf.py`)
- `RetrievalCache` (`app/rag/retrieval_cache.py`)
- `LexicalPgRepository` (`app/db/postgres/repositories/lexical_repo.py`)

## API Contract Additions (Additive)
- `QueryResponse.quality`
- `QueryResponse.grounding`
- `QueryResponse.retrieval_trace`

## Explainability Payload
Per chunk in `retrieval_trace.explainability`:
- `chunk_id`
- `retrieval_source`
- `vector_score`
- `bm25_score`
- `entity_score`
- `rrf_score`
- `rerank_score`

## Benchmark / Gate Commands
```bash
python scripts/evaluate_retrieval.py --output-json > reports_v11.json
python scripts/check_release_gates.py --report reports_v11.json
```

Optional baseline comparison:
```bash
python scripts/compare_benchmarks.py --baseline reports_baseline.json --candidate reports_v11.json --output benchmark_comparison.json
```

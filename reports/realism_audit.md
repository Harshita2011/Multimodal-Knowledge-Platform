# Realism Audit Report

## Preflight
- execution_mode: live
- coverage: 100.00%
- excluded_queries: 0

## vector_only
- unique_rrf_scores: 1
- unique_rerank_scores: 298
- rrf_stdev: 0.00000000
- rerank_stdev: 0.16622369
- FLAG: RRF scores are near-constant; evaluation may be non-representative.
- FLAG: Missing retrieval_source diagnostics detected.

## vector_bm25
- unique_rrf_scores: 1
- unique_rerank_scores: 298
- rrf_stdev: 0.00000000
- rerank_stdev: 0.16622369
- FLAG: RRF scores are near-constant; evaluation may be non-representative.
- FLAG: Missing retrieval_source diagnostics detected.

## vector_entity
- unique_rrf_scores: 1
- unique_rerank_scores: 251
- rrf_stdev: 0.00000000
- rerank_stdev: 0.29183123
- FLAG: RRF scores are near-constant; evaluation may be non-representative.
- FLAG: Missing retrieval_source diagnostics detected.

## vector_bm25_entity
- unique_rrf_scores: 1
- unique_rerank_scores: 251
- rrf_stdev: 0.00000000
- rerank_stdev: 0.29183123
- FLAG: RRF scores are near-constant; evaluation may be non-representative.
- FLAG: Missing retrieval_source diagnostics detected.

## vector_bm25_entity_rrf
- unique_rrf_scores: 11
- unique_rerank_scores: 251
- rrf_stdev: 0.03110251
- rerank_stdev: 0.27980643

## Benchmark Weaknesses
- vector_only: RRF scores are near-constant; evaluation may be non-representative.
- vector_only: Missing retrieval_source diagnostics detected.
- vector_bm25: RRF scores are near-constant; evaluation may be non-representative.
- vector_bm25: Missing retrieval_source diagnostics detected.
- vector_entity: RRF scores are near-constant; evaluation may be non-representative.
- vector_entity: Missing retrieval_source diagnostics detected.
- vector_bm25_entity: RRF scores are near-constant; evaluation may be non-representative.
- vector_bm25_entity: Missing retrieval_source diagnostics detected.
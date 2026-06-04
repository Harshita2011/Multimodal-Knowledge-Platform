# Retrieval Diagnostics

- Dataset version: `retrieval-stress-v1-diagnostics`
- Queries evaluated: 100
- Categories: BM25-dominant, Entity-dominant, Hybrid-dominant, Multi-hop-dominant, Vector-dominant
- Preflight coverage: 100.00%

## Category Winners Before Reranking
- BM25-dominant: Vector Only | score=0.9475 | mrr=1.0000 | recall@10=0.9250 | delta_vs_vector=0.00%
- Entity-dominant: Vector + Entity | score=0.5925 | mrr=0.5750 | recall@10=0.6000 | delta_vs_vector=27.24%
- Hybrid-dominant: Vector + Entity | score=0.6742 | mrr=0.5750 | recall@10=0.7167 | delta_vs_vector=44.21%
- Multi-hop-dominant: Vector + Entity | score=0.7788 | mrr=0.4375 | recall@10=0.9250 | delta_vs_vector=6.24%
- Vector-dominant: Vector Only | score=0.7138 | mrr=0.5125 | recall@10=0.8000 | delta_vs_vector=0.00%

## Category Winners After Reranking
- BM25-dominant: Vector Only | score=0.9475 | mrr=1.0000 | recall@10=0.9250 | delta_vs_vector=0.00%
- Entity-dominant: Vector + Entity | score=0.4857 | mrr=0.3357 | recall@10=0.5500 | delta_vs_vector=2.12%
- Hybrid-dominant: Vector + BM25 + Entity + RRF | score=0.5342 | mrr=0.5750 | recall@10=0.5167 | delta_vs_vector=14.67%
- Multi-hop-dominant: Vector + BM25 + Entity | score=0.9400 | mrr=0.9750 | recall@10=0.9250 | delta_vs_vector=13.25%
- Vector-dominant: Vector Only | score=0.7338 | mrr=0.5792 | recall@10=0.8000 | delta_vs_vector=0.00%

## Relative Improvements Before Reranking

### BM25-dominant
- Vector + BM25: score=0.00% | mrr=0.00% | recall@10=0.00%
- Vector + Entity: score=0.00% | mrr=0.00% | recall@10=0.00%
- Vector + BM25 + Entity: score=0.00% | mrr=0.00% | recall@10=0.00%
- Vector + BM25 + Entity + RRF: score=-1.27% | mrr=-4.00% | recall@10=0.00%

### Entity-dominant
- Vector + BM25: score=0.00% | mrr=0.00% | recall@10=0.00%
- Vector + Entity: score=27.24% | mrr=113.83% | recall@10=9.09%
- Vector + BM25 + Entity: score=27.24% | mrr=113.83% | recall@10=9.09%
- Vector + BM25 + Entity + RRF: score=27.24% | mrr=113.83% | recall@10=9.09%

### Hybrid-dominant
- Vector + BM25: score=0.00% | mrr=0.00% | recall@10=0.00%
- Vector + Entity: score=44.21% | mrr=13.11% | recall@10=59.26%
- Vector + BM25 + Entity: score=44.21% | mrr=13.11% | recall@10=59.26%
- Vector + BM25 + Entity + RRF: score=44.21% | mrr=13.11% | recall@10=59.26%

### Multi-hop-dominant
- Vector + BM25: score=0.00% | mrr=0.00% | recall@10=0.00%
- Vector + Entity: score=6.24% | mrr=-45.99% | recall@10=32.14%
- Vector + BM25 + Entity: score=6.24% | mrr=-45.99% | recall@10=32.14%
- Vector + BM25 + Entity + RRF: score=3.85% | mrr=-45.99% | recall@10=28.57%

### Vector-dominant
- Vector + BM25: score=0.00% | mrr=0.00% | recall@10=0.00%
- Vector + Entity: score=-1.05% | mrr=-4.88% | recall@10=0.00%
- Vector + BM25 + Entity: score=-1.05% | mrr=-4.88% | recall@10=0.00%
- Vector + BM25 + Entity + RRF: score=-1.05% | mrr=-4.88% | recall@10=0.00%

## Relative Improvements After Reranking

### BM25-dominant
- Vector + BM25: score=0.00% | mrr=0.00% | recall@10=0.00%
- Vector + Entity: score=0.00% | mrr=0.00% | recall@10=0.00%
- Vector + BM25 + Entity: score=0.00% | mrr=0.00% | recall@10=0.00%
- Vector + BM25 + Entity + RRF: score=0.00% | mrr=0.00% | recall@10=0.00%

### Entity-dominant
- Vector + BM25: score=0.00% | mrr=0.00% | recall@10=0.00%
- Vector + Entity: score=2.12% | mrr=11.11% | recall@10=0.00%
- Vector + BM25 + Entity: score=2.12% | mrr=11.11% | recall@10=0.00%
- Vector + BM25 + Entity + RRF: score=2.12% | mrr=11.11% | recall@10=0.00%

### Hybrid-dominant
- Vector + BM25: score=0.00% | mrr=0.00% | recall@10=0.00%
- Vector + Entity: score=10.02% | mrr=0.00% | recall@10=15.38%
- Vector + BM25 + Entity: score=10.02% | mrr=0.00% | recall@10=15.38%
- Vector + BM25 + Entity + RRF: score=14.67% | mrr=6.15% | recall@10=19.23%

### Multi-hop-dominant
- Vector + BM25: score=0.00% | mrr=0.00% | recall@10=0.00%
- Vector + Entity: score=11.90% | mrr=4.17% | recall@10=15.62%
- Vector + BM25 + Entity: score=13.25% | mrr=8.33% | recall@10=15.62%
- Vector + BM25 + Entity + RRF: score=9.79% | mrr=4.17% | recall@10=12.50%

### Vector-dominant
- Vector + BM25: score=0.00% | mrr=0.00% | recall@10=0.00%
- Vector + Entity: score=0.00% | mrr=0.00% | recall@10=0.00%
- Vector + BM25 + Entity: score=0.00% | mrr=0.00% | recall@10=0.00%
- Vector + BM25 + Entity + RRF: score=0.00% | mrr=0.00% | recall@10=0.00%

## Cases Where Vector-Only Wins
- None.

## Cases Where BM25 Wins
- None.

## Cases Where Entity Retrieval Wins
- None.

## Cases Where RRF Wins
- [Hybrid-dominant] HBX-511 js MERGE01 cookie hydration rollout safeguard | score=0.616667
- [Hybrid-dominant] Which control avoids partially initialized sessions during staged exposure for HBX-511 MERGE01 on js workloads? | score=0.616667
- [Hybrid-dominant] Find the rollout rule behind HBX-510 MERGE00 state divergence protection for k8s. | score=0.533333
- [Hybrid-dominant] Find the rollout rule behind HBX-511 MERGE01 state divergence protection for js. | score=0.533333

## Reranking Convergence
- average_spread_before_rerank: 0.1052
- average_spread_after_rerank: 0.0434
- spread_delta_after_minus_before: -0.0618
- collapsed_non_vector_wins: 0

## Cases Where Reranking Removes Differences
- None detected.

## Category Spread Before Reranking
- BM25-dominant: avg_spread=0.0120, max_spread=0.2400
- Entity-dominant: avg_spread=0.1418, max_spread=0.9769
- Hybrid-dominant: avg_spread=0.2067, max_spread=0.2833
- Multi-hop-dominant: avg_spread=0.1583, max_spread=0.3500
- Vector-dominant: avg_spread=0.0075, max_spread=0.1500

## Category Spread After Reranking
- BM25-dominant: avg_spread=0.0000, max_spread=0.0000
- Entity-dominant: avg_spread=0.0101, max_spread=0.2000
- Hybrid-dominant: avg_spread=0.0683, max_spread=0.2833
- Multi-hop-dominant: avg_spread=0.1388, max_spread=0.5750
- Vector-dominant: avg_spread=0.0000, max_spread=0.0000

## Reranker Fallback Rate
- Vector Only: 0.00%
- Vector + BM25: 0.00%
- Vector + Entity: 0.00%
- Vector + BM25 + Entity + RRF: 0.00%
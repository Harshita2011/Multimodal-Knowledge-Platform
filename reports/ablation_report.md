# Retrieval Stress Ablation Report

- Dataset version: `retrieval-stress-v1`
- Source documents: 160
- Evaluation queries: 512
- Preflight coverage: 100.00%
- Benchmark quality flag: OK
- Quality rationale: Category-level and overall deltas show measurable separation.

## Overall Metric Deltas vs Vector Only

### Vector + BM25
- recall_at_5: 0.00%
- recall_at_10: 0.00%
- recall_at_20: 0.00%
- mrr: 0.00%
- ndcg: 0.00%
- citation_accuracy: 0.00%
- grounding_score: 0.00%
- claim_support_rate: 0.00%
- p50_latency_ms: 46.32%
- p95_latency_ms: 47.87%

### Vector + Entity
- recall_at_5: -10.78%
- recall_at_10: -3.19%
- recall_at_20: -5.09%
- mrr: -19.41%
- ndcg: -14.24%
- citation_accuracy: -5.03%
- grounding_score: -5.03%
- claim_support_rate: -5.03%
- p50_latency_ms: 13.58%
- p95_latency_ms: 27.74%

### Vector + BM25 + Entity
- recall_at_5: -10.78%
- recall_at_10: -3.19%
- recall_at_20: -5.09%
- mrr: -19.41%
- ndcg: -14.24%
- citation_accuracy: -5.03%
- grounding_score: -5.03%
- claim_support_rate: -5.03%
- p50_latency_ms: 53.93%
- p95_latency_ms: 55.87%

### Vector + BM25 + Entity + RRF
- recall_at_5: -11.44%
- recall_at_10: -3.35%
- recall_at_20: -5.25%
- mrr: -19.66%
- ndcg: -14.63%
- citation_accuracy: -5.03%
- grounding_score: -5.03%
- claim_support_rate: -5.03%
- p50_latency_ms: 54.83%
- p95_latency_ms: 57.20%

## Category Breakdown

### Ambiguous Queries
- winning_channel: Vector Only
- winner_score: 1.0000
- winner_mrr: 1.0000
- winner_recall_at_10: 1.0000
- delta_vs_vector_score: 0.0000
- vector_only_mrr: 1.0000
- vector_only_recall_at_10: 1.0000
- vector_bm25: mrr=1.0000, recall_at_10=1.0000, citation_accuracy=1.0000
- vector_entity: mrr=0.8333, recall_at_10=1.0000, citation_accuracy=1.0000
- vector_bm25_entity: mrr=0.8333, recall_at_10=1.0000, citation_accuracy=1.0000
- vector_bm25_entity_rrf: mrr=0.8333, recall_at_10=1.0000, citation_accuracy=1.0000

### BM25-Dominant
- winning_channel: Vector Only
- winner_score: 0.9398
- winner_mrr: 1.0000
- winner_recall_at_10: 0.9141
- delta_vs_vector_score: 0.0000
- vector_only_mrr: 1.0000
- vector_only_recall_at_10: 0.9141
- vector_bm25: mrr=1.0000, recall_at_10=0.9141, citation_accuracy=1.0000
- vector_entity: mrr=1.0000, recall_at_10=0.9141, citation_accuracy=1.0000
- vector_bm25_entity: mrr=1.0000, recall_at_10=0.9141, citation_accuracy=1.0000
- vector_bm25_entity_rrf: mrr=0.9875, recall_at_10=0.9141, citation_accuracy=1.0000

### Dense-Dominant
- winning_channel: Vector Only
- winner_score: 0.2230
- winner_mrr: 0.1602
- winner_recall_at_10: 0.2500
- delta_vs_vector_score: 0.0000
- vector_only_mrr: 0.1602
- vector_only_recall_at_10: 0.2500
- vector_bm25: mrr=0.1602, recall_at_10=0.2500, citation_accuracy=0.2500
- vector_entity: mrr=0.1523, recall_at_10=0.2500, citation_accuracy=0.2500
- vector_bm25_entity: mrr=0.1523, recall_at_10=0.2500, citation_accuracy=0.2500
- vector_bm25_entity_rrf: mrr=0.1523, recall_at_10=0.2500, citation_accuracy=0.2500

### Entity-Dominant
- winning_channel: Vector + Entity
- winner_score: 0.1852
- winner_mrr: 0.1797
- winner_recall_at_10: 0.1875
- delta_vs_vector_score: 0.0396
- vector_only_mrr: 0.0840
- vector_only_recall_at_10: 0.1719
- vector_bm25: mrr=0.0840, recall_at_10=0.1719, citation_accuracy=0.1719
- vector_entity: mrr=0.1797, recall_at_10=0.1875, citation_accuracy=0.1875
- vector_bm25_entity: mrr=0.1797, recall_at_10=0.1875, citation_accuracy=0.1875
- vector_bm25_entity_rrf: mrr=0.1797, recall_at_10=0.1875, citation_accuracy=0.1875

### Hybrid-Dominant
- winning_channel: Vector + Entity
- winner_score: 0.4451
- winner_mrr: 0.3776
- winner_recall_at_10: 0.4740
- delta_vs_vector_score: 0.0401
- vector_only_mrr: 0.4870
- vector_only_recall_at_10: 0.3698
- vector_bm25: mrr=0.4870, recall_at_10=0.3698, citation_accuracy=1.0000
- vector_entity: mrr=0.3776, recall_at_10=0.4740, citation_accuracy=1.0000
- vector_bm25_entity: mrr=0.3776, recall_at_10=0.4740, citation_accuracy=1.0000
- vector_bm25_entity_rrf: mrr=0.3776, recall_at_10=0.4740, citation_accuracy=1.0000

### Long Context
- winning_channel: Vector Only
- winner_score: 0.5625
- winner_mrr: 0.5625
- winner_recall_at_10: 0.5625
- delta_vs_vector_score: 0.0000
- vector_only_mrr: 0.5625
- vector_only_recall_at_10: 0.5625
- vector_bm25: mrr=0.5625, recall_at_10=0.5625, citation_accuracy=0.5625
- vector_entity: mrr=0.5391, recall_at_10=0.5625, citation_accuracy=0.5625
- vector_bm25_entity: mrr=0.5391, recall_at_10=0.5625, citation_accuracy=0.5625
- vector_bm25_entity_rrf: mrr=0.5391, recall_at_10=0.5625, citation_accuracy=0.5625

### Multi-Hop
- winning_channel: Vector + Entity
- winner_score: 0.6109
- winner_mrr: 0.4688
- winner_recall_at_10: 0.6719
- delta_vs_vector_score: 0.0216
- vector_only_mrr: 0.6702
- vector_only_recall_at_10: 0.5547
- vector_bm25: mrr=0.6702, recall_at_10=0.5547, citation_accuracy=0.9219
- vector_entity: mrr=0.4688, recall_at_10=0.6719, citation_accuracy=1.0000
- vector_bm25_entity: mrr=0.4688, recall_at_10=0.6719, citation_accuracy=1.0000
- vector_bm25_entity_rrf: mrr=0.4688, recall_at_10=0.6641, citation_accuracy=1.0000

### Noisy Documents
- winning_channel: Vector Only
- winner_score: 0.9876
- winner_mrr: 0.9588
- winner_recall_at_10: 1.0000
- delta_vs_vector_score: 0.0000
- vector_only_mrr: 0.9588
- vector_only_recall_at_10: 1.0000
- vector_bm25: mrr=0.9588, recall_at_10=1.0000, citation_accuracy=1.0000
- vector_entity: mrr=0.4164, recall_at_10=0.6094, citation_accuracy=0.6094
- vector_bm25_entity: mrr=0.4164, recall_at_10=0.6094, citation_accuracy=0.6094
- vector_bm25_entity_rrf: mrr=0.4164, recall_at_10=0.6094, citation_accuracy=0.6094

## Retrieval Failures
- [Dense-Dominant] Describe the method used to cut hands-on rescue work before an availability zone starts wobbling. | expected=['dense_semantic_04_p3_c1'] | top3=['dense_semantic_00_p4_c0', 'dense_semantic_06_p1_c0', 'dense_semantic_00_p3_c1']
- [Dense-Dominant] Describe the method used to cut hands-on rescue work before an availability zone starts wobbling. | expected=['dense_semantic_08_p3_c1'] | top3=['dense_semantic_00_p4_c0', 'dense_semantic_06_p1_c0', 'dense_semantic_00_p3_c1']
- [Dense-Dominant] Describe the method used to cut hands-on rescue work before an availability zone starts wobbling. | expected=['dense_semantic_12_p3_c1'] | top3=['dense_semantic_00_p4_c0', 'dense_semantic_06_p1_c0', 'dense_semantic_00_p3_c1']
- [Dense-Dominant] Describe the method used to keep generated answers from wandering outside policy boundaries. | expected=['dense_semantic_06_p3_c1'] | top3=['dense_semantic_02_p3_c1', 'dense_semantic_02_p4_c0', 'dense_semantic_06_p1_c0']
- [Dense-Dominant] Describe the method used to keep generated answers from wandering outside policy boundaries. | expected=['dense_semantic_10_p3_c1'] | top3=['dense_semantic_02_p3_c1', 'dense_semantic_02_p4_c0', 'dense_semantic_06_p1_c0']
- [Dense-Dominant] Describe the method used to keep generated answers from wandering outside policy boundaries. | expected=['dense_semantic_14_p3_c1'] | top3=['dense_semantic_02_p3_c1', 'dense_semantic_02_p4_c0', 'dense_semantic_06_p1_c0']
- [Dense-Dominant] Describe the method used to lower customer pain when a rollout starts degrading quietly. | expected=['dense_semantic_07_p3_c1'] | top3=['hybrid_entity_01_p1_c0', 'dense_semantic_03_p4_c0', 'dense_semantic_03_p3_c1']
- [Dense-Dominant] Describe the method used to lower customer pain when a rollout starts degrading quietly. | expected=['dense_semantic_11_p3_c1'] | top3=['hybrid_entity_01_p1_c0', 'dense_semantic_03_p4_c0', 'dense_semantic_03_p3_c1']
- [Dense-Dominant] Describe the method used to lower customer pain when a rollout starts degrading quietly. | expected=['dense_semantic_15_p3_c1'] | top3=['hybrid_entity_01_p1_c0', 'dense_semantic_03_p4_c0', 'dense_semantic_03_p3_c1']
- [Dense-Dominant] Describe the method used to reduce the chance that a stolen session can act like a real employee. | expected=['dense_semantic_05_p3_c1'] | top3=['dense_semantic_01_p3_c1', 'hybrid_target_00_p1_c0', 'incident_response_runbook_p8_c1']
- [Dense-Dominant] Describe the method used to reduce the chance that a stolen session can act like a real employee. | expected=['dense_semantic_09_p3_c1'] | top3=['dense_semantic_01_p3_c1', 'hybrid_target_00_p1_c0', 'incident_response_runbook_p8_c1']
- [Dense-Dominant] Describe the method used to reduce the chance that a stolen session can act like a real employee. | expected=['dense_semantic_13_p3_c1'] | top3=['dense_semantic_01_p3_c1', 'hybrid_target_00_p1_c0', 'incident_response_runbook_p8_c1']
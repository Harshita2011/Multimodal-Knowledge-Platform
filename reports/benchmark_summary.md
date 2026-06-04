# Benchmark Summary

- Dataset size (input): 320
- Dataset size (evaluated): 320
- Preflight coverage: 100.00%
- Final PASS/FAIL: **PASS**

## Component Contribution Metrics (% vs Vector Only)

### vector_bm25
- recall_at_5: 0.00%
- recall_at_10: 0.00%
- recall_at_20: 0.00%
- mrr: 0.00%
- ndcg: 0.00%
- citation_accuracy: 0.00%
- grounding_score: 0.00%
- claim_support_rate: 0.00%
- p50_latency_ms: 14.34%
- p95_latency_ms: 9.68%
- note: no measurable retrieval-quality gain over `vector_only` in this run.

### vector_entity
- recall_at_5: 0.00%
- recall_at_10: 0.00%
- recall_at_20: 0.00%
- mrr: 0.00%
- ndcg: 0.00%
- citation_accuracy: 0.00%
- grounding_score: 0.00%
- claim_support_rate: 0.00%
- p50_latency_ms: 20.86%
- p95_latency_ms: 17.62%
- note: no measurable retrieval-quality gain over `vector_only` in this run.

### vector_bm25_entity
- recall_at_5: 0.00%
- recall_at_10: 0.00%
- recall_at_20: 0.00%
- mrr: 0.00%
- ndcg: 0.00%
- citation_accuracy: 0.00%
- grounding_score: 0.00%
- claim_support_rate: 0.00%
- p50_latency_ms: 27.72%
- p95_latency_ms: 23.86%
- note: no measurable retrieval-quality gain over `vector_only` in this run.

### vector_bm25_entity_rrf
- recall_at_5: 0.00%
- recall_at_10: 0.00%
- recall_at_20: 0.00%
- mrr: 0.00%
- ndcg: 0.00%
- citation_accuracy: 0.00%
- grounding_score: 0.00%
- claim_support_rate: 0.00%
- p50_latency_ms: 39.36%
- p95_latency_ms: 36.97%
- note: no measurable retrieval-quality gain over `vector_only` in this run.

## Retrieval Failure Examples

## Retrieval Success Examples
- What safeguards are specified for privileged access? | expected=['security_policy_v2_p12_c3'] | top3=['security_policy_v2_p12_c3']
- How does the platform protect sensitive data at rest? | expected=['security_policy_v2_p12_c3'] | top3=['security_policy_v2_p12_c3']
- Which resiliency measures are defined for outages? | expected=['security_policy_v2_p12_c3'] | top3=['security_policy_v2_p12_c3']
- What does the document specify for MFA in admin workflows? | expected=['security_policy_v2_p12_c3'] | top3=['security_policy_v2_p12_c3']
- How is SSO integrated with API authentication? | expected=['security_policy_v2_p12_c3'] | top3=['security_policy_v2_p12_c3']
- What SLA constraints are documented for uptime? | expected=['security_policy_v2_p12_c3'] | top3=['security_policy_v2_p12_c3']
- What does this corpus say about k8s reliability controls? | expected=['security_policy_v2_p12_c3'] | top3=['security_policy_v2_p12_c3']
- What guidance is provided for JS runtime security? | expected=['security_policy_v2_p12_c3'] | top3=['security_policy_v2_p12_c3']

## Top Queries Improved by BM25
- None detected in this run.

## Top Queries Improved by Entity Retrieval
- None detected in this run.

## Top Queries Improved by RRF
- None detected in this run.
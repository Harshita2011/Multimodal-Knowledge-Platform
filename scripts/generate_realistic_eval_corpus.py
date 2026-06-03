import json
from pathlib import Path


SCENARIOS = [
    "synonym",
    "acronym",
    "entity_alias",
    "keyword_heavy",
    "semantic_only",
    "conflicting_documents",
    "multi_document",
    "ambiguous",
    "long_context",
    "technical_doc",
]


DOCS = [
    ("security_policy_v2.pdf", "security policy", "security controls and access policies", 12, "security_policy_v2_p12_c3"),
    ("incident_response_runbook.pdf", "incident response", "incident handling and escalation", 8, "incident_response_runbook_p8_c1"),
    ("kubernetes_ops_manual.pdf", "kubernetes", "cluster operations and reliability", 14, "kubernetes_ops_manual_p14_c2"),
    ("javascript_platform_guide.pdf", "javascript", "frontend platform standards", 5, "javascript_platform_guide_p5_c0"),
    ("llm_governance_framework.pdf", "large language model", "llm policy and governance", 9, "llm_governance_framework_p9_c1"),
    ("api_gateway_reference.pdf", "api gateway", "api gateway auth and routing", 7, "api_gateway_reference_p7_c2"),
    ("data_retention_policy.pdf", "data retention", "retention schedules and deletion", 3, "data_retention_policy_p3_c0"),
    ("privacy_impact_assessment.pdf", "privacy", "privacy controls and pii handling", 6, "privacy_impact_assessment_p6_c2"),
    ("release_notes_v1_v2.pdf", "release notes", "version issues and fixes", 10, "release_notes_v1_v2_p10_c1"),
    ("architecture_decisions_log.pdf", "architecture", "design tradeoffs and decisions", 4, "architecture_decisions_log_p4_c1"),
]


TEMPLATES = {
    "synonym": [
        "What safeguards are specified for privileged access?",
        "How does the platform protect sensitive data at rest?",
        "Which resiliency measures are defined for outages?",
    ],
    "acronym": [
        "What does the document specify for MFA in admin workflows?",
        "How is SSO integrated with API authentication?",
        "What SLA constraints are documented for uptime?",
    ],
    "entity_alias": [
        "What does this corpus say about k8s reliability controls?",
        "What guidance is provided for JS runtime security?",
        "How does the policy govern LLM usage in production?",
    ],
    "keyword_heavy": [
        "authentication authorization encryption compliance controls",
        "kubernetes cluster autoscaling pod disruption budget",
        "api gateway timeout retry backoff circuit breaker",
    ],
    "semantic_only": [
        "How should we reduce user-impact during production failures?",
        "What pattern is recommended for handling identity risk?",
        "How should model outputs be constrained to policy?",
    ],
    "conflicting_documents": [
        "Which timeout is correct when one document says 30s and another says 60s?",
        "What is the reconciled retention period across conflicting policies?",
        "Do versions disagree on deprecation timelines?",
    ],
    "multi_document": [
        "Compare policy obligations with technical implementation details.",
        "How do governance controls map to deployment runbooks?",
        "Which operational actions satisfy security policy requirements?",
    ],
    "ambiguous": [
        "What is the default setting?",
        "How should this be configured?",
        "What does the platform recommend here?",
    ],
    "long_context": [
        "Summarize all controls relevant to security, privacy, retention, and incident response with constraints.",
        "Give a comprehensive cross-document explanation of reliability and recovery strategy.",
        "Provide a detailed answer connecting architecture rationale to release behavior changes.",
    ],
    "technical_doc": [
        "What API parameters control authentication behavior?",
        "Which implementation examples show retry and timeout configuration?",
        "How is request validation enforced in gateway flows?",
    ],
}


def _expected_for(doc_idx: int, scenario: str) -> tuple[str, int, str]:
    file_name, _, _, page, chunk_id = DOCS[doc_idx]
    # conflicting and multi-doc intentionally point to adjacent docs too.
    if scenario in {"conflicting_documents", "multi_document"}:
        alt = DOCS[(doc_idx + 1) % len(DOCS)]
        return alt[0], alt[3], alt[4]
    return file_name, page, chunk_id


def _document_id_for(source_doc: str) -> str:
    return Path(source_doc).stem


def build_corpus(min_queries: int = 300) -> list[dict]:
    rows: list[dict] = []
    qid = 0
    while len(rows) < min_queries:
        for doc_idx, doc in enumerate(DOCS):
            for scenario in SCENARIOS:
                for template in TEMPLATES[scenario]:
                    src_doc, page, chunk_id = _expected_for(doc_idx, scenario)
                    row = {
                        "dataset_version": "enterprise-v11-gold-300",
                        "query_id": f"q{qid:04d}",
                        "scenario": scenario,
                        "category": "enterprise",
                        "source_doc": src_doc,
                        "document_filter": _document_id_for(src_doc),
                        "query": template,
                        "expected_pages": [page],
                        "expected_chunk_ids": [chunk_id],
                        "k": 20,
                    }
                    rows.append(row)
                    qid += 1
                    if len(rows) >= min_queries:
                        return rows
    return rows


def main() -> None:
    path = Path("tests/evaluation/retrieval_eval_corpus_v11.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    corpus = build_corpus(min_queries=320)
    path.write_text(json.dumps(corpus, indent=2), encoding="utf-8")
    print(f"Wrote {len(corpus)} queries to {path}")


if __name__ == "__main__":
    main()

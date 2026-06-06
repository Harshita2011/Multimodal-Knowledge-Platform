from sqlalchemy import text

from app.api.dependencies import get_embedding_service, get_lexical_repository, get_vector_repository
from app.models.domain.entities import ChunkMetadata, DocumentChunk
from app.rag.scopes import BENCHMARK_RETRIEVAL_USER_ID
from app.utils.time import utc_now

DOCS = [
    (
        "security_policy_v2",
        "security_policy_v2.pdf",
        12,
        "security_policy_v2_p12_c3",
        "policy",
        "Privileged access requires MFA, SSO-backed identity checks, least-privilege authorization, approval workflows, and audited admin actions. Sensitive data at rest is protected with encryption, managed keys, secret rotation, and restricted operator access. Reliability controls define outage resiliency, recovery priorities, and uptime commitments. The policy also governs production LLM usage with human review, grounding requirements, prompt safety controls, and compliance evidence.",
        ["MFA", "SSO", "API", "LLM", "encryption", "compliance", "privileged access"],
    ),
    (
        "incident_response_runbook",
        "incident_response_runbook.pdf",
        8,
        "incident_response_runbook_p8_c1",
        "manual",
        "The incident response runbook defines detection, triage, escalation, containment, recovery, and post-incident review. It specifies reliability actions for outages, service restoration priorities, rollback criteria, communication SLAs, and operational safeguards for privileged responders. Evidence handling, encryption of artifacts, and access controls protect sensitive data during investigations.",
        ["SLA", "outage", "recovery", "incident", "encryption", "privileged access"],
    ),
    (
        "kubernetes_ops_manual",
        "kubernetes_ops_manual.pdf",
        14,
        "kubernetes_ops_manual_p14_c2",
        "technical_doc",
        "The Kubernetes operations manual documents reliability controls including autoscaling, pod disruption budgets, readiness probes, failure domains, backup and restore, and cluster recovery. Authentication and authorization are enforced for admin workflows, and runtime hardening covers secrets, encryption, and resilient outage handling for production services.",
        ["kubernetes", "k8s", "autoscaling", "pod disruption budget", "reliability", "secrets"],
    ),
    (
        "javascript_platform_guide",
        "javascript_platform_guide.pdf",
        5,
        "javascript_platform_guide_p5_c0",
        "technical_doc",
        "The JavaScript platform guide covers runtime security, package governance, secure defaults, request validation, API authentication, retry and timeout standards, and frontend reliability practices. It explains how JS services integrate with SSO, enforce MFA for admin tooling, and protect data with encryption and compliance controls.",
        ["javascript", "js", "runtime security", "API", "SSO", "MFA", "retry", "timeout"],
    ),
    (
        "llm_governance_framework",
        "llm_governance_framework.pdf",
        9,
        "llm_governance_framework_p9_c1",
        "policy",
        "The LLM governance framework requires policy-based prompting, approved model usage, output grounding, citation accuracy, human review for high-risk tasks, and production safety controls. It maps model behavior to privacy, retention, incident response, authentication, and compliance obligations for enterprise deployment.",
        ["LLM", "model governance", "grounding", "citation", "privacy", "compliance"],
    ),
    (
        "api_gateway_reference",
        "api_gateway_reference.pdf",
        7,
        "api_gateway_reference_p7_c2",
        "technical_doc",
        "The API gateway reference documents authentication parameters, authorization checks, SSO integration, request validation, timeout configuration, retry backoff, circuit breaker settings, and gateway routing controls. Implementation examples show how API behavior is enforced in production with secure defaults and audited admin workflows.",
        ["API gateway", "authentication", "authorization", "timeout", "retry", "circuit breaker", "SSO"],
    ),
    (
        "data_retention_policy",
        "data_retention_policy.pdf",
        3,
        "data_retention_policy_p3_c0",
        "policy",
        "The data retention policy defines retention schedules, deletion workflows, legal hold exceptions, privacy controls, encryption requirements, and audit evidence. It reconciles conflicting retention periods across systems and explains how sensitive data handling aligns with security and compliance obligations.",
        ["retention", "deletion", "privacy", "legal hold", "encryption", "compliance"],
    ),
    (
        "privacy_impact_assessment",
        "privacy_impact_assessment.pdf",
        6,
        "privacy_impact_assessment_p6_c2",
        "policy",
        "The privacy impact assessment describes PII handling, data minimization, consent boundaries, encryption, access restrictions, retention constraints, and cross-functional review steps. It connects privacy controls to incident response, security safeguards, and operational governance for production systems.",
        ["privacy", "PII", "data minimization", "consent", "retention", "incident response"],
    ),
    (
        "release_notes_v1_v2",
        "release_notes_v1_v2.pdf",
        10,
        "release_notes_v1_v2_p10_c1",
        "technical_doc",
        "The release notes compare versions, highlight fixes, identify deprecation timelines, and explain changes to timeout behavior, retry defaults, authentication flows, and reliability improvements. They clarify disagreements between versions and summarize rollout impacts for security, operations, and platform teams.",
        ["release notes", "deprecation", "timeout", "retry", "authentication", "reliability"],
    ),
    (
        "architecture_decisions_log",
        "architecture_decisions_log.pdf",
        4,
        "architecture_decisions_log_p4_c1",
        "wiki",
        "The architecture decisions log records design tradeoffs, operational constraints, security rationale, reliability patterns, retention implications, and governance decisions. It links architecture choices to deployment runbooks, release behavior, privacy requirements, and implementation guidance for APIs and platform controls.",
        ["architecture", "tradeoffs", "runbook", "release", "privacy", "API", "governance"],
    ),
]


def main() -> None:
    embeddings = get_embedding_service()
    vectors = get_vector_repository()
    lexical = get_lexical_repository()
    engine = lexical.engine
    now = utc_now()
    chunks: list[DocumentChunk] = []

    with engine.begin() as conn:
        owner_id = BENCHMARK_RETRIEVAL_USER_ID
        conn.execute(
            text(
                """
                INSERT INTO users (id, email, name, is_active, created_at, updated_at)
                VALUES (:id, :email, :name, TRUE, :created_at, :updated_at)
                ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                name = EXCLUDED.name,
                is_active = EXCLUDED.is_active,
                updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "id": owner_id,
                "email": "benchmark-seed@example.com",
                "name": "Benchmark Seed",
                "created_at": now,
                "updated_at": now,
            },
        )

    for document_id, filename, page_number, chunk_id, doc_type, body, entities in DOCS:
        vectors.delete_document(document_id)
        lexical.delete_document(document_id)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO documents (id, user_id, filename, storage_path, status, page_count, chunk_count, deleted_at, created_at, updated_at)
                    VALUES (:id, :user_id, :filename, :storage_path, 'ingested', :page_count, :chunk_count, NULL, :created_at, :updated_at)
                    ON CONFLICT (id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    filename = EXCLUDED.filename,
                    storage_path = EXCLUDED.storage_path,
                    status = EXCLUDED.status,
                    page_count = EXCLUDED.page_count,
                    chunk_count = EXCLUDED.chunk_count,
                    deleted_at = NULL,
                    updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "id": document_id,
                    "user_id": owner_id,
                    "filename": filename,
                    "storage_path": f"{document_id}_{filename}",
                    "page_count": page_number,
                    "chunk_count": 1,
                    "created_at": now,
                    "updated_at": now,
                },
            )
        metadata = ChunkMetadata(
            document_id=document_id,
            filename=filename,
            page_number=page_number,
            chunk_id=chunk_id,
            ingestion_timestamp=now,
            owner_user_id=owner_id,
            workspace_id=owner_id,
            doc_type=doc_type,
            section_path="benchmark_seed",
            heading="benchmark_seed",
            entities=entities,
        )
        chunks.append(
            DocumentChunk(
                chunk_id=chunk_id,
                document_id=document_id,
                page_number=page_number,
                text=body,
                metadata=metadata,
            )
        )

    lexical.upsert_chunks(chunks)
    vector_embeddings = embeddings.embed_texts([chunk.text for chunk in chunks])
    vectors.upsert_chunks(chunks, vector_embeddings)
    print(f"Seeded {len(chunks)} benchmark chunks.")


if __name__ == "__main__":
    main()

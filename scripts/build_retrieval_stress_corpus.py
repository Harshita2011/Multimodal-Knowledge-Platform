import json
from pathlib import Path

DOC_TYPES = [
    "policy",
    "manual",
    "technical_doc",
    "wiki",
    "contract",
    "research_paper",
    "meeting_notes",
    "presentation",
]

DOC_EXTENSIONS = {
    "policy": "pdf",
    "manual": "pdf",
    "technical_doc": "pdf",
    "wiki": "docx",
    "contract": "pdf",
    "research_paper": "pdf",
    "meeting_notes": "docx",
    "presentation": "pptx",
}


def _chunk_id(document_id: str, page_number: int, chunk_index: int) -> str:
    return f"{document_id}_p{page_number}_c{chunk_index}"


def _chunk(document_id: str, page_number: int, chunk_index: int, text: str, heading: str, entities: list[str] | None = None) -> dict:
    return {
        "chunk_id": _chunk_id(document_id, page_number, chunk_index),
        "page_number": page_number,
        "chunk_index": chunk_index,
        "heading": heading,
        "section_path": heading,
        "text": text,
        "entities": entities or [],
    }


def _document(document_id: str, doc_type: str, title: str, chunks: list[dict]) -> dict:
    return {
        "document_id": document_id,
        "filename": f"{document_id}.{DOC_EXTENSIONS[doc_type]}",
        "doc_type": doc_type,
        "title": title,
        "page_count": max(chunk["page_number"] for chunk in chunks),
        "chunks": chunks,
    }


def _query(
    query_id: str,
    query: str,
    category: str,
    expected_strategy: str,
    gold_chunk_ids: list[str],
    gold_document_ids: list[str],
    k: int = 20,
) -> dict:
    return {
        "query_id": query_id,
        "query": query,
        "retrieval_category": category,
        "expected_strategy": expected_strategy,
        "gold_chunk_ids": gold_chunk_ids,
        "gold_document_ids": gold_document_ids,
        "k": k,
    }


def _bm25_documents() -> tuple[list[dict], list[dict]]:
    documents: list[dict] = []
    queries: list[dict] = []
    for i in range(16):
        code = f"QPX-{401 + i}"
        acronym = f"CPJ{i:02d}"
        marker = f"SIGIL{i:02d}"
        document_id = f"bm25_exact_{i:02d}"
        glossary_id = f"bm25_glossary_{i:02d}"
        distractor_id = f"bm25_semantic_{i:02d}"
        doc_type = DOC_TYPES[i % len(DOC_TYPES)]
        gold = _chunk(
            document_id,
            4,
            0,
            (
                f"Control bulletin {code} defines cold-path journaling, escrow nonce rotation, and tenant failback ordering. "
                f"Operators must apply safeguard {acronym} when the {code} bulletin appears in storage ledgers."
            ),
            "Exact Terminology",
        )
        glossary = _chunk(
            glossary_id,
            2,
            0,
            (
                f"{code} {acronym} {marker} cold-path journaling escrow nonce rotation tenant failback ordering exact lookup glossary terms."
            ),
            "Glossary",
        )
        chunks = [
            _chunk(
                document_id,
                1,
                0,
                "This handbook reviews storage safeguards, ledger hygiene, and fallback procedures for operators.",
                "Overview",
            ),
            gold,
            _chunk(
                document_id,
                5,
                0,
                (
                    f"Nearby bulletins discuss journaling and nonce rotation but reference alternate controls QPX-{901 + i} and ALT{i:02d}."
                ),
                "Adjacent Controls",
                entities=[f"QPX-{901 + i}", f"ALT{i:02d}"],
            ),
        ]
        documents.extend(
            [
                _document(document_id, doc_type, f"BM25 Exact Control {code}", chunks),
                _document(glossary_id, DOC_TYPES[(i + 1) % len(DOC_TYPES)], f"BM25 Glossary {code}", [_chunk(glossary_id, 1, 0, "Storage glossary overview.", "Overview"), glossary]),
                _document(
                    distractor_id,
                    DOC_TYPES[(i + 2) % len(DOC_TYPES)],
                    f"BM25 Semantic Distractor {code}",
                    [
                        _chunk(
                            distractor_id,
                            3,
                            0,
                            "This note covers storage safeguards, journaling behavior, failback ordering, and operator procedures without the exact bulletin labels.",
                            "Semantic Neighbor",
                        )
                    ],
                ),
            ]
        )
        prompts = [
            f"What does {code} specify for cold-path journaling {marker}?",
            f"{acronym} {marker} escrow nonce rotation guidance",
            f"exact keyword lookup {code} {acronym} {marker}",
            f"Find bulletin {code} {marker} failback ordering",
        ]
        for j, prompt in enumerate(prompts):
            queries.append(
                _query(
                    f"bm25_{i:02d}_{j}",
                    prompt,
                    "BM25-Dominant",
                    "vector_bm25",
                    [gold["chunk_id"], glossary["chunk_id"]],
                    [document_id, glossary_id],
                )
            )
    return documents, queries


def _dense_documents() -> tuple[list[dict], list[dict]]:
    documents: list[dict] = []
    queries: list[dict] = []
    scenarios = [
        (
            "regional instability",
            "cut hands-on rescue work before an availability zone starts wobbling",
            "prewarm standby execution paths before regional instability so operators avoid manual recovery work",
            "manual rescue work in unstable regions should be audited after the event instead of reduced before it",
        ),
        (
            "identity misuse",
            "reduce the chance that a stolen session can act like a real employee",
            "bind each session to device posture and rotating proof keys so hijacked identities lose useful privileges quickly",
            "employee sessions are reviewed monthly for awareness training and policy reminders",
        ),
        (
            "model overreach",
            "keep generated answers from wandering outside policy boundaries",
            "constrain model output with grounded evidence windows and reviewer checkpoints to keep responses inside policy",
            "policy boundaries are explained to business stakeholders during quarterly reviews",
        ),
        (
            "release fatigue",
            "lower customer pain when a rollout starts degrading quietly",
            "stage traffic through shadow canaries and progressive rollback triggers to soften silent release regressions",
            "quiet degradation should be noted in release retrospectives and communication plans",
        ),
    ]
    for i in range(16):
        instability, query_phrase, target_phrase, distractor_phrase = scenarios[i % len(scenarios)]
        document_id = f"dense_semantic_{i:02d}"
        doc_type = DOC_TYPES[(i + 1) % len(DOC_TYPES)]
        gold = _chunk(
            document_id,
            3,
            1,
            (
                f"This design note explains how to {target_phrase}. The approach is used when {instability} threatens service continuity."
            ),
            "Semantic Guidance",
        )
        chunks = [
            _chunk(document_id, 1, 0, "This note discusses resilience planning, staff drills, and service continuity review practices.", "Summary"),
            gold,
            _chunk(document_id, 4, 0, distractor_phrase, "Lexical Distractor"),
        ]
        documents.append(_document(document_id, doc_type, f"Dense Scenario {i:02d}", chunks))
        prompts = [
            f"How do we {query_phrase}?",
            f"What approach helps when {instability} begins and we want to {query_phrase}?",
            f"Which practice is recommended to {query_phrase}?",
            f"Describe the method used to {query_phrase}.",
        ]
        for j, prompt in enumerate(prompts):
            queries.append(_query(f"dense_{i:02d}_{j}", prompt, "Dense-Dominant", "vector_only", [gold["chunk_id"]], [document_id]))
    return documents, queries


def _entity_documents() -> tuple[list[dict], list[dict]]:
    documents: list[dict] = []
    queries: list[dict] = []
    families = [
        (
            "k8s",
            "kubernetes",
            "The cluster resilience standard requires disruption budgets, surge pools, drain rehearsals, and node quarantine before maintenance.",
            [
                "Which k8s safeguard limits voluntary outages during maintenance?",
                "k8s upgrade outage guardrail",
                "How does the k8s standard avoid drain-related downtime?",
                "k8s disruption budget guidance",
            ],
        ),
        (
            "js",
            "javascript",
            "The browser runtime standard requires dependency pinning, origin isolation, package review, and signed release manifests before deployment.",
            [
                "How does the JS runtime prevent dependency drift?",
                "JS package review control",
                "Which JS safeguard enforces signed release manifests?",
                "js origin isolation requirement",
            ],
        ),
        (
            "llm",
            "large language model",
            "The model governance program requires evidence-grounded responses, prompt risk scoring, approval for high-risk use, and post-release audit review.",
            [
                "How does the LLM program keep risky responses grounded?",
                "LLM approval control for high-risk use",
                "Which LLM safeguard requires audit review?",
                "llm evidence grounding rule",
            ],
        ),
    ]
    for i in range(16):
        alias, canonical, text, prompts = families[i % len(families)]
        document_id = f"entity_alias_{i:02d}"
        doc_type = DOC_TYPES[(i + 2) % len(DOC_TYPES)]
        gold = _chunk(document_id, 2, 0, text, "Alias Resolution", entities=[canonical])
        chunks = [
            _chunk(document_id, 1, 0, "This standard outlines controls for operations, approvals, and evidence tracking.", "Context"),
            gold,
            _chunk(document_id, 4, 0, "A neighboring guideline discusses reviews and approvals for unrelated tooling.", "Distractor"),
        ]
        documents.append(_document(document_id, doc_type, f"Entity Alias {canonical.title()} {i:02d}", chunks))
        for j, prompt in enumerate(prompts):
            queries.append(_query(f"entity_{i:02d}_{j}", prompt, "Entity-Dominant", "vector_entity", [gold["chunk_id"]], [document_id]))
    return documents, queries


def _hybrid_documents() -> tuple[list[dict], list[dict]]:
    documents: list[dict] = []
    queries: list[dict] = []
    for i in range(8):
        code = f"HBX-{510 + i}"
        marker = f"MERGE{i:02d}"
        document_id = f"hybrid_target_{i:02d}"
        lexical_doc_id = f"hybrid_lexical_{i:02d}"
        semantic_doc_id = f"hybrid_semantic_{i:02d}"
        entity_doc_id = f"hybrid_entity_{i:02d}"
        alias = ["k8s", "js", "llm"][i % 3]
        canonical = "kubernetes" if alias == "k8s" else "javascript" if alias == "js" else "large language model"
        doc_type = DOC_TYPES[(i + 3) % len(DOC_TYPES)]
        gold = _chunk(
            document_id,
            6,
            1,
            (
                f"Control {code} prevents half-configured sessions during staged rollouts by verifying cookie hydration before traffic shifts "
                "and pausing exposure when state divergence appears."
            ),
            "Hybrid Answer",
            entities=[code],
        )
        lexical_only = _chunk(
            lexical_doc_id,
            2,
            0,
            f"{code} {marker} cookie-hydration staged-exposure state-divergence lexical appendix entry.",
            "Glossary Entry",
            entities=[code],
        )
        semantic_only = _chunk(
            semantic_doc_id,
            5,
            0,
            "To avoid exposing users to partially initialized sessions during canary rollouts, verify cookie hydration before shifting traffic.",
            "Semantic Mirror",
        )
        entity_only = _chunk(
            entity_doc_id,
            4,
            0,
            "Platform rollout governance requires workload-specific release gates and evidence review before exposure moves forward.",
            "Entity Mirror",
            entities=[canonical],
        )
        documents.extend(
            [
                _document(document_id, doc_type, f"Hybrid Target {code}", [_chunk(document_id, 1, 0, "Release controls and session safety overview.", "Overview"), gold]),
                _document(lexical_doc_id, DOC_TYPES[(i + 4) % len(DOC_TYPES)], f"Hybrid Lexical {code}", [_chunk(lexical_doc_id, 1, 0, "Approval routing overview.", "Summary"), lexical_only]),
                _document(semantic_doc_id, DOC_TYPES[(i + 5) % len(DOC_TYPES)], f"Hybrid Semantic {code}", [_chunk(semantic_doc_id, 1, 0, "Canary release safety overview.", "Summary"), semantic_only]),
                _document(entity_doc_id, DOC_TYPES[(i + 6) % len(DOC_TYPES)], f"Hybrid Entity {code}", [_chunk(entity_doc_id, 1, 0, "Workload-specific rollout overview.", "Summary"), entity_only]),
            ]
        )
        prompts = [
            f"How does {code} {marker} keep {alias} canary releases from exposing users to half-configured sessions?",
            f"{code} {alias} {marker} cookie hydration rollout safeguard",
            f"Which control avoids partially initialized sessions during staged exposure for {code} {marker} on {alias} workloads?",
            f"Find the rollout rule behind {code} {marker} state divergence protection for {alias}.",
            f"Explain how {code} {marker} stops users from seeing incomplete session state during {alias} traffic shifts.",
            f"{code} {alias} {marker} staged rollout session safety",
            f"What rollout safety practice is paired with {code} {marker} to verify cookie hydration on {alias} workloads?",
            f"{code} {marker} pause exposure when session state diverges for {alias}",
        ]
        for j, prompt in enumerate(prompts):
            queries.append(
                _query(
                    f"hybrid_{i:02d}_{j}",
                    prompt,
                    "Hybrid-Dominant",
                    "vector_bm25_entity_rrf",
                    [lexical_only["chunk_id"], semantic_only["chunk_id"], entity_only["chunk_id"]],
                    [lexical_doc_id, semantic_doc_id, entity_doc_id],
                )
            )
    return documents, queries


def _multihop_documents() -> tuple[list[dict], list[dict]]:
    documents: list[dict] = []
    queries: list[dict] = []
    for i in range(8):
        control = f"MP-{620 + i}"
        alias = ["k8s", "js", "llm"][i % 3]
        policy_doc = f"multihop_policy_{i:02d}"
        runbook_doc = f"multihop_runbook_{i:02d}"
        policy_chunk = _chunk(
            policy_doc,
            3,
            0,
            f"Policy control {control} requires limiting blast radius during privileged maintenance and documenting approval checkpoints.",
            "Policy Obligation",
            entities=[control],
        )
        runbook_chunk = _chunk(
            runbook_doc,
            7,
            1,
            (
                f"The operations playbook uses {alias}-specific surge pools, disruption budgets, and rollback rehearsals to limit restart storms "
                "during maintenance."
            ),
            "Execution Steps",
            entities=["kubernetes" if alias == "k8s" else "javascript" if alias == "js" else "large language model"],
        )
        documents.extend(
            [
                _document(policy_doc, DOC_TYPES[(i + 1) % len(DOC_TYPES)], f"Multi-Hop Policy {control}", [_chunk(policy_doc, 1, 0, "Maintenance control overview.", "Summary"), policy_chunk]),
                _document(runbook_doc, DOC_TYPES[(i + 2) % len(DOC_TYPES)], f"Multi-Hop Runbook {control}", [_chunk(runbook_doc, 1, 0, "Execution overview.", "Summary"), runbook_chunk]),
            ]
        )
        prompts = [
            f"Which operational action satisfies {control} while limiting restart storms during {alias} maintenance?",
            f"Map {control} to the runbook step that reduces restart storms for {alias}.",
            f"How do teams implement {control} in the {alias} playbook?",
            f"What evidence and action pair answer {control} for {alias} maintenance?",
            f"Connect policy {control} with the maintenance step that lowers restart storms in {alias}.",
            f"Which {alias} runbook action fulfills {control}?",
            f"Find the policy-rule and runbook-step pair for {control}.",
            f"How is {control} enforced during {alias} maintenance operations?",
        ]
        gold_chunks = [policy_chunk["chunk_id"], runbook_chunk["chunk_id"]]
        gold_docs = [policy_doc, runbook_doc]
        for j, prompt in enumerate(prompts):
            queries.append(_query(f"multihop_{i:02d}_{j}", prompt, "Multi-Hop", "vector_bm25_entity_rrf", gold_chunks, gold_docs))
    return documents, queries


def _ambiguous_documents() -> tuple[list[dict], list[dict]]:
    documents: list[dict] = []
    queries: list[dict] = []
    for i in range(8):
        version_a = f"2026.{i + 1}"
        version_b = f"2027.{i + 1}"
        doc_a = f"ambiguous_left_{i:02d}"
        doc_b = f"ambiguous_right_{i:02d}"
        chunk_a = _chunk(
            doc_a,
            5,
            0,
            f"Edition {version_a} sets the authentication grace window to {14 + i} minutes for roaming administrators.",
            "Edition A",
            entities=[version_a],
        )
        chunk_b = _chunk(
            doc_b,
            5,
            0,
            f"Edition {version_b} sets the authentication grace window to {21 + i} minutes for roaming administrators.",
            "Edition B",
            entities=[version_b],
        )
        documents.extend(
            [
                _document(doc_a, DOC_TYPES[(i + 2) % len(DOC_TYPES)], f"Ambiguous Edition {version_a}", [_chunk(doc_a, 1, 0, "Authentication roaming overview.", "Summary"), chunk_a]),
                _document(doc_b, DOC_TYPES[(i + 3) % len(DOC_TYPES)], f"Ambiguous Edition {version_b}", [_chunk(doc_b, 1, 0, "Authentication roaming overview.", "Summary"), chunk_b]),
            ]
        )
        prompts = [
            f"In version {version_a}, what is the roaming admin grace period?",
            f"Which grace window belongs to release {version_a}?",
            f"Find the authentication grace period for edition {version_a}.",
            f"Version {version_a} roaming administrator timeout",
        ]
        for j, prompt in enumerate(prompts):
            queries.append(_query(f"ambiguous_{i:02d}_{j}", prompt, "Ambiguous Queries", "vector_bm25", [chunk_a["chunk_id"]], [doc_a]))
        prompts_b = [
            f"In version {version_b}, what is the roaming admin grace period?",
            f"Which grace window belongs to release {version_b}?",
            f"Find the authentication grace period for edition {version_b}.",
            f"Version {version_b} roaming administrator timeout",
        ]
        for j, prompt in enumerate(prompts_b):
            queries.append(_query(f"ambiguous_{i:02d}_b{j}", prompt, "Ambiguous Queries", "vector_bm25", [chunk_b["chunk_id"]], [doc_b]))
    return documents, queries


def _long_context_documents() -> tuple[list[dict], list[dict]]:
    documents: list[dict] = []
    queries: list[dict] = []
    for i in range(8):
        needle = f"deep escrow checkpoint {730 + i}"
        document_id = f"long_context_{i:02d}"
        doc_type = DOC_TYPES[(i + 4) % len(DOC_TYPES)]
        chunks = []
        for page in range(1, 10):
            heading = f"Long Context Section {page}"
            if page == 9:
                chunks.append(
                    _chunk(
                        document_id,
                        page,
                        0,
                        (
                            f"After many planning sections, the answer appears here: use {needle} to verify delayed escrow recovery before promoting standby writers."
                        ),
                        heading,
                        entities=[needle],
                    )
                )
            else:
                chunks.append(
                    _chunk(
                        document_id,
                        page,
                        0,
                        "This chapter discusses recovery planning, standby writers, escrow routines, and promotion sequencing in broad terms.",
                        heading,
                    )
                )
        documents.append(_document(document_id, doc_type, f"Long Context Playbook {i:02d}", chunks))
        prompts = [
            f"Where is {needle} used before promoting standby writers?",
            f"Find the deep answer for {needle}.",
            "Which checkpoint verifies delayed escrow recovery before standby promotion?",
            f"{needle} standby writer promotion rule",
            f"Locate the answer hidden deep in the document about {needle}.",
            "How is delayed escrow recovery verified before promotion?",
            "Which deep checkpoint appears near the end of the playbook?",
            "What is the escrow recovery checkpoint before standby writers are promoted?",
        ]
        gold_chunk = _chunk_id(document_id, 9, 0)
        for j, prompt in enumerate(prompts):
            queries.append(_query(f"long_{i:02d}_{j}", prompt, "Long Context", "vector_bm25", [gold_chunk], [document_id]))
    return documents, queries


def _noisy_documents() -> tuple[list[dict], list[dict]]:
    documents: list[dict] = []
    queries: list[dict] = []
    for i in range(8):
        alias = ["k8s", "js", "llm"][i % 3]
        canonical = "kubernetes" if alias == "k8s" else "javascript" if alias == "js" else "large language model"
        control = f"NOISE-{810 + i}"
        document_id = f"noisy_doc_{i:02d}"
        doc_type = DOC_TYPES[(i + 5) % len(DOC_TYPES)]
        chunks = [
            _chunk(document_id, 1, 0, "Sc4nned t3xt: mainten4nce contr0ls ar3 listed with dup1icate headers and brok3n spacing.", "OCR Noise"),
            _chunk(document_id, 2, 0, "Duplicate section duplicate section duplicate section with little actionable guidance.", "Duplicate"),
            _chunk(document_id, 3, 0, "Irrelevant appendix on cafeteria seating and projector booking.", "Irrelevant"),
            _chunk(
                document_id,
                4,
                0,
                (
                    f"Control {control} requires {canonical} workloads to verify rollback evidence, preserve grounded audit notes, and reject noisy state before release promotion."
                ),
                "Clean Finding",
                entities=[canonical, control],
            ),
        ]
        documents.append(_document(document_id, doc_type, f"Noisy Source {control}", chunks))
        prompts = [
            f"How does {alias} control {control} reject noisy state before release promotion?",
            f"{alias} rollback evidence rule {control}",
            f"Which safeguard preserves grounded audit notes for {alias} workloads in {control}?",
            f"Find the clean guidance behind noisy source {control}.",
            f"What does {control} require before promoting a {alias} release?",
            f"{control} noisy state rejection for {alias}",
            f"Which rule in {control} preserves audit notes?",
            f"How are releases protected from noisy state in {control}?",
        ]
        gold_chunk = _chunk_id(document_id, 4, 0)
        for j, prompt in enumerate(prompts):
            queries.append(_query(f"noisy_{i:02d}_{j}", prompt, "Noisy Documents", "vector_bm25_entity_rrf", [gold_chunk], [document_id]))
    return documents, queries


def build_manifest() -> dict:
    documents: list[dict] = []
    queries: list[dict] = []
    builders = [
        _bm25_documents,
        _dense_documents,
        _entity_documents,
        _hybrid_documents,
        _multihop_documents,
        _ambiguous_documents,
        _long_context_documents,
        _noisy_documents,
    ]
    for builder in builders:
        docs, qs = builder()
        documents.extend(docs)
        queries.extend(qs)
    return {
        "dataset_version": "retrieval-stress-v1",
        "document_count": len(documents),
        "query_count": len(queries),
        "documents": documents,
        "queries": queries,
    }


def main() -> None:
    output = Path("tests/evaluation/retrieval_stress_manifest.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {manifest['document_count']} documents and {manifest['query_count']} queries to {output}")


if __name__ == "__main__":
    main()

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from sqlalchemy import create_engine, text

from app.api.dependencies import (
    get_embedding_service,
    get_lexical_repository,
    get_retrieval_cache,
    get_vector_repository,
)
from app.core.settings import get_settings
from app.db.postgres.session import normalize_sync_database_url
from scripts.audit_corpus import (
    _load_documents,
    _load_chunk_rows,
    audit_corpus,
    backfill_chroma_ownership_metadata,
    reindex_stale_documents,
    _write_report,
    CorpusAuditSummary,
    _load_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair the retrieval corpus explicitly")
    parser.add_argument("--report-json", default="reports/corpus_audit.json")
    parser.add_argument("--report-markdown", default="reports/corpus_audit.md")
    args = parser.parse_args()

    settings = get_settings()
    engine = create_engine(normalize_sync_database_url(settings.database_url), future=True)
    collection_repo = get_vector_repository()
    lexical_repository = get_lexical_repository()
    retrieval_cache = get_retrieval_cache()
    embeddings = get_embedding_service()

    print("Step 1: Auditing current corpus...")
    documents = _load_documents(engine)
    chunk_rows = _load_chunk_rows(engine)
    audit_rows, summary = audit_corpus(collection_repo.collection, documents, chunk_rows, settings.pdf_storage_dir)

    print("Step 2: Repairing legacy Chroma metadata (backfilling ownership)...")
    changed_documents, updated_rows = backfill_chroma_ownership_metadata(collection_repo.collection, documents)
    print(f"  - Repaired Chroma metadata for {len(changed_documents)} documents ({updated_rows} chunk rows).")

    print("Step 2b: Repairing PostgreSQL chunks metadata (backfilling ownership)...")
    pg_updated_docs = 0
    pg_updated_chunks = 0
    with engine.begin() as conn:
        for doc in documents:
            user_id = doc.get("user_id") or "anonymous"
            workspace_id = user_id
            rows = conn.execute(
                text("SELECT chunk_id, metadata_json FROM chunks WHERE document_id = :doc_id"),
                {"doc_id": doc["id"]}
            ).mappings().all()

            doc_changed = False
            for row in rows:
                md = _load_json(row["metadata_json"])
                changed = False
                if not md.get("owner_user_id"):
                    md["owner_user_id"] = user_id
                    changed = True
                if not md.get("workspace_id"):
                    md["workspace_id"] = workspace_id
                    changed = True

                if changed:
                    conn.execute(
                        text("UPDATE chunks SET metadata_json = :md_json WHERE chunk_id = :cid AND document_id = :doc_id"),
                        {
                            "md_json": json.dumps(md),
                            "cid": row["chunk_id"],
                            "doc_id": doc["id"]
                        }
                    )
                    pg_updated_chunks += 1
                    doc_changed = True
            if doc_changed:
                pg_updated_docs += 1
                if doc["id"] not in changed_documents:
                    changed_documents.append(doc["id"])
    print(f"  - Repaired PostgreSQL chunks for {pg_updated_docs} documents ({pg_updated_chunks} chunk rows).")

    print("Step 3: Reindexing stale documents (if source files exist)...")
    repaired_documents = reindex_stale_documents(
        documents=documents,
        audit_rows=audit_rows,
        collection=collection_repo.collection,
        lexical_repository=lexical_repository,
        embeddings=embeddings,
        retrieval_cache=retrieval_cache,
        storage_dir=settings.pdf_storage_dir,
    )
    print(f"  - Reindexed {len(repaired_documents)} documents.")

    print("Step 4: Running final audit after repairs...")
    documents = _load_documents(engine)
    chunk_rows = _load_chunk_rows(engine)
    audit_rows, summary = audit_corpus(collection_repo.collection, documents, chunk_rows, settings.pdf_storage_dir)

    summary = CorpusAuditSummary(
        documents_scanned=summary.documents_scanned,
        documents_needing_reindex=summary.documents_needing_reindex,
        documents_repaired_metadata=len(changed_documents),
        documents_reindexed=len(repaired_documents),
        missing_sources=summary.missing_sources,
        ownership_coverage_rate=summary.ownership_coverage_rate,
        vector_coverage_rate=summary.vector_coverage_rate,
    )

    report_payload = {
        "summary": asdict(summary),
        "repaired_metadata_documents": changed_documents,
        "repaired_metadata_rows": updated_rows,
        "reindexed_documents": repaired_documents,
        "documents": [asdict(row) for row in audit_rows],
    }
    Path(args.report_json).write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
    _write_report(Path(args.report_markdown), audit_rows, summary, repaired_documents)
    print("\nFinal Audit Summary after Repair:")
    print(json.dumps(report_payload["summary"], indent=2))


if __name__ == "__main__":
    main()

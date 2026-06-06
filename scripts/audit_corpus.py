from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from app.api.dependencies import (
    get_embedding_service,
    get_lexical_repository,
    get_retrieval_cache,
    get_vector_repository,
)
from app.core.settings import get_settings
from app.db.postgres.repositories.auth_repo import UserPgRepository
from app.ingestion.chunker import PDFChunker
from app.ingestion.parser import PDFParser
from app.rag.retrieval_cache import RetrievalCache
from app.db.postgres.session import normalize_sync_database_url


@dataclass(slots=True)
class CorpusDocumentAudit:
    document_id: str
    filename: str
    user_id: str | None
    status: str
    storage_path: str
    db_chunk_count: int
    vector_count: int
    missing_embeddings: int
    ownership_missing: bool
    source_exists: bool
    stale_reasons: list[str]


@dataclass(slots=True)
class CorpusAuditSummary:
    documents_scanned: int
    documents_needing_reindex: int
    documents_repaired_metadata: int
    documents_reindexed: int
    missing_sources: int
    ownership_coverage_rate: float
    vector_coverage_rate: float


def _load_json(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def resolve_storage_path(base_dir: Path, storage_path: str) -> Path:
    candidate = Path(storage_path)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    resolved = (base_dir / storage_path).resolve()
    if resolved.exists():
        return resolved
    if candidate.exists():
        return candidate.resolve()
    return resolved


def detect_stale_reasons(
    *,
    status: str,
    db_chunk_count: int,
    vector_count: int,
    missing_embeddings: int,
    ownership_missing: bool,
    source_exists: bool,
) -> list[str]:
    reasons: list[str] = []
    if status != "ingested":
        reasons.append(f"status:{status}")
    if db_chunk_count != vector_count:
        reasons.append("chunk_vector_mismatch")
    if missing_embeddings > 0:
        reasons.append("missing_embeddings")
    if ownership_missing:
        reasons.append("missing_ownership_metadata")
    if not source_exists:
        reasons.append("missing_source_file")
    return reasons


def _flatten_rows(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list) and value and isinstance(value[0], list):
        return list(value[0])
    if isinstance(value, list):
        return list(value)
    return [value]


def _build_storage_root() -> Path:
    return get_settings().pdf_storage_dir


def _load_documents(engine) -> list[dict[str, Any]]:
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, user_id, filename, storage_path, status, chunk_count
                FROM documents
                WHERE deleted_at IS NULL
                ORDER BY created_at ASC, id ASC
                """
            )
        ).mappings().all()
    return [dict(row) for row in rows]


def _load_chunk_rows(engine) -> list[dict[str, Any]]:
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT document_id, metadata_json
                FROM chunks
                ORDER BY document_id ASC, chunk_id ASC
                """
            )
        ).mappings().all()
    return [dict(row) for row in rows]


def _chunk_ownership_missing(chunk_rows: list[dict[str, Any]], document_id: str) -> bool:
    for row in chunk_rows:
        if row["document_id"] != document_id:
            continue
        md = _load_json(row.get("metadata_json"))
        if not md.get("owner_user_id") or not md.get("workspace_id"):
            return True
    return False


def _vector_stats_for_document(collection, document_id: str) -> tuple[list[str], list[dict[str, Any]], int]:
    result = collection.get(where={"document_id": document_id}, include=["metadatas", "embeddings"])
    ids = _flatten_rows(result.get("ids"))
    metadatas = _flatten_rows(result.get("metadatas"))
    embeddings = _flatten_rows(result.get("embeddings"))
    missing_embeddings = sum(1 for embedding in embeddings if embedding is None)
    return [str(item) for item in ids], [dict(item or {}) for item in metadatas], missing_embeddings


def _normalize_chroma_metadata(metadata: dict[str, Any], *, owner_user_id: str, workspace_id: str) -> dict[str, Any]:
    normalized = dict(metadata)
    entities = normalized.get("entities", "")
    if isinstance(entities, (list, tuple, set)):
        normalized["entities"] = ",".join(str(entity).strip() for entity in entities if str(entity).strip())
    elif entities is None:
        normalized["entities"] = ""
    else:
        normalized["entities"] = str(entities)
    normalized["owner_user_id"] = owner_user_id
    normalized["workspace_id"] = workspace_id or owner_user_id
    return normalized


def backfill_chroma_ownership_metadata(collection, documents: list[dict[str, Any]]) -> tuple[list[str], int]:
    changed_documents: list[str] = []
    updated_rows = 0
    for doc in documents:
        user_id = doc.get("user_id") or UserPgRepository.ANONYMOUS_USER_ID
        ids, metadatas, _ = _vector_stats_for_document(collection, doc["id"])
        if not ids:
            continue
        update_ids: list[str] = []
        update_metadatas: list[dict[str, Any]] = []
        for chunk_id, metadata in zip(ids, metadatas, strict=False):
            owner_user_id = metadata.get("owner_user_id") or user_id
            workspace_id = metadata.get("workspace_id") or owner_user_id
            if metadata.get("owner_user_id") == owner_user_id and metadata.get("workspace_id") == workspace_id:
                continue
            merged = _normalize_chroma_metadata(metadata, owner_user_id=owner_user_id, workspace_id=workspace_id)
            update_ids.append(chunk_id)
            update_metadatas.append(merged)
        if update_ids:
            collection.update(ids=update_ids, metadatas=update_metadatas)
            changed_documents.append(doc["id"])
            updated_rows += len(update_ids)
    return changed_documents, updated_rows


def _chunks_for_document(document_chunks: list[dict[str, Any]], document_id: str) -> int:
    return sum(1 for row in document_chunks if row["document_id"] == document_id)


def audit_corpus(collection, documents: list[dict[str, Any]], chunk_rows: list[dict[str, Any]], storage_dir: Path) -> tuple[list[CorpusDocumentAudit], CorpusAuditSummary]:
    records: list[CorpusDocumentAudit] = []
    ownership_covered = 0
    vector_covered = 0
    missing_sources = 0
    stale_documents = 0

    for doc in documents:
        ids, metadatas, missing_embeddings = _vector_stats_for_document(collection, doc["id"])
        vector_count = len(ids)
        db_chunk_count = _chunks_for_document(chunk_rows, doc["id"])
        ownership_missing = _chunk_ownership_missing(chunk_rows, doc["id"]) or any(
            not md.get("owner_user_id") or not md.get("workspace_id") for md in metadatas
        )
        source_exists = resolve_storage_path(storage_dir, doc["storage_path"]).exists()
        stale_reasons = detect_stale_reasons(
            status=doc["status"],
            db_chunk_count=db_chunk_count,
            vector_count=vector_count,
            missing_embeddings=missing_embeddings,
            ownership_missing=ownership_missing,
            source_exists=source_exists,
        )
        if not ownership_missing:
            ownership_covered += 1
        if vector_count == db_chunk_count and vector_count > 0:
            vector_covered += 1
        if not source_exists:
            missing_sources += 1
        if stale_reasons:
            stale_documents += 1
        records.append(
            CorpusDocumentAudit(
                document_id=doc["id"],
                filename=doc["filename"],
                user_id=doc.get("user_id"),
                status=doc["status"],
                storage_path=doc["storage_path"],
                db_chunk_count=db_chunk_count,
                vector_count=vector_count,
                missing_embeddings=missing_embeddings,
                ownership_missing=ownership_missing,
                source_exists=source_exists,
                stale_reasons=stale_reasons,
            )
        )

    summary = CorpusAuditSummary(
        documents_scanned=len(records),
        documents_needing_reindex=stale_documents,
        documents_repaired_metadata=0,
        documents_reindexed=0,
        missing_sources=missing_sources,
        ownership_coverage_rate=(ownership_covered / max(1, len(records))),
        vector_coverage_rate=(vector_covered / max(1, len(records))),
    )
    return records, summary


def reindex_stale_documents(
    *,
    documents: list[dict[str, Any]],
    audit_rows: list[CorpusDocumentAudit],
    collection,
    lexical_repository,
    embeddings,
    retrieval_cache: RetrievalCache,
    storage_dir: Path,
) -> list[str]:
    parser = PDFParser()
    chunker = PDFChunker(chunk_size=get_settings().chunk_size, chunk_overlap=get_settings().chunk_overlap)
    repaired: list[str] = []
    for doc in audit_rows:
        if not doc.stale_reasons:
            continue
        document_row = next(row for row in documents if row["id"] == doc.document_id)
        source_path = resolve_storage_path(storage_dir, document_row["storage_path"])
        if not source_path.exists():
            continue
        owner_id = document_row.get("user_id") or UserPgRepository.ANONYMOUS_USER_ID
        pages = parser.parse_file(source_path, document_row["filename"])
        if not pages:
            continue
        collection.delete(where={"document_id": doc.document_id})
        lexical_repository.delete_document(doc.document_id)
        chunks = chunker.chunk_pages(
            doc.document_id,
            document_row["filename"],
            pages,
            owner_user_id=owner_id,
            workspace_id=owner_id,
        )
        vector_embeddings = embeddings.embed_texts([chunk.text for chunk in chunks])
        lexical_repository.upsert_chunks(chunks)
        collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=vector_embeddings,
            metadatas=[
                _normalize_chroma_metadata(
                    chunk.metadata.model_dump(mode="json"),
                    owner_user_id=owner_id,
                    workspace_id=owner_id,
                )
                for chunk in chunks
            ],
        )
        with lexical_repository.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE documents
                    SET status = 'ingested',
                        page_count = :page_count,
                        chunk_count = :chunk_count,
                        user_id = :user_id
                    WHERE id = :document_id
                    """
                ),
                {
                    "document_id": doc.document_id,
                    "page_count": len(pages),
                    "chunk_count": len(chunks),
                    "user_id": owner_id,
                },
            )
        retrieval_cache.invalidate_document(doc.document_id)
        repaired.append(doc.document_id)
    return repaired


def _write_report(path: Path, records: list[CorpusDocumentAudit], summary: CorpusAuditSummary, repaired_documents: list[str]) -> None:
    lines = [
        "# Corpus Audit",
        "",
        f"- Documents scanned: {summary.documents_scanned}",
        f"- Documents needing reindex: {summary.documents_needing_reindex}",
        f"- Documents repaired metadata: {summary.documents_repaired_metadata}",
        f"- Documents reindexed: {len(repaired_documents)}",
        f"- Missing source files: {summary.missing_sources}",
        f"- Ownership coverage: {summary.ownership_coverage_rate:.2%}",
        f"- Vector coverage: {summary.vector_coverage_rate:.2%}",
        "",
        "## Stale Documents",
    ]
    stale_rows = [record for record in records if record.stale_reasons]
    if stale_rows:
        for row in stale_rows:
            lines.append(
                f"- {row.filename} ({row.document_id}) | reasons={', '.join(row.stale_reasons)} | "
                f"chunks={row.db_chunk_count} | vectors={row.vector_count}"
            )
    else:
        lines.append("- None.")
    lines.append("")
    lines.append("## Reindexed Documents")
    if repaired_documents:
        for doc_id in repaired_documents:
            lines.append(f"- {doc_id}")
    else:
        lines.append("- None.")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the retrieval corpus (Read-Only)")
    parser.add_argument("--report-json", default="reports/corpus_audit.json")
    parser.add_argument("--report-markdown", default="reports/corpus_audit.md")
    args = parser.parse_args()

    settings = get_settings()
    engine = create_engine(normalize_sync_database_url(settings.database_url), future=True)
    collection_repo = get_vector_repository()

    documents = _load_documents(engine)
    chunk_rows = _load_chunk_rows(engine)

    audit_rows, summary = audit_corpus(collection_repo.collection, documents, chunk_rows, settings.pdf_storage_dir)

    report_payload = {
        "summary": asdict(summary),
        "repaired_metadata_documents": [],
        "repaired_metadata_rows": 0,
        "reindexed_documents": [],
        "documents": [asdict(row) for row in audit_rows],
    }
    Path(args.report_json).write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
    _write_report(Path(args.report_markdown), audit_rows, summary, [])
    print(json.dumps(report_payload["summary"], indent=2))


if __name__ == "__main__":
    main()

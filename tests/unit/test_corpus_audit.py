from pathlib import Path

from scripts.audit_corpus import detect_stale_reasons, resolve_storage_path


def test_detect_stale_reasons_reports_missing_ownership_and_mismatch():
    reasons = detect_stale_reasons(
        status="ingesting",
        db_chunk_count=4,
        vector_count=2,
        missing_embeddings=1,
        ownership_missing=True,
        source_exists=False,
    )
    assert "status:ingesting" in reasons
    assert "chunk_vector_mismatch" in reasons
    assert "missing_embeddings" in reasons
    assert "missing_ownership_metadata" in reasons
    assert "missing_source_file" in reasons


def test_resolve_storage_path_prefers_existing_files(tmp_path: Path):
    base_dir = tmp_path / "documents"
    base_dir.mkdir()
    stored = base_dir / "doc_1_resume.pdf"
    stored.write_text("payload", encoding="utf-8")

    resolved = resolve_storage_path(base_dir, "doc_1_resume.pdf")
    assert resolved == stored.resolve()

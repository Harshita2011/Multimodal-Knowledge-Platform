from app.models.domain.entities import ParsedPage
from app.ingestion.chunker import PDFChunker


def test_chunker_generates_stable_ids():
    chunker = PDFChunker(chunk_size=20, chunk_overlap=0)
    pages = [ParsedPage(page_number=1, text="a " * 50)]
    chunks = chunker.chunk_pages("docx", "f.pdf", pages)
    assert chunks[0].chunk_id == "docx_p1_c0"
    assert all(c.metadata.chunk_id == c.chunk_id for c in chunks)


def test_chunker_is_section_aware_for_resume_like_text():
    chunker = PDFChunker(chunk_size=120, chunk_overlap=0)
    text = (
        "Education VIT Integrated M.Tech in Computer Science. "
        "Skills Python FastAPI ChromaDB. "
        "Projects Built a RAG platform with citations."
    )
    pages = [ParsedPage(page_number=1, text=text)]
    chunks = chunker.chunk_pages("resume", "resume.pdf", pages)
    joined = " ".join(c.text for c in chunks).lower()
    assert "education" in joined
    assert "skills" in joined
    assert "projects" in joined

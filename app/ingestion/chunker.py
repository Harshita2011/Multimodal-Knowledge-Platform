import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ingestion.entity_extractor import EntityExtractor
from app.models.domain.entities import ChunkMetadata, DocumentChunk, ParsedPage
from app.rag.query_strategy import detect_doc_type
from app.utils.ids import make_chunk_id
from app.utils.time import utc_now


class PDFChunker:
    _SECTION_PATTERN = re.compile(
        r"\b(Education|Skills|Projects|Experience|Leadership|Activities|Certifications|Summary|Objective)\b",
        re.IGNORECASE,
    )

    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
        self.entity_extractor = EntityExtractor()

    def _source_type(self, filename: str) -> str:
        low = filename.lower()
        if low.endswith(".docx"):
            return "docx"
        if low.endswith(".pptx"):
            return "pptx"
        return "pdf"

    def _heading(self, section: str) -> str:
        line = section.strip().split(":")[0].strip()
        return line[:120]

    def _split_sections(self, text: str) -> list[str]:
        matches = list(self._SECTION_PATTERN.finditer(text))
        if not matches:
            return [text]
        sections: list[str] = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section = text[start:end].strip()
            if section:
                sections.append(section)
        return sections or [text]

    def chunk_pages(self, document_id: str, filename: str, pages: list[ParsedPage]) -> list[DocumentChunk]:
        ts = utc_now()
        chunks: list[DocumentChunk] = []
        source_type = self._source_type(filename)
        doc_type = detect_doc_type(" ".join(p.text for p in pages[:3]), filename=filename)
        for page in pages:
            split: list[str] = []
            sections = self._split_sections(page.text)
            for section in sections:
                split.extend(self.splitter.split_text(section))
            for idx, text in enumerate(split):
                chunk_id = make_chunk_id(document_id, page.page_number, idx)
                section = sections[min(idx, len(sections) - 1)] if sections else ""
                heading = self._heading(section) if section else ""
                entities = self.entity_extractor.extract(text)
                block_type = "heading" if heading and len(text) < 200 else "paragraph"
                md = ChunkMetadata(
                    document_id=document_id,
                    filename=filename,
                    page_number=page.page_number,
                    chunk_id=chunk_id,
                    ingestion_timestamp=ts,
                    source_type=source_type,  # type: ignore[arg-type]
                    modality="text",
                    doc_type=doc_type,  # type: ignore[arg-type]
                    section_path=heading,
                    heading=heading,
                    block_type=block_type,  # type: ignore[arg-type]
                    entities=entities,
                )
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        page_number=page.page_number,
                        text=text,
                        metadata=md,
                    )
                )
        return chunks

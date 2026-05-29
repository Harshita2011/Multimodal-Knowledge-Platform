import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.models.domain.entities import ChunkMetadata, DocumentChunk, ParsedPage
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
        for page in pages:
            split: list[str] = []
            for section in self._split_sections(page.text):
                split.extend(self.splitter.split_text(section))
            for idx, text in enumerate(split):
                chunk_id = make_chunk_id(document_id, page.page_number, idx)
                md = ChunkMetadata(
                    document_id=document_id,
                    filename=filename,
                    page_number=page.page_number,
                    chunk_id=chunk_id,
                    ingestion_timestamp=ts,
                    source_type="pdf",
                    modality="text",
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

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import fitz

from app.core.exceptions import AppError
from app.models.domain.entities import ParsedPage


class PDFParser:
    _MOJIBAKE_MAP = {
        "Â": " ",
        "Ã¯": "i",
        "Ã©": "e",
        "â€¢": "-",
        "â": "-",
        "â": "-",
        "â¢": "-",
        "â€™": "'",
        "â€œ": '"',
        "â€": '"',
        "Â§": " ",
    }

    @classmethod
    def _normalize_text(cls, text: str) -> str:
        cleaned = text
        for bad, good in cls._MOJIBAKE_MAP.items():
            cleaned = cleaned.replace(bad, good)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def parse(self, pdf_path: Path) -> list[ParsedPage]:
        pages: list[ParsedPage] = []
        try:
            doc = fitz.open(pdf_path)
        except Exception as exc:
            raise AppError("pdf_parse_failed", "Unable to open PDF", 422) from exc
        try:
            for i, page in enumerate(doc, start=1):
                raw = page.get_text("text") or page.get_text("blocks")
                text = self._normalize_text(str(raw))
                if not text:
                    continue
                pages.append(ParsedPage(page_number=i, text=text))
        finally:
            doc.close()
        return pages

    def parse_file(self, path: Path, filename: str) -> list[ParsedPage]:
        low = filename.lower()
        if low.endswith(".pdf"):
            return self.parse(path)
        if low.endswith(".docx"):
            return self._parse_docx(path)
        if low.endswith(".pptx"):
            return self._parse_pptx(path)
        raise AppError("unsupported_file_type", "Unsupported file type", 415)

    def _parse_docx(self, file_path: Path) -> list[ParsedPage]:
        try:
            with zipfile.ZipFile(file_path) as zf:
                xml = zf.read("word/document.xml")
        except Exception as exc:
            raise AppError("docx_parse_failed", "Unable to open DOCX", 422) from exc
        root = ET.fromstring(xml)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        parts: list[str] = []
        for para in root.findall(".//w:p", ns):
            runs = [t.text or "" for t in para.findall(".//w:t", ns)]
            line = self._normalize_text(" ".join(runs))
            if line:
                parts.append(line)
        text = "\n".join(parts).strip()
        if not text:
            return []
        return [ParsedPage(page_number=1, text=text)]

    def _parse_pptx(self, file_path: Path) -> list[ParsedPage]:
        try:
            with zipfile.ZipFile(file_path) as zf:
                slide_names = sorted([n for n in zf.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")])
                slides: list[ParsedPage] = []
                for idx, name in enumerate(slide_names, start=1):
                    xml = zf.read(name)
                    root = ET.fromstring(xml)
                    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
                    texts = [t.text or "" for t in root.findall(".//a:t", ns)]
                    content = self._normalize_text(" ".join(texts))
                    if content:
                        slides.append(ParsedPage(page_number=idx, text=content))
                return slides
        except Exception as exc:
            raise AppError("pptx_parse_failed", "Unable to open PPTX", 422) from exc

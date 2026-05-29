from pathlib import Path
import re

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

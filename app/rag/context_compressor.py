import re
from dataclasses import dataclass

from app.models.domain.entities import RetrievedChunk


@dataclass(slots=True)
class CompressionStats:
    input_chunks: int
    output_units: int
    compression_ratio: float


class ContextCompressor:
    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip().lower()

    def compress(self, chunks: list[RetrievedChunk], max_units: int = 10) -> tuple[list[RetrievedChunk], CompressionStats]:
        if not chunks:
            return [], CompressionStats(input_chunks=0, output_units=0, compression_ratio=1.0)
        seen: set[str] = set()
        out: list[RetrievedChunk] = []
        for c in chunks:
            key = f"{c.metadata.document_id}:{c.metadata.page_number}:{self._normalize(c.text)[:250]}"
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
            if len(out) >= max_units:
                break
        ratio = len(out) / max(1, len(chunks))
        return out, CompressionStats(input_chunks=len(chunks), output_units=len(out), compression_ratio=ratio)

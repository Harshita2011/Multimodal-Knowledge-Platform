from app.models.domain.entities import RetrievedChunk


class ChunkDeduplicator:
    def __init__(self, similarity_threshold: float = 0.90):
        self.similarity_threshold = similarity_threshold

    def deduplicate(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        kept: list[RetrievedChunk] = []
        signatures: list[set[str]] = []
        for chunk in chunks:
            sig = self._signature(chunk.text)
            if any(self._jaccard(sig, existing) >= self.similarity_threshold for existing in signatures):
                continue
            kept.append(chunk)
            signatures.append(sig)
        return kept

    @staticmethod
    def _signature(text: str) -> set[str]:
        return set(text.lower().split()[:48])

    @staticmethod
    def _jaccard(a: set[str], b: set[str]) -> float:
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

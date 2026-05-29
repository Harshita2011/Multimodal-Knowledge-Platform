import re

from app.models.domain.entities import Citation, RetrievedChunk


class CitationMapper:
    _sentence_split = re.compile(r"(?<=[.!?])\s+")

    def _snippet(self, text: str, query: str | None = None, limit: int = 250) -> str:
        sentences = self._sentence_split.split(text.strip())
        if not sentences:
            return text[:limit].rsplit(" ", 1)[0]
        if query:
            q_terms = {t for t in re.findall(r"\w+", query.lower()) if len(t) >= 3}
            ranked: list[tuple[float, str]] = []
            for s in sentences:
                terms = {t for t in re.findall(r"\w+", s.lower())}
                overlap = len(terms.intersection(q_terms))
                length_bonus = min(len(s), limit) / max(1, limit)
                penalty = 1.0 if len(terms) < 3 else 0.0
                ranked.append((overlap + length_bonus - penalty, s))
            ranked.sort(key=lambda x: (-x[0], x[1]))
            best = ranked[0][1].strip()
            if best and len(best) <= limit:
                return best
        buf: list[str] = []
        size = 0
        for sentence in sentences:
            if size + len(sentence) + 1 > limit:
                break
            if len(sentence.split()) < 3:
                continue
            buf.append(sentence)
            size += len(sentence) + 1
        if buf:
            return " ".join(buf)
        return text[:limit].rsplit(" ", 1)[0]

    def map(self, chunks: list[RetrievedChunk], query: str | None = None) -> list[Citation]:
        out: list[Citation] = []
        for c in chunks:
            out.append(
                Citation(
                    filename=c.metadata.filename,
                    page_number=c.metadata.page_number,
                    chunk_id=c.chunk_id,
                    snippet=self._snippet(c.text, query=query),
                )
            )
        return out

import re


class EntityExtractor:
    _TECH_HINTS = {"kubernetes", "docker", "python", "fastapi", "postgresql", "chromadb", "tensorflow", "pytorch", "aws", "azure", "gcp"}

    def extract(self, text: str) -> list[str]:
        entities: set[str] = set()
        words = re.findall(r"[A-Za-z][A-Za-z0-9.+-]*", text)
        for idx, token in enumerate(words):
            low = token.lower()
            if low in self._TECH_HINTS:
                entities.add(token)
            if token[:1].isupper() and idx + 1 < len(words) and words[idx + 1][:1].isupper():
                entities.add(f"{token} {words[idx + 1]}")
            if re.match(r"v?\d+\.\d+(\.\d+)?", token):
                entities.add(token)
        return sorted(e for e in entities if len(e) >= 2)[:50]

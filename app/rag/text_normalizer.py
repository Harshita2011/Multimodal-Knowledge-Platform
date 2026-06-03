import re
import unicodedata

_ALIASES = {
    "k8s": "kubernetes",
    "js": "javascript",
    "llm": "large language model",
}


def normalize_query_text(text: str) -> str:
    value = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    value = value.casefold()
    value = re.sub(r"[^a-z0-9\s.-]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def simple_stem(token: str) -> str:
    for suffix in ("ing", "ed", "ly", "es", "s"):
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            return token[: -len(suffix)]
    return token


def expand_aliases(tokens: list[str]) -> list[str]:
    expanded: set[str] = set(tokens)
    for t in tokens:
        if t in _ALIASES:
            expanded.add(_ALIASES[t])
    return sorted(expanded)

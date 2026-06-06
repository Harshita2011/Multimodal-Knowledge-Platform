import re

from app.utils.tokenizer import HeuristicTokenizer

_TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_heuristic = HeuristicTokenizer()


def estimate_token_count(text: str) -> int:
    return _heuristic.count_tokens(text)


def truncate_text_to_tokens(text: str, max_tokens: int) -> str:
    return _heuristic.truncate_to_tokens(text, max_tokens)


def pack_context_by_tokens(texts: list[str], max_tokens: int) -> list[str]:
    used = 0
    out: list[str] = []
    for text in texts:
        if used >= max_tokens:
            break
        text_tokens = estimate_token_count(text)
        if used + text_tokens <= max_tokens:
            out.append(text)
            used += text_tokens
            continue
        remaining = max_tokens - used
        truncated = truncate_text_to_tokens(text, remaining)
        if truncated:
            out.append(truncated)
        break
    return out

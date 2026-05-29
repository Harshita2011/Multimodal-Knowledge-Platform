import logging
import re
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)
_TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class Tokenizer(ABC):
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        raise NotImplementedError


class HeuristicTokenizer(Tokenizer):
    def count_tokens(self, text: str) -> int:
        return len(_TOKEN_PATTERN.findall(text))

    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        if max_tokens <= 0:
            return ""
        sentences = _SENTENCE_SPLIT.split(text.strip())
        kept: list[str] = []
        used = 0
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            if used + sentence_tokens <= max_tokens:
                kept.append(sentence)
                used += sentence_tokens
                continue
            remaining = max_tokens - used
            if remaining <= 0:
                break
            parts = _TOKEN_PATTERN.findall(sentence)
            kept.append("".join(parts[:remaining]))
            break
        return " ".join(p for p in kept if p).strip()


class TiktokenTokenizer(Tokenizer):
    def __init__(self):
        import tiktoken  # optional dependency at runtime

        self._enc = tiktoken.get_encoding("cl100k_base")
        self._heuristic = HeuristicTokenizer()

    def count_tokens(self, text: str) -> int:
        return len(self._enc.encode(text))

    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        # sentence-aware trim first, then exact token trim if needed
        pre = self._heuristic.truncate_to_tokens(text, max_tokens)
        toks = self._enc.encode(pre)
        if len(toks) <= max_tokens:
            return pre
        return self._enc.decode(toks[:max_tokens]).strip()


def build_tokenizer(strict: bool = False) -> Tokenizer:
    try:
        return TiktokenTokenizer()
    except Exception as exc:
        if strict:
            raise RuntimeError("tiktoken is required when TOKENIZER_STRICT=true") from exc
        logger.warning("tiktoken unavailable, using heuristic tokenizer fallback")
        return HeuristicTokenizer()
